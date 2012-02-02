#!/usr/bin/env python
# -*- coding: utf-8 -*-
from VanillaBackend import *

import scipy
from scipy.weave import inline


class WovenBackend(VanillaBackend):

    def __init__(self):
        VanillaBackend.__init__(self)

        # reusable storage
        self.cached_shape = None
        self.cached_gauss2d_fft = None
        self.M = None
        self.O = None
        self.F = None
        self.S = None
        self.sepfir_firstpass = None

        self.type_string = 'float'
        self.autotuned = False

    def autotune(self, example_im):

        self.dtype = example_im.dtype
        if self.dtype == float32:
            self.type_string = 'float'
        elif self.dtype == uint8:
            self.type_string = 'uint8'
        else:
            self.type_string = 'double'

        # print self.type_string
        # (re)initialize reusable storage
        self.cached_shape = example_im.shape
        self.cached_gauss2d_fft = None
        self.M = zeros_like(example_im)
        self.O = zeros_like(example_im)
        self.F = zeros_like(example_im)
        self.S = zeros_like(example_im)
        self.sepfir_firstpass = zeros_like(example_im)
        self.sepfir_result = zeros_like(example_im)

        self.autotuned = True
        return

    def sobel3x3(self, image, **kwargs):
        return self.sobel3x3_separable(image)

    # @clockit
    def sobel3x3_separable(self, image, **kwargs):

        sobel_c = array([-1., 0., 1.]).astype(image.dtype)
        sobel_r = array([1., 2., 1.]).astype(image.dtype)

        imgx = self.separable_convolution2d(image, sobel_c, sobel_r)
        imgy = self.separable_convolution2d(image, sobel_r, sobel_c)

        mag = sqrt(imgx ** 2 + imgy ** 2) + 1e-16

        return (mag, imgx, imgy)

    # @clockit
    def separable_convolution2d(self, image, row, col, **kwargs):

        if not self.autotuned:
            self.autotune(image)

        code = \
            """
            Py_BEGIN_ALLOW_THREADS

            #define __TYPE  %s

            int h = Nimage[0];
            int w = Nimage[1];

            int image_r_stride = image_array->strides[0];
            int image_c_stride = image_array->strides[1];
            int fp_r_stride = firstpass_array->strides[0];
            int fp_c_stride = firstpass_array->strides[1];

            int row_width = Nrow[0];
            int row_halfwidth;
            if((row_width %% 2) == 0){
                row_halfwidth = (row_width-1) / 2;
            } else {
                row_halfwidth = row_width / 2;
            }

            int col_width = Ncol[0];
            int col_halfwidth;
            if((col_width %% 2) == 0){
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
                    __TYPE *result_ptr = (__TYPE *)((char *)firstpass_array->data + result_offset);
                    result_ptr[0] = 0.0;

                    for(int k = 0; k < row_width; k++){
                        int k_index = k - row_halfwidth + c;

                        //if(k_index < 0 || k_index > w) continue;
                        if(k_index < 0) k_index *= -1;  // reflect at boundaries
                        if(k_index >= w) k_index = w - (k - row_halfwidth);

                        __TYPE *image_ptr = (__TYPE *)((char *)image_array->data + image_r_stride*r + image_c_stride*k_index);
                        __TYPE kernel_coef = *((__TYPE*)((char *)row_array->data + row_array->strides[0] * k));
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
                    __TYPE *result_ptr = (__TYPE *)((char *)result_array->data + result_offset);
                    result_ptr[0] = 0.0;

                    for(int k = 0; k < col_width; k++){
                        int k_index = k - col_halfwidth + r;

                        //if(k_index < 0 || k_index > h) continue;
                        if(k_index < 0) k_index *= -1;  // reflect at boundaries
                        if(k_index >= h) k_index = h - (k - col_halfwidth);

                        __TYPE *image_ptr = (__TYPE *)((char *)firstpass_array->data + k_index*fp_r_stride + fp_c_stride*c);

                        __TYPE kernel_coef = *((__TYPE *)((char *)col_array->data + col_array->strides[0]*k));
                        *result_ptr += kernel_coef * (*image_ptr);

                    }
                }
            }
            Py_END_ALLOW_THREADS
        """ \
            % self.type_string

        firstpass = zeros_like(image)
        result = zeros_like(image)
        inline(code, ['image', 'row', 'col', 'firstpass', 'result'], verbose=0)

        return result

    # borrowed with some translation from Peter Kovesi's fastradial.m
    # @clockit
    def fast_radial_transform(self, image, radii, alpha, **kwargs):

        if not self.autotuned:
            self.autotune(image)

        gaussian_kernel_cheat = 1.
        reuse_storage = False

        use_spline_approximation = 0
        use_sep_fir = 0
        use_fft_filter = 0

        (rows, cols) = image.shape

        use_cached_sobel = False
        cached_mag = None
        cached_x = None
        cached_y = None
        if 'cached_sobel' in kwargs:
            (cached_mag, cached_x, cached_y) = kwargs['cached_sobel']
            (sobel_rows, sobel_cols) = cached_sobel_mag.shape

            if sobel_rows == rows or sobel_cols == cols:
                use_cached_sobel = True

        if use_cached_sobel:
            mag = cached_mag
            imgx = cached_x
            imgy = cached_y
        else:
            (mag, imgx, imgy) = self.sobel3x3(image)

        # Normalise gradient values so that [imgx imgy] form unit
        # direction vectors.
        imgx = imgx / mag
        imgy = imgy / mag

        Ss = list(radii)

        (y, x) = mgrid[0:rows, 0:cols]  # meshgrid(1:cols, 1:rows);

        # S_sub = zeros((rows,cols))

        if reuse_storage:

            M = self.M  # Magnitude projection image
            O = self.O  # Orientation projection image
            F = self.F  # the result, prior to accumulation
            S = self.S  # the accumulated result
            self._fast_clear_array2d(S)
        else:
            M = zeros_like(image)
            O = zeros_like(image)
            F = zeros_like(image)
            S = zeros_like(image)

        for r in range(0, len(radii)):

            n = radii[r]

            if reuse_storage:
                self._fast_clear_array2d(M)
                self._fast_clear_array2d(O)
                self._fast_clear_array2d(F)
            else:
                M = zeros_like(image)
                O = zeros_like(image)
                F = zeros_like(image)

            # Coordinates of 'positively' and 'negatively' affected pixels
            posx = x + n * imgx
            posy = y + n * imgy

            negx = x - n * imgx
            negy = y - n * imgy

            # Clamp Orientation projection matrix values to a maximum of
            # +/-kappa,  but first set the normalization parameter kappa to the
            # values suggested by Loy and Zelinski
            kappa = 9.9
            if n == 1:
                kappa = 8

            # Form the orientation and magnitude projection matrices

            code = \
                """
            Py_BEGIN_ALLOW_THREADS

            #define __TYPE  %s

            int rows = Nmag[0];
            //int rstart = 0;
            //int rend = rows;
            int tile_size = rows / n_tiles;
            int rstart = (tile) * tile_size;
            int rend;
            if(tile == n_tiles-1){
                rend = rows;
            } else {
                rend = (tile+1) * tile_size - 1;
            }

            int cols = Nmag[1];
            int cstart = 0;
            int cend = cols;

            for(int r = rstart; r < rend; r++){
                for(int c = cstart; c < cend; c++){
                    int index = r*cols + c;

                    int posx_ = round(posx[index]);
                    int posy_ = round(posy[index]);
                    int negx_ = round(negx[index]);
                    int negy_ = round(negy[index]);

                    if(posx_ < 0 || posx_ > cols-1 ||
                       posy_ < 0 || posy_ > rows-1 ||
                       negx_ < 0 || negx_ > cols-1 ||
                       negy_ < 0 || negy_ > rows-1){
                        continue;
                    }

                    if(posx_ < 0) posx_ = 0;
                    if(posx_ > cols-1) posx_ = cols-1;
                    if(posy_ < 0) posy_ = 0;
                    if(posy_ > rows-1) posy_ = rows-1;

                    if(negx_ < 0) negx_ = 0;
                    if(negx_ > cols-1) negx_ = cols-1;
                    if(negy_ < 0) negy_ = 0;
                    if(negy_ > rows-1) negy_ = rows-1;

                    int pos_index = (int)posy_*cols + (int)posx_;
                    int neg_index = (int)negy_*cols + (int)negx_;

                    O[pos_index] += 1.0;
                    O[neg_index] -= 1.0;

                    M[pos_index] += mag[index];
                    M[neg_index] -= mag[index];
                }
            }

            for(int r = rstart; r < rend; r++){
                for(int c=cstart; c < cend; c++){
                    int index = r*cols + c;
                    __TYPE O_ = abs(O[index]);
                    if(O_ > kappa) O_ = kappa;

                    F[index] = M[index]/kappa * pow(O_/kappa, alpha);
                }
            }


            Py_END_ALLOW_THREADS
            """ \
                % self.type_string

            multithreaded_weave = 0

            def run_inline(tile, O, M, mag, posx, posy, negx, negy, kappa, F,
                           alpha, n_tiles):
                inline(code, [  # , type_converters=converters.blitz)
                    'O',
                    'M',
                    'mag',
                    'posx',
                    'posy',
                    'negx',
                    'negy',
                    'kappa',
                    'F',
                    'alpha',
                    'n_tiles',
                    'tile',
                    ], verbose=0)

            if multithreaded_weave:
                n_tiles = 2
                foreach(lambda t: run_inline(
                        t,
                        O,
                        M,
                        mag,
                        posx,
                        posy,
                        negx,
                        negy,
                        kappa,
                        F,
                        alpha,
                        n_tiles,
                        ), range(0, n_tiles), 2)
            else:
                n_tiles = 1
                tile = 0
                inline(code, [
                    'O',
                    'M',
                    'mag',
                    'posx',
                    'posy',
                    'negx',
                    'negy',
                    'kappa',
                    'F',
                    'alpha',
                    'n_tiles',
                    'tile',
                    ], verbose=0)

            # Generate a Gaussian of size proportional to n to smooth and spread
            # the symmetry measure.  The Gaussian is also scaled in magnitude
            # by n so that large scales do not lose their relative weighting.
            # A = fspecial('gaussian',[n n], 0.25*n) * n;
            # S = S + filter2(A,F);

            if True:
                width = round(gaussian_kernel_cheat * n)
                if mod(width, 2) == 0:
                    width += 1
                gauss1d = scipy.signal.gaussian(width, 0.25
                        * n).astype(image.dtype)
                # print gauss1d.shape

                S += self.separable_convolution2d(F, gauss1d, gauss1d)
            else:
                S += F

        if False:
            width = round(gaussian_kernel_cheat * radii[len(radii) - 1])
            if mod(width, 2) == 0:
                width += 1
            gauss1d = scipy.signal.gaussian(width, 0.25
                    * width).astype(image.dtype)
            # print gauss1d.shape

            S = self.separable_convolution2d(S, gauss1d, gauss1d)

        S = S / len(radii)  # Average

        return S

    def find_minmax(self, image, **kwargs):
        # print "Here (woven)"
        # print image

        if image == None:
            return ([0, 0], [0])

        code = \
            """
            Py_BEGIN_ALLOW_THREADS


            int rows = Nimage[0];
            int cols = Nimage[1];

            #define __TYPE  %s

            __TYPE themax = -999999;
            __TYPE themin = 999999;

            for(int r = 0; r < rows; r++){
                for(int c = 0; c < cols; c++){

                    __TYPE *pixel_ptr = (__TYPE *)((char *)image_array->data + r * image_array->strides[0] + c * image_array->strides[1]);


                    if(*pixel_ptr > themax){

                        themax = *pixel_ptr;
                        coordinates[2] = (__TYPE)r;
                        coordinates[3] = (__TYPE)c;
                    }

                    if(*pixel_ptr < themin){

                        themin = *pixel_ptr;
                        coordinates[0] = (__TYPE)r;
                        coordinates[1] = (__TYPE)c;
                    }
                }
            }

            Py_END_ALLOW_THREADS
        """ \
            % self.type_string

        coordinates = array([0., 0., 0., 0.])
        themax = 0.
        themin = 0.

        inline(code, ['image', 'coordinates'])

        # print coordinates

        return (coordinates[0:2], coordinates[2:4])

    def _fast_clear_array2d(self, arr):

        code = \
            """
            Py_BEGIN_ALLOW_THREADS

            #define __TYPE  %s

            int rows = Narr[0];
            int cols = Narr[1];

            for(int r=0; r < rows; r++){
                for(int c=0; c < cols; c++){
                    __TYPE *arr_ptr = (__TYPE *)((char *)arr_array->data + r*arr_array->strides[0] + c*arr_array->strides[1]);
                    *arr_ptr = 0.0;
                }
            }

            Py_END_ALLOW_THREADS
            """ \
            % self.type_string

        inline(code, ['arr'])

        return


