#
#  EyeFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 7/29/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

from numpy import *


class EyeFeatureFinder(object):

    # analyze the image and return dictionary of features gleaned
    # from it
    def analyze_image(self, image, guess=None, **kwargs):
        return

    def get_processed_image(self):
        return None
    
    
    def get_param(self, param):
        return object.__getattribute__(self, param)
    
    def set_param(self, param, value):
        return object.__setattr__(self, param, value)
