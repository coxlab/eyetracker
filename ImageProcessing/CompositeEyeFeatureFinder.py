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



class CompositeEyeFeatureFinder(EyeFeatureFinder):


    # ==================================== function: __init__ ========================================
    def __init__(self, ff_radial, ff_starbust):
            
        self.result = None
        self.last = None
        
        # Feature finders
        self.ff_fast_radial = ff_radial
        self.ff_starburst = ff_starbust

        
        

    # ==================================== function: analyzeImage ========================================
    @clockit
    def analyze_image(self, im, guess = None, **kwargs):
        
                    
        # #### FEATURE FINDER # 1: Get intial guess of pupil and CR using the fast radial finder
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
        
        # #### FEATURE FINDER # 2: Refine the traking using the star burst finder
        try:
        # If available, pass the last CR and Pupil radiuses as intial guesses for the star burst ff
            #if(self.last != None and 'pupil_radius' in self.last):
            #   features['pupil_radius'] = self.last['pupil_radius']
            #if(self.last != None and 'cr_radius' in self.last):
            #   features['cr_radius'] = self.last['cr_radius']
                
            # Run the starburst ff
            self.ff_starburst.analyze_image(im, features.copy())
            features = self.ff_starburst.get_result()
        except Exception, e:
            features['pupil_radius'] = None
            features['cr_radius'] = None
            features['pupil_position'] = None
            features['cr_position'] = None
            print e.message
        
        # Add features axtracted by the first feature finder to the final feature vector
        features['im_array'] = im
        features['im_array_stage1'] = im_array_stage1    
        features['pupil_position_stage1'] = pupil_position_stage1 * ds
        features['cr_position_stage1'] = cr_position_stage1 * ds
        features['im_shape'] = im.shape
        
        if(sobel_avg is not None):
            features['sobel_avg'] = sobel_avg
        
        features['timestamp'] = guess.get('timestamp', 0)
        
        self.result = self.last = features


    def get_result(self):
        return self.result