class WovenSSEBackend(WovenBackend):

    # NOTE: this isn't done well at all, and is not any faster than without SSE
    def separable_convolution2d(self, image, row, col, **kwargs):

        code = \
            """
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
                    __m128 vec;     // 128bit alignment
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
                    __TYPE *result_ptr = (__TYPE *)((char *)result_array->data + result_offset);
                    result_ptr[0] = 0.0;

                    for(int k = 0; k < col_width; k++){
                        int k_index = k - col_halfwidth + r;

                        //if(k_index < 0 || k_index > h) continue;
                        if(k_index < 0) k_index *= -1;  // reflect at boundaries
                        if(k_index >= h) k_index = h - (k - col_halfwidth);

                        __TYPE *image_ptr = (__TYPE *)((char *)firstpass_array->data + k_index*fp_r_stride + fp_c_stride*c);

                        __TYPE kernel_coef = *((__TYPE *)((char *)col_array->data + col_array->strides[0]*k));
                        __TYPE before = *result_ptr;
                        *result_ptr += kernel_coef * (*image_ptr);

                    }
                }
            }
            Py_END_ALLOW_THREADS
        """

        firstpass = zeros_like(image)
        result = zeros_like(image)
        inline(code, ['image', 'row', 'col', 'firstpass', 'result'], verbose=0,
               extra_compile_args=['-march=pentium4', '-msse3'],
               headers=['<xmmintrin.h>', '<emmintrin.h>', '<pmmintrin.h>'])

        return result


