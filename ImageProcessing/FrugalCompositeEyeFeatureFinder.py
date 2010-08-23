#
#  CompositeEyeFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by Davide Zoccolan on 9/10/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#


from EyeFeatureFinder import *
from scipy import *
import time
from matplotlib.pylab import *
from PIL import Image
from PIL import ImageFilter
from numpy import *
import numpy.random as random
import os
from FastRadialFeatureFinder import *
from SubpixelStarburstEyeFeatureFinder import *



class FrugalCompositeEyeFeatureFinder(EyeFeatureFinder):


    # ==================================== function: __init__ ========================================
    def __init__(self, ff_radial, ff_starbust):
            
        self.result = None
        self.last = None
        
        # Feature finders
        self.ff_fast_radial = ff_radial
        self.ff_starburst = ff_starbust
        
        self.first_run = True

        self.reseed_threshold = 100.
        self.minimum_frames_to_reseed = 50
        self.reseed_count = self.minimum_frames_to_reseed
        

    # ==================================== function: analyzeImage ========================================
    @clockit
    def analyze_image(self, im, guess = None, **kwargs):
        
        features = None
        im_array_stage1 = None
        sobel_avg = None
        
        reseed = False
        self.reseed_count = self.reseed_count - 1
        
        error_level = inf
        
        if not self.first_run:
            # Try to track with the starburst finder using the previous guess as a seed
            try:
                self.ff_starburst.analyze_image(im, guess.copy())
                features = self.ff_starburst.get_result()
            except Exception, e:
                features['pupil_radius'] = None
                features['cr_radius'] = None
                features['pupil_position'] = None
                features['cr_position'] = None
                print e.message
                
        
        
        if features is not None and ('starburst' in features) and ('pupil_err' in features['starburst']):
            cr_error = features['starburst']['cr_err']
            pupil_error = features['starburst']['pupil_err']
            error_level = max(cr_error, pupil_error)
            print("error_level: %f" % error_level)
        
        if self.first_run or error_level > self.reseed_threshold or self.reseed_count <= 0:
            reseed = True
             
             
        if reseed:    
        
            print("RESEEDING")
            self.reseed_count = self.minimum_frames_to_reseed
                                                                                                                                                                                                                                                                                                                                                                                                                                        
            # Exhaustive Search: Get intial guess of pupil and CR using the fast radial finder
            #self.ff_fast_radial.target_kpixels = 10 #50
            self.ff_fast_radial.analyze_image(im, guess) # NOTE: for now, the guess is not used by the fast radial feature finder
            features = self.ff_fast_radial.get_result()                
            ds = features['dwnsmp_factor_coord']
            pupil_position_stage1 = features['pupil_position']
            cr_position_stage1 = features['cr_position']
            im_array_stage1 = features['im_array']
            
            if("sobel_avg" in features):
                sobel_avg = features["sobel_avg"]
            else:
                sobel_avg = None
            
            # Refine the traking using the star burst finder
            try:
            
                # Run the starburst ff
                self.ff_starburst.analyze_image(im, features.copy())
                features = self.ff_starburst.get_result()
            except Exception, e:
                features['pupil_radius'] = None
                features['cr_radius'] = None
                features['pupil_position'] = None
                features['cr_position'] = None
                print e.message
                
                
            features['im_array_stage1'] = im_array_stage1    
            features['pupil_position_stage1'] = pupil_position_stage1 * ds
            features['cr_position_stage1'] = cr_position_stage1 * ds
            
        # Add features axtracted by the first feature finder to the final feature vector
        features['im_array'] = im
        features['im_shape'] = im.shape
        
        if(sobel_avg is not None):
            features['sobel_avg'] = sobel_avg
        
        features['timestamp'] = guess.get('timestamp', 0)
        
        self.result = self.last = features

        self.first_run = False


    def get_result(self):
        return self.result













