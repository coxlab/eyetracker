#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from numpy import *
from EyeFeatureFinder import *

from VanillaBackend import *
from WovenBackend import *


class FastRadialFeatureFinder(EyeFeatureFinder):

    def __init__(self):

        # self.backend = VanillaBackend()
        self.backend = WovenBackend()
        # self.backend = OpenCLBackend()

        self.target_kpixels = 80.0  # 8.0
        self.max_target_kpixels = 50.0
        self.min_target_kpixels = 1.
        self.parameters_updated = 1

        self.alpha = 10.
        self.min_radius_fraction = 0.0126  # 1./2000.
        self.max_radius_fraction = 0.12  # 1./8.
        self.min_fraction = 1. / 1000.
        self.max_fraction = 0.35
        self.radius_steps = 6
        self.radiuses_to_try = [1]
        self.ds_factor = 1

        self.correct_downsampling = False

        self.do_refinement_phase = 0

        self.return_sobel = 0

        self.albino_mode = False
        self.albino_threshold = 10.

        self.cache_sobel = True
        self.cached_sobel = None
        self.compute_sobel_avg = True  # for autofocus
        self.sobel_avg = None

        # Voting
        self.outlier_cutoff = 1.
        self.maxmin_consensus_votes = 1

        self.image_contribution = 1

        self.last_positions = []

        self.available_filters = [u'sepfir', u'spline', u'fft', u'convolve2d']

        self.result = None

        self.restrict_top = 0
        self.restrict_bottom = 123
        self.restrict_left = 0
        self.restrict_right = 164

    # analyze the image and return dictionary of features gleaned
    # from it
    # @clockit
    def analyze_image(self, image, guess=None, **kwargs):
        # print "fr"
        im_array = image
        # im_array = image.astype(double)
        im_array = im_array[::self.ds_factor, ::self.ds_factor]

        if guess is not None:
            features = guess
        else:
            features = {'pupil_size': None, 'cr_size': None}

        if self.parameters_updated or self.backend.cached_shape \
            != im_array.shape:
            logging.debug('Recaching...')
            logging.debug('Target kPixels: %s' % self.target_kpixels)
            logging.debug('Max Radius Fraction: %s' % self.max_radius_fraction)
            logging.debug('Radius steps: %s' % self.radius_steps)
            im_pixels = image.shape[0] * image.shape[1]
            self.ds_factor = int(sqrt(im_pixels / int(self.target_kpixels
                                 * 1000)))
            if self.ds_factor <= 0:
                self.ds_factor = 1
            im_array = image[::self.ds_factor, ::self.ds_factor]

            self.backend.autotune(im_array)
            self.parameters_updated = 0

            self.radiuses_to_try = linspace(ceil(self.min_radius_fraction
                    * im_array.shape[0]), ceil(self.max_radius_fraction
                    * im_array.shape[0]), self.radius_steps)
            self.radiuses_to_try = unique(self.radiuses_to_try.astype(int))
            logging.debug('Radiuses to try: %s' % self.radiuses_to_try)
            logging.debug('Downsampling factor: %s' % self.ds_factor)

        ds = self.ds_factor

        S = self.backend.fast_radial_transform(im_array, self.radiuses_to_try,
                self.alpha)

        S[:, 0:self.restrict_left] = -1.
        S[:, self.restrict_right:] = -1.
        S[0:self.restrict_top, :] = -1.
        S[self.restrict_bottom:, :] = -1.

        if self.albino_mode:
            (pupil_coords, cr_coords) = self.find_albino_features(S, im_array)
        else:
            (pupil_coords, cr_coords) = self.backend.find_minmax(S)

        if pupil_coords is None:
            pupil_coords = array([0., 0.])

        if cr_coords is None:
            cr_coords = array([0., 0.])

        if self.correct_downsampling:
            features['pupil_position'] = array([pupil_coords[0],
                    pupil_coords[1]]) * ds
            features['cr_position'] = array([cr_coords[0], cr_coords[1]]) * ds
            features['dwnsmp_factor_coord'] = 1
        else:
            features['pupil_position'] = array([pupil_coords[0],
                    pupil_coords[1]])
            features['cr_position'] = array([cr_coords[0], cr_coords[1]])
            features['dwnsmp_factor_coord'] = ds

        features['transform'] = S
        features['im_array'] = im_array
        features['im_shape'] = im_array.shape

        features['restrict_top'] = self.restrict_top
        features['restrict_bottom'] = self.restrict_bottom
        features['restrict_left'] = self.restrict_left
        features['restrict_right'] = self.restrict_right

        if self.return_sobel:
            # this is very inefficient, and only for debugging
            (m, x, y) = self.backend.sobel3x3(im_array)
            features['sobel'] = m

        self.result = features

    def update_parameters(self):
        self.parameters_updated = 1

    def get_result(self):
        return self.result

    def find_albino_features(self, T, im):
        import scipy.ndimage as ndi

        binarized = zeros_like(T)
        binarized[T > self.albino_threshold] = True
        (labels, nlabels) = ndi.label(binarized)
        slices = ndi.find_objects(labels)

        intensities = []
        transform_means = []

        if len(slices) < 2:
            return (None, None)

        for s in slices:

            transform_means.append(mean(T[s]))
            intensities.append(mean(im[s]))

        sorted_transform_means = argsort(transform_means)
        candidate1 = sorted_transform_means[-1]
        candidate2 = sorted_transform_means[-2]

        c1_center = array(ndi.center_of_mass(im, labels, candidate1 + 1))
        c2_center = array(ndi.center_of_mass(im, labels, candidate2 + 1))

        if intensities[candidate1] > intensities[candidate2]:
            return (c2_center, c1_center)
        else:
            return (c1_center, c2_center)


