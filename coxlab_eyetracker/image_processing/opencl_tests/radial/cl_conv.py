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


def separable_convolution2d(self, im, row, col):
    dimension_signature = (im.shape[0], im.shape[1], row.shape[0], col.shape[0])

    # check to see if we've already compiled a prog for this signature