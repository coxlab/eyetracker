from VanillaBackend import *
from WovenBackend import *

import numpy
import pyopencl as cl
mf = cl.mem_flags
import string

import stopwatch

KERNEL_RADIUS = 4
UNROLL_INNER_LOOP = True
KERNEL_W = 2 * KERNEL_RADIUS + 1
ROW_TILE_W = 128
KERNEL_RADIUS_ALIGNED = 16
COLUMN_TILE_W = 16
COLUMN_TILE_H = 48

class OpenCLBackend (VanillaBackend):

    def __init__(self):
        platforms = cl.get_platforms()
        self.platform = platforms[0]
        devices = self.platform.get_devices()
        self.device = devices[2]
        self.ctx = cl.Context([self.device])
        self.queue = cl.CommandQueue(self.ctx)
        self.autotuned = False
        self.intermediate_dev = None
        self.results_dev = None
        return
        
    def autotune(self, example_im, **kwargs):
        
        self.autotuned = True
        
        # pre-compile optimized OpenCL kernels
        
        # get kernel widths, etc. from the kwargs
        
        # sobel kernel

        
        # separable_convolution kernel
        nbytes = 4 * example_im.shape[0] * example_im.shape[1]
        
        self.intermediate_dev = cl.Buffer(self.ctx, mf.READ_WRITE, nbytes)
        # allocate a buffer for the result
        self.result_dev = cl.Buffer(self.ctx, mf.WRITE_ONLY, nbytes)

        if False:
            sep_conv_naive = """
                
                __kernel void separable_convolution_row(__global float *result, 
                                                        __global const float *input,
                                                        unsigned int image_width,
                                                        unsigned int image_height,
                                                        __global const float *kernel_row,
                                                        unsigned int kernel_width){
                   
                    
                    const int kernel_radius = kernel_width / 2;
                    
                    
                    int row = get_global_id(0);
                    int col = get_global_id(1);
                    
                    float sum = 0.0;
                    
                    int im_index = row * image_width + col;
                    
                    for(int i = 0; i < kernel_width; i++){
                        int k = i - kernel_radius;
                        if( (col + k) < 0 ){
                            k *= -1;
                        }
                        
                        if( (col + k) >= image_width){
                            k *= -1;
                        }
                        
                        sum += input[im_index + k] * kernel_row[i];
                        
                    }
                    
                    result[im_index] = sum;
                    return;
                }
                
                
                __kernel void separable_convolution_col(__global float *result, 
                                                        __global  const float *input,
                                                        unsigned int image_width,
                                                        unsigned int image_height,
                                                        __global  const float *kernel_col,
                                                        unsigned int kernel_width){
                   
                    
                    const int kernel_radius = kernel_width / 2;
                    
                    int row = get_global_id(0);
                    int col = get_global_id(1);
                     
                    float sum = 0.0;
                    
                    for(int i = 0; i < kernel_width; i++){
                        int k = i - kernel_radius;
                        
                        if( (row + k) < 0 ){
                            k *= -1;
                        }
                        
                        if( (row + k) >= image_height ){
                            k *= -1;
                        }
                        
                        int im_index = (row + k) * image_width + col;
                    
                        sum = sum + input[im_index]*kernel_col[i];
                        
                    }
                    result[row * image_width + col] = sum;
                    
                }
            """
            self.separable_convolution_program = cl.Program(self.ctx, sep_conv_naive)

            try:
                self.separable_convolution_program.build()
            except cl.RuntimeError as e:
                print(e)
                print(self.separable_convolution_program.get_build_info(self.device, cl.program_build_info.LOG))
                exit()


        if False:
            sep_conv_smarter = """
                
                __kernel void separable_convolution_row(__global float *result, 
                                                        __global const float *input,
                                                        unsigned int image_width,
                                                        unsigned int image_height,
                                                        __global const float *kernel_row,
                                                        unsigned int kernel_width){
                   
                    
                    
                    
                    const int kernel_radius = kernel_width / 2;
                    
                    
                    int row = get_global_id(0);
                    int col = get_global_id(1);
                    
                    float sum = 0.0;
                    
                    int im_index = row * image_width + col;
                    
                    for(int i = 0; i < kernel_width; i++){
                        int k = i - kernel_radius;
                        if( (col + k) < 0 ){
                            k *= -1;
                        }
                        
                        if( (col + k) >= image_width){
                            k *= -1;
                        }
                        
                        sum += input[im_index + k] * kernel_row[i];
                        
                    }
                    
                    result[im_index] = sum;
                    return;
                }
                
                
                __kernel void separable_convolution_col(__global float *result, 
                                                        __global  const float *input,
                                                        unsigned int image_width,
                                                        unsigned int image_height,
                                                        __global  const float *kernel_col,
                                                        unsigned int kernel_width){
                   
                    
                    const int kernel_radius = kernel_width / 2;
                    
                    int row = get_global_id(0);
                    int col = get_global_id(1);
                     
                    float sum = 0.0;
                    
                    for(int i = 0; i < kernel_width; i++){
                        int k = i - kernel_radius;
                        
                        if( (row + k) < 0 ){
                            k *= -1;
                        }
                        
                        if( (row + k) >= image_height ){
                            k *= -1;
                        }
                        
                        int im_index = (row + k) * image_width + col;
                    
                        sum = sum + input[im_index]*kernel_col[i];
                        
                    }
                    result[row * image_width + col] = sum;
                    
                }
            """
            self.separable_convolution_program = cl.Program(self.ctx, sep_conv_naive)

            try:
                self.separable_convolution_program.build()
            except cl.RuntimeError as e:
                print(e)
                print(self.separable_convolution_program.get_build_info(self.device, cl.program_build_info.LOG))
                exit()

        
        if True:
            # separable_convolution kernel
            
            template = """
            
                //24-bit multiplication is faster on G80,
                //but we must be sure to multiply integers
                //only within [-8M, 8M - 1] range
                
                //#define IMUL(a, b) __mul24(a, b)
                #define IMUL(a,b) a*b
                
                #define KERNEL_RADIUS $KERNEL_RADIUS
                #define KERNEL_W $KERNEL_W
                //__global float kernel_row[KERNEL_W];
                //__global float kernel_column[KERNEL_W];
                
                // Assuming ROW_TILE_W, KERNEL_RADIUS_ALIGNED and image_width 
                // are multiples of coalescing granularity size,
                // all global memory operations are coalesced in separable_convolution_row()
                #define     ROW_TILE_W              $ROW_TILE_W
                #define     KERNEL_RADIUS_ALIGNED   $KERNEL_RADIUS_ALIGNED

                // Assuming COLUMN_TILE_W and image_width are multiples
                // of coalescing granularity size, all global memory operations 
                // are coalesced in convolutionColumnGPU()
                #define COLUMN_TILE_W $COLUMN_TILE_W
                #define COLUMN_TILE_H $COLUMN_TILE_H
                
                __kernel void separable_convolution_row(__global float *result, 
                                                        __global const float *input,
                                                        unsigned image_width,
                                                        unsigned image_height,
                                                        __global const float *kernel_row){
            
                    __local float tile_cache[KERNEL_RADIUS + ROW_TILE_W + KERNEL_RADIUS];
                    
                    //Current tile and apron limits, relative to row start
                    const int         tile_start = IMUL(get_group_id(0), ROW_TILE_W);
                    const int           tile_end = tile_start + ROW_TILE_W - 1;
                    const int        apron_start = tile_start - KERNEL_RADIUS;
                    const int          apron_end = tile_end   + KERNEL_RADIUS;

                    //Clamp tile and apron limits by image borders
                    const int apron_start_clamped = max(apron_start, 0);
                    const int    tile_end_clamped = min(tile_end, (int)image_width - 1);
                    const int   apron_end_clamped = min(apron_end, (int)image_width - 1); 
                    
                    //Row start index in d_Data[]
                    const int          rowStart = IMUL(get_group_id(1), (int)image_width);

                    //Aligned apron start. Assuming image_width and ROW_TILE_W are multiples 
                    //of half-warp size, rowStart + apron_start_aligned is also a 
                    //multiple of half-warp size, thus having proper alignment 
                    //for coalesced d_Data[] read.
                    const int apron_start_aligned = tile_start - KERNEL_RADIUS_ALIGNED;

                    const int load_pos = apron_start_aligned + get_local_id(0);
                    //Set the entire data cache contents
                    //Load global memory values, if indices are within the image borders,
                    //or initialize with zeroes otherwise
                    if(load_pos >= apron_start){
                        const int local_mem_pos = load_pos - apron_start;

                        tile_cache[local_mem_pos] = 
                            ((load_pos >= apron_start_clamped) && (load_pos <= apron_end_clamped)) ?
                            input[rowStart + load_pos] : 0;
                    }

                    //Ensure the completness of the loading stage
                    //because results, emitted by each thread depend on the data,
                    //loaded by another threads
                    barrier(CLK_LOCAL_MEM_FENCE);
                    
                    const int write_pos = tile_start + get_local_id(0);
                    
                    //Assuming image_width and ROW_TILE_W are multiples of half-warp size,
                    //rowStart + tile_start is also a multiple of half-warp size,
                    //thus having proper alignment for coalesced d_Result[] write.
                    if(write_pos <= tile_end_clamped){
                        const int local_mem_pos = write_pos - apron_start;
                        float sum = 0;
                        
                        for(int k = -KERNEL_RADIUS; k <= KERNEL_RADIUS; k++){
                            sum += tile_cache[local_mem_pos + k] * kernel_row[KERNEL_RADIUS - k];
                        }
                        
                        result[rowStart + write_pos] = sum;
                    }
                }
                
                __kernel void separable_convolution_col(__global float *result,
                                                           __global const float *input,
                                                           int image_width,
                                                           int image_height,
                                                           __global const float *kernel_column,  
                                                           int local_mem_stride,
                                                           int global_mem_stride){
                    
                    //Data cache
                    __local float tile_cache[COLUMN_TILE_W * 
                    (KERNEL_RADIUS + COLUMN_TILE_H + KERNEL_RADIUS)];

                    //Current tile and apron limits, in rows
                    const int         tile_start = IMUL(get_group_id(1), COLUMN_TILE_H);
                    const int           tile_end = tile_start + COLUMN_TILE_H - 1;
                    const int        apron_start = tile_start - KERNEL_RADIUS;
                    const int          apron_end = tile_end   + KERNEL_RADIUS;

                    //Clamp tile and apron limits by image borders
                    const int    tile_end_clamped = min(tile_end, image_height - 1);
                    const int apron_start_clamped = max(apron_start, 0);
                    const int   apron_end_clamped = min(apron_end, image_height - 1);

                    //Current column index
                    const int       columnStart = IMUL(get_group_id(0), COLUMN_TILE_W) + get_local_id(0);

                    //Shared and global memory indices for current column
                    int local_mem_pos = IMUL(get_local_id(1), COLUMN_TILE_W) + get_local_id(0);
                    int global_mem_pos = IMUL(apron_start + get_local_id(1), image_width) + columnStart;
                    
                    //Cycle through the entire data cache
                    //Load global memory values, if indices are within the image borders,
                    //or initialize with zero otherwise
                    for(int y = apron_start + get_local_id(1); y <= apron_end; y += get_local_size(1)){
                        tile_cache[local_mem_pos] = ((y >= apron_start_clamped) && (y <= apron_end_clamped)) ? 
                                                                                input[global_mem_pos] : 0;
                        local_mem_pos += local_mem_stride;
                        global_mem_pos += global_mem_stride;
                    }

                    //Ensure the completness of the loading stage
                    //because results, emitted by each thread depend on the data, 
                    //loaded by another threads
                    barrier(CLK_LOCAL_MEM_FENCE);
                    
                    //Shared and global memory indices for current column
                    local_mem_pos = IMUL(get_local_id(1) + KERNEL_RADIUS, COLUMN_TILE_W) + get_local_id(0);
                    global_mem_pos = IMUL(tile_start + get_local_id(1) , image_width) + columnStart;
                    //Cycle through the tile body, clamped by image borders
                    //Calculate and output the results
                    for(int y = tile_start + get_local_id(1); y <= tile_end_clamped; y += get_local_size(1)){
                        float sum = 0;
               
                        for(int k = -KERNEL_RADIUS; k <= KERNEL_RADIUS; k++){
                            sum += tile_cache[local_mem_pos + IMUL(k, COLUMN_TILE_W)] * kernel_column[KERNEL_RADIUS - k];
                        }
                        
                        result[global_mem_pos] = sum;        
                        local_mem_pos += local_mem_stride;
                        global_mem_pos += global_mem_stride;
                    }
                }
                                
                """
            template = string.Template(template)
            code = template.substitute(KERNEL_RADIUS = KERNEL_RADIUS,  
                               KERNEL_W = KERNEL_W,  
                               COLUMN_TILE_H=COLUMN_TILE_H,  
                               COLUMN_TILE_W=COLUMN_TILE_W,  
                               ROW_TILE_W=ROW_TILE_W,  
                               KERNEL_RADIUS_ALIGNED=KERNEL_RADIUS_ALIGNED)
             
            self.separable_convolution_program = cl.Program(self.ctx, code)

        try:
            self.separable_convolution_program.build()
        except cl.RuntimeError as e:
            print(e)
            print(self.separable_convolution_program.get_build_info(self.device, cl.program_build_info.LOG))
            exit()
        
        # fast_radial_transform kernel
        
        return
        
    def transfer_to_device(self, im):
        
        im_device = None
        
        if(type(im) == cl._cl.Buffer):
            im_device = im  # already on the device
        else:
            im_device = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, 0, im)
        
        return im_device
    
    def transfer_from_device(self, result_dev, shape):
        result_host = numpy.zeros(shape, dtype="float32")
        evt = cl.enqueue_read_buffer(self.queue, result_dev, result_host)
        evt.wait()
        return result_host


    def _sobel_3x3(self, im, **kwargs):

        im_dev = self.transfer_to_device
        
        # do it!

        if "readback_from_device" in kwargs and kwargs["readback_from_device"]:
            imgx = self.transfer_from_device(imgx_dev)
            imgy = self.transfer_from_device(imgy_dev)
            mag = self.transfer_from_device(mag_dev)
        else:
            imgx = imgx_dev
            imgy = imgy_dev
            mag = mag_dev
            
        return (imgx, imgy, mag)
        
        
    def separable_convolution2d(self, im, row, col, **kwargs):
        return self._separable_convolution2d(im, row, col, **kwargs)
    
    @clockit
    def _separable_convolution2d(self, im, row, col, **kwargs):
        
        if(type(im) == cl._cl.Buffer):
            im_shape = kwargs["im_shape"]
        else:
            im_shape = im.shape
            
        if(type(row) == cl._cl.Buffer):
            row_shape = kwargs["row_shape"]
        else:
            row_shape = row.shape
            
        if(type(col) == cl._cl.Buffer):
            col_shape = kwargs["col_shape"]
        else:
            col_shape = col.shape

        (DATA_H, DATA_W) = im_shape
        
        nbytes = 4 * im_shape[0] * im_shape[1]
        
        # if on the host, shoot it up to the device
        im_dev = self.transfer_to_device(im)
        row_dev = self.transfer_to_device(row)
        col_dev = self.transfer_to_device(col)

        
        #allocate an intermediate result buffer
        if(self.intermediate_dev == None):
            self.intermediate_dev = cl.Buffer(self.ctx, mf.READ_WRITE, nbytes)
        
            # allocate a buffer for the result
            self.result_dev = cl.Buffer(self.ctx, mf.WRITE_ONLY, nbytes)
        
                
        # do the kernel magic
        prg = self.separable_convolution_program

        local_size_rows = (KERNEL_RADIUS_ALIGNED + ROW_TILE_W + KERNEL_RADIUS, 1, 1)
        local_size_cols = (COLUMN_TILE_W, 8, 1)
        
        DATA_H = numpy.int32(DATA_H)
        DATA_W = numpy.int32(DATA_W)
        
        local_mem_stride = numpy.int32(COLUMN_TILE_W * local_size_cols[1])
        global_mem_stride = numpy.int32(DATA_W * local_size_cols[1])

        print("Rows...")
        #exec_evt = prg.separable_convolution_row(self.queue, im_shape, self.intermediate_dev, im_dev, numpy.uint32(im_shape[1]), numpy.uint32(im_shape[0]), row_dev, numpy.uint32(row_shape[0]))
        exec_evt = prg.separable_convolution_row(self.queue, im_shape, self.result_dev, im_dev, numpy.uint32(im_shape[1]), numpy.uint32(im_shape[0]), row_dev)
        exec_evt.wait()

        print("Cols...")
        #exec_evt = prg.separable_convolution_col(self.queue, im_shape, self.result_dev, self.intermediate_dev, numpy.uint32(im_shape[1]), numpy.uint32(im_shape[0]), col_dev, numpy.uint32(col_shape[0]))
        #exec_evt = prg.separable_convolution_col(self.queue, im_shape, self.result_dev, self.intermediate_dev, numpy.uint32(im_shape[1]), numpy.uint32(im_shape[0]), col_dev, local_mem_stride, global_mem_stride)
        #exec_evt.wait()

        if ("readback_from_device" in kwargs) and (kwargs["readback_from_device"]):
            result = self.transfer_from_device(self.result_dev, im_shape)
            
        else:
            result = self.result_dev
            
        return result
        
    def _fast_radial_transform(self, im, radii, alpha, **kwargs):

        if readback_from_device:
            pass

        return S



