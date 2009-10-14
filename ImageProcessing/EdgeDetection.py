#
#  ImageEdgeDetector.py
#  EyeTrackerStageDriver
#
#  Created by Davide Zoccolan on 9/10/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#


from numpy import *
import scipy
from scipy import signal

try:
    import pyopencl as cl
except Exception, e:
    pass


class ImageProcessingBackend:

    def sobel3x3(im, **kwargs):
        mag = None
        imgx = None
        imgy = None
        return (mag, imgx, imgy)
        
    def separable_convolution(im, row, col, **kwargs):
        result = None
        return result
    
    def find_minmax(im):
        min_coord = None
        max_coord = None
        return (min_coord, max_coord)
        
    def fast_radial_transform


class vanilla (ImageProcessingBackend):


    def sobel3x3(im):
        return sobel3x3_separable(im)

    def sobel3x3_separable(image):
        
        sobel_c = array([-1.,0.,1.])
        sobel_r = array([1.,2.,1.])
        
        imgx = signal.sepfir2d(image, sobel_c, sobel_r)
        imgy = signal.sepfir2d(image, sobel_r, sobel_c)
            
        mag = sqrt(imgx**2 + imgy**2) + 1e-16
        
        return (mag, imgx, imgy)

    def sobel3x3_naive(image):
        sobel_x = array([[-1.,0.,1.],[-2.,0., 2.],[1.,0.,-1]])
        sobel_y = array([[1.,2.,-1.],[0.,0., 0.],[-1.,-2.,1]])
        imgx = signal.convolve2d( image, sobel_x, mode='same', boundary='symm' )
        imgy = signal.convolve2d( image, sobel_y, mode='same', boundary='symm' )
        mag = sqrt(imgx**2 + imgy**2) + 2e-16
        
        return (mag, imgx, imgy)




class woven:

    from scipy.weave import inline
    from scipy.weave import converters

    def sobel3x3(image):
        return sobel3x3_separable(image)


    def sobel3x3_separable(image, use_weave=0, use_sse=0):
        
        sobel_c = array([-1.,0.,1.])
        sobel_r = array([1.,2.,1.])
        
        imgx = woven_sepfir2d(image, sobel_c, sobel_r)
        imgy = woven_sepfir2d(image, sobel_r, sobel_c)
            
        mag = sqrt(imgx**2 + imgy**2) + 1e-16
        
        return (mag, imgx, imgy)

    def woven_sepfir2d(image, row, col):
        
        code = """
            Py_BEGIN_ALLOW_THREADS
            int h = Nimage[0];
            int w = Nimage[1];
            
            int image_r_stride = image_array->strides[0];
            int image_c_stride = image_array->strides[1];
            int fp_r_stride = firstpass_array->strides[0];
            int fp_c_stride = firstpass_array->strides[1];
            
            int row_width = Nrow[0];
            int row_halfwidth;
            if((row_width % 2) == 0){
                row_halfwidth = (row_width-1) / 2;
            } else {
                row_halfwidth = row_width / 2;
            }
            
            int col_width = Ncol[0];
            int col_halfwidth;
            if((col_width % 2) == 0){
                col_halfwidth = (col_width-1) / 2;
            } else {
                col_halfwidth = col_width / 2;
            }
            
            int r_stride = firstpass_array->strides[0];
            int c_stride = firstpass_array->strides[1];
            
            // Apply the row kernel
            for(int r = 0; r < h; r++){
                for(int c = 0; c < w; c++){
                    int result_offset = r_stride * r + c_stride*c;
                    double *result_ptr = (double *)((char *)firstpass_array->data + result_offset);
                    result_ptr[0] = 0.0;
                    
                    for(int k = 0; k < row_width; k++){
                        int k_index = k - row_halfwidth + c;
                        
                        //if(k_index < 0 || k_index > w) continue;
                        if(k_index < 0) k_index *= -1;  // reflect at boundaries
                        if(k_index >= w) k_index = w - (k - row_halfwidth);
                        
                        double *image_ptr = (double *)((char *)image_array->data + image_r_stride*r + image_c_stride*k_index);
                        double kernel_coef = *((double*)((char *)row_array->data + row_array->strides[0] * k));
                        *result_ptr += kernel_coef * (*image_ptr);
                        
                    }
                }
            }
            
            
            r_stride = result_array->strides[0];
            c_stride = result_array->strides[1];
            
            // Apply the col kernel
            for(int c = 0; c < w; c++){
                for(int r = 0; r < h; r++){
                    
                    int result_offset = r_stride*r + c_stride*c;
                    double *result_ptr = (double *)((char *)result_array->data + result_offset);
                    result_ptr[0] = 0.0;
                    
                    for(int k = 0; k < col_width; k++){
                        int k_index = k - col_halfwidth + r;
                        
                        //if(k_index < 0 || k_index > h) continue;
                        if(k_index < 0) k_index *= -1;  // reflect at boundaries
                        if(k_index >= h) k_index = h - (k - col_halfwidth);
                        
                        double *image_ptr = (double *)((char *)firstpass_array->data + k_index*fp_r_stride + fp_c_stride*c);
                        
                        double kernel_coef = *((double *)((char *)col_array->data + col_array->strides[0]*k));
                        *result_ptr += kernel_coef * (*image_ptr);
                        
                    }
                }
            }
            Py_END_ALLOW_THREADS
        """
        
        firstpass = zeros_like(image)
        result = zeros_like(image)
        inline(code, ['image', 'row', 'col', 'firstpass', 'result'], verbose=2)
        
        return result


