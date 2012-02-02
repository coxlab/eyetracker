#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  ImageEdgeDetector.py
#  EyeTrackerStageDriver
#
#  Created by Davide Zoccolan on 9/10/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

from numpy import *


class ImageProcessingBackend:

    def __init__(self):
        self.cached_shape = (0, 0)

    def autotune(self, example_im):
        self.cached_shape = example_im.shape
        return

    def sobel3x3(self, im, **kwargs):
        mag = None
        imgx = None
        imgy = None
        return (mag, imgx, imgy)

    def separable_convolution2d(self, im, row, col, **kwargs):
        result = None
        return result

    def find_minmax(self, im, **kwargs):
        min_coord = None
        max_coord = None
        return (min_coord, max_coord)

    def fast_radial_transform(self, im, radii, alpha, **kwargs):
        S = None
        return S