if __name__ == "__main__":

    from numpy.random import rand
    import numpy
    from pylab import *
    
    test_im = (rand(768,1024)).astype(numpy.float32)
    row = array([0.25, 0.3, 0.4, 0.6, 0.7, 0.6, 0.4, 0.3, 0.25]).astype(numpy.float32)
    #row = array([0.25, 0.4, 0.6, 0.4, 0.25]).astype(numpy.float32)
    row = row / sum(row)
    
    col = row
    cl_backend = OpenCLBackend()
    vanilla_backend = VanillaBackend()
    woven_backend = WovenBackend()
    
    woven_backend.autotune(test_im)
    cl_backend.autotune(test_im)
    print("CL Filtering...")
    row_dev = cl.Buffer(cl_backend.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, 0, row.astype(float32))
    col_dev = cl.Buffer(cl_backend.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, 0, col.astype(float32))
    
    print cl_backend.device.name
    
    cl_filtered = cl_backend.separable_convolution2d(test_im.astype(float32), row_dev, col_dev, readback_from_device=False, im_shape=test_im.shape, row_shape=row.shape, col_shape=col.shape)
    for i in range(0,8):
        cl_filtered = cl_backend.separable_convolution2d(cl_filtered, row_dev, col_dev, readback_from_device=False, im_shape=test_im.shape, row_shape=row.shape, col_shape=col.shape)
    cl_filtered = cl_backend.separable_convolution2d(cl_filtered, row_dev, col_dev, readback_from_device=True, im_shape=test_im.shape, row_shape=row.shape, col_shape=col.shape)

    
    print "Vanilla Filtering..."
    vanilla_filtered = vanilla_backend.separable_convolution2d(test_im.astype(float32), row, col)
    for i in range(0,8):
        vanilla_filtered = vanilla_backend.separable_convolution2d(vanilla_filtered, row, col)
    vanilla_filtered = vanilla_backend.separable_convolution2d(vanilla_filtered, row, col) 

        
    print "Woven filtering..."
    woven_filtered = woven_backend.separable_convolution2d(test_im.astype(float32), row, col)
    for i in range(0,9):
        woven_filtered = woven_backend.separable_convolution2d(woven_filtered, row, col)
    
    #print(vanilla_filtered)
   
    #print(cl_filtered)
    
    vmin = 0.4
    vmax = 0.6
     
    subplot(3,1,1)
    imshow(cl_filtered, vmin=vmin, vmax=vmax)
    subplot(3,1,2)
    imshow(vanilla_filtered, vmin=vmin, vmax=vmax)
    subplot(3,1,3)
    imshow(woven_filtered, vmin=vmin, vmax=vmax)
    
    
    #show()