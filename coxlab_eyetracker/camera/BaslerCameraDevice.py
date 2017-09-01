#
#  ProsilicaCameraDevice.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 7/29/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

#
#  SimulatedCameraDevice.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 5/26/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

import pypylon as pylon
from numpy import *
#import matplotlib.pylab as pylab

import os
import time

import PIL.Image

import threading


def acquire_continuously(camera, ff):

    for im_array in self.camera.grab_images(-1):
        # frame = camera.getAndLockCurrentFrame()
        # im_array = (asarray(frame)).copy()
        # camera.releaseCurrentFrame()

        print "got a frame"

        ff.analyzeImage(im_array)


class BaslerCameraDevice:

    def __init__(self, _feature_finder, **kwargs):

        self.frame_number = 0

        self.camera = None

        self.im_array = None
        self.image_center = array([0, 0])
        self.pupil_position = array([0., 0.])
        self.cr_position = array([0., 0.])

        self.nframes_done = 0

        self.acquire_continuously = 0
        self.acquisition_thread = None

        self.feature_finder = _feature_finder
        
        print "Finding valid cameras..."
        time.sleep(1)
        camera_list = pylon.factory.find_devices()
        print camera_list

        if(len(camera_list) <= 0):
            raise Exception("Couldn't find a valid camera")

        try:
            print "Trying..."
            self.camera = pylon.factory.create_device(camera_list[0])
            self.camera.open()
            print "Did it"
        except:
            print "No good"
            raise Exception("Couldn't instantiate camera")

        # self.camera.setAttribute("BinningX", 1)
        # self.camera.setAttribute("BinningY", 1)
        
        # try:
        #     self.timestampFrequency = self.camera.getUint32Attribute("TimeStampFrequency")
        #     print "Found TimestampFrequency of: %f" % self.timestampFrequency
        # except:
        #     self.timestampFrequency = 1
        #     print "attribute: TimestampFrequency not found for camera, defaulting to 1"
        
        if(self.acquire_continuously):
            self.acquisition_thread = threading.Thread(target=acquire_continuously, args=[self.camera, self.feature_finder])
            self.acquisition_thread.start()

    def shutdown(self):
        print "Deleting camera (in python)"
        if(self.acquire_continuously):
            print "Terminating acquisition thread in BaslerCameraDevice"
            self.acquisition_thread.terminate()
        if(self.camera is not None):
            print "ending camera capture in BaslerCameraDevice"
            self.camera.close()

    def __del__(self):
        print "Deleting camera (in python)"
        if(self.acquire_continuously):
            self.acquisition_thread.terminate()
        if(self.camera is not None):
            self.camera.close()


    def acquire_image(self):

        if(self.acquire_continuously):
            return

        if(self.camera is None):
            raise Exception, "No valid camera is in place"

        self.im_array = self.camera.grab_image()
        self.im_array = self.im_array[0:240, 0:320]

        # frame = self.camera.getAndLockCurrentFrame()
        # self.im_array = (asarray(frame)).copy()
        # We could convert the timestamp from clock cycles to seconds by dividing by the available timestampFrequency
        # However, this could result in rounding errors. It might be easier to account for this in analysis scripts
        # or pass along timestampFrequency
        
        # timestamp = frame.timestamp / float(self.timestampFrequency)
        
        timestamp = 0 # dummy for now

        #timestamp = frame.timestamp
        #print "Timestamp: ", timestamp
        # self.camera.releaseCurrentFrame()
        self.frame_number += 1

        # start the analysis process

        #self.feature_finder.analyze_image(self.im_array.copy(), None)

        # push the image to the feature analyzer
        self.feature_finder.analyze_image(self.im_array.astype(float32), {"pupil_position":self.pupil_position, "cr_position": self.cr_position, "frame_number" : self.frame_number, "timestamp" : timestamp})
        return



    def get_processed_image(self, guess = None):

        features = self.feature_finder.get_result()

        if(features is None):
            return features

        if(features.has_key('pupil_position')):
            self.pupil_position = features['pupil_position']

        if(features.has_key('cr_position')):
            self.cr_position = features['cr_position']

        self.nframes_done += 1
        #features["frame_number"] = self.frame_number
        return features


