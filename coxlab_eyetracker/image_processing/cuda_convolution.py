import pycuda.autoinit
import pycuda.driver as cuda
import pycuda.compiler as cuda_compiler 
import numpy
from numpy.random import rand

import mako.template

class NoProgramToFreezeException (Exception):
    def __str__(self):
        return "No cl program to freeze"

class KernelMustUseFloat32Exception (Exception):
    def __str__(self):
        return "This kernel only operates on float32 data"

class UnknownArrayShapeException (Exception):
    def __str__(self):
        return "Array shape unknown for OpenCL buffer object"

# Helper functions for computing alignment...
def int_div_up(a, b):
    # Round a / b to nearest higher integer value
    a = numpy.int32(a)
    b = numpy.int32(b)
    return (a / b + 1) if (a % b != 0) else (a / b)

def int_div_down(a, b):
    # Round a / b to nearest lower integer value
    a = numpy.int32(a)
    b = numpy.int32(b)
    return a / b;

def int_align_up(a, b):
    # Align a to nearest higher multiple of b
    a = numpy.int32(a)
    b = numpy.int32(b)
    return (a - a % b + b) if (a % b != 0) else a

def int_align_down(a, b):
    # Align a to nearest lower multiple of b
    a = numpy.int32(a)
    b = numpy.int32(b)
    return a - a % b


class MetaKernel:

    def __init__(self, ctx):    
        self.cached_programs = {}
        self.cached_shapes = {}
        self.cached_types = {}
        
        
        #self.queue = queue
        #self.ctx = queue.get_info(cl.command_queue_info.CONTEXT)
        self.ctx = ctx
        
    def __call__(self, *args, **kwargs):
        return
    
    def freeze(self):
        if self.last_program is None:
            raise NoProgramToFreezeException
        self.frozen_program = self.last_program
        
    def thaw(self):
        self.frozen_program = None

    def cache_program(self, key, program):
        self.cached_programs[key] = program
        self.last_program = program

    #@clockit
    def transfer_to_device(self, buf):

        #self.ctx.push()
        buf_device = None
        buf_shape = None
        if(buf.__class__ == pycuda._driver.DeviceAllocation):
            buf_device = buf  # already on the device
            buf_shape = self.cached_shapes.get(buf_device, None)
            buf_type = self.cached_types.get(buf_device, None)
        else:
            buf_device = cuda.mem_alloc(buf.nbytes)
            cuda.memcpy_htod(buf_device, buf)
            self.cached_shapes[buf_device] = buf.shape
            self.cached_types[buf_device] = buf.dtype
            buf_shape = buf.shape
            buf_type = buf.dtype

        #self.ctx.pop()
        return (buf_device, buf_shape, buf_type)

    @clockit
    def transfer_from_device(self, result_device, result_host=None, **kwargs):
        self.ctx.push()
        if result_host is None:
            #print("Allocating result buffer")
            shape = self.cached_shapes.get(result_device, None)
            dtype = self.cached_types.get(result_device, None)
            #print dtype
            result_host = numpy.zeros(shape, dtype=dtype)
        
        cuda.memcpy_dtoh(result_host, result_device)
        self.ctx.pop()
        return result_host


