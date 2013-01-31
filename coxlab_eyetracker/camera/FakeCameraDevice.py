#
#  SimulatedCameraDevice.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 5/26/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#


from numpy import *
import os
import cPickle as pickle
import PIL.Image as Image
import time

import threading
from Queue import Queue

def acquire_continuously(im_array_, ff):
    while(1):    
        im_array = im_array_.copy()
        ff.analyzeImage(im_array, None);


def load_image(fn):
    ext = os.path.splitext(fn)[1].lower()
    if ext in ('.jpg', '.png'):
        im = Image.open(fn)
        im_array = array(im).astype(double)
        if(im_array.ndim == 3):
            im_array = mean(im_array[:,:,:3], 2)
    elif ext == '.pkl':
        im_array = pickle.load(open(fn)).astype(double)
    return im_array


def make_file_iter(d, exts=('.jpg', '.png', '.pkl')):
    while True:  # this is an infinite iterator
        for r, sd, fs in os.walk(d):
            for fn in fs:
                ext = os.path.splitext(fn)[1].lower()
                if ext in exts:
                    yield os.path.join(r, fn)


class FakeCameraDevice:
    
    def __init__(self, _feature_finder, _filename = None):
        
        self.feature_finder = None
        self.filename = None
        self.im_array = None
        
        self.camera = None
        
        self.pupil_position = None
        self.cr_position = None
        self.pupil_radius = None
        self.cr_radius = None
        self.pupil_radius_CV = None
        self.cr_radius_CV = None

        self.acquire_continuously = 0
        self.image_center = array([0,0])
        
        self.acquisition_thread = None

        self.feature_finder = _feature_finder
        self.filename = _filename

        if(self.filename != None):
            if (os.path.isdir(self.filename)):
                self.file_iter = make_file_iter(self.filename)
            else:
                self.im_array = load_image(self.filename)
        else:
            self.im_array = None
        
        self.wait = 0.5
        
        
        if(self.acquire_continuously):
            self.acquisition_thread = threading.Thread(target=acquireContinuously, args=[self.im_array, self.feature_finder])
            self.acquisition_thread.start()
        

    def acquire_image(self):
        if hasattr(self, 'file_iter'):
            self.im_array = load_image(self.file_iter.next())
        self.feature_finder.analyze_image(self.im_array, {'timestamp': time.time()});
        time.sleep(self.wait)
       
        return

    def	get_processed_image(self, guess = None):
        if(self.im_array == None):
            raise Exception, "Attempt to process an image without acquiring one"

        image_center = array(self.im_array.shape)
        
        features = self.feature_finder.get_result();

        if(features == None):
            return features

        

        # Pupil features
        if 'pupil_position' in features:
            self.pupil_position = features['pupil_position']
        if 'pupil_radius' in features:
            self.pupil_radius = features['pupil_radius']
        if 'pupil_radius_CV' in features:
            self.pupil_radius_CV = features['pupil_radius_CV']
        # CR features
        if "cr_position" in features:
            self.cr_position = features['cr_position'];
        if "cr_radius" in features:
            self.cr_radius = features['cr_radius'];
        if "cr_radius_CV" in features:
            self.cr_radius_CV = features['cr_radius_CV'];
        return features
    
    def shutdown(self):
        return


