#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  CompositeEyeFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by Davide Zoccolan on 9/10/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

from EyeFeatureFinder import *
from scipy import *
from numpy import *
from FastRadialFeatureFinder import *
from SubpixelStarburstEyeFeatureFinder import *

from threading import Thread
from Queue import Queue

def ff(ff, in_queue, out_queue):
    while True:
        features = in_queue.get()
        ff.analyze_image(features['im_array'], features)
        new_features = ff.get_result()
        out_queue.put(new_features)

class CompositeEyeFeatureFinder(EyeFeatureFinder):

    # ==================================== function: __init__ ========================================
    def __init__(self, ff_radial, ff_starbust, pipelined=False):

        self.result = None
        self.last = None

        # Feature finders
        self.ff_fast_radial = ff_radial
        self.ff_starburst = ff_starbust

        self.pipelined = pipelined

        if pipelined:

            self.pipeline_primed_stage_1 = False
            self.pipeline_primed_stage_2 = False

            self.radial_ff_queue = Queue(5)
            self.starburst_ff_queue = Queue(5)
            self.out_queue = Queue(5)

            self.radial_ff_thread = Thread(target=ff, args=(self.ff_fast_radial, self.radial_ff_queue, self.starburst_ff_queue))
            self.starburst_ff_thread = Thread(target=ff, args=(self.ff_starburst, self.starburst_ff_queue, self.out_queue))

            self.radial_ff_thread.start()
            self.starburst_ff_thread.start()

    # ==================================== function: analyzeImage ========================================
    # @clockit
    def analyze_image(self, im, guess={}, **kwargs):

        if self.pipelined:
            if not self.pipeline_primed_stage_1:
                self.ff_fast_radial.analyze_image(im, guess)
                self.radial_primer = self.ff_fast_radial.get_result()
                self.pipeline_primed_stage_1 = True
            elif self.pipeline_primed_stage_2:
                self.starburst_ff_queue.put(self.radial_primer)
                self.pipeline_primed_stage_2 = True

            self.analyze_image_threaded(im, guess, **kwargs)
        else:
            self.analyze_image_serial(im, guess, **kwargs)


    def analyze_image_threaded(self, im, guess={}, **kwargs):
        guess['im_array'] = im
        self.radial_ff_queue.put(guess)

    def analyze_image_serial(self, im, guess={}, **kwargs):

        # #### FEATURE FINDER # 1: Get intial guess of pupil and CR using the fast radial finder
        # self.ff_fast_radial.target_kpixels = 10 #50
        self.ff_fast_radial.analyze_image(im, guess)  # NOTE: for now, the guess is not used by the fast radial feature finder
        features = self.ff_fast_radial.get_result()
        ds = features['dwnsmp_factor_coord']
        pupil_position_stage1 = features['pupil_position']
        cr_position_stage1 = features['cr_position']
        im_array_stage1 = features['im_array']

        if 'sobel_avg' in features:
            sobel_avg = features['sobel_avg']
        else:
            sobel_avg = None

        # #### FEATURE FINDER # 2: Refine the tracking using the star burst finder
        try:
        # If available, pass the last CR and Pupil radiuses as intial guesses for the star burst ff
            # if(self.last != None and 'pupil_radius' in self.last):
            #   features['pupil_radius'] = self.last['pupil_radius']
            # if(self.last != None and 'cr_radius' in self.last):
            #   features['cr_radius'] = self.last['cr_radius']

            # Run the starburst ff
            self.ff_starburst.analyze_image(im, features)
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

        if sobel_avg is not None:
            features['sobel_avg'] = sobel_avg

        features['timestamp'] = guess.get('timestamp', 0)

        self.result = self.last = features

    def get_result(self):
        if self.pipelined:
            return self.out_queue.get()
        else:
            return self.result