# class NaiveSeparableConvolutionKernel (MetaKernel):
#     def __init__(self, queue):
#         MetaKernel.__init__(self,queue)
#         self.cached_intermediate_buffers = {}
#         self.cached_result_buffers = {}
#         self.cached_row_kernels = {}
#         self.cached_col_kernels = {}
#      
#     ##@clockit   
#     def build_program(self):
#         
#         code = """
#             __kernel void separable_convolution_row(__global float *result, 
#                                                     __global const float *input,
#                                                     unsigned int image_width,
#                                                     unsigned int image_height,
#                                                     __global const float *kernel_row,
#                                                     unsigned int kernel_width){
# 
#                 const int kernel_radius = kernel_width / 2;
# 
#                 int row = get_global_id(0);
#                 int col = get_global_id(1);
# 
#                 float sum = 0.0;
# 
#                 int im_index = row * image_width + col;
# 
#                 for(int i = 0; i < kernel_width; i++){
#                     int k = i - kernel_radius;
#                     if( (col + k) < 0 ){
#                         k *= -1;
#                     }
# 
#                     if( (col + k) >= image_width){
#                         k *= -1;
#                     }
# 
#                     sum += input[im_index + k] * kernel_row[i];
# 
#                 }
# 
#                 result[im_index] = sum;
#                 return;
#             }
# 
# 
#             __kernel void separable_convolution_col(__global float *result, 
#                                                     __global  const float *input,
#                                                     unsigned int image_width,
#                                                     unsigned int image_height,
#                                                     __global  const float *kernel_col,
#                                                     unsigned int kernel_width){
# 
# 
#                 const int kernel_radius = kernel_width / 2;
# 
#                 int row = get_global_id(0);
#                 int col = get_global_id(1);
# 
#                 float sum = 0.0;
# 
#                 for(int i = 0; i < kernel_width; i++){
#                     int k = i - kernel_radius;
# 
#                     if( (row + k) < 0 ){
#                         k *= -1;
#                     }
# 
#                     if( (row + k) >= image_height ){
#                         k *= -1;
#                     }
# 
#                     int im_index = (row + k) * image_width + col;
# 
#                     sum = sum + input[im_index]*kernel_col[i];
# 
#                 }
#                 result[row * image_width + col] = sum;
# 
#             }
#         """
#         program = cl.Program(self.ctx, code)
# 
#         try:
#             program.build()
#         except cl.RuntimeError as e:
#             print(e)
#             exit()
#             
#         self.cache_program(None, program)
#             
#         return program
# 
#     ##@clockit
#     def __call__(self, input_im, row_kernel, col_kernel, result=None, input_shape=None, row_shape=None, col_shape=None, **kwargs):
#         
#         use_cached_buffers = kwargs.get("use_cached_buffers", True)
#         
#         if input_im.__class__ == numpy.ndarray and input_im.dtype != numpy.float32:
#             raise KernelMustUseFloat32Exception
#         
#         
#         (input_dev, input_shape, input_type) = self.transfer_to_device(input_im)
#         (row_dev, row_shape, row_type) = self.transfer_to_device(row_kernel)
#         (col_dev, col_shape, col_type) = self.transfer_to_device(col_kernel)
#         
#         if input_shape is None:
#             raise UnknownArrayShapeException
#                 
#         if row_shape is None:
#             raise UnknownArrayShapeException
#                 
#         if col_shape is None:
#             raise UnknownArrayShapeException
#                 
#         if None in self.cached_programs:
#             prg = self.cached_programs[None]
#         else:
#             prg = self.build_program()
#         
#         
#         # a device buffer for the intermediate result
#         intermediate_dev = None
#         if (use_cached_buffers) and (input_shape in self.cached_intermediate_buffers):
#             intermediate_dev = self.cached_intermediate_buffers[input_shape]
#         else:
#             intermediate_dev = cl.Buffer(self.ctx, mf.READ_WRITE, input_shape[0] * input_shape[1] * 4)
#             self.cached_intermediate_buffers[input_shape] = intermediate_dev
#         
#         # a device buffer for the result, if not already supplied
#         result_dev = None
#         if result is None or result.__class__ == numpy.ndarray:
#             # need to make or repurpose a device buffer
#             if (use_cached_buffers) and (input_shape in self.cached_result_buffers):
#                 result_dev  = self.cached_result_buffers[input_shape]
#             else:
#                 result_dev = cl.Buffer(self.ctx, mf.READ_WRITE, input_shape[0] * input_shape[1] * 4)
#                 self.cached_result_buffers[input_shape] = result_dev
#                 self.cached_shapes[results_dev] = input_shape
#                 self.cached_types[results_dev] = input_type
#         else:
#             # assume that result is a device buffer already (possibly not a safe assumption)
#             result_dev = result
#                         
#         t = Timer()
#         try:
#             exec_evt = prg.separable_convolution_row(self.queue, input_shape, intermediate_dev, input_dev, numpy.uint32(input_shape[1]), numpy.uint32(input_shape[0]), row_dev, numpy.uint32(row_shape[0]))
#         except Exception as e:
#             print(input_shape)
#             print(intermediate_dev)
#             print(input_dev)
#             print(row_dev)
#             print(row_shape)
#             raise e
#         exec_evt.wait()
#         print("Rows in %f" % t.elapsed)
# 
#         t = Timer()
#         try:
#             exec_evt = prg.separable_convolution_col(self.queue, input_shape, result_dev, intermediate_dev, numpy.uint32(input_shape[1]), numpy.uint32(input_shape[0]), col_dev, numpy.uint32(col_shape[0]))
#         except Exception as e:
#             print(input_shape)
#             print(result_dev)
#             print(intermediate_dev)
#             print(row_dev)
#             print(row_shape)
#             raise e
#         exec_evt.wait()
#         print("Cols in %f" % t.elapsed)
# 
#         if kwargs.get("readback_from_device", False):
#             if result is None:
#                 result = self.transfer_from_device(result_dev, shape=input_shape)
#             else:
#                 self.transfer_from_device(result_dev, result)
#         else:
#             result = result_dev
# 
#         return result

            
class LocalMemorySeparableConvolutionKernel (MetaKernel):
    def __init__(self, ctx):
        MetaKernel.__init__(self, ctx)
        self.cached_intermediate_buffers = {}
        self.cached_result_buffers = {}
        self.cached_row_kernels = {}
        self.cached_col_kernels = {}

    ##@clockit   
    def build_program(self, dtype, im_shape, row_kernel_radius, row_kernel_radius_aligned, row_tile_width, col_kernel_radius, col_tile_width, col_tile_height, col_hstride):

        row_kernel_width = row_kernel_radius * 2 + 1
        col_kernel_width = col_kernel_radius * 2 + 1
        
        tile_cache_width = row_kernel_radius * 2 + row_tile_width
        (image_height, image_width) = im_shape
        
        col_input_load_stride = image_width * col_hstride
        col_tile_cache_stride = col_tile_width * col_hstride

        TYPE = ""
        if dtype == numpy.float32:
            TYPE = "float"
        elif dtype == numpy.uint8:
            TYPE = "unsigned char"
        elif dtype == numpy.uint16:
            TYPE = "unsigned short"
        
        code = """

            __global__ void separable_convolution_row(${TYPE} *output, 
                                                      ${TYPE} *input,
                                                      float *row_kernel){

                __shared__ ${TYPE} tile_cache[${tile_cache_width}];
                
                // --------------------------------------------------------------------
                // Cooperatively load a tile of data into the local memory tile cache
                // --------------------------------------------------------------------                
                
                // Some critical indices
                // "tile" = area where we will actually compute output values (for this work group)
                // "apron" = additional area of the input on either side that we need to access to compute those outputs
                const int   tile_start = blockIdx.x * ${row_tile_width};
                const int   tile_end = tile_start + ${row_tile_width} - 1;
                const int   apron_start = tile_start - ${row_kernel_radius};
                const int   apron_end = tile_end + ${row_kernel_radius};
                
                // "Clamp" the indices that would otherwise be off the end of the image
                const int   tile_end_clamped = min(tile_end, ${image_width}-1); // don't run tile off of end of image
                const int   apron_start_clamped = max(apron_start, 0); // don't run apron past beginning
                const int   apron_end_clamped = min(apron_end, ${image_width}-1); // don't run apron past end
                
                // Compute the linear offset for this particular row
                const int   row_start_offset = blockIdx.y * ${image_width};  // n * width for the nth row
                
                
                // Align the start of the apron so that we get coallesced reads.  This may mean reading extra data that we
                // otherwise would not care about, but it is much faster this way, since the memory can be read all at once
                const int apron_start_aligned = tile_start - ${row_kernel_radius_aligned};
                
                // Compute the data position that this particular thread will load
                const int input_load_offset = apron_start_aligned + threadIdx.x;
                
                // Do the actual load
                if(input_load_offset >= apron_start){
                    const int tile_cache_offset = input_load_offset - apron_start;  // get the comparable offset in the cache
                    
                    if(input_load_offset < 0){
                        tile_cache[tile_cache_offset] = input[row_start_offset - input_load_offset];
                    } else if(input_load_offset > apron_end_clamped){
                        tile_cache[tile_cache_offset] = input[row_start_offset + (2*apron_end_clamped - input_load_offset)];
                    } else {
                        tile_cache[tile_cache_offset] = input[row_start_offset + input_load_offset];
                    } 
                }
                
                // At this point, hopefully all of the data we need is loaded into the tile cache
                
                // Synchronize with the other threads so that we're sure we've loaded
                __syncthreads();
                
                
                // --------------------------------------------------------------------
                // Compute the convolution value for this thread's assigned pixel
                // --------------------------------------------------------------------

                // compute where the result will go
                const int output_write_offset = tile_start + threadIdx.x;

                if(output_write_offset <= tile_end_clamped){ // don't write off end of row
                    const int tile_cache_read_offset = output_write_offset - apron_start;
                    float sum = 0;
                    
                    %for r in range(-row_kernel_radius, row_kernel_radius+1):
                        sum += (float)tile_cache[tile_cache_read_offset + (${r})] * row_kernel[${row_kernel_radius} - (${r})];
                    %endfor
                    //sum = tile_cache[tile_cache_read_offset + ${row_kernel_radius}];
                    //sum = 1.0;
                
                    // write the output back to global memory
                    output[row_start_offset + output_write_offset] = (${TYPE})sum;
                }

            }
            
            
            __global__ void separable_convolution_col(${TYPE} *output, 
                                                      ${TYPE} *input,
                                                      float *col_kernel){


                __shared__ float tile_cache[${col_tile_width} * (2*${col_kernel_radius} + ${col_tile_height})];

                
                // --------------------------------------------------------------------
                // Cooperatively load a tile of data into the local memory tile cache
                // --------------------------------------------------------------------                
                
                // Some critical indices
                // "tile" = area where we will actually compute output values (for this work group)
                // "apron" = additoinal area of the input on either side that we need to access to compute those outputs
                const int   tile_start = blockIdx.y * ${col_tile_height};
                const int   tile_end = tile_start + ${col_tile_height} - 1;
                const int   apron_start = tile_start - ${col_kernel_radius};
                const int   apron_end = tile_end + ${col_kernel_radius};
                
                // "Clamp" the indices that would otherwise be off the end of the image
                const int   tile_end_clamped = min(tile_end, ${image_height}-1);
                const int   apron_start_clamped = max(apron_start, 0);
                const int   apron_end_clamped = min(apron_end, ${image_height}-1);
                
                // Compute the linear offset for this particular column
                const int   col_start_offset = blockIdx.x * ${col_tile_width} + threadIdx.x;
                
                
                ## // Align the start of the apron so that we get coallesced reads.  This may mean reading extra data that we
                ## // otherwise would not care about, but it is much faster this way, since the memory can be read all at once
                
                
                // Compute the starting data position that this particular thread will load
                int     input_load_offset = (apron_start + threadIdx.y) * ${image_width} + col_start_offset;
                
                // Compute the starting position to load data into in the tile cache
                int     tile_cache_offset = threadIdx.y * ${col_tile_width} + threadIdx.x;
                
                // Do the actual loads
                for(int y = apron_start + threadIdx.y; y <= apron_end; y += blockDim.y){
                    if( y < 0 ){
                        tile_cache[tile_cache_offset] = (float)input[col_start_offset - y *${image_width}];
                    } else if(y > apron_end_clamped){
                        tile_cache[tile_cache_offset] = (float)input[col_start_offset + (2*apron_end_clamped-y)*${image_width}];
                    } else {
                        tile_cache[tile_cache_offset] = (float)input[input_load_offset];
                    }
                    
                    input_load_offset += ${col_input_load_stride};
                    tile_cache_offset += ${col_tile_cache_stride};
                }
                
                
                // At this point, hopefully all of the data we need is loaded into the tile cache
                
                // Synchronize with the other threads so that we're sure we've loaded
                __syncthreads();
                
                // --------------------------------------------------------------------
                // Compute the covolution value for this thread's assigned pixel
                // --------------------------------------------------------------------

                input_load_offset = (tile_start + threadIdx.y) * ${image_width} + col_start_offset;
                tile_cache_offset = (threadIdx.y + ${col_kernel_radius}) * ${col_tile_width} + threadIdx.x;
                
                for(int y = tile_start + threadIdx.y; y <= tile_end_clamped; y += blockDim.y){
                    float sum = 0;
                    
                    %for k in range(-col_kernel_radius, col_kernel_radius+1):
                        sum += tile_cache[tile_cache_offset + (${k}*${col_tile_width})] * col_kernel[${col_kernel_radius} - (${k})]; 
                    %endfor
                    
                    output[input_load_offset] = (${TYPE})sum;
                    input_load_offset += ${col_input_load_stride};
                    tile_cache_offset += ${col_tile_cache_stride};
                }

            }
        """
        
        local_vars = locals()
        local_vars.pop("self")
        templated_code = mako.template.Template(code).render(**local_vars)
        #print templated_code
        
        try:
            program = cuda_compiler.SourceModule(templated_code)
        except Exception as e:
            print(e)
            exit()

        self.cache_program((dtype, im_shape, row_kernel_radius, row_kernel_radius_aligned, row_tile_width, col_kernel_radius, col_tile_width, col_tile_height, col_hstride), program)

        return program

    @clockit
    def __call__(self, input_im, row_kernel, col_kernel, result=None, input_shape=None, row_shape=None, col_shape=None, **kwargs):

        self.ctx.push()
        use_cached_buffers = kwargs.get("use_cached_buffers", True)

        if input_im.__class__ == numpy.ndarray and input_im.dtype != numpy.float32:
            raise KernelMustUseFloat32Exception


        (input_dev, input_shape, input_type) = self.transfer_to_device(input_im)
        (row_dev, row_shape, row_type) = self.transfer_to_device(row_kernel)
        (col_dev, col_shape, col_type) = self.transfer_to_device(col_kernel)

        if input_shape is None:
            raise UnknownArrayShapeException

        if row_shape is None:
            raise UnknownArrayShapeException

        if col_shape is None:
            raise UnknownArrayShapeException

        row_tile_width = 128
        col_tile_width = 16
        col_tile_height = 48
        col_hstride = 8
        assert numpy.mod(row_shape[0],2) == 1, "Kernels must be of odd width"
        row_kernel_radius = row_shape[0] / 2

        coallescing_quantum = 16
        row_kernel_radius_aligned = (row_kernel_radius / coallescing_quantum) * coallescing_quantum
        if row_kernel_radius_aligned == 0:
            row_kernel_radius_aligned = coallescing_quantum

        assert numpy.mod(col_shape[0],2) == 1, "Kernels must be of odd width"
        col_kernel_radius = col_shape[0] / 2
        
        #build_args = (im_shape, row_kernel_radius, row_kernel_radius_aligned, row_tile_width, col_kernel_radius, col_tile_width, col_tile_height, col_hstride
        build_args = (input_type, input_shape, row_kernel_radius, row_kernel_radius_aligned, row_tile_width, col_kernel_radius, col_tile_width, col_tile_height, col_hstride)
        if build_args in self.cached_programs:
            prg = self.cached_programs[build_args]
        else:
            prg = self.build_program(*build_args)

        row_local_size = (row_kernel_radius_aligned + row_tile_width + row_kernel_radius, 1,1)
        row_group_size = (int_div_up(input_shape[1],row_tile_width), input_shape[0])
        row_global_size = (row_local_size[0]*row_group_size[0], row_local_size[1]*row_group_size[1])

        col_local_size = (col_tile_width, col_hstride,1)
        col_group_size = (int_div_up(input_shape[1],col_tile_width), int_div_up(input_shape[0], col_tile_height)) 
        col_global_size = (col_local_size[0]*col_group_size[0], col_local_size[1]*col_group_size[1])
        
        #print col_local_size
        #print col_group_size
        #print col_global_size

        # a device buffer for the intermediate result
        intermediate_dev = None
        if (use_cached_buffers) and ((input_shape, input_type) in self.cached_intermediate_buffers):
            intermediate_dev = self.cached_intermediate_buffers[(input_shape, input_type)]
        else:
            dummy = numpy.array([1], dtype=input_type)
            intermediate_dev = cuda.mem_alloc(input_shape[0] * input_shape[1] * dummy.itemsize)
            self.cached_intermediate_buffers[(input_shape, input_type)] = intermediate_dev

        # a device buffer for the result, if not already supplied
        result_dev = None
        if result is None or result.__class__ == numpy.ndarray:
            # need to make or repurpose a device buffer
            if (use_cached_buffers) and ((input_shape, input_type) in self.cached_result_buffers):
                result_dev  = self.cached_result_buffers[(input_shape, input_type)]
                #print "Here"
                #print(result_dev)
            else:
                dummy = numpy.array([1], dtype=input_type)
                result_dev = cuda.mem_alloc(input_shape[0] * input_shape[1] * dummy.itemsize)
                self.cached_result_buffers[(input_shape, input_type)] = result_dev
                self.cached_shapes[result_dev] = input_shape
                self.cached_types[result_dev] = input_type
        else:
            # assume that result is a device buffer already (possibly not a safe assumption)
            result_dev = result

        #t = Timer()
        try:
           f = prg.get_function("separable_convolution_row")
           f(intermediate_dev, input_dev, row_dev, grid=[int(e) for e in row_group_size], block=[int(e) for e in row_local_size])
           self.ctx.synchronize()
        except Exception as e:
           print(input_shape)
           print(intermediate_dev)
           print(input_dev)
           print(row_dev)
           print(row_global_size)
           print(row_local_size)
           raise e
        
        try:
            f = prg.get_function("separable_convolution_col")
            f(result_dev, intermediate_dev, col_dev, grid= [int(e) for e in col_group_size], block=[int(e) for e in col_local_size])
            self.ctx.synchronize()
        except Exception as e:
            print(input_shape)
            print(result_dev)
            print(intermediate_dev)
            print(row_dev)
            print(row_shape)
            raise e
            
        #print("Elapsed: %f" % t.elapsed)

        if kwargs.get("readback_from_device", False):
            if result is None:
                result = self.transfer_from_device(result_dev, shape=input_shape)
            else:
                self.transfer_from_device(result_dev, result)
        else:
            result = result_dev


        self.ctx.pop()
        return result


