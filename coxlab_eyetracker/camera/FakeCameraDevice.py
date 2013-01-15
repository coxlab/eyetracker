#
#  SimulatedCameraDevice.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 5/26/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#


from numpy import *
import os
import PIL.Image as Image
import time
import cPickle as pkl

import threading
from Queue import Queue

def acquire_continuously(im_array_, ff):
    while(1):
        im_array = im_array_.copy()
        ff.analyzeImage(im_array, None);



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

        self.frame_number = 0

        if(self.filename != None):
            ext = os.path.splitext(self.filename)[-1]
            print ext
            if ext == '.pkl':
                im = pkl.load(open(self.filename))
            else:
                im = Image.open(self.filename)

            self.im_array = array(im).astype(double)

            if(self.im_array.ndim == 3):
                self.im_array = mean(self.im_array, 2)
        else:
            self.im_array = None


        if(self.acquire_continuously):
            self.acquisition_thread = threading.Thread(target=acquireContinuously, args=[self.im_array, self.feature_finder])
            self.acquisition_thread.start()

    def acquire_image(self):
        self.frame_number += 1
        noise = 0.1 * random.rand(self.im_array.shape[0], self.im_array.shape[1])
        self.feature_finder.analyze_image(self.im_array + noise, {'timestamp':time.time()});

        return

    def	get_processed_image(self, guess=None):
        if(self.im_array == None):
            raise Exception, "Attempt to process an image without acquiring one"

        image_center = array(self.im_array.shape)

        features = self.feature_finder.get_result();
        features['frame_number'] = self.frame_number

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


