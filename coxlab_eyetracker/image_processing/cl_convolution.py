
import pyopencl as cl
import numpy
from numpy.random import rand

import mako.template
mf = cl.mem_flags

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


class DeviceBuffer(cl.Buffer):
    def __init__(self, ctx, flags, arr=None, **kwargs):
        
        if arr is not None:
            cl.Buffer.__init__(self, ctx, flags, 0, arr)
            self.shape = arr.shape
            self.dtype = arr.dtype
        else:
            self.shape = kwargs.get("shape", None)
            if self.shape is None:
                raise UnknownShapeException
            self.dtype = kwargs.get("dtype", numpy.float32)
            dummy = numpy.zeros((1,1), dtype=self.dtype)
            cl.Buffer.__init__(self, ctx, flags, dummy.itemsize * self.shape[0] * self.shape[1])
        
class MetaKernel:

    def __init__(self, queue):    
        self.cached_programs = {}
        self.last_program = None
        self.frozen_program = None
        self.queue = queue
        self.ctx = queue.get_info(cl.command_queue_info.CONTEXT)
        
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

        if(buf.__class__ == DeviceBuffer):
            buf_device = buf  # already on the device
        else:
            #buf_device = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, 0, buf)
            buf_device = DeviceBuffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, buf)
            
        return buf_device

    @clockit
    def transfer_from_device(self, result_device, result_host=None, **kwargs):
        if result_host is None:
            #print("Allocating result buffer")
            shape = result_device.shape
            dtype = result_device.dtype
            print dtype
            result_host = numpy.zeros(shape, dtype=dtype)
            
        evt = cl.enqueue_read_buffer(self.queue, result_device, result_host)
        evt.wait()
        return result_host