def gaussian_kernel(width = 17, sigma = 4.0):
    assert width == numpy.floor(width),  'argument width should be an integer!'
    radius = (width - 1)/2.0
    x = numpy.linspace(-radius,  radius,  width)
    x = numpy.float32(x)
    sigma = numpy.float32(sigma)
    filterx = x*x / (2 * sigma * sigma)
    filterx = numpy.exp(-1 * filterx)
    assert filterx.sum()>0,  'something very wrong if gaussian kernel sums to zero!'
    filterx /= filterx.sum()
    return filterx

    
if __name__ == "__main__":
    
    cuda.init()
    assert cuda.Device.count() >= 1

    dev = cuda.Device(0)
    ctx = dev.make_context()
    
    convolution_kernel = LocalMemorySeparableConvolutionKernel(ctx)  
    
    w = 640
    h = 480
    
    #result_im = numpy.zeros_like(test_im)
    row = gaussian_kernel(17, 4.0)
    col = gaussian_kernel(17, 4.0)
    #row = numpy.array([-1., 0., 1.])
    #col = numpy.array([1., 2., 1.])
    
    (row_dev, dummy, dummy2) = convolution_kernel.transfer_to_device(row)
    (col_dev, dummy, dummy2) = convolution_kernel.transfer_to_device(col)
    
    print("float32")
    
    test_im = rand(h,w).astype(numpy.float32)
    (test_im_dev,dummy,dummy2) = convolution_kernel.transfer_to_device(test_im)
    
    if True:
        result = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=True)
        t = Timer()
        for i in range(0,200):
            result = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=False)
        result = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=True)
        print("Total time: %f" % t.elapsed)
    
    print result
    
    if False:
        from pylab import *
        imshow(result, interpolation='nearest')
        colorbar()
        show()
    