#!/usr/bin/env python

import sys

import numpy
import pylab
import scipy.signal

import pyopencl
from coxlab_eyetracker.image_processing import OpenCLImageProcessing

ck = numpy.array([-1., 0., 1.], dtype=numpy.float32)
rk = numpy.array([1., 2., 1.], dtype=numpy.float32)
im = pylab.imread('test.png')[:, :, 0].astype(numpy.float32)

ctx = pyopencl.create_some_context(False)
q = pyopencl.CommandQueue(ctx)
lconv = OpenCLImageProcessing.LocalMemorySeparableConvolutionKernel(q)

def sx(im):
    return scipy.signal.sepfir2d(im, ck, rk)


def sy(im):
    return scipy.signal.sepfir2d(im, rk, ck)


def mag(x, y):
    return numpy.sqrt(x ** 2 + y ** 2) + 1e-16


def sobel(im):
    x = sx(im)
    y = sy(im)
    return mag(x, y), x, y


def clx(im):
    return lconv(im, ck, rk, readback_from_device=True)


def cly(im):
    return lconv(im, rk, ck, readback_from_device=True)


def clsobel(im):
    from coxlab_eyetracker.image_processing.simple_cl_conv import cl_test_sobel
    return cl_test_sobel(im)
    #return im, im, im
    # x = clx(im)
    # y = cly(im)
    # return mag(x, y), x, y


def report(t, c):
    print "Max:", t.max(), c.max()
    print "Min:", t.min(), c.min()
    pylab.figure()
    pylab.subplot(221)
    pylab.imshow(t, cmap=pylab.cm.gray)
    pylab.title("Truth")
    pylab.subplot(222)
    pylab.imshow(c, cmap=pylab.cm.gray)
    pylab.title("CL")
    pylab.subplot(223)
    pylab.imshow(t - c, cmap=pylab.cm.gray)
    pylab.title("Truth - CL")


def test(t, c):
    if (numpy.abs(t - c)).max() > 1e-8:
        report(t, c)
        return False
    return True


failure = False

tm, tx, ty = sobel(im)

cm, cx, cy = clsobel(im)

print "X"
failure |= (not test(tx, cx))
if failure:
    pylab.show()
    #sys.exit(1)

print "Y"
failure |= (not test(ty, cy))
if failure:
    pylab.show()
    #sys.exit(1)

print "Mag"
failure |= (not test(tm, cm))
if failure:
    pylab.show()
    #sys.exit(1)

if not failure:
    print "Success!"