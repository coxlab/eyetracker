#!/usr/bin/env python
# -*- coding: utf-8 -*-
from VanillaBackend import *
from WovenBackend import *
from OpenCLImageProcessing import *

import numpy
import pyopencl as cl
mf = cl.mem_flags


class OpenCLBackend(WovenBackend):

    def __init__(self):
        WovenBackend.__init__(self)
        platforms = cl.get_platforms()
        platform = platforms[0]
        devices = platform.get_devices()
        device = devices[0]
        self.ctx = cl.Context([device])
        self.queue = cl.CommandQueue(self.ctx)
        self.convolution_cl_kernel = \
            LocalMemorySeparableConvolutionKernel(self.queue)

    def autotune(self, example_im, **kwargs):
        self.autotuned = True

#    def _sobel_3x3(self, im, **kwargs):
#        return (imgx, imgy, mag)

    def separable_convolution2d(self, im, row, col, **kwargs):
        return self.convolution_cl_kernel(im, row, col,
                readback_from_device=True)

    def _fast_radial_transform(self, im, radii, alpha, **kwargs):

        if readback_from_device:
            pass

        return S


if __name__ == '__main__':

    from numpy.random import rand
    from pylab import *

    test_im = rand(2250, 2250).astype(numpy.float32)
    # test_im = (rand(768,1024)).astype(numpy.float32)
    row = array([0.25, 0.3, 0.4]).astype(numpy.float32)
    # row = array([0.25, 0.3, 0.4, 0.6, 0.7, 0.6, 0.4, 0.3, 0.25]).astype(numpy.float32)
    # row = array([0.25, 0.4, 0.6, 0.4, 0.25]).astype(numpy.float32)
    row = row / sum(row)

    col = row

    cl_backend = OpenCLBackend()
    vanilla_backend = VanillaBackend()
    woven_backend = WovenBackend()

    woven_backend.autotune(test_im)
    cl_backend.autotune(test_im)
    print 'CL Filtering...'
    # row_dev = cl.Buffer(cl_backend.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, 0, row.astype(float32))
    # col_dev = cl.Buffer(cl_backend.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, 0, col.astype(float32))

    row_dev = DeviceBuffer(cl_backend.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                           row.astype(float32))
    col_dev = DeviceBuffer(cl_backend.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                           col.astype(float32))

    # print cl_backend.device.name

    cl_filtered = cl_backend.separable_convolution2d(
        test_im.astype(float32),
        row_dev,
        col_dev,
        readback_from_device=False,
        im_shape=test_im.shape,
        row_shape=row.shape,
        col_shape=col.shape,
        )
    for i in range(0, 8):
        cl_filtered = cl_backend.separable_convolution2d(
            cl_filtered,
            row_dev,
            col_dev,
            readback_from_device=False,
            im_shape=test_im.shape,
            row_shape=row.shape,
            col_shape=col.shape,
            )
    cl_filtered = cl_backend.separable_convolution2d(
        cl_filtered,
        row_dev,
        col_dev,
        readback_from_device=True,
        im_shape=test_im.shape,
        row_shape=row.shape,
        col_shape=col.shape,
        )

    print 'Vanilla Filtering...'
    vanilla_filtered = \
        vanilla_backend.separable_convolution2d(test_im.astype(float32), row,
            col)
    for i in range(0, 8):
        vanilla_filtered = \
            vanilla_backend.separable_convolution2d(vanilla_filtered, row, col)
    vanilla_filtered = \
        vanilla_backend.separable_convolution2d(vanilla_filtered, row, col)

    print 'Woven filtering...'
    woven_filtered = \
        woven_backend.separable_convolution2d(test_im.astype(float32), row, col)
    for i in range(0, 9):
        woven_filtered = woven_backend.separable_convolution2d(woven_filtered,
                row, col)

    # print(vanilla_filtered)

    # print(cl_filtered)

    vmin = 0.4
    vmax = 0.6

    subplot(3, 1, 1)
    imshow(cl_filtered, vmin=vmin, vmax=vmax)
    subplot(3, 1, 2)
    imshow(vanilla_filtered, vmin=vmin, vmax=vmax)
    subplot(3, 1, 3)
    imshow(woven_filtered, vmin=vmin, vmax=vmax)

    # show()
