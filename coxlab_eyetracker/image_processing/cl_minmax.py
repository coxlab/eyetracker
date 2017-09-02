import mako.template
import pyopencl as cl
import pyopencl.array as cla
import numpy as np
import functools


class MinMaxKernel:

    def __init__(self, ctx, queue, runlen=4):
        self.ctx = ctx
        self.queue = queue
        self.program_cache = {}
        self.imshape = None
        self.runlen = runlen

        self.minmax_scratch = []
        self.minmax_index_scratch = []

    def build_scratch(self, imshape):

        self.scratch = []
        self.index_scratch = []

        l = np.prod(imshape)
        self.array_indices = cla.arange(self.queue, 0, l, 1, dtype=np.int32)
        if l % self.runlen != 0:
            l += l % self.runlen
        while l > 1:
            l /= self.runlen
            self.scratch.append(cla.empty(self.queue, (l,), np.float32))
            self.index_scratch.append(cla.empty(self.queue, (l,), np.int32))

        self.imshape = imshape

    def build_kernel(self, datasize, compute_min):

        runlen = self.runlen
        prog_parameters = (datasize, compute_min, runlen)

        if prog_parameters in self.program_cache:
            return self.program_cache[prog_parameters]

        code = """
            __kernel void minmax_reduce(__global float *output,
                                         __global int *output_indices,
                                         __global const float *input,
                                         __global const int *input_indices){

                int start_index = ${runlen} * get_global_id(0);
                int reduced_index = get_global_id(0);

                float val = input[start_index];
                int val_index = input_indices[start_index];
                float cmpval;

                %for i in range(1, runlen):
                    cmpval = input[start_index + ${i}];
                    %if compute_min:
                    if(cmpval < val){
                    %else:
                    if(cmpval > val){
                    %endif
                        val = cmpval;
                        val_index = input_indices[start_index + ${i}];
                    }
                %endfor

                output[reduced_index] = val;
                output_indices[reduced_index] = val_index;

            }
        """

        local_vars = locals()
        local_vars.pop("self")
        templated_code = mako.template.Template(code).render(**local_vars)
        program = cl.Program(self.ctx, templated_code.encode('ascii'))

        try:
            program.build()
        except cl.RuntimeError as e:
            print(e)
            exit()

        kernel = program.minmax_reduce
        self.program_cache[prog_parameters] = kernel

        return kernel

    def __call__(self, input_dev):

        if input_dev.shape != self.imshape:
            self.build_scratch(input_dev.shape)

        datasize = np.prod(self.imshape)

        min_prg = self.build_kernel(datasize, compute_min=True)
        max_prg = self.build_kernel(datasize, compute_min=False)

        # MAX
        gsize = (int(self.scratch[0].shape[0]), 1)
        max_prg(self.queue,
                       gsize,
                       None,
                       self.scratch[0].data,
                       self.index_scratch[0].data,
                       input_dev.data,
                       self.array_indices.data)

        for i in range(0, len(self.scratch) - 1):
            gsize = (int(self.scratch[i + 1].shape[0]), 1)
            max_prg(self.queue,
                    gsize,
                    None,
                    self.scratch[i + 1].data,
                    self.index_scratch[i + 1].data,
                    self.scratch[i].data,
                    self.index_scratch[i].data)

        max_index = (self.index_scratch[-1].get())[0]

        # MIN
        min_prg(self.queue,
                       (int(self.scratch[0].shape[0]), 1),
                       None,
                       self.scratch[0].data,
                       self.index_scratch[0].data,
                       input_dev.data,
                       self.array_indices.data)

        for i in range(0, len(self.scratch) - 1):
            gsize = (int(self.scratch[i + 1].shape[0]), 1)
            min_prg(self.queue,
                    gsize,
                    None,
                    self.scratch[i + 1].data,
                    self.index_scratch[i + 1].data,
                    self.scratch[i].data,
                    self.index_scratch[i].data)

        min_index = (self.index_scratch[-1].get())[0]

        min_x = np.floor(min_index / self.imshape[1])
        min_y = min_index - min_x * self.imshape[1]

        max_x = np.floor(max_index / self.imshape[1])
        max_y = max_index - max_x * self.imshape[1]

        min_coords = np.array([min_x, min_y])
        max_coords = np.array([max_x, max_y])

        # self.queue.finish()

        # MIN
        return (min_coords, max_coords)


if __name__ == '__main__':

    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)

    a = np.array([[1, 2, 3], [4, 10, 4], [0, 4, 5]], dtype=np.float32)

    print a

    a_dev = cla.to_device(queue, a)

    minmax = MinMaxKernel(ctx, queue)

    coords = minmax(a_dev)

    print coords