def test_it():

    import matplotlib.pylab as plt
    import numpy
    from matplotlib.pylab import imread
    import time

    im = \
        imread('/Users/davidcox/Repositories/coxlab/eyetracker/ImageProcessing/RatEye_snap12_zoom.jpg'
               )
    im = im.astype(numpy.float64)

    noplot = 1

    f = FastRadialFeatureFinder()
    f.return_sobel = True
    trials = 100

    if 0:
        tic = time.time()
        for i in range(0, trials):
            test = f.analyze_image(im, filter='fft')

        print 'FFT: ', (time.time() - tic) / trials

        plt.figure()
        plt.imshow(test['transform'])
        plt.title('FFT')

    if 1:

        f.reuse_storage = 0
        f.use_sse3 = 0
        f.filter = 'sepfir'
        f.analyze_image(im, filter='sepfir')
        test = f.get_result()
        tic = time.time()
        for i in range(0, trials):
            f.analyze_image(im, filter='sepfir')
            test = f.get_result()
        seconds_per_frame = (time.time() - tic) / trials
        print 'Sep FIR: ', seconds_per_frame
# print '\t ', 1. / seconds_per_frame, ' FPS'

        if not noplot:
            plt.figure()
            plt.imshow(test['transform'])

            plt.figure()

            # pylab.imshow(test['im_array'], cmap=pylab.cm.gray)
            plt.imshow(test['sobel'], cmap=pylab.cm.gray)

            plt.hold('on')
            cr = test['cr_position']
            pupil = test['pupil_position']
            plt.plot([cr[1]], [cr[0]], 'r+')
            plt.plot([pupil[1]], [pupil[0]], 'b+')
            plt.title('Sep FIR')

    if 0:
        tic = time.time()
        for i in range(0, trials):
            test = f.analyze_image(im, filter='spline')
        print 'SPLINE: ', (time.time() - tic) / trials

        plt.figure()
        plt.imshow(test['transform'])
        plt.title('SPLINE')

    if 0:
        tic = time.time()
        for i in range(0, trials):
            test = f.analyze_image(im)
        print 'Convolve2d: ', (time.time() - tic) / trials

        plt.figure()
        plt.imshow(test['transform'])
        plt.title('Convolve2d')

    if 0:
        f.reuse_storage = 1
        tic = time.time()

        def sepfir_multithread_test(i, f, im):
            test = f.analyze_image(im, filter='sepfir')

        foreach(lambda t: sepfir_multithread_test(t, f, im), range(0, trials),
                3)
        print 'Sep FIR (multithreaded): ', (time.time() - tic) / trials


    # pylab.show()

if __name__ == '__main__':
    test_it()