class NaiveSeparableConvolutionKernel (MetaKernel):
    def __init__(self, queue):
        MetaKernel.__init__(self,queue)
        self.cached_intermediate_buffers = {}
        self.cached_result_buffers = {}
        self.cached_row_kernels = {}
        self.cached_col_kernels = {}
     
    ##@clockit   
    def build_program(self):
        
        code = """
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
        program = cl.Program(self.ctx, code)

        try:
            program.build()
        except cl.RuntimeError as e:
            print(e)
            exit()
            
        self.cache_program(None, program)
            
        return program

    ##@clockit
    def __call__(self, input_im, row_kernel, col_kernel, result=None, input_shape=None, row_shape=None, col_shape=None, **kwargs):
        
        use_cached_buffers = kwargs.get("use_cached_buffers", True)
        
        if input_im.__class__ == numpy.ndarray and input_im.dtype != numpy.float32:
            raise KernelMustUseFloat32Exception
        
        
        input_dev = self.transfer_to_device(input_im)
        row_dev = self.transfer_to_device(row_kernel)
        col_dev = self.transfer_to_device(col_kernel)
        
                
        if None in self.cached_programs:
            prg = self.cached_programs[None]
        else:
            prg = self.build_program()
        
        
        # a device buffer for the intermediate result
        intermediate_dev = None
        if (use_cached_buffers) and (input_shape in self.cached_intermediate_buffers):
            intermediate_dev = self.cached_intermediate_buffers[input_im.shape]
        else:
            intermediate_dev = DeviceBuffer(self.ctx, mf.READ_WRITE, shape = input_im.shape, dtype=input_im.dtype)
            self.cached_intermediate_buffers[input_shape] = intermediate_dev
        
        # a device buffer for the result, if not already supplied
        result_dev = None
        if result is None or result.__class__ == numpy.ndarray:
            # need to make or repurpose a device buffer
            if (use_cached_buffers) and (input_shape in self.cached_result_buffers):
                result_dev  = self.cached_result_buffers[input_shape]
            else:
                result_dev = DeviceBuffer(self.ctx, mf.READ_WRITE, input_im.shape[0] * input_im.shape[1] * 4)
                self.cached_result_buffers[input_shape] = result_dev
                
        else:
            # assume that result is a device buffer already (possibly not a safe assumption)
            result_dev = result
                        
        t = Timer()
        try:
            exec_evt = prg.separable_convolution_row(self.queue, input_im.shape, intermediate_dev, input_dev, numpy.uint32(input_im.shape[1]), numpy.uint32(input_im.shape[0]), row_dev, numpy.uint32(row.shape[0]))
        except Exception as e:
            print(input_im.shape)
            print(intermediate_dev)
            print(input_dev)
            print(row_dev)
            print(row.shape)
            raise e
        exec_evt.wait()
        print("Rows in %f" % t.elapsed)

        t = Timer()
        try:
            exec_evt = prg.separable_convolution_col(self.queue, input_im.shape, result_dev, intermediate_dev, numpy.uint32(input_im.shape[1]), numpy.uint32(input_im.shape[0]), col_dev, numpy.uint32(col.shape[0]))
        except Exception as e:
            print(input_im.shape)
            print(result_dev)
            print(intermediate_dev)
            print(col_dev)
            print(col.shape)
            raise e
        exec_evt.wait()
        print("Cols in %f" % t.elapsed)

        if kwargs.get("readback_from_device", False):
            if result is None:
                result = self.transfer_from_device(result_dev, shape=input_im.shape)
            else:
                self.transfer_from_device(result_dev, result)
        else:
            result = result_dev

        return result

            
class LocalMemorySeparableConvolutionKernel (MetaKernel):
    def __init__(self, queue):
        MetaKernel.__init__(self,queue)
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

            __kernel void separable_convolution_row(__global ${TYPE} *output, 
                                                    __global const ${TYPE} *input,
                                                    __global const float *row_kernel){

                __local ${TYPE} tile_cache[${tile_cache_width}];
                
                // --------------------------------------------------------------------
                // Cooperatively load a tile of data into the local memory tile cache
                // --------------------------------------------------------------------                
                
                // Some critical indices
                // "tile" = area where we will actually compute output values (for this work group)
                // "apron" = additional area of the input on either side that we need to access to compute those outputs
                const int   tile_start = get_group_id(0) * ${row_tile_width};
                const int   tile_end = tile_start + ${row_tile_width} - 1;
                const int   apron_start = tile_start - ${row_kernel_radius};
                const int   apron_end = tile_end + ${row_kernel_radius};
                
                // "Clamp" the indices that would otherwise be off the end of the image
                const int   tile_end_clamped = min(tile_end, ${image_width}-1); // don't run tile off of end of image
                const int   apron_start_clamped = max(apron_start, 0); // don't run apron past beginning
                const int   apron_end_clamped = min(apron_end, ${image_width}-1); // don't run apron past end
                
                // Compute the linear offset for this particular row
                const int   row_start_offset = get_group_id(1) * ${image_width};  // n * width for the nth row
                
                
                // Align the start of the apron so that we get coallesced reads.  This may mean reading extra data that we
                // otherwise would not care about, but it is much faster this way, since the memory can be read all at once
                const int apron_start_aligned = tile_start - ${row_kernel_radius_aligned};
                
                // Compute the data position that this particular thread will load
                const int input_load_offset = apron_start_aligned + get_local_id(0);
                
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
                barrier(CLK_LOCAL_MEM_FENCE);
                
                
                // --------------------------------------------------------------------
                // Compute the convolution value for this thread's assigned pixel
                // --------------------------------------------------------------------

                // compute where the result will go
                const int output_write_offset = tile_start + get_local_id(0);

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
            
            
            __kernel void separable_convolution_col(__global ${TYPE} *output, 
                                                    __global  const ${TYPE} *input,
                                                    __global  const float *col_kernel){


                __local float tile_cache[${col_tile_width} * (2*${col_kernel_radius} + ${col_tile_height})];

                
                // --------------------------------------------------------------------
                // Cooperatively load a tile of data into the local memory tile cache
                // --------------------------------------------------------------------                
                
                // Some critical indices
                // "tile" = area where we will actually compute output values (for this work group)
                // "apron" = additoinal area of the input on either side that we need to access to compute those outputs
                const int   tile_start = get_group_id(1) * ${col_tile_height};
                const int   tile_end = tile_start + ${col_tile_height} - 1;
                const int   apron_start = tile_start - ${col_kernel_radius};
                const int   apron_end = tile_end + ${col_kernel_radius};
                
                // "Clamp" the indices that would otherwise be off the end of the image
                const int   tile_end_clamped = min(tile_end, ${image_height}-1);
                const int   apron_start_clamped = max(apron_start, 0);
                const int   apron_end_clamped = min(apron_end, ${image_height}-1);
                
                // Compute the linear offset for this particular column
                const int   col_start_offset = get_group_id(0) * ${col_tile_width} + get_local_id(0);
                
                
                ## // Align the start of the apron so that we get coallesced reads.  This may mean reading extra data that we
                ## // otherwise would not care about, but it is much faster this way, since the memory can be read all at once
                
                
                // Compute the starting data position that this particular thread will load
                int     input_load_offset = (apron_start + get_local_id(1)) * ${image_width} + col_start_offset;
                
                // Compute the starting position to load data into in the tile cache
                int     tile_cache_offset = get_local_id(1) * ${col_tile_width} + get_local_id(0);
                
                // Do the actual loads
                for(int y = apron_start + get_local_id(1); y <= apron_end; y += get_local_size(1)){
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
                barrier(CLK_LOCAL_MEM_FENCE);
                
                // --------------------------------------------------------------------
                // Compute the covolution value for this thread's assigned pixel
                // --------------------------------------------------------------------

                input_load_offset = (tile_start + get_local_id(1)) * ${image_width} + col_start_offset;
                tile_cache_offset = (get_local_id(1) + ${col_kernel_radius}) * ${col_tile_width} + get_local_id(0);
                
                for(int y = tile_start + get_local_id(1); y <= tile_end_clamped; y += get_local_size(1)){
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
        program = cl.Program(self.ctx, templated_code)

        try:
            program.build()
        except cl.RuntimeError as e:
            print(e)
            exit()

        self.cache_program((dtype, im_shape, row_kernel_radius, row_kernel_radius_aligned, row_tile_width, col_kernel_radius, col_tile_width, col_tile_height, col_hstride), program)

        return program

    @clockit
    def __call__(self, input_im, row_kernel, col_kernel, result=None, input_shape=None, row_shape=None, col_shape=None, **kwargs):

        use_cached_buffers = kwargs.get("use_cached_buffers", True)

        if input_im.__class__ == numpy.ndarray and input_im.dtype != numpy.float32:
            raise KernelMustUseFloat32Exception

        wait_for = kwargs.get("wait_for", None)

        input_dev = self.transfer_to_device(input_im)
        row_dev = self.transfer_to_device(row_kernel)
        col_dev = self.transfer_to_device(col_kernel)



        row_tile_width = 128
        col_tile_width = 16
        col_tile_height = 48
        col_hstride = 8
        assert numpy.mod(row.shape[0],2) == 1, "Kernels must be of odd width"
        row_kernel_radius = row.shape[0] / 2

        coallescing_quantum = 16
        row_kernel_radius_aligned = (row_kernel_radius / coallescing_quantum) * coallescing_quantum
        if row_kernel_radius_aligned == 0:
            row_kernel_radius_aligned = coallescing_quantum

        assert numpy.mod(col.shape[0],2) == 1, "Kernels must be of odd width"
        col_kernel_radius = col.shape[0] / 2
        
        #build_args = (im_type, im_shape, row_kernel_radius, row_kernel_radius_aligned, row_tile_width, col_kernel_radius, col_tile_width, col_tile_height, col_hstride
        build_args = (input_im.dtype, input_im.shape, row_kernel_radius, row_kernel_radius_aligned, row_tile_width, col_kernel_radius, col_tile_width, col_tile_height, col_hstride)
        if build_args in self.cached_programs:
            prg = self.cached_programs[build_args]
        else:
            prg = self.build_program(*build_args)

        row_local_size = (row_kernel_radius_aligned + row_tile_width + row_kernel_radius, 1)
        row_group_size = (int_div_up(input_im.shape[1],row_tile_width), input_im.shape[0])
        row_global_size = (row_local_size[0]*row_group_size[0], row_local_size[1]*row_group_size[1])

        col_local_size = (col_tile_width, col_hstride)
        col_group_size = (int_div_up(input_im.shape[1],col_tile_width), int_div_up(input_im.shape[0], col_tile_height)) 
        col_global_size = (col_local_size[0]*col_group_size[0], col_local_size[1]*col_group_size[1])
        
        #print col_local_size
        #print col_group_size
        #print col_global_size

        # a device buffer for the intermediate result
        intermediate_dev = None
        if (use_cached_buffers) and ((input_im.shape, input_im.dtype) in self.cached_intermediate_buffers):
            intermediate_dev = self.cached_intermediate_buffers[(input_im.shape, input_im.dtype)]
        else:
            #dummy = numpy.array([1], dtype=input_type)
            #intermediate_dev = cl.Buffer(self.ctx, mf.READ_WRITE, input_shape[0] * input_shape[1] * dummy.itemsize)
            intermediate_dev = DeviceBuffer(self.ctx, mf.READ_WRITE, shape=input_im.shape, dtype=input_im.dtype)
            self.cached_intermediate_buffers[(input_im.shape, input_im.dtype)] = intermediate_dev

        # a device buffer for the result, if not already supplied
        result_dev = None
        if result is None or result.__class__ == numpy.ndarray:
            # need to make or repurpose a device buffer
            if (use_cached_buffers) and ((input_im.shape, input_im.dtype) in self.cached_result_buffers):
                result_dev  = self.cached_result_buffers[(input_im.shape, input_im.dtype)]
                #print "Here"
                #print(result_dev)
            else:
                #dummy = numpy.array([1], dtype=input_im.dtype)
                #result_dev = cl.Buffer(self.ctx, mf.READ_WRITE, input_shape[0] * input_shape[1] * dummy.itemsize)
                result_dev = DeviceBuffer(self.ctx, mf.READ_WRITE, shape=input_im.shape, dtype=input_im.dtype)
                self.cached_result_buffers[(input_im.shape, input_im.dtype)] = result_dev
                
        else:
            # assume that result is a device buffer already (possibly not a safe assumption)
            result_dev = result

        #t = Timer()
        try:
            if wait_for is not None:
                row_evt = prg.separable_convolution_row(self.queue, [int(e) for e in row_global_size], intermediate_dev, input_dev, row_dev, local_size=[int(e) for e in row_local_size], wait_for=wait_for)
            else:
                row_evt = prg.separable_convolution_row(self.queue, [int(e) for e in row_global_size], intermediate_dev, input_dev, row_dev, local_size=[int(e) for e in row_local_size])
        except Exception as e:
           print(input_im.shape)
           print(intermediate_dev)
           print(input_dev)
           print(row_dev)
           print(row_global_size)
           print(row_local_size)
           print(wait_for)
           raise e
        
        
        try:
            exec_evt = prg.separable_convolution_col(self.queue, [int(e) for e in col_global_size], result_dev, intermediate_dev, col_dev, local_size=[int(e) for e in col_local_size], wait_for=[row_evt])
        except Exception as e:
            print(input_im.shape)
            print(result_dev)
            print(intermediate_dev)
            print(col_dev)
            print(col.shape)
            raise e
        #exec_evt.wait()
        #print("Elapsed: %f" % t.elapsed)

        evt = None
        if kwargs.get("readback_from_device", False):
            if result is None:
                result = self.transfer_from_device(result_dev, shape=input_im.shape, wait_for=[exec_evt])
            else:
                self.transfer_from_device(result_dev, result, wait_for=exec_evt)
        else:
            result = result_dev
            evt = [exec_evt]

        return (result, evt)


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
    
    platforms = cl.get_platforms()
    platform = platforms[0]
    devices = platform.get_devices()
    device = devices[0]
    ctx = cl.Context([device])
    queue = cl.CommandQueue(ctx)
    convolution_kernel = LocalMemorySeparableConvolutionKernel(queue)  
    convolution_kernel2 = NaiveSeparableConvolutionKernel(queue)
    
    w = 512
    h = 512
    
    #result_im = numpy.zeros_like(test_im)
    row = gaussian_kernel(7, 4.0)
    col = gaussian_kernel(7, 4.0)
    #row = numpy.array([-1., 0., 1.])
    #col = numpy.array([1., 2., 1.])
    
    row_dev = convolution_kernel.transfer_to_device(row)
    col_dev = convolution_kernel.transfer_to_device(col)
    
    print("float32")
    
    test_im = rand(h,w).astype(numpy.float32)
    test_im_dev = convolution_kernel.transfer_to_device(test_im)
    
    if True:
        (result, evt) = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=True)
        t = Timer()
        for i in range(0,200):
            (result, evt) = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=False, wait_for=None)
        
        (result, evt) = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=True, wait_for=evt)
        print("Total time: %f" % t.elapsed)
    
    # if False:
    #     print("uint8")
    #     test_im = (255* rand(h,w)).astype(numpy.uint8)
    #     (test_im_dev, dummy, dummy2) = convolution_kernel.transfer_to_device(test_im)
    # 
    #     result = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=False)
    #     result = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=False)
    #     result = convolution_kernel(test_im_dev, row_dev, col_dev, readback_from_device=True)
    
    
    # (test_im_dev, dummy, dummy2) = convolution_kernel2.transfer_to_device(test_im)
    #     (row_dev, dummy, dummy2) = convolution_kernel2.transfer_to_device(row)
    #     (col_dev, dummy, dummy2) = convolution_kernel2.transfer_to_device(col)
    #     
    #     result1_dev = convolution_kernel2(test_im_dev, row_dev, col_dev, readback_from_device=False)
    #     result = convolution_kernel2(test_im_dev, row_dev, col_dev, result_im, readback_from_device=True)
    #     
    
    print result
    
    if False:
        from pylab import *
        imshow(result, interpolation='nearest')
        colorbar()
        show()
    
