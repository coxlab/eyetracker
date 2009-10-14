#
#  EyeFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 7/29/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#


#from CobraEyeTrackerCpp import *
from numpy import *
import scipy
from scipy.weave import inline
from scipy.weave import converters
#from handythread import *
from scipy import signal
#from EdgeDetection import *
from EyeFeatureFinder import *
from stopwatch import *
from VanillaBackend import *
from WovenBackend import *

opencl_available = True
try:
    import pyopencl as cl
    cl_ctx = cl.create_context_from_type(cl.device_type.ALL)
    cl_queue = cl.CommandQueue(ctx)
except Exception, e:
    opencl_available = False


class FastRadialFeatureFinder (EyeFeatureFinder):

    def __init__(self):

        self.backend = WovenBackend()
                
        self.target_kpixels = 80.0 #8.0
        self.max_target_kpixels = 50.0
        self.min_target_kpixels = 1.0
        self.parameters_updated = 1
        
        self.alpha = 10.
        self.min_radius_fraction = 0.0226 #1./2000.
        self.max_radius_fraction = 0.0956 #1./8.
        self.min_fraction = 1./1000.
        self.max_fraction = 0.35
        self.radius_steps = 6
        self.radiuses_to_try = [1]
        self.ds_factor = 1
        
        self.correct_downsampling = False
        
        self.do_refinement_phase = 0
        
        self.shortcut_at_sobel = 0
        
        self.cache_sobel = True
        self.cached_sobel = None
        self.compute_sobel_avg = True # for autofocus
        self.sobel_avg = None
        
        # Voting
        self.outlier_cutoff = 1.
        self.maxmin_consensus_votes = 1
        
        self.image_contribution = 1
        
        self.last_positions = []
        
        self.available_filters = [u"sepfir", u"spline", u"fft", u"convolve2d"]
        
        self.result = None
    
    # analyze the image and return dictionary of features gleaned
    # from it
    @clockit
    def analyze_image(self, image, guess = None, **kwargs):
    
        im_array = image
        #im_array = image.astype(double)
        im_array = im_array[::self.ds_factor, ::self.ds_factor]
        
        if(guess != None):
            features = guess
        else:
            features = {'pupil_size' : None,
                        'cr_size' : None }	
		
        if(self.parameters_updated or self.backend.cached_shape != im_array.shape):
            print "Recaching..."
            print "Target kPixels: ", self.target_kpixels
            print "Max Radius Fraction: ", self.max_radius_fraction
            print "Radius steps: ", self.radius_steps
            im_pixels = image.shape[0] * image.shape[1]
            self.ds_factor = int(sqrt(im_pixels / int(self.target_kpixels*1000)))
            if(self.ds_factor <= 0):
                self.ds_factor = 1
            im_array = image[::self.ds_factor, ::self.ds_factor]
            
            self.backend.autotune(im_array)
            self.parameters_updated = 0
            
            self.radiuses_to_try = linspace(ceil(self.min_radius_fraction*im_array.shape[0]), ceil(self.max_radius_fraction*im_array.shape[0]), self.radius_steps)
            self.radiuses_to_try = unique(self.radiuses_to_try.astype(int))
            print "Radiuses to try: ", self.radiuses_to_try
            print "Downsampling factor: ", self.ds_factor
			
        ds = self.ds_factor;
        
        S = self.backend.fast_radial_transform(im_array, self.radiuses_to_try, self.alpha)        
        (min_coords, max_coords) = self.backend.find_minmax(S)
        
        if(self.correct_downsampling):
            features['pupil_position'] = array([min_coords[0], min_coords[1]]) * ds
            features['cr_position'] = array([max_coords[0], max_coords[1]]) * ds 
            features['dwnsmp_factor_coord'] = 1           
        else:
            features['pupil_position'] = array([min_coords[0], min_coords[1]])
            features['cr_position'] = array([max_coords[0], max_coords[1]])      
            features['dwnsmp_factor_coord'] = ds      

        features['transform'] = S
        features['im_array'] = im_array
        features['im_shape'] = im_array.shape
        
        self.result = features
        
            
    def update_parameters(self):
        self.parameters_updated = 1
        
    def get_result(self):
        return self.result
    
 
if __name__ == "__main__":
    import pylab
    import numpy
    import PIL.Image
    import time
    
    pil_im = pil_im = PIL.Image.open("/Users/davidcox/Development/svn.coxlab.org/eyetracking/code/EyeTrackerStageDriver/example_eyes/RatEye_snap20_zoom.jpg")
    im = asarray(pil_im).astype(numpy.float64)
    
    noplot = 1
    
    f = FastRadialFeatureFinder()
    trials = 50
    
    if(0):
        tic = time.time()
        for i in range(0,trials):
            test = f.analyze_image(im, filter='fft')
    
        print 'FFT: ', (time.time() - tic)/trials

        pylab.figure()
        pylab.imshow(test['transform'])
        pylab.title('FFT')
        
    if(1):
        
        f.reuse_storage = 0
        f.use_sse3 = 0
        f.filter = 'sepfir'
        tic = time.time()
        for i in range(0,trials):
            f.analyze_image(im, filter='sepfir')
            test = f.get_result()
        seconds_per_frame = (time.time() - tic)/trials
        print 'Sep FIR: ', seconds_per_frame
        print '\t ', 1. / seconds_per_frame, ' FPS' 

        if(not noplot):
            pylab.figure()
            pylab.imshow(test['transform'])
            
            pylab.figure()
            #pylab.imshow(im, cmap=pylab.cm.gray)
            pylab.imshow(test['im_array'], cmap=pylab.cm.gray)
            pylab.hold('on')
            cr = test['cr_position']
            pupil = test['pupil_position']
            pylab.plot([cr[1]], [cr[0]], 'r+')
            pylab.plot([pupil[1]], [pupil[0]], 'b+')
            pylab.title('Sep FIR')
        
    if(0):
        tic = time.time()
        for i in range(0,trials):
            test = f.analyze_image(im, filter='spline')
        print 'SPLINE: ', (time.time() - tic)/trials
        
        pylab.figure()
        pylab.imshow(test['transform'])
        pylab.title('SPLINE')

    if(0):
        tic = time.time()
        for i in range(0,trials):
            test = f.analyze_image(im)
        print 'Convolve2d: ', (time.time() - tic)/trials
        
        pylab.figure()
        pylab.imshow(test['transform'])
        pylab.title('Convolve2d')
	
    if(0):
        f.reuse_storage = 1	
        tic = time.time()
        def sepfir_multithread_test(i, f, im):	
            test = f.analyze_image(im, filter='sepfir')
        foreach(lambda t: sepfir_multithread_test(t,f, im), range(0,trials), 3)
        print 'Sep FIR (multithreaded): ', (time.time() - tic)/trials	
	
    pylab.show()
	
