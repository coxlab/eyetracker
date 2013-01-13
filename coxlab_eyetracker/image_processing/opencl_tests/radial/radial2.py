#!/usr/bin/env python

import numpy
import pylab
import pyopencl
import pyopencl.array
import scipy.ndimage.filters
import scipy.signal
import pyopencl.array as cla

from coxlab_eyetracker.image_processing.simple_cl_conv import NaiveSeparableCorrelation, Sobel
from coxlab_eyetracker.image_processing.localmem_cl_conv import LocalMemorySeparableCorrelation
from coxlab_eyetracker.image_processing.cl_minmax import MinMaxKernel

from coxlab_eyetracker.image_processing.WovenBackend import WovenBackend
from pyopencl.elementwise import ElementwiseKernel


PROGRAM = """

#pragma extension cl_khr_global_int32_base_atomics : enable

inline void AtomicAdd(volatile __global float* source, const float operand) {
    union {
        unsigned int intVal;
        float floatVal;
    } newVal;
    union {
        unsigned int intVal;
        float floatVal;
    } prevVal;
    do {
        prevVal.floatVal = *source;
        newVal.floatVal = prevVal.floatVal + operand;
    } while (atomic_cmpxchg((volatile __global unsigned int *)source,
        prevVal.intVal, newVal.intVal) != prevVal.intVal);
}

__kernel void calcOM(__global float* m, __global float* x, __global float* y,
    __global float* O, __global float* M, const int radius)
{
    const int ix = get_global_id(1);
    const int iy = get_global_id(0);

    const int width = get_global_size(1);
    const int height = get_global_size(0);

    const int id = ix + iy * width;
    /*
    const int id = iy + ix * height;
    */

    float mv = m[id];
    const float xv = x[id] / mv;
    const float yv = y[id] / mv;

    const int px = (int)(round(ix + radius * xv));
    const int py = (int)(round(iy + radius * yv));
    const int nx = (int)(round(ix - radius * xv));
    const int ny = (int)(round(iy - radius * yv));

    /*
    O[id] = px;
    M[id] = xv;
    */

    if (!(
        (px < 0) || (px > (width - 1)) || (py < 0) || (py > (height - 1))
        || (nx < 0) || (nx > (width - 1)) || (ny < 0) || (ny > (height - 1))
        ))
    {
        int p = px + py * width;
        int n = nx + ny * width;

        AtomicAdd(&(O[p]), 1.);
        AtomicAdd(&(O[n]), -1.);

        AtomicAdd(&(M[p]), mv);
        AtomicAdd(&(M[n]), -mv);
    }
}

__kernel void calcF(__global float* O, __global float* M, __global float* F,
    const float kappa, const float alpha)
    {
        const int ix = get_global_id(1);
        const int iy = get_global_id(0);

        const int width = get_global_size(1);
        //const int height = get_global_size(0);

        const int id = ix + iy * width;
        float ov = O[id];
        if (ov > kappa)
        {
            ov = kappa;
        } else if (ov < -kappa)
        {
            ov = -kappa;
        };
        F[id] = M[id] / kappa * pow((fabs(ov) / kappa), alpha);
        /* we're done with O and M, zero it out for the next iteration */
        M[id] = 0.;
        O[id] = 0.;
    }
"""


