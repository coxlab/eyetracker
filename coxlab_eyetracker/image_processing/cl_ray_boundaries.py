import pyopencl as cl
import pyopencl.array as cla
import pyopencl.tools as clt
from pyopencl.elementwise import ElementwiseKernel
import numpy as np
import mako.template
from stopwatch import clockit
import matplotlib.pylab as plt

class ArraySet:
    pass

class FindRayBoundaries:

    def __init__(self, ctx, queue):
        self.ctx = ctx
        self.queue = queue

        self.allocator = clt.ImmediateAllocator(self.queue)
        self.memory_pool = clt.MemoryPool(self.allocator)

        self.program_cache = {}
        self.array_cache = {}
        self.arrays = None


        self.square_array = ElementwiseKernel(self.ctx,
                                                "float *in, float *out",
                                                "out[i] = in[i]*in[i]",
                                                "square")

    def setup_arrays(self, nrays, nsamples, cutoff):

        prog_params = (nrays, nsamples, cutoff)

        if prog_params in self.array_cache:
            return self.array_cache[prog_params]

        else:
            arrays = ArraySet()
            arrays.scratch = cla.empty(self.queue,
                                 (nsamples, nrays),
                                 dtype=np.float32,
                                 allocator=self.memory_pool)

            arrays.result = cla.empty(self.queue,
                                (nrays,),
                                dtype=np.int32,
                                allocator=self.memory_pool)

            arrays.pre_cutoff = cla.empty(self.queue,
                                    (nrays, cutoff),
                                    dtype=np.float32,
                                    allocator=self.memory_pool)

            arrays.pre_cutoff_squared = cla.empty_like(arrays.pre_cutoff)

            arrays.idx = cla.arange(self.queue, 0, cutoff * nrays, 1,
                                    dtype=np.int32,
                                    allocator=self.memory_pool)

            self.array_cache[prog_params] = arrays
            return arrays

    def build_program(self, nrays, nsamples, ray_step):

        prog_params = (nrays, nsamples, ray_step)

        if prog_params in self.program_cache:
            return self.program_cache[prog_params]

        code = """

            #define PI  3.14159
            __constant sampler_t sampler = (CLK_NORMALIZED_COORDS_FALSE |
                                            CLK_ADDRESS_CLAMP_TO_EDGE |
                                            CLK_FILTER_LINEAR);

            __kernel void sample_rays(__global float *output,
                                      __read_only image2d_t input,
                                      float const seed_x,
                                      float const seed_y){

                float theta = get_global_id(1) * 2 * PI / (get_global_size(1)-1);


                float ray_step = ${ray_step};
                float r = ((float)get_global_id(0)+2) * ray_step;

                float r0 = ((float)get_global_id(0)+1) * ray_step;

                float x = r * cos(theta) + seed_x;
                float y = r * sin(theta) + seed_y;

                float x0 = r0 * cos(theta) + seed_x;
                float y0 = r0 * sin(theta) + seed_y;

                float sample = read_imagef(input, sampler, (int2)(x,y)).x;
                float sample0 = read_imagef(input, sampler, (int2)(x0,y0)).x;

                output[get_global_id(0) * get_global_size(1) +
                       get_global_id(1)] = fabs(sample - sample0);
            }

            __kernel void scan_boundary(__global int *result,
                                        __global float *in,
                                        float threshold){

                int ray_id = get_global_id(0);
                int idx;
                for(int i = 0; i < ${nsamples}; i++){
                    idx = i * ${nrays} + ray_id;
                    if(in[idx] > threshold){
                        result[ray_id] = i;
                        return;
                    }
                }
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

        self.program_cache[prog_params] = program

        return program

    def __call__(self, im, nrays, nsamples, ray_step, seed_pt, cutoff, thresh):

        nrays = int(nrays)
        nsamples = int(nsamples)
        cutoff = np.int32(cutoff)

        arrays = self.setup_arrays(nrays, nsamples, cutoff)

        prog = self.build_program(nrays, nsamples, ray_step)

        prog.sample_rays(self.queue,
                        (nsamples, nrays),
                        None,
                        arrays.scratch.data,
                        im,
                        np.float32(seed_pt[0]),
                        np.float32(seed_pt[1]))

        # take the region in the cutoff zone
        cla.take(arrays.scratch,
                 arrays.idx,
                 out=arrays.pre_cutoff)

        # plt.imshow(self.pre_cutoff.get())
        # plt.show()
        self.square_array(arrays.pre_cutoff, arrays.pre_cutoff_squared)

        inside_mean = cla.sum(arrays.pre_cutoff).get() / (cutoff * nrays)
        inside_sumsq = cla.sum(arrays.pre_cutoff_squared).get() / (cutoff * nrays)
        inside_std = np.sqrt(inside_sumsq - inside_mean ** 2)

        normed_thresh = inside_std * thresh

        prog.scan_boundary(self.queue,
                          (nrays,),
                          None,
                          arrays.result.data,
                          arrays.scratch.data,
                          np.float32(normed_thresh))

        # print normed_thresh
        # plt.figure()
        # plt.hold(True)
        # plt.imshow(arrays.scratch.get())
        # plt.plot(np.arange(0, nrays), arrays.result.get())
        # plt.show()

        return arrays.result.get()