class woven_SSE (woven):

    # NOTE: this isn't done well, and is not any faster
    def woven_sepfir2d(self, image, row, col):

        code = """
            Py_BEGIN_ALLOW_THREADS
            int h = Nimage[0];
            int w = Nimage[1];

            int image_r_stride = image_array->strides[0];
            int image_c_stride = image_array->strides[1];
            int fp_r_stride = firstpass_array->strides[0];
            int fp_c_stride = firstpass_array->strides[1];

            int row_width = Nrow[0];
            int row_halfwidth;
            if((row_width % 2) == 0){
                row_halfwidth = (row_width-1) / 2;
            } else {
                row_halfwidth = row_width / 2;
            }

            int col_width = Ncol[0];
            int col_halfwidth;
            if((col_width % 2) == 0){
                col_halfwidth = (col_width-1) / 2;
            } else {
                col_halfwidth = col_width / 2;
            }

            
            bool process_conventionally = false;

            int r_stride = firstpass_array->strides[0];
            int c_stride = firstpass_array->strides[1];
            
            // SSE optimized kernel
            typedef struct vector4f_t{
                union {
                    __m128 vec;		// 128bit alignment
                    float xyzw[4];
                    struct {
                        float x, y, z, w;
                    };
                    
                };
            } vec4;
            
            float zeros[4] = {0.0, 0.0, 0.0, 0.0};
            
            vec4 *padded_row_kernel;
            int padded_row_kernel_length_quads;
            if(row_width % 4 == 0){
                padded_row_kernel_length_quads = row_width / 4;
                padded_row_kernel = new vec4[padded_row_kernel_length_quads];
            } else {
                padded_row_kernel_length_quads = (row_width/4) + 1;
                padded_row_kernel = new vec4[padded_row_kernel_length_quads];
                // Zero out the not-full quad
                int p = padded_row_kernel_length_quads - 1;
                padded_row_kernel[p].x = 0.0;
                padded_row_kernel[p].y = 0.0;
                padded_row_kernel[p].z = 0.0;
                padded_row_kernel[p].w = 0.0;
            }
            
            // Copy in the kernel data
            memcpy(padded_row_kernel, row, row_width*sizeof(float));

            // Apply the row kernel
            for(int r = 0; r < h; r++){
                for(int c = 0; c < w; c++){
                    
                    int result_offset = r_stride * r + c_stride*c;
                    float *result_ptr = (float *)((char *)firstpass_array->data + result_offset);
                    result_ptr[0] = 0.0;
                    
                    
                    if(c < row_width ||  (w - c) < row_width){
                        for(int k = 0; k < row_width; k++){
                            int k_index = k - row_halfwidth + c;

                            if(k_index < 0) k_index *= -1;  // reflect at boundaries
                            if(k_index >= w) k_index = w - (k - row_halfwidth);

                            float *image_ptr = (float *)((char *)image_array->data + image_r_stride*r + image_c_stride*k_index);
                            float kernel_coef = *((float*)((char *)row_array->data + row_array->strides[0] * k));
                            float before = *result_ptr;
                            *result_ptr += kernel_coef * (*image_ptr);

                        }
                    } else {
                        // The SSE bits
                        
                        for(int kq = 0; kq < padded_row_kernel_length_quads; kq++){
                            vec4 *quad = padded_row_kernel + kq;
                            vec4 data;
                            float *data_unaligned = (float *)((char *)image_array->data + image_r_stride*r + image_c_stride*c) + kq*4;
                            memcpy((float *)(data.xyzw),data_unaligned, 4*sizeof(float));
                            vec4 result;
                            
                            __m128 quad_sse, data_sse, mult_sse, sum_sse, zero_sse;
                            
                            quad_sse = _mm_load_ps((float*)quad->xyzw);
                            data_sse = _mm_load_ps((float*)&data);
                            zero_sse = _mm_load_ps((float*)zeros);
                            mult_sse = _mm_mul_ps(quad_sse, data_sse);
                            sum_sse = _mm_hadd_ps(mult_sse, mult_sse);
                            sum_sse = _mm_hadd_ps(sum_sse, sum_sse);
                            _mm_store_ps((float *)&result,sum_sse);
                        
                            *result_ptr += result.x;
                        }
                        
                    }
                }
            }
            
            r_stride = result_array->strides[0];
            c_stride = result_array->strides[1];

            // Apply the col kernel
            for(int c = 0; c < w; c++){
                for(int r = 0; r < h; r++){
                    

                    int result_offset = r_stride*r + c_stride*c;
                    double *result_ptr = (double *)((char *)result_array->data + result_offset);
                    result_ptr[0] = 0.0;

                    for(int k = 0; k < col_width; k++){
                        int k_index = k - col_halfwidth + r;

                        //if(k_index < 0 || k_index > h) continue;
                        if(k_index < 0) k_index *= -1;  // reflect at boundaries
                        if(k_index >= h) k_index = h - (k - col_halfwidth);

                        double *image_ptr = (double *)((char *)firstpass_array->data + k_index*fp_r_stride + fp_c_stride*c);

                        double kernel_coef = *((double *)((char *)col_array->data + col_array->strides[0]*k));
                        double before = *result_ptr;
                        *result_ptr += kernel_coef * (*image_ptr);

                    }
                }
            }
            Py_END_ALLOW_THREADS
        """

        firstpass = zeros_like(image)
        result = zeros_like(image)
        inline(code, ['image', 'row', 'col', 'firstpass', 'result'], verbose=2, extra_compile_args=['-march=pentium4','-msse3'], headers=['<xmmintrin.h>','<emmintrin.h>','<pmmintrin.h>'])

        return result



class opencl:

    def sobel3x3(image, ctx, queue):

        kernel = """
        blah
        """





    