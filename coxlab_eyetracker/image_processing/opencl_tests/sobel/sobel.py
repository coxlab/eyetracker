#!/usr/bin/env python

import numpy
import pyopencl


def build_sobel(ctx):
    return pyopencl.Program(ctx, """
    __kernel void sobel(__global float *im, __global float *m,
        __global float *x, __global float *y)
    {
        m[get_local_id(0)+get_local_size(0)*get_group_id(0)] =
            im[get_local_id(0)+get_local_size(0)*get_group_id(0)] * 2.;
        x[get_local_id(0)+get_local_size(0)*get_group_id(0)] =
            -im[get_local_id(0)+get_local_size(0)*get_group_id(0)];
        y[get_local_id(0)+get_local_size(0)*get_group_id(0)] =
            im[get_local_id(0)+get_local_size(0)*get_group_id(0)];
    }
    """).build()


def setup(im):
    ctx = pyopencl.create_some_context(False)
    queue = pyopencl.CommandQueue(ctx)
    im_dev = pyopencl.Buffer(ctx, pyopencl.mem_flags.READ_ONLY, size=im.nbytes)
    m_dev = pyopencl.Buffer(ctx, pyopencl.mem_flags.READ_WRITE, size=im.nbytes)
    x_dev = pyopencl.Buffer(ctx, pyopencl.mem_flags.READ_WRITE, size=im.nbytes)
    y_dev = pyopencl.Buffer(ctx, pyopencl.mem_flags.READ_WRITE, size=im.nbytes)
    prg = build_sobel(ctx)
    return dict(ctx=ctx, queue=queue, im_dev=im_dev, m_dev=m_dev, \
            x_dev=x_dev, y_dev=y_dev, prg=prg)


def sobel(im, cl=None):
    if cl is None:
        cl = setup(im)
    im = im.astype(numpy.float32)
    pyopencl.enqueue_write_buffer(cl['queue'], cl['im_dev'], im)
    cl['prg'].sobel(cl['queue'], im.shape, (3,), \
            cl['im_dev'], cl['m_dev'], cl['x_dev'], cl['y_dev'])
    m = numpy.empty_like(im)
    x = numpy.empty_like(im)
    y = numpy.empty_like(im)
    pyopencl.enqueue_read_buffer(cl['queue'], cl['m_dev'], m).wait()
    pyopencl.enqueue_read_buffer(cl['queue'], cl['x_dev'], x).wait()
    pyopencl.enqueue_read_buffer(cl['queue'], cl['y_dev'], y).wait()
    return m, x, y


def test_with_noise():
    im = numpy.random.randn(100, 100)
    cl = setup(im)
    m, x, y = sobel(im, cl)


if __name__ == '__main__':
    test_with_noise()