class OpenCLBackend (WovenBackend):
    def __init__(self, ctx=None, queue=None):

        WovenBackend.__init__(self)

        if ctx is None:
            self.ctx = pyopencl.create_some_context(False)
        else:
            self.ctx = ctx

        if queue is None:
            self.q = pyopencl.CommandQueue(self.ctx)
        else:
            self.q = queue

        self.clIm = None
        self.imshape = None

    def autotune(self, im):
        pass

    def setup_device(self, imshape):

        print('Setting up with imshape = %s' % (str(imshape)))

        self.imshape = imshape

        self.clIm = cla.Array(self.q, imshape, numpy.float32)
        self.clm = cla.empty_like(self.clIm)
        self.clx = cla.empty_like(self.clIm)
        self.cly = cla.empty_like(self.clIm)
        self.clO = cla.zeros_like(self.clIm)
        self.clM = cla.zeros_like(self.clIm)
        self.clF = cla.empty_like(self.clIm)
        self.clS = cla.empty_like(self.clIm)
        self.clThisS = cla.empty_like(self.clIm)
        self.clScratch = cla.empty_like(self.clIm)

        self.prg = pyopencl.Program(self.ctx, PROGRAM).build()

        self.sobel = Sobel(self.ctx, self.q)

        #self.sepcorr2d = NaiveSeparableCorrelation(self.ctx, self.q)
        self.sepcorr2d = LocalMemorySeparableCorrelation(self.ctx, self.q)

        self.accum = ElementwiseKernel(self.ctx,
                                       'float *a, float *b',
                                       'a[i] += b[i]')

        self.norm_s = ElementwiseKernel(self.ctx,
                                        'float *s, const float nRadii',
                                        's[i] = -1 * s[i] / nRadii',
                                        'norm_s')

        self.accum_s = ElementwiseKernel(self.ctx,
                                         'float *a, float *b, const float nr',
                                         'a[i] -= b[i] / nr')

        self.gaussians = {}
        self.gaussian_prgs = {}

        self.minmax = MinMaxKernel(self.ctx, self.q)



    def sobel3x3(self, im):
        sobel_c = numpy.array([-1., 0., 1.], dtype=im.dtype)
        sobel_r = numpy.array([1., 2., 1.], dtype=im.dtype)

        imgx = self.separable_convolution2d(im, sobel_c, sobel_r)
        imgy = self.separable_convolution2d(im, sobel_r, sobel_c)

        mag = numpy.sqrt(imgx ** 2 + imgy ** 2) + 1e-16
        return mag, imgx, imgy

    def separable_convolution2d(self, im, row, col):
        return scipy.signal.sepfir2d(im, row, col)

    def fast_radial_transform(self, im, radii, alpha):

        if im.shape != self.imshape:
            self.setup_device(im.shape)

        self.clIm.set(im.astype(numpy.float32))

        self.sobel(self.clIm, self.clx, self.cly, self.clm)

        self.clS.fill(numpy.float32(0), self.q)
        #self.clO.fill(numpy.float32(0), self.q)
        #self.clM.fill(numpy.float32(0), self.q)

        for radius in radii:

            #print "------ Running -------"
            self.prg.calcOM(self.q, im.shape, None, #(3, 4),
                    self.clm.data, self.clx.data, self.cly.data,
                    self.clO.data, self.clM.data,
                    numpy.int32(radius))

            if radius == 1:
                kappa = 8
            else:
                kappa = 9.9

            self.prg.calcF(self.q, im.shape, None, #(3, 4),
                           self.clO.data, self.clM.data, self.clF.data,
                           numpy.float32(kappa), numpy.float32(alpha))

            # Unsmoothed symmetry measure at this radius value

            if radius in self.gaussian_prgs:
                blur = self.gaussian_prgs[radius]
                clGauss1D = self.gaussians[radius]
            else:
                width = round(radius)
                if numpy.mod(width, 2) == 0:
                    width += 1
                gauss1d = scipy.signal.gaussian(width, 0.25 * radius)

                blur = LocalMemorySeparableCorrelation(self.ctx, self.q, gauss1d, gauss1d)
                self.gaussian_prgs[radius] = blur

                clGauss1D = cla.to_device(self.q, gauss1d.astype(numpy.float32))
                self.gaussians[radius] = clGauss1D

            # self.sepcorr2d(self.clF, clGauss1D, clGauss1D, self.clThisS, self.clScratch)
            blur(self.clF, clGauss1D, clGauss1D, self.clThisS, self.clScratch)

            self.accum(self.clS, self.clThisS)
            #self.accum_s(self.clS, self.clThisS, numpy.float32(len(radii)))

        self.norm_s(self.clS, numpy.float32(len(radii)))

        return self.clS

    def find_minmax(self, im):
        return self.minmax(im)


def test_with_noise():
    im = numpy.random.randn(123, 164)
    print "testing inline"
    r = test_inline(im)
    print "Radial returned:", r.max(), r.min()
    return r


def test_with_file(fn):
    im = pylab.imread(fn)
    if im.ndim > 2:
        im = numpy.mean(im[:, :, :3], 2)
    pylab.imsave("intermediate.png", im, vmin=0, vmax=1., cmap=pylab.cm.gray)
    r = test_inline(im)
    return r


def test_inline(im, radii=[1, 3, 5, 9, 12, 15], alpha=10.):
    b = OpenCLBackend()
    return b.fast_radial_transform(im, radii, alpha)


def main():
    import sys
    if len(sys.argv) > 1:
        S = test_with_file(sys.argv[1])
    else:
        S = test_with_noise()

    print "Values of min and max"
    print S.min(), S.max()
    print "Location of min and max"
    print numpy.unravel_index(S.argmin(), S.shape), \
            numpy.unravel_index(S.argmax(), S.shape)
    pylab.imsave('result.png', S, cmap=pylab.cm.gray)


def profile():

    import hotshot, hotshot.stats
    prof = hotshot.Profile("test.prof")
    r = prof.runcall(test_with_noise)
    prof.close()
    stats = hotshot.stats.load("test.prof")
    stats.strip_dirs()
    stats.sort_stats('time', 'calls')
    stats.print_stats(200)

if __name__ == '__main__':
    profile()
