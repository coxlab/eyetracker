#!/usr/bin/env python

import numpy
import pylab
import pyopencl
import pyopencl.array
import scipy.ndimage.filters
import scipy.signal

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
        const int height = get_global_size(0);

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


class OpenCLBackend:
    def __init__(self):
        self.setup_device((123, 164))

    def autotune(self, im):
        pass

    def setup_device(self, imshape):
        self.ctx = pyopencl.create_some_context(False)
        self.q = pyopencl.CommandQueue(self.ctx)
        self.clm = pyopencl.array.Array(self.q, imshape, numpy.float32)
        self.clx = pyopencl.array.Array(self.q, imshape, numpy.float32)
        self.cly = pyopencl.array.Array(self.q, imshape, numpy.float32)
        self.clO = pyopencl.array.Array(self.q, imshape, numpy.float32)
        self.clM = pyopencl.array.Array(self.q, imshape, numpy.float32)
        self.clF = pyopencl.array.Array(self.q, imshape, numpy.float32)
        self.prg = pyopencl.Program(self.ctx, PROGRAM).build()

        # this will build the fill program
        self.clO.fill(numpy.float32(0), self.q)
        self.clM.fill(numpy.float32(0), self.q)
        pass

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
        # TODO move this to GPU
        sm, sx, sy = self.sobel3x3(im)
        sm = sm.astype(numpy.float32)
        sx = sx.astype(numpy.float32)
        sy = sy.astype(numpy.float32)
        #print "SM:", sm.shape, sm.max(), sm.min()
        #print "SX:", sx.shape, sx.max(), sx.min()
        #print "SY:", sy.shape, sy.max(), sy.min()

        #O = numpy.zeros(im.shape, dtype=numpy.int32)
        #M = numpy.zeros(im.shape, dtype=numpy.int32)
        S = numpy.zeros(im.shape, dtype=numpy.float32)
        F = numpy.zeros(im.shape, dtype=numpy.float32)
        #clO.set(O)
        #clM.set(M)
        self.clm.set(sm, self.q)
        self.clx.set(sx, self.q)
        self.cly.set(sy, self.q)

        # calcF also calls this
        self.clO.fill(numpy.float32(0), self.q)
        self.clM.fill(numpy.float32(0), self.q)

        for radius in radii:

            #print "------ Running -------"
            self.prg.calcOM(self.q, im.shape, (3, 4), \
                    self.clm.data, self.clx.data, self.cly.data, \
                    self.clO.data, self.clM.data, \
                    numpy.int32(radius))

            #print "------ Copying -------"
            #O = self.clO.get(self.q)
            #M = self.clM.get(self.q)
            #print 'O', O.shape, O.max(), O.min()
            #print O[:3, :3]
            #print O[-3:, -3:]
            #print 'M', M.shape, M.max(), M.min()
            #print M[:3, :3]
            #print M[-3:, -3:]

            if radius == 1:
                kappa = 8
            else:
                kappa = 9.9

            self.prg.calcF(self.q, im.shape, (3, 4), \
                    self.clO.data, self.clM.data, self.clF.data,
                    numpy.float32(kappa), numpy.float32(alpha))

            #O[numpy.where(O > kappa)] = kappa
            #O[numpy.where(O < -kappa)] = -kappa
            #print 'O', O.shape, O.max(), O.min()

            # Unsmoothed symmetry measure at this radius value
            #F = M / kappa * (abs(O) / kappa) ** alpha
            self.clF.get(self.q, F)
            #print "-- Radius: %i --" % radius
            #print "F:", F.shape, F.max(), F.min()
            # smooth : TODO move this to GPU
            width = round(radius)
            if numpy.mod(width, 2) == 0:
                width += 1
            gauss1d = scipy.signal.gaussian(width, 0.25 * radius)
            thisS = self.separable_convolution2d(F.astype(float), \
                    gauss1d, gauss1d)
            #print "S:", thisS.shape, thisS.max(), thisS.min()
            # TODO : move this to GPU
            S += thisS
            #print "S:", S.shape, S.max(), S.min()
        # TODO : move this to GPU
        S = -S / len(radii)
        #print "S:", S.shape, S.max(), S.min()
        #print "S(center)", S[:, :124].max(), S[:, 124:].min()
        #print "S(edge  )", S[:, 124:].max(), S[:, 124:].min()
        return S


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


def test_inline(im, radii=[1, 3, 6, 9, 12, 15], alpha=10.):
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


if __name__ == '__main__':
    main()
