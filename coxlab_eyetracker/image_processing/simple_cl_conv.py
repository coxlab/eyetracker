
import pyopencl as cl
import pyopencl.array as cl_array
from pyopencl import clmath
from pyopencl.elementwise import ElementwiseKernel
import numpy as np


class NaiveSeparableConvolution:

    def __init__(self, ctx, queue):
        self.ctx = ctx
        self.queue = queue

        code = """
            __kernel void separable_correlation_row(__global float *result,
                                            __global const float *input,
                                            int image_width,
                                            int image_height,
                                            __global const float *kernel_row,
                                            int kernel_width){

                const int kernel_radius = kernel_width / 2;

                int row = get_global_id(0);
                int col = get_global_id(1);

                float sum = 0.0;

                int im_index = row * image_width + col;

                for(int i = 0; i < kernel_width; i++){
                    int k = i - kernel_radius;
                    if( (col + k) < 0 ){
                        k *= -1;
                        k -= 1;
                    }

                    if( (col + k) >= image_width){
                        k *= -1;
                        k += 1;
                    }

                    sum += input[im_index + k] * kernel_row[i];

                }

                result[im_index] = sum;

                return;
            }


            __kernel void separable_correlation_col(__global float *result,
                                            __global  const float *input,
                                            int image_width,
                                            int image_height,
                                            __global  const float *kernel_col,
                                            int kernel_width){


                const int kernel_radius = kernel_width / 2;

                int row = get_global_id(0);
                int col = get_global_id(1);

                float sum = 0.0;

                for(int i = 0; i < kernel_width; i++){
                    int k = i - kernel_radius;

                    if( (row + k) < 0 ){
                        k *= -1;
                        k -= 1;
                    }

                    if( (row + k) >= image_height ){
                        k *= -1;
                        k += 1;
                    }

                    int im_index = (row + k) * image_width + col;

                    sum = sum + input[im_index]*kernel_col[i];

                }
                result[row * image_width + col] = sum;

            }
        """

        self.program = cl.Program(self.ctx, code).build()

    def __call__(self,
                 input_buf,
                 row_buf,
                 col_buf,
                 output_buf,
                 intermed_buf=None):

        (h, w) = input_buf.shape
        r = row_buf.shape[0]
        c = col_buf.shape[0]

        if intermed_buf is None:
            intermed_buf = cl_array.empty_like(input_buf)

        self.program.separable_correlation_row(self.queue,
                                               (h, w),
                                               None,
                                               intermed_buf.data,
                                               input_buf.data,
                                               np.int32(w), np.int32(h),
                                               row_buf.data,
                                               np.int32(r))
        #evt.wait()

        self.program.separable_correlation_col(self.queue,
                                               (h, w),
                                               None,
                                               output_buf.data,
                                               intermed_buf.data,
                                               np.int32(w), np.int32(h),
                                               col_buf.data,
                                               np.int32(c))
        #evt.wait()


class Sobel:

    def __init__(self, ctx, queue):
        self.ctx = ctx
        self.queue = queue
        sobel_c = np.array([1., 0., -1.]).astype(np.float32)
        sobel_r = np.array([1., 2., 1.]).astype(np.float32)
        self.sobel_c = cl_array.to_device(self.queue, sobel_c)
        self.sobel_r = cl_array.to_device(self.queue, sobel_r)

        self.scratch = None

        self.sepconv = NaiveSeparableConvolution(self.ctx, self.queue)

        self.mag = ElementwiseKernel(ctx,
                                    "float *result, float *imgx, float *imgy",
                                    "result[i] = sqrt(imgx[i]*imgx[i] + imgy[i]*imgy[i])",
                                    "mag")

    def __call__(self,
                 input_buf,
                 imgx_buf,
                 imgy_buf,
                 mag_buf):

        if self.scratch is None or self.scratch.shape != input_buf.shape:
            self.scratch = cl_array.empty_like(input_buf)

        self.sepconv(input_buf, self.sobel_c, self.sobel_r, imgx_buf, self.scratch)
        self.sepconv(input_buf, self.sobel_r, self.sobel_c, imgy_buf, self.scratch)
        self.mag(mag_buf, imgx_buf, imgy_buf)


def cl_test_sobel(im):
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)

    sobel = Sobel(ctx, queue)

    im_buf = cl_array.to_device(queue, im)
    mag_buf = cl_array.empty_like(im_buf)
    imgx_buf = cl_array.empty_like(im_buf)
    imgy_buf = cl_array.empty_like(im_buf)

    sobel(im_buf, imgx_buf, imgy_buf, mag_buf)
    return (mag_buf.get(), imgx_buf.get(), imgy_buf.get())

if __name__ == '__main__':

    if True:
        test_im = np.random.rand(7, 5).astype(np.float32)
        row_k = np.random.rand(3,).astype(np.float32)
        col_k = np.random.rand(3,).astype(np.float32)
    elif False:
        a = np.array([1,2,3,4,5], dtype=np.float32)
        test_im = np.outer(a, a)
        row_k = np.array([1, 2, 3]).astype(np.float32)
        col_k = np.array([2, 4, 5]).astype(np.float32)
    else:
        test_im = np.ones([10, 10]).astype(np.float32)
        row_k = np.array([1, 2, 3]).astype(np.float32)
        col_k = np.array([2, 4, 5]).astype(np.float32)


    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)

    in_buf = cl_array.to_device(queue, test_im)
    row_buf = cl_array.to_device(queue, row_k)
    col_buf = cl_array.to_device(queue, col_k)
    out_buf = cl_array.empty_like(in_buf)
    imgx_buf = cl_array.empty_like(in_buf)
    imgy_buf = cl_array.empty_like(in_buf)
    mag_buf = cl_array.empty_like(in_buf)


    # Test the Sobel
    sobel = Sobel(ctx, queue)
    sobel(in_buf, imgx_buf, imgy_buf, mag_buf)

    print(imgx_buf.get())
    print(mag_buf.get())

    # Test the conv
    conv = NaiveSeparableConvolution(ctx, queue)

    conv(in_buf, row_buf, col_buf, out_buf)

    full_kernel = np.outer(col_k, row_k)
    print(full_kernel)
    from scipy.signal import correlate2d as c2d
    gt = c2d(test_im, full_kernel, mode='same', boundary='symm')

    print "Input: "
    print(test_im)

    print "ground truth"
    print(gt)

    print "cl output"
    print(out_buf.get())

    print "diff"
    print(gt - out_buf.get())


