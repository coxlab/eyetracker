import mako.template
import pyopencl as cl
import pyopencl.array as cla
import numpy as np


# Helper functions for computing alignment...
def int_div_up(a, b):
    # Round a / b to nearest higher integer value
    a = np.int32(a)
    b = np.int32(b)
    return (a / b + 1) if (a % b != 0) else (a / b)


def int_div_down(a, b):
    # Round a / b to nearest lower integer value
    a = np.int32(a)
    b = np.int32(b)
    return a / b


def int_align_up(a, b):
    # Align a to nearest higher multiple of b
    a = np.int32(a)
    b = np.int32(b)
    return (a - a % b + b) if (a % b != 0) else a


def int_align_down(a, b):
    # Align a to nearest lower multiple of b
    a = np.int32(a)
    b = np.int32(b)
    return a - a % b


class LocalMemorySeparableCorrelation:

    def __init__(self, ctx, queue, row=None, col=None):
        self.ctx = ctx
        self.queue = queue
        self.program_cache = {}

        if row is not None:
            self.fixed_row_kernel = tuple(row)
        else:
            self.fixed_row_kernel = None

        if col is not None:
            self.fixed_col_kernel = tuple(col)
        else:
            self.fixed_col_kernel = None

    def build_program(self,
                      dtype,
                      im_shape,
                      row_kernel_radius,
                      row_kernel_radius_aligned,
                      row_tile_width,
                      col_kernel_radius,
                      col_tile_width,
                      col_tile_height,
                      col_hstride):

        row_kernel_width = row_kernel_radius * 2 + 1
        col_kernel_width = col_kernel_radius * 2 + 1

        tile_cache_width = row_kernel_radius * 2 + row_tile_width
        (image_height, image_width) = im_shape

        col_input_load_stride = image_width * col_hstride
        col_tile_cache_stride = col_tile_width * col_hstride

        TYPE = ""
        if dtype == np.float32:
            TYPE = "float"
        elif dtype == np.uint8:
            TYPE = "unsigned char"
        elif dtype == np.uint16:
            TYPE = "unsigned short"

        row_kernel_fixed = self.fixed_row_kernel
        col_kernel_fixed = self.fixed_col_kernel

        prog_parameters = (dtype,
                   im_shape,
                   row_kernel_radius,
                   row_kernel_radius_aligned,
                   row_tile_width,
                   col_kernel_radius,
                   col_tile_width,
                   col_tile_height,
                   col_hstride,
                   row_kernel_fixed,
                   col_kernel_fixed)

        if prog_parameters in self.program_cache:
            return self.program_cache[prog_parameters]

        code = """

            __kernel void separable_convolution_row(__global ${TYPE} *output,
                                            __global const ${TYPE} *input,
                                            __global const float *row_kernel){

                __local ${TYPE} tile_cache[${tile_cache_width}];

                // ------------------------------------------------------------
                // Cooperatively load a tile of data into the local memory tile cache
                // ------------------------------------------------------------

                // Some critical indices
                // "tile" = area where we will actually compute output values
                // (for this work group)
                // "apron" = additional area of the input on either side that
                // we need to access to compute those outputs
                const int   tile_start = get_group_id(0) * ${row_tile_width};
                const int   tile_end = tile_start + ${row_tile_width} - 1;
                const int   apron_start = tile_start - ${row_kernel_radius};
                const int   apron_end = tile_end + ${row_kernel_radius};

                // "Clamp" the indices that would otherwise be off the end of the image
                const int   tile_end_clamped = min(tile_end, ${image_width}-1); // don't run tile off of end of image
                // const int   apron_start_clamped = max(apron_start, 0); // don't run apron past beginning
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
                        tile_cache[tile_cache_offset] = input[row_start_offset - input_load_offset - 1];
                    } else if(input_load_offset > apron_end_clamped){
                        tile_cache[tile_cache_offset] = input[row_start_offset + (2*apron_end_clamped - input_load_offset + 1)];
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

                    %if col_kernel_fixed is not None:
                        float tmp;
                    %endif

                    %for r in range(-row_kernel_radius, row_kernel_radius+1):
                        %if row_kernel_fixed is not None:
                            tmp = (${row_kernel_fixed[row_kernel_radius + r]}); // bcz compiler is shitty
                            sum += (float)tile_cache[tile_cache_read_offset + (${r})] * tmp;
                        %else:
                            sum += (float)tile_cache[tile_cache_read_offset + (${r})] * row_kernel[${row_kernel_radius} + (${r})];
                        %endif
                    %endfor

                    // write the output back to global memory
                    output[row_start_offset + output_write_offset] = (${TYPE})sum;

                }

            }


            __kernel void separable_convolution_col(__global ${TYPE} *output,
                                                    __global  const ${TYPE} *input,
                                                    __global  const float *col_kernel){


                // The tile cache is tile_width x tile_height with a 2*kernel_radius apron, top & bottom
                __local float tile_cache[${col_tile_width} * (2*${col_kernel_radius} + ${col_tile_height})];


                // --------------------------------------------------------------------
                // Cooperatively load a tile of data into the local memory tile cache
                // --------------------------------------------------------------------

                // Some critical indices
                // "tile" = area where we will actually compute output values (for this work group)
                // "apron" = additional area of the input on either side that we need to access to compute those outputs

                // Where does the tile start and end in image coordinates
                const int   tile_start_y = get_group_id(1) * ${col_tile_height}; // image-rel "y" coord
                const int   tile_end_y = tile_start_y + ${col_tile_height} - 1;
                const int   apron_start_y = tile_start_y - ${col_kernel_radius}; // with extra apron added
                const int   apron_end_y = tile_end_y + ${col_kernel_radius};

                // where is this threads column 'x' coordinate
                // group-based offset, plus local coordinate
                const int   col_x_offset = get_group_id(0) * ${col_tile_width} + get_local_id(0);
                if(col_x_offset >= ${image_width}) return;

                // "Clamp" the indices that would otherwise be off the end of the image
                const int   tile_end_y_clamped = min(tile_end_y, ${image_height}-1); // don't go off edge of the im
                const int   apron_start_y_clamped = max(apron_start_y, 0);  // don't go start before the image
                const int   apron_end_y_clamped = min(apron_end_y, ${image_height} - 1); //


                // Compute the starting data position that this particular thread will load
                // (linear data index, relative to image buffer)
                int     input_load_linear_offset = (apron_start_y + get_local_id(1)) * ${image_width} + col_x_offset;

                // Compute the starting position to load data into in the tile cache
                // (linear data index, relative to tile)
                int     tile_cache_linear_offset = get_local_id(1) * ${col_tile_width} + get_local_id(0);


                // Do the actual loads.  In this kernel, each thread is resonsible for a portion of one column,
                // strided by local_size along the entire column

                for(int y = apron_start_y + get_local_id(1); y <= apron_end_y; y += get_local_size(1)){
                    if( y < apron_start_y_clamped ){
                        tile_cache[tile_cache_linear_offset] = (float)input[col_x_offset + (-y - 1) * ${image_width}];
                    } else if(y > apron_end_y_clamped){
                        tile_cache[tile_cache_linear_offset] = (float)input[col_x_offset + (2*apron_end_y_clamped - y + 1)*${image_width}];
                    } else {
                        tile_cache[tile_cache_linear_offset] = (float)input[input_load_linear_offset];
                    }

                    input_load_linear_offset += ${col_input_load_stride}; // should be local_size * image_width
                    tile_cache_linear_offset += ${col_tile_cache_stride}; // should be local_size * tile_width
                }


                // At this point, hopefully all of the data we need is loaded into the tile cache

                // Synchronize with the other threads so that we're sure we've loaded
                barrier(CLK_LOCAL_MEM_FENCE);

                // --------------------------------------------------------------------
                // Compute the covolution value for this thread's assigned pixel
                // --------------------------------------------------------------------

                input_load_linear_offset = (tile_start_y + get_local_id(1)) * ${image_width} + col_x_offset;
                tile_cache_linear_offset = (get_local_id(1) + ${col_kernel_radius}) * ${col_tile_width} + get_local_id(0);

                %if col_kernel_fixed is not None:
                    float tmp;
                %endif

                for(int y = tile_start_y + get_local_id(1); y <= tile_end_y_clamped; y += get_local_size(1)){
                    float sum = 0;

                    %for k in range(-col_kernel_radius, col_kernel_radius+1):
                        %if col_kernel_fixed is not None:
                            tmp = (${col_kernel_fixed[col_kernel_radius + k]}); // bcz compiler is shitty
                            sum += tile_cache[tile_cache_linear_offset + (${k}*${col_tile_width})] * tmp;
                        %else:
                            sum += tile_cache[tile_cache_linear_offset + (${k}*${col_tile_width})] * col_kernel[${col_kernel_radius} + ${k}];
                        %endif
                    %endfor


                    output[input_load_linear_offset] = (${TYPE})sum;

                    input_load_linear_offset += ${col_input_load_stride};
                    tile_cache_linear_offset += ${col_tile_cache_stride};
                }

            }
        """

        local_vars = locals()
        local_vars.pop("self")
        templated_code = mako.template.Template(code).render(**local_vars)
        # print templated_code
        program = cl.Program(self.ctx, templated_code.encode('ascii'))

        try:
            program.build()
        except cl.RuntimeError as e:
            print(e)
            exit()

        self.program_cache[prog_parameters] = program

        return program

    def __call__(self,
                 input_dev,
                 row_dev,
                 col_dev,
                 result_dev,
                 scratch_dev=None):

        if scratch_dev is None:
            scratch_dev = cla.empty_like(input_dev)

        row_tile_width = 128
        #row_tile_width = 64

        col_tile_width = 8
        #col_tile_height = 16
        col_tile_height = 8

        #col_tile_width = 16
        #col_tile_height = 48

        col_hstride = 8
        assert (np.mod(row_dev.shape[0], 2) == 1,
                "Kernels must be of odd width")
        row_kernel_radius = row_dev.shape[0] / 2

        coallescing_quantum = 16
        row_kernel_radius_aligned = ((row_kernel_radius /
                                      coallescing_quantum) *
                                     coallescing_quantum)

        if row_kernel_radius_aligned == 0:
            row_kernel_radius_aligned = coallescing_quantum

        assert (np.mod(col_dev.shape[0], 2) == 1,
                "Kernels must be of odd width")
        col_kernel_radius = col_dev.shape[0] / 2

        prg = self.build_program(input_dev.dtype,
                                 input_dev.shape,
                                 row_kernel_radius,
                                 row_kernel_radius_aligned,
                                 row_tile_width,
                                 col_kernel_radius,
                                 col_tile_width,
                                 col_tile_height,
                                 col_hstride)

        # Row kernel launch parameters
        row_local_size = (row_kernel_radius_aligned +
                          row_tile_width +
                          row_kernel_radius, 1)

        row_group_size = (int_div_up(input_dev.shape[1], row_tile_width),
                          input_dev.shape[0])

        row_global_size = (row_local_size[0] * row_group_size[0],
                           row_local_size[1] * row_group_size[1])

        # Column kernel launch parameters
        col_local_size = (min(input_dev.shape[1], col_tile_width),
                          min(input_dev.shape[0], col_hstride))

        col_group_size = (int_div_up(input_dev.shape[1], col_tile_width),
                          int_div_up(input_dev.shape[0], col_tile_height))

        col_global_size = (col_local_size[0] * col_group_size[0],
                           col_local_size[1] * col_group_size[1])

        row_global_size = tuple(int(e) for e in row_global_size)
        row_local_size = tuple(int(e) for e in row_local_size)
        col_global_size = tuple(int(e) for e in col_global_size)
        col_local_size = tuple(int(e) for e in col_local_size)

        try:
            prg.separable_convolution_row(self.queue,
                                          row_global_size,
                                          row_local_size,
                                          scratch_dev.data,
                                          input_dev.data,
                                          row_dev.data)
        except Exception as ex:
            print(input_dev.shape)
            print(row_dev.shape)
            print(row_global_size)
            print(row_local_size)
            raise ex

        try:
            prg.separable_convolution_col(self.queue,
                                         col_global_size,
                                         col_local_size,
                                         result_dev.data,
                                         scratch_dev.data,
                                         col_dev.data)
        except Exception as e:
            print(input_dev.shape)
            print(result_dev)
            print(scratch_dev)
            print(col_dev)
            print(col_dev.shape)
            raise e
