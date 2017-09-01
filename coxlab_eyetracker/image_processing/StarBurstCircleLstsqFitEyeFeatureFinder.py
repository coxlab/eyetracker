#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  StarBurstEyeFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 7/29/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

from EyeFeatureFinder import *
from scipy import *
from pylab import *
from numpy import *
import numpy.random as random
from scipy import optimize
from EdgeDetection import *


class StarBurstEyeFeatureFinder(EyeFeatureFinder):

    # ==================================== function: __init__ ========================================
    def __init__(self):

        # Intialize some visualization and print flags
        self.FlagPlotFinal = False
        self.FlagPlotCR = False
        self.FlagPrintCR = False
        self.FlagPlotPupil = False
        self.FlagPrintPupil = False

        # ####### Intialize some variables and arrays #######

        # #### Circle detection parameters ####
        self.FittingMethod = 2  # 0=circle; 2=ellipse; do not use 1

        # General
        self.Points2SkipInDxAndSxSearchAlongRays = 4
        self.starburst_object_parameters_updated = 0
        self.FlagCompAltGuesses = False
        self.FlagSmooth = 0
        self.mfact_grad_star_std = 0.5  # 2.5 #1.5
        self.Dpix_ToHigh = 3
        self.mfact_CR_radius = 4  # 2.5 #2

        # Pupil specific
        self.ThPup = 0.05
        self.Nrays_quadPupil = 12
        self.RayLenght_default_Pup = 25
        self.Perc_PupImgSize2RayLengDefault = 0.5  # 0.1 # must be between 0 and 1
        self.mFact_PupRadius2RayLeng = 2.5
        self.mFact_PupRadius2GradImgPatch = 1.2 * self.mFact_PupRadius2RayLeng
        self.mFatc_PupGradImgPatch2ThImgPatch = 2

        # CR specific
        self.ThCR = 0.97
        self.Nrays_quadCR = 8
        self.RayLenght_default_CR = 20
        self.Perc_CRImgSize2RayLengDefault = 0.2  # 0.05 # must be between 0 and 1
        self.mFact_CRRadius2RayLeng = 2.5
        self.mFact_CRRadius2GradImgPatch = 1.2 * self.mFact_CRRadius2RayLeng
        self.mFatc_CRGradImgPatch2ThImgPatch = 2

        # Threshould on the Coefficient of Variation of the CR and Pupil radius (used to assess if theey are ROUND ENOUGH)
        self.Th_Pup_radius_CV = 0.4  # 0.2
        self.Th_CR_radius_CV = 0.4  # 0.2

        # Pupil and CR ccenter and radius
        self.CR_cntr = array([])
        self.CR_radius = 0
        self.Pup_cntr = array([])
        self.Pup_radius = 0
        self.result = None

        # Image and gradient properties
        self.N_rows_crop = 50
        self.N_cols_crop = 50
        self.im_array = array([])
        self.im_array_whole = array([])
        self.im_grad_x = array([])
        self.im_grad_y = array([])
        self.im_grad_mag = array([])

        # Choose which algorithm must be used to execute the starburst
        self.SB = StarBurstVectorized(self.mfact_grad_star_std,
                                      self.Dpix_ToHigh)

    # ==================================== function: reset_ ========================================
    def reset(self):

        # #### Circle detection parameters ####
        # General
        self.Points2SkipInDxAndSxSearchAlongRays = 4
        self.starburst_object_parameters_updated = 1
        self.FlagCompAltGuesses = False
        self.FlagSmooth = 0
        self.mfact_grad_star_std = 1.5
        self.Dpix_ToHigh = 3
        self.mfact_CR_radius = 2.5  # 2
        # Pupil specific
        self.ThPup = 0.05
        self.Nrays_quadPupil = 4
        self.RayLenght_default_Pup = 25
        self.Perc_PupImgSize2RayLengDefault = 0.1  # must be between 0 and 1
        self.mFact_PupRadius2RayLeng = 2.5
        self.mFact_PupRadius2GradImgPatch = 2 * self.mFact_PupRadius2RayLeng
        self.mFatc_PupGradImgPatch2ThImgPatch = 2
        # CR specific
        self.ThCR = 0.97
        self.Nrays_quadCR = 4
        self.RayLenght_default_CR = 20
        self.Perc_CRImgSize2RayLengDefault = 0.05  # must be between 0 and 1
        self.mFact_CRRadius2RayLeng = 2.5
        self.mFact_CRRadius2GradImgPatch = 2 * self.mFact_CRRadius2RayLeng
        self.mFatc_CRGradImgPatch2ThImgPatch = 2

        # Threshould on the Coefficient of Variation of the CR and Pupil radius (used to assess if theey are ROUND ENOUGH)
        self.Th_Pup_radius_CV = 0.2
        self.Th_CR_radius_CV = 0.2

    # ==================================== function: updateParameters ========================================
    def update_parameters(self):
        self.starburst_object_parameters_updated = 1

    # ==================================== function: reinstantiateStarBurst ========================================
    def reinstantiate_starburst(self, mfact_grad_star_std=None,
                                Dpix_ToHigh=None):

        if mfact_grad_star_std is not None:
            self.mfact_grad_star_std = mfact_grad_star_std
        if Dpix_ToHigh is not None:
            self.Dpix_ToHigh = Dpix_ToHigh

        self.SB = StarBurstVectorized(self.mfact_grad_star_std,
                                      self.Dpix_ToHigh)

    # ==================================== function: analyzeImage ========================================
    def analyze_image(self, im, guess=None, **kwargs):
        # print "Guess: ", guess

        # ### Read out the inital guess
        # Pupil features
        if guess is not None:
            if 'pupil_position' in guess and guess['pupil_position'] \
                is not None:
                _StartPupiCoord = guess['pupil_position']
                StartPupiCoord = array([0.0, 0.0])
                StartPupiCoord[0] = _StartPupiCoord[1]
                StartPupiCoord[1] = _StartPupiCoord[0]
            else:
                StartPupiCoord = []
            if 'pupil_radius' in guess and guess['pupil_radius'] is not None:
                StartPupiRadius = guess['pupil_radius']
            else:
                StartPupiRadius = None
            if 'pupil_radius_CV' in guess and guess['pupil_radius_CV'] \
                is not None:
                StartPupCV = guess['pupil_radius_CV']
            else:
                StartPupCV = None

            # CR features
            if 'cr_position' in guess and guess['cr_position'] is not None:
                _StartCRCoord = guess['cr_position']
                StartCRCoord = array([0.0, 0.0])
                StartCRCoord[0] = _StartCRCoord[1]
                StartCRCoord[1] = _StartCRCoord[0]
            else:
                StartCRCoord = []
            if 'cr_radius' in guess and guess['cr_radius'] is not None:
                StartCRRadius = guess['cr_radius']
            else:
                StartCRRadius = None
            if 'cr_radius_CV' in guess and guess['cr_radius_CV'] is not None:
                StartCRCV = guess['cr_radius_CV']
            else:
                StartCRCV = None
            # Downsampling factor used to compute the Pupil and CR coorinates that were passed to this method
            if 'dwnsmp_factor_coord' in guess and guess['dwnsmp_factor_coord'] \
                is not None:
                ds_factor_coord = guess['dwnsmp_factor_coord']
            else:
                ds_factor_coord = 1
            # Downsampling factor used to compute the Pupil and CR size that were passed to this method
            if 'dwnsmp_factor_size' in guess and guess['dwnsmp_factor_size'] \
                is not None:
                ds_factor_size = guess['dwnsmp_factor_size']
            else:
                ds_factor_size = 1
        else:
            StartPupiCoord = []
            StartPupiRadius = None
            StartCRCoord = []
            StartCRRadius = None
            ds_factor_coord = 1
            ds_factor_size = 1

        # Scale back all the eye features according to the downsampling factor
        if StartPupiCoord is not None:
            StartPupiCoord *= ds_factor_coord
        if StartPupiRadius is not None:
            StartPupiRadius *= ds_factor_size
        if StartCRCoord is not None:
            StartCRCoord *= ds_factor_coord
        if StartCRRadius is not None:
            StartCRRadius *= ds_factor_size

        # CLear all possible previously stored image and pupil/CR infos
        self._clear()

        # Get the input image
        if im is None or im.shape[0] == 0 or im.shape[1] == 0:
            raise Exception('Empty image')

        self.im_array_whole = self.im_array = double(im)

        # Test if the starburst object must be reinstantiated
        if self.starburst_object_parameters_updated:
            self.reinstantiate_starburst(self.mfact_grad_star_std,
                    self.Dpix_ToHigh)
            self.starburst_object_parameters_updated = 0

        # ****************** Find CR center ******************
        # Compute the default ray length as a fraction of the image size
        self.RayLenght_default_CR = int(self.Perc_CRImgSize2RayLengDefault
                                        * self.im_array_whole.shape[1])
        if self.FlagPrintCR:
            print 'percentage of the image taken to compute the CR ray length =', \
                self.Perc_CRImgSize2RayLengDefault
            print 'im array shape =', self.im_array_whole.shape[1]
            print 'computed ray length =', self.RayLenght_default_CR
        try:
            # First, try to use the initial guess of the CR center passed by the calling function (if available)
            FlagForceGuessCRCntr = False
            cr_info = self._find_CR(
                self.Nrays_quadCR,
                StartCRCoord,
                StartCRRadius,
                FlagForceGuessCRCntr,
                self.FlagPlotCR,
                self.FlagPrintCR,
                )
        except Exception, e:
            print e.message
            if self.FlagCompAltGuesses:
                if size(StartCRCoord) != 0:
                    try:
                        # Next, try to recompute the intial guess, searching an image patch centered on the previous guess
                        if self.FlagPlotFinal:
                            print '------->>> Local search (threshold) on an image patch to find an intial guess for the CR'
                        self._clear()
                        FlagForceGuessCRCntr = True
                        cr_info = self._find_CR(
                            self.Nrays_quadCR,
                            StartCRCoord,
                            StartCRRadius,
                            FlagForceGuessCRCntr,
                            self.FlagPlotCR,
                            self.FlagPrintCR,
                            )
                    except:
                        # Finally, start fresh and look for an initial guess over the whole image
                        if self.FlagPlotFinal:
                            print '------->>> Search (threshold) the whole image to find an intial guess for the CR'
                        self._clear()
                        StartCRCoord = []
                        cr_info = self._find_CR(
                            self.Nrays_quadCR,
                            StartCRCoord,
                            StartCRRadius,
                            FlagForceGuessCRCntr,
                            self.FlagPlotCR,
                            self.FlagPrintCR,
                            )
                else:

                # The initial guess based on the Th was wrong ... try other spots
                    FlagPlot = self.FlagPlotCR  # True
                    (CR_cntr, iCR, jCR) = self._first_guess_CR_center(FlagPlot)
                    # NOTE: spedwise, creating and then permuting a list is quicker than creating and then permuting an array or using the "permutation" function
                    I = range(len(iCR))
                    random.shuffle(I)
    #                 iCR[I[0]] = 64
    #                 jCR[I[0]] = 120
                    k = 0
                    MaxCount = 10
                    FlagIterate = 1
                    while FlagIterate and k < MaxCount:
                        self._clear()
                        FlagIterate = 0
                        # Choose a new guess
                        StartCRCoord = [jCR[I[k]], iCR[I[k]]]
                        k = k + 1
                        try:
                            if self.FlagPlotFinal:
                                print '--->>> Attempt #', k, \
                                    ': try as a new CR center guess: ', \
                                    StartCRCoord
                            if FlagPlot:
                                # Plot image
                                figure()
                                imshow(self.im_array_whole)
                                hold(1)
                                # Plot pupil
                                plot(jCR, iCR, 'r.')
                                ho = plot(array([StartCRCoord[0]]),
                                        array([StartCRCoord[1]]), '+b')
                                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                                setp(gca(), 'xlim', [1,
                                     self.im_array_whole.shape[1]], 'ylim',
                                     [self.im_array_whole.shape[0], 1])
                            cr_info = self._findCR(
                                self.Nrays_quadCR,
                                StartCRCoord,
                                StartCRRadius,
                                FlagForceGuessCRCntr,
                                self.FlagPlotCR,
                                self.FlagPrintCR,
                                )
                        except:
                            FlagIterate = 1
                    # If no new guess was found
                    if FlagIterate:
                        raise Exception('Search for a suitable guess of the CR center FAILED!')
            else:

            # Do not look for new guesses ... just give up
                raise Exception('The starburst finder failed to find a reliable CR!')

        # ****************** Find Pupil center ******************
        # Compute the default ray length as a fraction of the image size
        self.RayLenght_default_Pup = int(self.Perc_PupImgSize2RayLengDefault *
                                         self.im_array_whole.shape[1])
        if self.FlagPrintPupil:
            print 'percentage of the image taken to compute the Pupil ray length =', \
                self.Perc_PupImgSize2RayLengDefault
            print 'im array shape =', self.im_array_whole.shape[1]
            print 'computed ray length =', self.RayLenght_default_Pup
        try:
            # First, try to use the initial guess of the Pupil center passed by the calling function (if available)
            FlagForceGuessPupCntr = False
            pupil_info = self._find_pupil(
                self.Nrays_quadPupil,
                StartPupiCoord,
                StartPupiRadius,
                FlagForceGuessPupCntr,
                self.FlagPlotPupil,
                self.FlagPrintPupil,
                )
        except Exception, error:
            # Restore the correct value of the CR center (it may have been changed by the _findPupil into the coordinates of the image patch over which the gradient was computed)
            self.CR_cntr = cr_info[0]
            if self.FlagCompAltGuesses:
                if size(StartPupiCoord) != 0:
                    try:
                        # Next, try to recompute the intial guess, searching an image patch centered on the previous guess
                        if self.FlagPlotFinal:
                            print '------->>> Local search (threshold) on an image patch to find an intial guess for the Pupil'
                        FlagForceGuessPupCntr = True
                        pupil_info = self._find_pupil(
                            self.Nrays_quadPupil,
                            StartPupiCoord,
                            StartPupiRadius,
                            FlagForceGuessPupCntr,
                            self.FlagPlotPupil,
                            self.FlagPrintPupil,
                            )
                    except:
                        # Restore the correct value of the CR center (it may have been changed by the _findPupil into the coordinates of the image patch over which the gradient was computed)
                        self.CR_cntr = cr_info[0]
                        # Finally, start fresh and look for an initial guess over the whole image
                        if self.FlagPlotFinal:
                            print '------->>> Search (threshold) the whole image to find an intial guess for the Pupil'
                        StartPupiCoord = []
    #                     self.ThPup = 0.20 # make it fail
                        pupil_info = self._find_pupil(
                            self.Nrays_quadPupil,
                            StartPupiCoord,
                            StartPupiRadius,
                            FlagForceGuessPupCntr,
                            self.FlagPlotPupil,
                            self.FlagPrintPupil,
                            )
                else:

                # The initial guess based on the Th was wrong ... try other spots
                    FlagPlot = self.FlagPlotPupil  # True
                    (Pup_cntr, iPup, jPup) = \
                        self._first_guess_pupil_centr(FlagPlot)
                    # NOTE: spedwise, creating and then permuting a list is quicker than creating and then permuting an array or using the "permutation" function
                    I = range(len(iPup))
                    random.shuffle(I)
    #                 iPup[I[0]] = 190.45
    #                 jPup[I[0]] = 221.12
                    k = 0
                    MaxCount = 10
                    FlagIterate = 1
                    while FlagIterate and k < MaxCount:
                        FlagIterate = 0
                        # Restore the correct value of the CR center (it may have been changed by the _findPupil into the coordinates of the image patch over which the gradient was computed)
                        self.CR_cntr = cr_info[0]
                        # Choose a new guess
                        StartPupiCoord = [jPup[I[k]], iPup[I[k]]]
                        k = k + 1
                        try:
                            if self.FlagPlotFinal:
                                print '--->>> Attempt #', k, \
                                    ': try as a new pupil center guess: ', \
                                    StartPupiCoord
                            if FlagPlot:
                                # Plot image
                                figure()
                                imshow(self.im_array_whole)
                                hold(1)
                                # Plot pupil
                                plot(jPup, iPup, 'g.')
                                ho = plot(array([StartPupiCoord[0]]),
                                        array([StartPupiCoord[1]]), '+b')
                                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                                setp(gca(), 'xlim', [1,
                                     self.im_array_whole.shape[1]], 'ylim',
                                     [self.im_array_whole.shape[0], 1])
                            pupil_info = self._find_pupil(
                                self.Nrays_quadPupil,
                                StartPupiCoord,
                                StartPupiRadius,
                                FlagForceGuessPupCntr,
                                self.FlagPlotPupil,
                                self.FlagPrintPupil,
                                )
                        except:
                            FlagIterate = 1
                    # If no new guess was found
                    if FlagIterate:
                        raise Exception('Search for a suitable guess of the Pupil center FAILED!')
            else:

            # Do not look for new guesses ... just give up
                # raise Exception, "The starburst finder failed to find a reliable Pupil: " + error
                raise Exception(error)

        features = {
            'pupil_position': pupil_info[0],
            'pupil_radius': 2 * pupil_info[1],
            'pupil_radius_CV': pupil_info[2],
            'cr_position': cr_info[0],
            'cr_radius': 2 * cr_info[1],
            'cr_radius_CV': cr_info[2],
            }
        # Rays and boundary intersections coordinates (x and y order is reversed before saving them to the features dictionary)

        starburst = {}
        starburst['pupil_rays_start'] = pupil_info[3][:, -1:-3:-1]
        starburst['pupil_rays_end'] = pupil_info[4][:, -1:-3:-1]
        starburst['pupil_boundary'] = pupil_info[5][:, -1:-3:-1]
        starburst['cr_rays_start'] = cr_info[3][:, -1:-3:-1]
        starburst['cr_rays_end'] = cr_info[4][:, -1:-3:-1]
        starburst['cr_boundary'] = cr_info[5][:, -1:-3:-1]

        features['starburst'] = starburst

        # reverse the order of the coordinates
        pupil_pos = features['pupil_position']
        features['pupil_position'] = pupil_pos[::-1]
        cr_pos = features['cr_position']
        features['cr_position'] = cr_pos[::-1]
        features['im_array'] = im
        self.result = features

        # return features

    # ==================================== function: get_result ========================================
    def get_result(self):
        return self.result

    # TODO: this is a hack to be compatible with Davide's code.
    # There is no reason that these shouldn't be taken directly from
    # the image array whenever they are needed

    def _get_im_array_nrows(self):
        if self.im_array is None or self.im_array.shape is None \
            or len(self.im_array.shape) < 1:
            return 0

        return self.im_array.shape[0]

    def _get_im_array_ncols(self):
        if self.im_array is None or self.im_array.shape is None \
            or len(self.im_array.shape) < 2:
            return 0

        return self.im_array.shape[1]

    nrow = property(_get_im_array_nrows)
    ncol = property(_get_im_array_ncols)

    # ==================================== function: _clear ========================================
    def _clear(self):

        # Reset to empty all image information
        self.im_array = array([])
        self.im_grad_x = array([])
        self.im_grad_y = array([])

        self.im_grad_mag = array([])

        # Rest also CR center and radius
        self.CR_cntr = array([])
        self.CR_radius = 0

#         self.Pup_cntr = array([])
#         self.Pup_radius = 0

    # ==================================== function: _firstGuessPupilCntr ========================================
    def _first_guess_pupil_center(self, FlagPlot=False, Frame_cntr=None,
                                  N_rows_crop=None, N_cols_crop=None):

        if FlagPlot:
            print '\nGuess PUPIL center: INITIAL N_rows_crop =', N_rows_crop, \
                '; N_cols_crop =', N_cols_crop

        # Choose whether the Pupil center should be guessed over the whole image (no patch infos passed as arguments) or over a patch of the image (use patch infos passed as arguments)
        if Frame_cntr is None:
            # Use the whole image to search the Pupil
            self.im_array = self.im_array_whole
        else:
            # Crop the image area over which the Pupil must be looked for (first make sure that the cropping mask is within the image)
            if Frame_cntr[1] - N_rows_crop < 0:
                N_rows_crop = Frame_cntr[1]
            if Frame_cntr[1] + N_rows_crop + 1 > self.im_array_whole.shape[0]:
                N_rows_crop = self.im_array_whole.shape[0] - Frame_cntr[1] - 1
            if Frame_cntr[0] - N_cols_crop < 0:
                N_cols_crop = Frame_cntr[0]
            if Frame_cntr[0] + N_cols_crop + 1 > self.im_array_whole.shape[1]:
                N_cols_crop = self.im_array_whole.shape[1] - Frame_cntr[0] - 1
            self.im_array = self.im_array_whole[Frame_cntr[1] - N_rows_crop:
                    Frame_cntr[1] + N_rows_crop + 1, Frame_cntr[0]
                    - N_cols_crop:Frame_cntr[0] + N_cols_crop + 1]

        if FlagPlot:
            print 'Guess PUPIL center: N_rows_crop =', N_rows_crop, \
                '; N_cols_crop', N_cols_crop
            if Frame_cntr is not None:
                print 'Initial guess =', Frame_cntr
                print 'Cropped rows =', Frame_cntr[1] - N_rows_crop, ',', \
                    Frame_cntr[1] + N_rows_crop + 1
                print 'Cropped cols =', Frame_cntr[0] - N_cols_crop, ',', \
                    Frame_cntr[0] + N_cols_crop + 1

        # Find pupil
        (iPup, jPup) = where(self.im_array < self.im_array.min() + self.ThPup
                             * (self.im_array.max() - self.im_array.min()))
        iPup = double(iPup)
        jPup = double(jPup)
    #     Pup_cntr = [jPup.mean(), iPup.mean()]
        Pup_cntr = array([int(median(jPup)), int(median(iPup))])

        if FlagPlot:
            # Plot image
            figure()
            imshow(self.im_array)
            hold(1)
            # Plot pupil
            plot(jPup, iPup, 'g.')
            ho = plot(array([Pup_cntr[0]]), array([Pup_cntr[1]]), '+b')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            setp(gca(), 'xlim', [1, self.im_array.shape[1]], 'ylim',
                 [self.im_array.shape[0], 1])

        if Frame_cntr is not None:
            # Change back the coordinates of the guessed Pupil center into the reference system of the whole image
            # The coordinate change is given by this expression: Pupcntr_wholeImg = FrameCntr_wholeImg + Pupcntr_patchImg - FrameCntr_patchImg
            Pup_cntr = Frame_cntr + Pup_cntr - array([N_cols_crop, N_rows_crop])
            iPup = Frame_cntr[1] + iPup - N_rows_crop
            jPup = Frame_cntr[0] + jPup - N_cols_crop

        return (Pup_cntr, iPup, jPup)

    # ==================================== function: _firstGuessCRCntr ========================================
    def _first_guess_CR_center(self, FlagPlot=False, Frame_cntr=None,
                               N_rows_crop=None, N_cols_crop=None):

        # Choose whether the CR center should be guessed over the whole image (no patch infos passed as arguments) or over a patch of the image (use patch infos passed as arguments)
        if Frame_cntr is None:
            # Use the whole image to search the CR
            self.im_array = self.im_array_whole
        else:
            # Crop the image area over which the CR must be looked for (first make sure that the cropping mask is within the image)
            if Frame_cntr[1] - N_rows_crop < 0:
                N_rows_crop = Frame_cntr[1]
            if Frame_cntr[1] + N_rows_crop + 1 > self.im_array_whole.shape[0]:
                N_rows_crop = self.im_array_whole.shape[0] - Frame_cntr[1] - 1
            if Frame_cntr[0] - N_cols_crop < 0:
                N_cols_crop = Frame_cntr[0]
            if Frame_cntr[0] + N_cols_crop + 1 > self.im_array_whole.shape[1]:
                N_cols_crop = self.im_array_whole.shape[1] - Frame_cntr[0] - 1
            self.im_array = self.im_array_whole[Frame_cntr[1] - N_rows_crop:
                    Frame_cntr[1] + N_rows_crop + 1, Frame_cntr[0]
                    - N_cols_crop:Frame_cntr[0] + N_cols_crop + 1]

        # Find CR
        (iCR, jCR) = where(self.im_array > self.ThCR * self.im_array.max())
        iCR = double(iCR)
        jCR = double(jCR)
        CR_cntr = array([int(median(jCR)), int(median(iCR))])

        if FlagPlot:
            # Plot image
            fig = figure()
            imshow(self.im_array)
            hold(1)
            # Plot CR
            plot(jCR, iCR, 'r.')
            ho = plot(array([CR_cntr[0]]), array([CR_cntr[1]]), '+b')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            setp(gca(), 'xlim', [1, self.im_array.shape[1]], 'ylim',
                 [self.im_array.shape[0], 1])

        if Frame_cntr is not None:
            # Change back the coordinates of the guessed CR center into the reference system of the whole image
            # The coordinate change is given by this expression: CRcntr_wholeImg = FrameCntr_wholeImg + CRcntr_patchImg - FrameCntr_patchImg
            CR_cntr = Frame_cntr + CR_cntr - array([N_cols_crop, N_rows_crop])

        return (CR_cntr, iCR, jCR)

    # ==================================== function: _computeImageGradient ========================================
    def _compute_image_gradient(self, Frame_cntr, N_rows_crop, N_cols_crop,
                                FlagPlot=False):

        if FlagPlot:
            print '\nGradient patch: INITIAL N_rows_crop =', N_rows_crop, \
                '; N_cols_crop =', N_cols_crop

        # ##### The next code (and the flaf FlagPadVsCrop) matters when the patch over which the gradient must be computed extends beyond the image boundaries.
        # In this case two options are available:
        # 1) FlagPadVsCrop = 1: the image is cropped where it exceeds its boundaries and then the resulting image patch is PADDED so that it meets
        #    the (2*N_rows_crop+1) x (2*N_cols_crop size+1) originally requested (this implies that NO rays are ever shot OUTSIDE the image patch)
        # 2) FlagPadVsCrop = 0: the image is cropped not only where it exceeds its boundaries but also on the other side of the patch center (i.e., the pupil
        #    or CR guess), so that the guessed center is actually the center of the patch (this impies that some rays CAN be shot OUTSIDE the image patch,
        #    forcing the program to exit with an error conditions).
        # To summarize:
        # 1 -> extend (pad) the image beyond its boundaries to meet the required image patch size
        # 2 -> reduce (crop) the image (in a way that is symmetrical around the guessed center), so that the image patch is contained within the image boundaries
        # #####
        FlagPadVsCrop = 1

        # ########### 1) PAD the image ###########
        if FlagPadVsCrop:
            # Crop out the part of the image that exceed the image boundaries
            if Frame_cntr[1] - N_rows_crop < 0:
                N_rows_crop_sx = Frame_cntr[1]
            else:
                N_rows_crop_sx = N_rows_crop
            if Frame_cntr[1] + N_rows_crop + 1 > self.im_array_whole.shape[0]:
                N_rows_crop_dx = self.im_array_whole.shape[0] - Frame_cntr[1] \
                    - 1
            else:
                N_rows_crop_dx = N_rows_crop
            if Frame_cntr[0] - N_cols_crop < 0:
                N_cols_crop_top = Frame_cntr[0]
            else:
                N_cols_crop_top = N_cols_crop
            if Frame_cntr[0] + N_cols_crop + 1 > self.im_array_whole.shape[1]:
                N_cols_crop_bot = self.im_array_whole.shape[1] - Frame_cntr[0] \
                    - 1
            else:
                N_cols_crop_bot = N_cols_crop

            # Build the pad array (all padding pixels are set to the average of the image boundaries that are crossed by the image patch)
            edge_array = array([])
            if Frame_cntr[1] - N_rows_crop < 0:
                edge_array = hstack((edge_array,
                                    self.im_array_whole[Frame_cntr[1]
                                    - N_rows_crop_sx, Frame_cntr[0]
                                    - N_cols_crop_top:Frame_cntr[0]
                                    + N_cols_crop_bot + 1]))
            if Frame_cntr[1] + N_rows_crop + 1 > self.im_array_whole.shape[0]:
                edge_array = hstack((edge_array,
                                    self.im_array_whole[Frame_cntr[1]
                                    + N_rows_crop_dx, Frame_cntr[0]
                                    - N_cols_crop_top:Frame_cntr[0]
                                    + N_cols_crop_bot + 1]))
            if Frame_cntr[0] - N_cols_crop < 0:
                edge_array = hstack((edge_array,
                                    self.im_array_whole[Frame_cntr[1]
                                    - N_rows_crop_sx:Frame_cntr[1]
                                    + N_rows_crop_dx + 1, Frame_cntr[0]
                                    - N_cols_crop_top]))
            if Frame_cntr[0] + N_cols_crop + 1 > self.im_array_whole.shape[1]:
                edge_array = hstack((edge_array,
                                    self.im_array_whole[Frame_cntr[1]
                                    - N_rows_crop_sx:Frame_cntr[1]
                                    + N_rows_crop_dx + 1, Frame_cntr[0]
                                    + N_cols_crop_bot]))

            if edge_array.shape[0] > 0:
                pad_array = edge_array.mean() * ones((2 * N_rows_crop + 1, 2
                        * N_cols_crop + 1))
            else:
                pad_array = zeros((2 * N_rows_crop + 1, 2 * N_cols_crop + 1))

            # NOTE: tmp_array is only for debug (it is not used): keep it commented
            # tmp_array = pad_array[ N_rows_crop-N_rows_crop_sx:N_rows_crop-N_rows_crop_sx+N_rows_crop_sx+N_rows_crop_dx+1, N_cols_crop-N_cols_crop_top:N_cols_crop-N_cols_crop_top+N_cols_crop_top+N_cols_crop_bot+1 ]
            # print 'tmp_array shape = ', tmp_array.shape

            # Substitute the cropped image into the proper area of the pad array
            im_array = self.im_array_whole[Frame_cntr[1] - N_rows_crop_sx:
                    Frame_cntr[1] + N_rows_crop_dx + 1, Frame_cntr[0]
                    - N_cols_crop_top:Frame_cntr[0] + N_cols_crop_bot + 1]
            pad_array[N_rows_crop - N_rows_crop_sx:N_rows_crop - N_rows_crop_sx
                      + N_rows_crop_sx + N_rows_crop_dx + 1, N_cols_crop
                      - N_cols_crop_top:N_cols_crop - N_cols_crop_top
                      + N_cols_crop_top + N_cols_crop_bot + 1] = im_array
            self.im_array = pad_array

            if FlagPlot:
                print '\npad_array shape = ', pad_array.shape
                print 'N_rows_crop = ', N_rows_crop
                print 'N_cols_crop = ', N_cols_crop
                print 'N_rows_crop_sx = ', N_rows_crop_sx
                print 'N_rows_crop_dx = ', N_rows_crop_dx
                print 'N_cols_crop_top = ', N_cols_crop_top
                print 'N_cols_crop_bot = ', N_cols_crop_bot
                print 'im_array shape = ', im_array.shape
        else:

        # ########### 2) CROP the image ###########
            # Crop the image area over which the gradient must be computed (first make sure that the cropping mask is within the image)
            if Frame_cntr[1] - N_rows_crop < 0:
                N_rows_crop = Frame_cntr[1]
            if Frame_cntr[1] + N_rows_crop + 1 > self.im_array_whole.shape[0]:
                N_rows_crop = self.im_array_whole.shape[0] - Frame_cntr[1] - 1
            if Frame_cntr[0] - N_cols_crop < 0:
                N_cols_crop = Frame_cntr[0]
            if Frame_cntr[0] + N_cols_crop + 1 > self.im_array_whole.shape[1]:
                N_cols_crop = self.im_array_whole.shape[1] - Frame_cntr[0] - 1
            self.im_array = self.im_array_whole[Frame_cntr[1] - N_rows_crop:
                    Frame_cntr[1] + N_rows_crop + 1, Frame_cntr[0]
                    - N_cols_crop:Frame_cntr[0] + N_cols_crop + 1]

        if FlagPlot:
            print 'Gradient patch: N_rows_crop =', N_rows_crop, \
                '; N_cols_crop =', N_cols_crop
            print 'Initial guess =', Frame_cntr
            print 'Cropped rows =', Frame_cntr[1] - N_rows_crop, ',', \
                Frame_cntr[1] + N_rows_crop + 1
            print 'Cropped cols =', Frame_cntr[0] - N_cols_crop, ',', \
                Frame_cntr[0] + N_cols_crop + 1

        # Compute x,y components of the image gradient
        EdgeDetectAlg = 'sobel3x3separable'
        if EdgeDetectAlg == 'sobel3x3separable':
            use_sse3 = 0
            (self.im_grad_mag, self.im_grad_x, self.im_grad_y) = \
                sobel3x3_separable(self.im_array, use_sse3)
        elif EdgeDetectAlg == 'sobel3x3':
                                          # unfortunately is too slow (takes 2 times more than regular gradient)
            sobel_y = array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
            sobel_x = array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
            self.im_grad_y = signal.correlate2d(self.im_array, sobel_y,
                    mode='same', boundary='symm')
            self.im_grad_x = signal.correlate2d(self.im_array, sobel_x,
                    mode='same', boundary='symm')
        elif EdgeDetectAlg == 'gradient':
            (self.im_grad_y, self.im_grad_x) = gradient(self.im_array)

#         print 'max in x grad=', self.im_grad_x.max()
#         print 'min in x grad=', self.im_grad_x.min()

        # Compute gradient magnitude
        if EdgeDetectAlg != 'sobel3x3separable':
            FlagApprGradMag = True
            if FlagApprGradMag:
                self.im_grad_mag = abs(self.im_grad_y) + abs(self.im_grad_x)
            else:
                self.im_grad_mag = sqrt(pow(self.im_grad_y, 2)
                                        + pow(self.im_grad_x, 2))

        # Return the values of N_rows_crop and N_cols_crop that were actually used (they may differ from those originally passed as arguments to this method)
        return (N_rows_crop, N_cols_crop)

    # ==================================== function: _findPupil ========================================
    def _find_pupil(self, Nrays_quad=2, StartPupiCoord=[],
                    StartPupiRadius=None, FlagForceGuessPupCntr=False,
                    FlagPlot=False, FlagPrint=False):
        """ Extract corneal reflection (CR) and pupil center from an eye image.

        ARGUMENTS:
        - FileName = name of the file containing the eye image
        - ThCR = threshold on pixel itensity to detect the CR (allowed range = 0-1)
        - ThPup = threshold on pupil intensity to detect the pupil (allowed range = 0-1)
        """

        # Load image into numpy array
        # if self.nrow == 0:
        #    self.LoadImage(FileName, FlagSmooth)

        # Compute the CR center
        if self.CR_cntr.shape[0] == 0:
            self._find_CR(0.97, [])

        # Define the length of the rays to be shot and the image area over which the gradient will be computed (according to the previous pupil radius)
        if StartPupiRadius is not None:
            RayLeng = int(self.mFact_PupRadius2RayLeng * StartPupiRadius)
            N_rows_crop = N_cols_crop = int(self.mFact_PupRadius2GradImgPatch
                    * StartPupiRadius)
        else:
            RayLeng = self.RayLenght_default_Pup
            N_rows_crop = N_cols_crop = int(2.3 * RayLeng)

        # Check if an intial guess of the pupil center is passed by the user or it may be estimated doing a threshold on pix values
        if size(StartPupiCoord) == 0:
            # Guess Pup center looking over the whole image
            (Pup_cntr, iPup, jPup) = self._first_guess_pupil_center(FlagPlot)
        else:
            # Just use the Pupil coordinated passed as arguments
            if FlagForceGuessPupCntr == False:
                Pup_cntr = StartPupiCoord
            else:
            # Search for a better guess in a patch of image centered on the Pupil coordinated passed as arguments
                (Pup_cntr, iPup, jPup) = \
                    self._first_guess_pupil_center(FlagPlot, StartPupiCoord,
                        int(self.mFatc_PupGradImgPatch2ThImgPatch
                        * N_rows_crop),
                        int(self.mFatc_PupGradImgPatch2ThImgPatch
                        * N_cols_crop))

        # Make double sure that the intial guess is an array of integers
        Pup_cntr = array(Pup_cntr).astype(int)

        # Compute x,y components and absolute magnitude of the image gradient over an image area centered on the guessed pupil position
        # NOTE: the N_rows_crop and N_cols_crop values actually used to crop the image patch may differ from those originally passed to _computeImageGradient (this is why they are returned)
        (N_rows_crop, N_cols_crop) = self._compute_image_gradient(Pup_cntr,
                N_rows_crop, N_cols_crop, FlagPlot)
        # Set the guessed Pupil position (will be the center of the shooting rays) to the center of the croped image patch (it must be like this by contruction),
        # but save first the coordinates of the guessed CR in the reference system of the whole image
        Pup_cntr_whole_img = Pup_cntr
        Pup_cntr = array([N_cols_crop, N_rows_crop])

        # Change the CR coordinates from the reference system of the whole image to the reference system of the croped image patch
        # The coordinate changes is given by this expression: CRcntr_patchImg = guessPupilCntr_patchImg + CRcntr_wholeImg - guessPupilCntr_wholeImg
        self.CR_cntr = Pup_cntr + self.CR_cntr - Pup_cntr_whole_img

        if FlagPlot:
            # Plot image
            fig = figure()
            subplot(2, 2, 1)
            imshow(self.im_array)
            # Plot gradient components and magnitude
            subplot(2, 2, 3)
            imshow(self.im_grad_x)
            title('Gradient: x component')
            subplot(2, 2, 4)
            imshow(self.im_grad_y)
            title('Gradient: y component')
            subplot(2, 2, 2)
            imshow(self.im_grad_mag)
            hold(1)
            FlagPlotVectField = False
            if FlagPlotVectField:
                # Plot gradient as a vector field
                x = arange(1, self.ncol + 1)
                y = arange(1, self.nrow + 1)
                (X, Y) = meshgrid(x, y)
                hq = quiver(X, Y, self.im_grad_x, self.im_grad_y)
                setp(hq, 'Color', 'r')
                title('Gradient')

        # =========== STARBURST algorithm to find pupil boundary ==========
        # tic = time.time()
        # Build a matrix with a "star" of shooting rays starting from the pupil's current position
        if FlagPrint:
            print 'RayLeng used for pupil = ', RayLeng

        # Rays from -pi/4 to pi/4
        shoot_angle = arange(-pi / 4, +pi / 4, pi / (2 * Nrays_quad))
        shoot_slope = tan(shoot_angle)
        Dx = arange(-RayLeng, RayLeng + 1, 1)
        shoot_slope.shape = (size(shoot_slope), 1)
        x = Pup_cntr[0] + ones((size(shoot_slope), 1)) * Dx
        y = Pup_cntr[1] + shoot_slope * Dx
        # Rays from pi/4 to 3/4 pi
        shoot_angle = arange(pi / 4, -pi / 4, -pi / (2 * Nrays_quad))
        shoot_slope = tan(shoot_angle)
        shoot_slope.shape = (size(shoot_slope), 1)
        y2 = Pup_cntr[1] + ones((size(shoot_slope), 1)) * Dx
        x2 = Pup_cntr[0] + shoot_slope * Dx
        # Add the vertical shooting ray (obviously x is constant)
        x = vstack((x2, x))
        y = vstack((y2, y))
        Nrays = x.shape[0]

        # Save rays start and end coordinates
        rays_start = hstack((x[:, 0].reshape(-1, 1), y[:, 0].reshape(-1, 1)))
        rays_end = hstack((x[:, x.shape[1] - 1].reshape(-1, 1), y[:, y.shape[1]
                          - 1].reshape(-1, 1)))

        if FlagPlot:
            # Plot the star
            for i in xrange(1, 5):
                subplot(2, 2, i)
                plot(x.transpose(), y.transpose())
                setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])

        # Find intersections with the pupil boundary
        CurrTh = 1000
        (i_peak_right, i_peak_left, CurrTh) = \
            self.SB.find_edge_along_rays_from_center(
            self.im_grad_mag,
            x,
            y,
            CurrTh,
            FlagPlot,
            FlagPrint,
            )
        if FlagPrint:
            print '''i peak finali:
left =
''', i_peak_left, '''
right =
''', \
                i_peak_right

        if FlagPlot:
            # Plot pupil's edge points along the rays
            figure()
            imshow(self.im_array)
            hold(1)
            plot(x.transpose(), y.transpose())
            for i in xrange(x.shape[0]):
                if ~isnan(i_peak_right[i]):
                    plot([x[i, i_peak_right[i]]], [y[i, i_peak_right[i]]], 'or')
                if ~isnan(i_peak_left[i]):
                    plot([x[i, i_peak_left[i]]], [y[i, i_peak_left[i]]], 'og')
            setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])

        # Remove NaNs from final vectors with intersection (edge) indexes (NaNs correspond to cases in which no edge was found)
        Iok_right = where(~isnan(i_peak_right))
        Iok_left = where(~isnan(i_peak_left))
        i_peak_right = i_peak_right.astype(int)
        i_peak_left = i_peak_left.astype(int)
        if FlagPrint:
            print '''i peak finali (after removal of NaNs):
left =
''', \
                i_peak_left, '''
right =
''', i_peak_right
        if not Iok_right and not Iok_left:
            raise Exception, \
                'No ray was found that intersected the pupil boundary in 2 points!'

        # Final vectors with coordinates of boundary points
        x_bound = concatenate((x[arange(x.shape[0])[Iok_right],
                              i_peak_right[Iok_right]],
                              x[arange(x.shape[0])[Iok_left],
                              i_peak_left[Iok_left]]), axis=0).astype(float)
        y_bound = concatenate((y[arange(x.shape[0])[Iok_right],
                              i_peak_right[Iok_right]],
                              y[arange(x.shape[0])[Iok_left],
                              i_peak_left[Iok_left]]), axis=0).astype(float)
    #     print 'run time first starburst =', runtime_starburst1
        if FlagPrint:
            print 'x on boundary = \n', x_bound, '''
y on boundary =
''', \
                y_bound

        # Eliminate intersections that are too close to the CR (because the CR may overlap with the pupil)
        d2CR = sqrt((x_bound - self.CR_cntr[0]) ** 2 + (y_bound
                    - self.CR_cntr[1]) ** 2)
        Ibad = where(d2CR < self.mfact_CR_radius * self.CR_radius)[0]
        if FlagPrint:
            print 'distance from CR =', d2CR
            print 'Intersections removed because too close to the CR:  x =', \
                x_bound[Ibad], '\ty =', y_bound[Ibad]
        if FlagPlot:
            # Show the intersection points that were removed because too close to the CR
            if Ibad.shape[0] > 0:
                ho = plot([x_bound[Ibad]], [y_bound[Ibad]], 'xy')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])
        x_bound = delete(x_bound, Ibad)
        y_bound = delete(y_bound, Ibad)
        if FlagPrint:
            print 'After removal of CR boundaries: x on boundary = \n', \
                x_bound, '''
y on boundary =
''', y_bound
        if x_bound.shape[0] == 0:
            raise Exception, \
                'No ray was found whose intersections with the pupil were NOT too close to the CR!'

        # Save final boundary points
        boundPoints = hstack((x_bound.reshape(-1, 1), y_bound.reshape(-1, 1)))

        # ========= Least square minimization to fit either a CIRCLE or an ELLIPSE trough the interseciton of the rays with the pupil edges =========
        if self.FittingMethod == 0:
            # Initial guess of circle parameters
            a0 = -2 * Pup_cntr[0]
            b0 = -2 * Pup_cntr[1]
            c0 = Pup_cntr[0] ** 2 + Pup_cntr[1] ** 2 - (x_bound
                    - Pup_cntr[0]).mean() ** 2
            p0 = [a0, b0, c0]
            if FlagPrint:
                print 'p0 = ', p0
            # Fit circle to the data points
            p = optimize.leastsq(self._residuals_circle, p0, args=(y_bound,
                                 x_bound))
            if FlagPrint:
                print 'circle fit parameters = ', p
            (a, b, c) = p[0]
            # Calculate the location of center and radius
            Pup_cntr_fit = [-a / 2, -b / 2]
            Pup_radius_fit = sqrt(Pup_cntr_fit[0] ** 2 + Pup_cntr_fit[1] ** 2
                                  - c)
            if FlagPrint:
                print 'Estimated Circle center = ', Pup_cntr_fit
                print 'Estimated Circle radius = ', Pup_radius_fit

            if FlagPlot:
                # Plot the boundary points and the results of the fit
                figure()
                plot(x_bound, y_bound, 'o')
                ho = plot(array([Pup_cntr_fit[0]]), array([Pup_cntr_fit[1]]),
                          '+r')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                plot(array([Pup_cntr_fit[0] - Pup_radius_fit, Pup_cntr_fit[0]
                     + Pup_radius_fit]), array([Pup_cntr_fit[1],
                     Pup_cntr_fit[1]]), '-')
                title('Pupil center = ' + str(Pup_cntr_fit))
        elif self.FittingMethod == 1:

        # Least Squares non-linear fit of an ELLIPSE

            # Initial guess of ellipse parameters
            a0 = b0 = c0 = d0 = f0 = g0 = 1
            p0 = [
                a0,
                b0,
                c0,
                d0,
                f0,
                g0,
                ]
            if FlagPrint:
                print 'p0 = ', p0

            # Test call fitting function
            err = self._residuals_ellipse(p0, y_bound, x_bound)
            print 'test call fitting function = ', err

            print 'x_bound=', x_bound

            p = optimize.leastsq(self._residuals_ellipse, p0, args=(y_bound,
                                 x_bound))
            if FlagPrint:
                pass
            print 'ellipse fit parameters = ', p
            (
                a,
                b,
                c,
                d,
                f,
                g,
                ) = p[0]
            # Calculate the location of center
            x_cntr_ellps = (c * d - b * f) / (b ** 2 - a * c)
            y_cntr_ellps = (a * f - b * d) / (b ** 2 - a * c)
            Pup_cntr_fit = [x_cntr_ellps, y_cntr_ellps]
            if FlagPrint:
                pass
            print 'Estimated Ellipse center = ', Pup_cntr_fit

            if FlagPlot:
                # Plot the boundary points and the results of the fit
                figure()
                plot(x_bound, y_bound, 'o')
                ho = plot(array([Pup_cntr_fit[0]]), array([Pup_cntr_fit[1]]),
                          '+r')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                title('Pupil center = ' + str(Pup_cntr_fit))
        elif self.FittingMethod == 2:

        # Least Squares fit of an ELLIPSE
            Pup_cntr_fit = self._fit_ellipse_to_circle(y_bound, x_bound)

            if FlagPlot:
                # Plot the boundary points and the results of the fit
                figure()
                plot(x_bound, y_bound, 'o')
                ho = plot(array([Pup_cntr_fit[0]]), array([Pup_cntr_fit[1]]),
                          '+r')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                title('Pupil center = ' + str(Pup_cntr_fit))

        # ========= Remove outlayers in the intersection boundary points and re-fit a circle to the remaining points
        # NOTE: this is done only when we fit the circle. We may consider doing it also for the ellipse
        if self.FittingMethod == 0:

            # Compute distance of boundary/intersection points to the pupil center (radiuses) and their statistics
            radiuses = sqrt((x_bound - Pup_cntr_fit[0]) ** 2 + (y_bound
                            - Pup_cntr_fit[1]) ** 2)
            Pup_radius_mean = radiuses.mean()
            Pup_radius_std = radiuses.std()

            # Find outaliers
            Ioutlay = where((radiuses > Pup_radius_mean + 1.0 * Pup_radius_std)
                            | (radiuses < Pup_radius_mean - 1.0
                            * Pup_radius_std))[0]
            if FlagPrint:
                print 'shape radiuses = ', radiuses.shape
                print 'Indexes of outlayers intersections = ', Ioutlay
                print 'Shape outlayer intersections = ', Ioutlay.shape
                print 'Intersections removed because they are outlayers:  x =', \
                    x_bound[Ioutlay], '\ty =', y_bound[Ioutlay]
            if FlagPlot:
                # Show the intersection points that were removed because too close to the CR
                if Ioutlay.shape[0] > 0:
                    ho = plot([x_bound[Ioutlay]], [y_bound[Ioutlay]], 'xc')
                    setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                    # setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])

            # Remove outliers and make a new fit
            if Ioutlay.shape[0] > 0:
                if FlagPrint:
                    print '\nSome OUTLIERS in the pupil boundary points were found: REMOVE them and make a new fit'
                x_bound = delete(x_bound, Ioutlay)
                y_bound = delete(y_bound, Ioutlay)
                # Save final boundary points
                boundPoints = hstack((x_bound.reshape(-1, 1),
                                     y_bound.reshape(-1, 1)))
                if FlagPrint:
                    print 'After removal of outlayers intersection points: x on boundary = \n', \
                        x_bound, '''
y on boundary =
''', y_bound
                if x_bound.shape[0] == 0:
                    raise Exception, \
                        'No ray was found whose intersections were NOT OUTLIERS!'
                # Fit a circle to the remaining intersection points
                p = optimize.leastsq(self._residuals_circle, p0, args=(y_bound,
                                     x_bound))
                if FlagPrint:
                    print 'circle fit parameters = ', p
                (a, b, c) = p[0]
                # Calculate the location of center and radius
                Pup_cntr_fit = [-a / 2, -b / 2]
                Pup_radius_fit = sqrt(Pup_cntr_fit[0] ** 2 + Pup_cntr_fit[1]
                                      ** 2 - c)
                if FlagPrint:
                    print 'Estimated Circle centr = ', Pup_cntr_fit
                    print 'Estimated Circle radius = ', Pup_radius_fit
                # Recompute distance of boundary/intersection points to the pupil center (radiuses) and their statistics
                radiuses = sqrt((x_bound - Pup_cntr_fit[0]) ** 2 + (y_bound
                                - Pup_cntr_fit[1]) ** 2)
                Pup_radius_mean = radiuses.mean()
                Pup_radius_std = radiuses.std()

                if FlagPlot:
                    # Plot the boundary points and the results of the fit
                    figure()
                    plot(x_bound, y_bound, 'o')
                    ho = plot(array([Pup_cntr_fit[0]]),
                              array([Pup_cntr_fit[1]]), '+r')
                    setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                    plot(array([Pup_cntr_fit[0] - Pup_radius_fit,
                         Pup_cntr_fit[0] + Pup_radius_fit]),
                         array([Pup_cntr_fit[1], Pup_cntr_fit[1]]), '-')
                    title('Pupil center = ' + str(Pup_cntr_fit))

        # ========= Obtain final pupil center and radius and test whether the pupil is round enough
        # Compute distance of boundary/intersection points to the pupil center (radiuses)
        radiuses = sqrt((x_bound - Pup_cntr_fit[0]) ** 2 + (y_bound
                        - Pup_cntr_fit[1]) ** 2)
        # self.Pup_radius = Pup_radius_fit
        # Test that the pupil is round enough (based on std of radieses)
        self.Pup_radius = Pup_radius_mean = radiuses.mean()
        Pup_radius_std = radiuses.std()
        Pup_radius_CV = Pup_radius_std / Pup_radius_mean
        if FlagPrint:
            print 'Average Pupil radius = ', self.Pup_radius
            print 'CV Pupil radius = ', Pup_radius_CV
        # Force a large CV in order to not accept the pupil center in case of too few pupil boundary points
        if len(radiuses) <= 4:
            Pup_radius_CV = 100000
        if Pup_radius_CV > self.Th_Pup_radius_CV:
            raise Exception, 'NO reliably circular Pupil detected!'

        # Plots pupil boundary points, new center and old center
        if FlagPlot:
            self.FlagPlotFinal = True
        if self.FlagPlotFinal:
            figure()
            imshow(self.im_array)
            hold(1)
            plot(x_bound.transpose(), y_bound.transpose(), 'og')
            ho = plot(array([Pup_cntr[0]]), array([Pup_cntr[1]]), '+b')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            ho = plot(array([Pup_cntr_fit[0]]), array([Pup_cntr_fit[1]]), '+g')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            title('Pupil center = ' + str(floor(Pup_cntr_fit)))
            setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])

        # Change back the coordinates of the pupil center into the reference system of the whole image (NOTE: Pup_cntr was the intial guess of the pupil postion = center of the croped image patch)
        # The coordinate changes is given by this expression: newPupcntr_wholeImg = guessPupcntr_wholeImg + newPupcntr_patchImg - guessPupcntr_patchImg
        # Do the same for the CR center
        self.Pup_cntr = Pup_cntr_whole_img + Pup_cntr_fit - Pup_cntr
        self.CR_cntr = Pup_cntr_whole_img + self.CR_cntr - Pup_cntr
        # Do the same for the rays and boundary points coordinates
        rays_start = ones((rays_start.shape[0], 1)) * Pup_cntr_whole_img \
            + rays_start - ones((rays_start.shape[0], 1)) * Pup_cntr
        rays_end = ones((rays_end.shape[0], 1)) * Pup_cntr_whole_img + rays_end \
            - ones((rays_end.shape[0], 1)) * Pup_cntr
        boundPoints = ones((boundPoints.shape[0], 1)) * Pup_cntr_whole_img \
            + boundPoints - ones((boundPoints.shape[0], 1)) * Pup_cntr

        # Plots new center and old center (initial guess) in the ORIGINAL IMAGE
        if FlagPlot:
            self.FlagPlotFinal = True
        if self.FlagPlotFinal:
            figure()
            imshow(self.im_array_whole)
            hold(1)
            ho = plot(array([Pup_cntr_whole_img[0]]),
                      array([Pup_cntr_whole_img[1]]), '+b')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            ho = plot(array([self.Pup_cntr[0]]), array([self.Pup_cntr[1]]), '+g'
                      )
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            ho = plot(array([self.CR_cntr[0]]), array([self.CR_cntr[1]]), '+r')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            title('Pupil center = ' + str(floor(self.Pup_cntr)))
            # plot( rays_start[:,0], rays_start[:,1], 'oy' )
            # plot( rays_end[:,0], rays_end[:,1], 'or' )
            # plot( boundPoints[:,0], boundPoints[:,1], 'og' )
            setp(gca(), 'xlim', [1, self.im_array_whole.shape[1]], 'ylim',
                 [self.im_array_whole.shape[0], 1])

        # Reset to empty all image information
        self._clear()

        return (
            self.Pup_cntr,
            self.Pup_radius,
            Pup_radius_CV,
            rays_start,
            rays_end,
            boundPoints,
            )

#             return Pup_cntr_new, Pup_cntr_new2, Pup_cntr_new3, runtime_starburst1, runtime_starburst2, x_min_lstsq1, runtime_lstsq1, x_min_lstsq2, runtime_lstsq2, Nrays

    # ==================================== function: _findCR ========================================
    def _find_CR(self, Nrays_quad=2, StartCRCoord=[], StartCRRadius=None,
                 FlagForceGuessCRCntr=False, FlagPlot=False, FlagPrint=False):
        """ Extract corneal reflection (CR) and pupil center from an eye image.

        ARGUMENTS:
        - FileName = name of the file containing the eye image
        - ThCR = threshold on pixel itensity to detect the CR (allowed range = 0-1)
        - ThPup = threshold on pupil intensity to detect the pupil (allowed range = 0-1)
        """

        # Load image into numpy array
        # if self.nrow == 0:
        #    self.LoadImage(FileName, FlagSmooth)

        # Define the length of the rays to be shot and the image area over which the gradient will be computed (according to the previous CR radius)
        if StartCRRadius is not None:
            RayLeng = int(self.mFact_CRRadius2RayLeng * StartCRRadius)
            N_rows_crop = N_cols_crop = int(self.mFact_CRRadius2GradImgPatch
                    * StartCRRadius)
        else:
            RayLeng = self.RayLenght_default_CR  # 15
            N_rows_crop = N_cols_crop = int(2 * RayLeng)  # 40

        # Check if an intial guess of the CR center is passed by the user or it may be estimated doign a threshold on pix values
        if size(StartCRCoord) == 0:
             # Guess CR center looking over the whole image
            (CR_cntr, iCR, jCR) = self._first_guess_CR_center(FlagPlot)
        else:
            # Just use the CR coordinated passed as arguments
            if FlagForceGuessCRCntr == False:
                CR_cntr = StartCRCoord
            else:
            # Search for a better guess in a patch of image centered on the CR coordinated passed as arguments
                (CR_cntr, iCR, jCR) = self._first_guess_CR_center(FlagPlot,
                        StartCRCoord, int(self.mFatc_CRGradImgPatch2ThImgPatch
                        * N_rows_crop),
                        int(self.mFatc_CRGradImgPatch2ThImgPatch * N_cols_crop))

        # Make double sure that the intial guess is an array of integers
        CR_cntr = array(CR_cntr).astype(int)

        # Compute x,y components and absolute magnitude of the image gradient over an image area centered on the guessed CR position
        if self.im_grad_x.shape[0] == 0:
            # NOTE: the N_rows_crop and N_cols_crop values actually used to crop the image patch may differ from those originally passed to _computeImageGradient (this is why theyr are returned)
            (N_rows_crop, N_cols_crop) = self._compute_image_gradient(CR_cntr,
                    N_rows_crop, N_cols_crop, FlagPlot)
            # Set the guessed CR position (will be the center of the shooting rays) to the center of the croped image patch (it must be like this by contruction),
            # but save first the coordinates of the guessed CR in the reference system of the whole image
            CR_cntr_whole_img = CR_cntr
            CR_cntr = array([N_cols_crop, N_rows_crop])

        if FlagPlot:
            # Plot image
            fig = figure()
            subplot(2, 2, 1)
            imshow(self.im_array)
            # Plot gradient components and magnitude
            subplot(2, 2, 3)
            imshow(self.im_grad_x)
            title('Gradient: x component')
            subplot(2, 2, 4)
            imshow(self.im_grad_y)
            title('Gradient: y component')
            subplot(2, 2, 2)
            imshow(self.im_grad_mag)
            hold(1)
            FlagPlotVectField = False
            if FlagPlotVectField:
                # Plot gradient as a vector field
                x = arange(1, self.ncol + 1)
                y = arange(1, self.nrow + 1)
                (X, Y) = meshgrid(x, y)
                hq = quiver(X, Y, self.im_grad_x, self.im_grad_y)
                setp(hq, 'Color', 'r')
                title('Gradient')

        # =========== STARBURST algorithm to find CR boundary ==========
        # tic = time.time()
        # Build a matrix with a "star" of shooting rays starting from the pupil's current position
        # Rays from -pi/4 to pi/4
        use_davides_rays = False
        shoot_angle = arange(-pi / 4, +pi / 4, pi / (2 * Nrays_quad))
        shoot_slope = tan(shoot_angle)
        Dx = arange(-RayLeng, RayLeng + 1, 1)
        shoot_slope.shape = (size(shoot_slope), 1)
        x = CR_cntr[0] + ones((size(shoot_slope), 1)) * Dx
        y = CR_cntr[1] + shoot_slope * Dx
        # Rays from pi/4 to 3/4 pi
        shoot_angle = arange(pi / 4, -pi / 4, -pi / (2 * Nrays_quad))
        shoot_slope = tan(shoot_angle)
        shoot_slope.shape = (size(shoot_slope), 1)
        y2 = CR_cntr[1] + ones((size(shoot_slope), 1)) * Dx
        x2 = CR_cntr[0] + shoot_slope * Dx
        # Add the vertical shooting ray (obviously x is constant)
        x = vstack((x2, x))
        y = vstack((y2, y))

        Nrays = x.shape[0]

        # Save rays start and end coordinates
        rays_start = hstack((x[:, 0].reshape(-1, 1), y[:, 0].reshape(-1, 1)))
        rays_end = hstack((x[:, x.shape[1] - 1].reshape(-1, 1), y[:, y.shape[1]
                          - 1].reshape(-1, 1)))

        if FlagPlot:
            # Plot the star
            for i in xrange(1, 5):
                subplot(2, 2, i)
                plot(x.transpose(), y.transpose())
                setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])

        # Find intersections with the CR boundary
        CurrTh = 1000
        (i_peak_right, i_peak_left, CurrTh) = \
            self.SB.find_edge_along_rays_from_center(
            self.im_grad_mag,
            x,
            y,
            CurrTh,
            FlagPlot,
            FlagPrint,
            )
        if FlagPrint:
            print '''i peak finali:
left =
''', i_peak_left, '''
right =
''', \
                i_peak_right

        if FlagPlot:
            # Plot CR's edge points along the rays
            figure()
            imshow(self.im_array)
            hold(1)
            plot(x.transpose(), y.transpose())
            for i in xrange(x.shape[0]):
                if not isnan(i_peak_right[i]):
                    plot([x[i, i_peak_right[i]]], [y[i, i_peak_right[i]]], 'or')
                if not isnan(i_peak_left[i]):
                    plot([x[i, i_peak_left[i]]], [y[i, i_peak_left[i]]], 'og')
            setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])

        # Remove NaNs from final vectors with intersection (edge) indexes (NaNs correspond to cases in which no edge was found)
        Iok_right = where(~isnan(i_peak_right))
        Iok_left = where(~isnan(i_peak_left))
        i_peak_right = i_peak_right.astype(int)
        i_peak_left = i_peak_left.astype(int)
        if FlagPrint:
            print '''i peak finali (after removal of NaNs):
left =
''', \
                i_peak_left, '''
right =
''', i_peak_right
        if not Iok_right and not Iok_left:
            raise Exception, \
                'No ray was found that intersected the CR boundary in 2 points!'

        # Final vectors with coordinates of boundary points
        x_bound = concatenate((x[arange(x.shape[0])[Iok_right],
                              i_peak_right[Iok_right]],
                              x[arange(x.shape[0])[Iok_left],
                              i_peak_left[Iok_left]]), axis=0).astype(float)
        y_bound = concatenate((y[arange(x.shape[0])[Iok_right],
                              i_peak_right[Iok_right]],
                              y[arange(x.shape[0])[Iok_left],
                              i_peak_left[Iok_left]]), axis=0).astype(float)
        # runtime_starburst1 = time.time() - tic
        # if FlagPrint: print 'run time first starburst =', runtime_starburst1
        if FlagPrint:
            print 'x on boundary = \n', x_bound, '''
y on boundary =
''', \
                y_bound

        # Save final boundary points
        boundPoints = hstack((x_bound.reshape(-1, 1), y_bound.reshape(-1, 1)))
        if FlagPrint:
            print 'boundPoints: ', boundPoints

        # ========= Least square minimization to fit a circle trough the interseciton of the rays with the CR edges =========
        if self.FittingMethod == 0:
            # Initial guess of circle parameters
            a0 = -2 * CR_cntr[0]
            b0 = -2 * CR_cntr[1]
            c0 = CR_cntr[0] ** 2 + CR_cntr[1] ** 2 - (x_bound
                    - CR_cntr[0]).mean() ** 2
            p0 = [a0, b0, c0]
            if FlagPrint:
                print 'p0 = ', p0
            # Fit circle to the data points
            p = optimize.leastsq(self._residuals_circle, p0, args=(y_bound,
                                 x_bound))
            if FlagPrint:
                print 'circle fit parameters = ', p
            (a, b, c) = p[0]
            # Calculate the location of center and radius
            CR_cntr_fit = [-a / 2, -b / 2]
            CR_radius_fit = sqrt(CR_cntr_fit[0] ** 2 + CR_cntr_fit[1] ** 2 - c)
            if FlagPrint:
                print 'Estimated Circle centr = ', CR_cntr_fit
                print 'Estimated Circle radius = ', CR_radius_fit

            if FlagPlot:
                # Plot the boundary points and the results of the fit
                figure()
                plot(x_bound, y_bound, 'o')
                ho = plot(array([CR_cntr_fit[0]]), array([CR_cntr_fit[1]]), '+r'
                          )
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                plot(array([CR_cntr_fit[0] - CR_radius_fit, CR_cntr_fit[0]
                     + CR_radius_fit]), array([CR_cntr_fit[1],
                     CR_cntr_fit[1]]), '-')
        elif self.FittingMethod == 1 or self.FittingMethod == 2:

        # Least Squares fit of an ELLIPSE
            CR_cntr_fit = self._fit_ellipse_to_circle(y_bound, x_bound)

            if FlagPlot:
                # Plot the boundary points and the results of the fit
                figure()
                plot(x_bound, y_bound, 'o')
                ho = plot(array([CR_cntr_fit[0]]), array([CR_cntr_fit[1]]), '+r'
                          )
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)

        # Compute radius of the CR
        radiuses = sqrt((x_bound - CR_cntr_fit[0]) ** 2 + (y_bound
                        - CR_cntr_fit[1]) ** 2)
        self.CR_radius = CR_radius_mean = radiuses.mean()
        # self.CR_radius = CR_radius_fit
        # Test that the CR is round enough (based on std of radiuses)
        CR_radius_CV = radiuses.std() / CR_radius_mean
        if FlagPrint:
            print 'Average CR radius = ', self.CR_radius
            print 'CV CR radius = ', CR_radius_CV
        # Force a large CV in order to not accept the CR center in case of too few CR boundary points
        if len(radiuses) <= 4:
            CR_radius_CV = 100000
        if CR_radius_CV > self.Th_CR_radius_CV:
            raise Exception, 'NO reliably circular CR detected!'

        # Plots pupil boundary points, new center and old center
        if FlagPlot:
            self.FlagPlotFinal = True
        if self.FlagPlotFinal:
            figure()
            imshow(self.im_array)
            hold(1)
            plot(x_bound.transpose(), y_bound.transpose(), 'og')
            ho = plot(array([CR_cntr[0]]), array([CR_cntr[1]]), '+b')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            ho = plot(array([CR_cntr_fit[0]]), array([CR_cntr_fit[1]]), '+g')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            title('CR center = ' + str(floor(CR_cntr_fit)))
            setp(gca(), 'xlim', [1, self.ncol], 'ylim', [self.nrow, 1])

        # Change back the coordinates of the CR center into the reference system of the whole image (NOTE: CR_cntr was the intial guess of the CR postion = center of the croped image patch)
        # The coordinate changes is given by this expression: newCRcntr_wholeImg = guessCRcntr_wholeImg + newCRcntr_patchImg - guessCRcntr_patchImg
        self.CR_cntr = CR_cntr_whole_img + CR_cntr_fit - CR_cntr
        # Do the same for the rays and boundary points coordinates
        rays_start = ones((rays_start.shape[0], 1)) * CR_cntr_whole_img \
            + rays_start - ones((rays_start.shape[0], 1)) * CR_cntr
        rays_end = ones((rays_end.shape[0], 1)) * CR_cntr_whole_img + rays_end \
            - ones((rays_end.shape[0], 1)) * CR_cntr
        boundPoints = ones((boundPoints.shape[0], 1)) * CR_cntr_whole_img \
            + boundPoints - ones((boundPoints.shape[0], 1)) * CR_cntr

        # Plots new center and old center (initial guess) in the ORIGINAL IMAGE
        if FlagPlot:
            self.FlagPlotFinal = True
        if self.FlagPlotFinal:
            figure()
            imshow(self.im_array_whole)
            hold(1)
            ho = plot(array([CR_cntr_whole_img[0]]),
                      array([CR_cntr_whole_img[1]]), '+b')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            ho = plot(array([self.CR_cntr[0]]), array([self.CR_cntr[1]]), '+g')
            setp(ho, 'markersize', 10, 'markeredgewidth', 2)
            # plot( rays_start[:,0], rays_start[:,1], 'oy' )
            # plot( rays_end[:,0], rays_end[:,1], 'or' )
            # plot( boundPoints[:,0], boundPoints[:,1], 'og' )
            title('CR center = ' + str(floor(self.CR_cntr)))
            setp(gca(), 'xlim', [1, self.im_array_whole.shape[1]], 'ylim',
                 [self.im_array_whole.shape[0], 1])

        return (
            self.CR_cntr,
            self.CR_radius,
            CR_radius_CV,
            rays_start,
            rays_end,
            boundPoints,
            )

    # ======================== function: _residuals_circle ===============================
    def _residuals_circle(self, p, y, x):
        (a, b, c) = p
        err = x ** 2 + y ** 2 + a * x + b * y + c
        return err

    # ======================== function: _residuals_ellipse ===============================
    def _residuals_ellipse(self, p, y, x):
        (
            a,
            b,
            c,
            d,
            f,
            g,
            ) = p
        err = a * x ** 2 + 2 * b * x * y + c * y ** 2 + 2 * d * x + 2 * f * y \
            + g
        return err

    # ======================== function: _fit_ellipse_to_circle ===============================
    def _fit_ellipse_to_circle(self, y, x):

        # initialize
        orientation_tolerance = 1e-3

        # remove bias of the ellipse - to make matrix inversion more accurate. (will be added later on).
        mean_x = mean(x)
        mean_y = mean(y)
        x = x - mean_x
        y = y - mean_y

        # Make x and y colum vectors
        x.shape = (size(x), 1)
        y.shape = (size(y), 1)

        # print "x no bias =", x

        # the estimation for the conic equation of the ellipse
        X = hstack((x ** 2, x * y, y ** 2, x, y))
        # print "X = ", X
        A = dot(sum(X, axis=0), linalg.inv(dot(X.transpose(), X)))
        # print "A =", A

        # extract parameters from the conic equation
        (a, b, c, d, e) = A
        # print a,b,c,d,e

        # remove the orientation from the ellipse
        if min(abs(b / a), abs(b / c)) > orientation_tolerance:
            # print "remove orientation"
            orientation_rad = 1 / 2 * arctan(b / (c - a))
            cos_phi = cos(orientation_rad)
            sin_phi = sin(orientation_rad)
            (a, b, c, d, e) = (a * cos_phi ** 2 - b * cos_phi * sin_phi + c
                               * sin_phi ** 2, 0, a * sin_phi ** 2 + b
                               * cos_phi * sin_phi + c * cos_phi ** 2, d
                               * cos_phi - e * sin_phi, d * sin_phi + e
                               * cos_phi)
            (mean_x, mean_y) = (cos_phi * mean_x - sin_phi * mean_y, sin_phi
                                * mean_x + cos_phi * mean_y)
        else:
            orientation_rad = 0
            cos_phi = cos(orientation_rad)
            sin_phi = sin(orientation_rad)

        # print a,b,c,d,e

        # check if conic equation represents an ellipse
        test = a * c
        # if we found an ellipse return it's data
        if test > 0:

            # make sure coefficients are positive as required
            if a < 0:
                (a, c, d, e) = (-a, -c, -d, -e)

            # final ellipse parameters
            X0 = mean_x - d / 2 / a
            Y0 = mean_y - e / 2 / c
            F = 1 + d ** 2 / (4 * a) + e ** 2 / (4 * c)
            (a, b) = (sqrt(F / a), sqrt(F / c))
            long_axis = 2 * max(a, b)
            short_axis = 2 * min(a, b)

            # rotate the axes backwards to find the center point of the original TILTED ellipse
            R = array([[cos_phi, sin_phi], [-sin_phi, cos_phi]])
            P_in = dot(R, array([[X0], [Y0]]))
            X0_in = P_in[0]
            Y0_in = P_in[1]

            Pup_cntr_fit = [X0_in[0], Y0_in[0]]
            # print "Estimated Ellipse center =", X0_in, Y0_in
            return Pup_cntr_fit
        elif test == 0:

            raise Exception, 'Parabola found'
        elif test < 0:
            raise Exception, 'Hyperbola found'


# =========================================================================
# ....The Guts of Davide's Algorithm
# =========================================================================

class StarBurst:

    def __init__(self, mfact_grad_star_std, Dpix_ToHigh):
        self.Dpix_ToHigh = Dpix_ToHigh
        self.mfact_star_std = mfact_grad_star_std

    def find_edge_along_rays_from_center(self, im_grad_mag, x, y, CurrTh=1000,
            FlagPlot=False, FlagPrint=False):
        pass

    def find_edge_along_rays_to_right(self, im_grad_mag, x, y, i_shift,
                                      CurrTh=1000, FlagPlot=False,
                                      FlagPrint=False):
        pass

    def find_edge_along_rays_to_left(self, im_grad_mag, x, y, i_shift,
                                     CurrTh=1000, FlagPlot=False,
                                     FlagPrint=False):
        pass


class StarBurstLoop(StarBurst):

    # ======================== function: FindCircleEdgeAlongRays_fromcntr ===============================
    def find_edge_along_rays_from_center(self, im_grad_mag, x, y, CurrTh=1000,
            FlagPlot=False, FlagPrint=False):

        # Find gradient magnitude along the rays
        x = x.astype(int)
        y = y.astype(int)
        if FlagPrint:
            print 'x =\n', x
            print 'y =\n', y
            print 'shape gradient = ', im_grad_mag.shape
            print 'maximal difference between rays pixels and image boundary along the y axis = ', \
                (y - im_grad_mag.shape[0]).max()
            print 'maximal difference between rays pixels and image boundary along the x axis = ', \
                (x - im_grad_mag.shape[1]).max()
        if (y - im_grad_mag.shape[0]).max() > 0 or (x
                - im_grad_mag.shape[1]).max() > 0 or x.min() < 0 or y.min() < 0:
            raise Exception, 'Some rays shooted outside the image boundaries!'
        grad_mag_star = im_grad_mag[y, x]

        # Set threshold to find the pupil's edge (e.g., the peak of gradient magnitude) along the rays.
        # This is done individually for each ray, but then the mininal threshold is taken
        grad_star_mean = grad_mag_star.mean(1)
        grad_star_std = grad_mag_star.std(1)
        ThGrad = grad_star_mean + 1.5 * grad_star_std
        ThGrad = min(ThGrad.min(), CurrTh)
        (ir, ic) = where(grad_mag_star > ThGrad)

        # Loop along each ray to find the pupil edge onset
        i_peak_right = []
        i_peak_left = []
        for i in xrange(grad_mag_star.shape[0]):
            Iok = where(grad_mag_star[i, :] > ThGrad)
            Iok_ctr = Iok[0] - grad_mag_star.shape[1] / 2
            if FlagPrint:
                print 'Iok_ctr = ', Iok_ctr
            IIok_ctr_p = where(Iok_ctr > 0)  # points > Th to the right of pupil center
            IIok_ctr_m = where(Iok_ctr < 0)  # points > Th to the left of pupil center
            # Check if an edge was found (i.e., IIok_ctr_p and IIok_ctr_m are not empty)
            if IIok_ctr_p[0].shape[0] > 0:
                i_peak_right.append(Iok[0][IIok_ctr_p[0][0]])
            else:
                i_peak_right.append(nan)  # print '... intersection not found: set index to NaN'

            if IIok_ctr_m[0].shape[0] > 0:
                i_peak_left.append(Iok[0][IIok_ctr_m[0][size(IIok_ctr_m) - 1]])
            else:
                i_peak_left.append(nan)  # print '... intersection not found: set index to NaN'

        i_peak_right = array(i_peak_right)
        i_peak_left = array(i_peak_left)

        if FlagPlot:
            # Plot gradient magnitude along the rays
            figure()
            ray_ax = ones((grad_mag_star.shape[0], 1)) \
                * arange(grad_mag_star.shape[1])
            plot(ray_ax.transpose(), grad_mag_star.transpose())
            # Plot threshold and points above threshold
            plot([0, grad_mag_star.shape[1]], [ThGrad, ThGrad], 'k--')
            plot(ray_ax[ir, ic].transpose(), grad_mag_star[ir, ic].transpose(),
                 'o')
            # Plot pupil edges
            for i in xrange(grad_mag_star.shape[0]):
                ho = plot([ray_ax[i, i_peak_right[i]]], [grad_mag_star[i,
                          i_peak_right[i]]], '+r')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                ho = plot([ray_ax[i, i_peak_left[i]]], [grad_mag_star[i,
                          i_peak_left[i]]], '+g')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)

        return (i_peak_right, i_peak_left, ThGrad)

    # ======================== function: FindCircleEdgeAlongRays_todx ===============================
    def find_edge_along_rays_to_right(self, im_grad_mag, x, y, i_shift,
                                      CurrTh=1000, FlagPlot=False,
                                      FlagPrint=False):
        """ Find the intersections between the pupil boundary and a set of rays.
        It starts from a starting point on each ray and looks to the right of it.

        ARGUMENTS:
        - im_grad_mag = gradient magnitude of the eye image
        - x[m,n] = x coordinates (n points) of the set of m rays
        - y[m,n] = y coordinates (n points) of the set of m rays
        - i_shift = index on each ray from which the intersections will be looked for
        - CurrTh = last value of the threshold used to detect the pupil edges

        RETURN:
        - x_edge, y_edge = intersection points
        """

        # Find gradient magnitude along the rays
        x = x.astype(int)
        y = y.astype(int)
        if FlagPrint:
            print 'x =\n', x
            print 'y =\n', y
            print 'shape gradient = ', im_grad_mag.shape
            print 'maximal difference between rays pixels and image boundary along the y axis = ', \
                (y - im_grad_mag.shape[0]).max()
            print 'maximal difference between rays pixels and image boundary along the x axis = ', \
                (x - im_grad_mag.shape[1]).max()
        if (y - im_grad_mag.shape[0]).max() > 0 or (x
                - im_grad_mag.shape[1]).max() > 0 or x.min() < 0 or y.min() < 0:
            raise Exception, 'Some rays shooted otside the image boundaries!'
        grad_mag_star = im_grad_mag[y, x]
        ray_ax = ones((grad_mag_star.shape[0], 1)) \
            * arange(grad_mag_star.shape[1])
        if FlagPrint:
            print '\nIn FindPupEdgeAlongRays_dx: grad_mag_star.shape =', \
                grad_mag_star.shape

        # Set threshold to find the pupil's edge (e.g., the peak of gradient magnitude) along the rays.
        # This is done individually for each ray, but, if a threshold is too high, is replaced by rays median
        grad_star_mean = grad_mag_star.mean(1)
        grad_star_std = grad_mag_star.std(1)
        ThGrad = grad_star_mean + 1.5 * grad_star_std
        ThGrad = min(ThGrad.min(), CurrTh)

        # Loop along each ray to find the pupil edge onset
        i_peak_right = []
        Ith = []
        for i in xrange(grad_mag_star.shape[0]):
            Iok = where(grad_mag_star[i, :] > ThGrad)
            if FlagPrint:
                print 'iok =', Iok
            Ith.append(Iok[0])
            Iok_ctr = Iok[0] - i_shift
            IIok_ctr_p = where(Iok_ctr > 0)  # points > Th to the right of i_shift
            if FlagPrint:
                print 'II edges = ', IIok_ctr_p, 'truth value =', \
                    IIok_ctr_p[0].any()
            # Check if an edge was found (i.e., IIok_ctr_m is not empty)
            if IIok_ctr_p[0].shape[0]:
                i_peak_right.append(Iok[0][IIok_ctr_p[0][0]])
            else:
                i_peak_right.append(nan)  # print '... in FindPupEdgeAlongRays_dx: intersection not found: set index to NaN'

        # Set NaNs = 100000 in the vectors with intersection indexes (NaNs correspond to cases in which no edge was found)
        i_peak_right = array(i_peak_right)
        Inan_right = where(isnan(i_peak_right))
        i_peak_right[Inan_right] = 0
        i_peak_right = i_peak_right.astype(int)
        if FlagPrint:
            print 'Inan_right =', Inan_right
            print 'i peak finali (after removal of NaNs): right =', i_peak_right
        x_edge = x[arange(x.shape[0]), i_peak_right].astype(float)
        y_edge = y[arange(x.shape[0]), i_peak_right].astype(float)
        x_edge[Inan_right] = 100000
        y_edge[Inan_right] = 100000

        if FlagPlot:
            # Plot gradient along rays and intersection points
            figure()
            Iok_right = setdiff1d(arange(x.shape[0]), Inan_right[0])
            Col = [
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                ]
            plot(ray_ax.transpose(), grad_mag_star.transpose(), '.-')
            for i in arange(grad_mag_star.shape[0])[Iok_right]:
                plot([0, grad_mag_star.shape[1]], [ThGrad, ThGrad], '--'
                     + Col[i])
                plot(ray_ax[i, Ith[i]], grad_mag_star[i, Ith[i]], 'o' + Col[i])
                ho = plot([ray_ax[i, i_peak_right[i]]], [grad_mag_star[i,
                          i_peak_right[i]]], '+k')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)

        return (x_edge, y_edge, ThGrad)

    # ======================== function: FindCircleEdgeAlongRays_tosx ===============================
    def find_edge_along_rays_to_left(self, im_grad_mag, x, y, i_shift,
                                     CurrTh=1000, FlagPlot=False,
                                     FlagPrint=False):
        """ Find the intersections between the pupil boundary and a set of rays.
        It starts from a starting point on each ray and looks to the left of it.

        ARGUMENTS:
        - im_grad_mag = gradient magnitude of the eye image
        - x[m,n] = x coordinates (n points) of the set of m rays
        - y[m,n] = y coordinates (n points) of the set of m rays
        - i_shift = index on each ray from which the intersections will be looked for
        - CurrTh = last value of the threshold used to detect the pupil edges

        RETURN:
        - x_edge, y_edge = intersection points
        """

        # Find gradient magnitude along the rays
        x = x.astype(int)
        y = y.astype(int)
        if FlagPrint:
            print 'x =\n', x
            print 'y =\n', y
            print 'shape gradient = ', im_grad_mag.shape
            print 'maximal difference between rays pixels and image boundary along the y axis = ', \
                (y - im_grad_mag.shape[0]).max()
            print 'maximal difference between rays pixels and image boundary along the x axis = ', \
                (x - im_grad_mag.shape[1]).max()
        if (y - im_grad_mag.shape[0]).max() > 0 or (x
                - im_grad_mag.shape[1]).max() > 0 or x.min() < 0 or y.min() < 0:
            raise Exception, 'Some rays shooted otside the image boundaries!'
        grad_mag_star = im_grad_mag[y, x]
        ray_ax = ones((grad_mag_star.shape[0], 1)) \
            * arange(grad_mag_star.shape[1])
        if FlagPrint:
            print '\nIn FindPupEdgeAlongRays_sx: grad_mag_star.shape =', \
                grad_mag_star.shape

        # Set threshold to find the pupil's edge (e.g., the peak of gradient magnitude) along the rays
        grad_star_mean = grad_mag_star.mean(1)
        grad_star_std = grad_mag_star.std(1)
        ThGrad = grad_star_mean + 1.5 * grad_star_std
        ThGrad = min(ThGrad.min(), CurrTh)

        # Loop along each ray to find the pupil edge onset
        i_peak_left = []
        Ith = []
        for i in xrange(grad_mag_star.shape[0]):
            Iok = where(grad_mag_star[i, :] > ThGrad)
            if FlagPrint:
                print 'iok =', Iok
            Ith.append(Iok[0])
            Iok_ctr = Iok[0] - (grad_mag_star.shape[1] - i_shift)
            IIok_ctr_m = where(Iok_ctr < 0)  # points > Th to the left of (grad_mag_star.shape[1] - i_shift)
    #         N_IIok_ctr_m = size(IIok_ctr_m)
            if FlagPrint:
                print 'II edges = ', IIok_ctr_m, 'truth value =', \
                    IIok_ctr_m[0].any()
            # Check if an edge was found (i.e., IIok_ctr_m is not empty)
            if IIok_ctr_m[0].shape[0]:
                i_peak_left.append(Iok[0][IIok_ctr_m[0][size(IIok_ctr_m) - 1]])
            else:
                i_peak_left.append(NaN)  # print '... in FindPupEdgeAlongRays_sx: intersection not found: set index to NaN'

        # Set NaNs = 100000 in the vectors with intersection indexes (NaNs correspond to cases in which no edge was found)
        i_peak_left = array(i_peak_left)
        Inan_left = where(isnan(i_peak_left))
        i_peak_left[Inan_left] = 0
        i_peak_left = i_peak_left.astype(int)
        if FlagPrint:
            print 'Inan_left =', Inan_left
            print 'i peak finali: left =', i_peak_left
        x_edge = x[arange(x.shape[0]), i_peak_left].astype(float)
        y_edge = y[arange(x.shape[0]), i_peak_left].astype(float)
        x_edge[Inan_left] = 100000
        y_edge[Inan_left] = 100000

        if FlagPlot:
            # Plot gradient along rays and intersection points
            figure()
            Iok_left = setdiff1d(arange(x.shape[0]), Inan_left[0])
            Col = [
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                ]
            plot(ray_ax.transpose(), grad_mag_star.transpose(), '.-')
            for i in arange(grad_mag_star.shape[0])[Iok_left]:
                plot([0, grad_mag_star.shape[1]], [ThGrad, ThGrad], '--'
                     + Col[i])
                plot(ray_ax[i, Ith[i]], grad_mag_star[i, Ith[i]], 'o' + Col[i])
                ho = plot([ray_ax[i, i_peak_left[i]]], [grad_mag_star[i,
                          i_peak_left[i]]], '+k')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)

        return (x_edge, y_edge, ThGrad)


class StarBurstVectorized(StarBurst):

    def _get_image_values(self, im, x, y):
        return self._get_image_values_interp(im, x, y)

    def _get_image_values_floor(self, im, x, y):
        x = x.astype(int)
        y = y.astype(int)
        return im[y, x]

    def _get_image_values_nearest(self, im, x, y):
        x = x.round()
        y = y.round()
        return im[y.astype(int), x.astype(int)]

    def _get_image_values_interp(self, im, x, y):
        # print "x = ", x
        vals = zeros(x.shape)
        floor_x = floor(x).astype(int)
        floor_y = floor(y).astype(int)
        ceil_x = ceil(x).astype(int)
        ceil_y = ceil(y).astype(int)
        # print 'x= ', x
        # print 'floor_x = ', floor_x
        x_frac = 1 - (x - floor_x)
        y_frac = 1 - (y - floor_y)
        # print "x_frac: ", x_frac

        for i in range(0, x.shape[0]):
            for j in range(0, x.shape[1]):
                a = im[floor_x[i, j], floor_y[i, j]]
                b = im[ceil_x[i, j], floor_y[i, j]]
                c = im[floor_x[i, j], ceil_y[i, j]]
                d = im[ceil_x[i, j], ceil_y[i, j]]
                # print x_frac[i,j]
                # print a
                val = 0.25 * ((x_frac[i, j] + y_frac[i, j]) * a + (1
                              - x_frac[i, j] + y_frac[i, j]) * b + (x_frac[i,
                              j] + 1 - y_frac[i, j]) * c + (1 - x_frac[i, j]
                              + 1 - y_frac[i, j]) * d)
                # val = x_frac[i,j] * y_frac[i,j] * a + (1-x_frac[i,j]) * y_frac[i,j] * b + \
                #          x_frac[i,j] * (1 - y_frac[i,j]) * c + (1-x_frac[i,j])*(1-y_frac[i,j])*d
                # print val
                vals[i, j] = val
        return vals

    # ======================== function: FindCircleEdgeAlongRays_fromcntr ===============================
    def find_edge_along_rays_from_center(self, im_grad_mag, x, y, CurrTh=1000,
            FlagPlot=False, FlagPrint=False):

        # Find gradient magnitude along the rays
        # x = x.astype(int)
        # y = y.astype(int)
        FlagPrint = 0
        # if FlagPrint:
        #    print 'x =\n', x
        #    print 'y =\n', y
        #    print 'shape gradient = ', im_grad_mag.shape
        #    print 'maximal difference between rays pixels and image boundary along the y axis = ', (y-im_grad_mag.shape[0]).max()
        #    print 'maximal difference between rays pixels and image boundary along the x axis = ', (x-im_grad_mag.shape[1]).max()
        if (y - im_grad_mag.shape[0]).max() >= 0 or (x
                - im_grad_mag.shape[1]).max() >= 0 or x.min() < 0 or y.min() \
            < 0:
            raise Exception, 'Some rays shooted outside the image boundaries!'

        # grad_mag_star = im_grad_mag[y,x]
        grad_mag_star = self._get_image_values(im_grad_mag, x, y)

        # Set threshold to find the pupil's edge (e.g., the peak of gradient magnitude) along the rays.
        # This is done individually for each ray, but then the mininal threshold is taken
        grad_star_mean = grad_mag_star.mean(1)
        grad_star_std = grad_mag_star.std(1)
        ThGrad = grad_star_mean + self.mfact_star_std * grad_star_std
        ThGrad = min(ThGrad.min(), CurrTh)
        (ir, ic) = where(grad_mag_star > ThGrad)
        if ir.shape[0] == 0 or ic.shape[0] == 0:
            raise Exception, \
                'In shoot rays from center: No intersection with Pupil/CR boundary was found!'

        # Find intersections of rays wit the pupil boundary
        x_idx = arange(0, grad_mag_star.shape[1])
        ColIdxIn_grad_star = (ones((grad_mag_star.shape[0], 1))
                              * x_idx).astype(int)
        if FlagPrint:
            print '\n gradient =', grad_mag_star
            print '\n indexes =', ColIdxIn_grad_star
        # Points > Th to the RIGHT of pupil center
        (Iok, Jok) = where((grad_mag_star > ThGrad) & (ColIdxIn_grad_star
                           - grad_mag_star.shape[1] / 2 > 0))
        if FlagPrint:
            print '\nIok=', Iok
            print '\nJok=', Jok
        if Iok.shape[0] == 0:
            raise Exception, \
                'No RIGHT intersection with Pupil/CR boundary was found!'
        Istart_ray = (concatenate(([Iok[0] + 1], Iok[:len(Iok) - 1]))
                      - Iok).nonzero()
        Idx_ray = Iok[Istart_ray]
        if FlagPrint:
            print 'Idx_ray=', Idx_ray
            print 'Istart_ray=', Istart_ray
            print 'Indexes peaks right =', Jok[Istart_ray]
        i_peak_right = zeros(grad_mag_star.shape[0])
        i_peak_right[Idx_ray] = Jok[Istart_ray]
        Idx_ray_all = arange(0, grad_mag_star.shape[0])
        Inan = setdiff1d(Idx_ray_all, Idx_ray)
        i_peak_right[Inan] = NaN
        if FlagPrint:
            print 'i_peak finale right = ', i_peak_right

        # Points > Th to the LEFT of pupil center
        (Iok, Jok) = where((grad_mag_star > ThGrad) & (ColIdxIn_grad_star
                           - grad_mag_star.shape[1] / 2 < 0))
        if Iok.shape[0] == 0:
            raise Exception, \
                'No LEFT intersection with Pupil/CR boundary was found!'
        Iok = Iok[len(Iok)::-1]
        Jok = Jok[len(Jok)::-1]
        if FlagPrint:
            print '\n gradient =', grad_mag_star
            print '\n indexes =', ColIdxIn_grad_star
        Istart_ray = (concatenate(([Iok[0] + 1], Iok[:len(Iok) - 1]))
                      - Iok).nonzero()
        Idx_ray = Iok[Istart_ray]
        if FlagPrint:
            print 'Idx_ray=', Idx_ray
            print 'Indexes peaks left =', Jok[Istart_ray]
        i_peak_left = zeros(grad_mag_star.shape[0])
        i_peak_left[Idx_ray] = Jok[Istart_ray]
        Idx_ray_all = arange(0, grad_mag_star.shape[0])
        Inan = setdiff1d(Idx_ray_all, Idx_ray)
        i_peak_left[Inan] = NaN
        if FlagPrint:
            print 'i_peak finale left = ', i_peak_left

        if FlagPlot:
            # Plot gradient magnitude along the rays
            figure()
            ray_ax = ones((grad_mag_star.shape[0], 1)) \
                * arange(grad_mag_star.shape[1])
            plot(ray_ax.transpose(), grad_mag_star.transpose())
            # Plot threshold and points above threshold
            plot([0, grad_mag_star.shape[1]], [ThGrad, ThGrad], 'k--')
            plot(ray_ax[ir, ic].transpose(), grad_mag_star[ir, ic].transpose(),
                 'o')
            # Plot pupil edges
            for i in xrange(grad_mag_star.shape[0]):
                ho = plot([ray_ax[i, i_peak_right[i]]], [grad_mag_star[i,
                          i_peak_right[i]]], '+r')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)
                ho = plot([ray_ax[i, i_peak_left[i]]], [grad_mag_star[i,
                          i_peak_left[i]]], '+g')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)

        return (i_peak_right, i_peak_left, ThGrad)

    # ======================== function: FindCircleEdgeAlongRays_todx ===============================
    def find_edge_along_rays_to_right(self, im_grad_mag, x, y, i_shift,
                                      CurrTh=1000, FlagPlot=False,
                                      FlagPrint=False):
        """ Find the intersections between the pupil boundary and a set of rays.
        It starts from a starting point on each ray and looks to the right of it.

        ARGUMENTS:
        - im_grad_mag = gradient magnitude of the eye image
        - x[m,n] = x coordinates (n points) of the set of m rays
        - y[m,n] = y coordinates (n points) of the set of m rays
        - i_shift = index on each ray from which the intersections will be looked for
        - CurrTh = last value of the threshold used to detect the pupil edges

        RETURN:
        - x_edge, y_edge = intersection points
        """

        # Find gradient magnitude along the rays
        # x = x.astype(int)
        # y = y.astype(int)
        # if FlagPrint:
        #    print 'x =\n', x
        #    print 'y =\n', y
        #    print 'shape gradient = ', im_grad_mag.shape
        #    print 'maximal difference between rays pixels and image boundary along the y axis = ', (y-im_grad_mag.shape[0]).max()
        #    print 'maximal difference between rays pixels and image boundary along the x axis = ', (x-im_grad_mag.shape[1]).max()
        if (y - im_grad_mag.shape[0]).max() > 0 or (x
                - im_grad_mag.shape[1]).max() > 0 or x.min() < 0 or y.min() < 0:
            raise Exception, 'Some rays shooted outside the image boundaries!'

        grad_mag_star = self._get_image_values(im_grad_mag, x, y)

        ray_ax = ones((grad_mag_star.shape[0], 1)) \
            * arange(grad_mag_star.shape[1])
        if FlagPrint:
            print '\nIn FindPupEdgeAlongRays_dx: grad_mag_star.shape =', \
                grad_mag_star.shape

        # Set threshold to find the pupil's edge (e.g., the peak of gradient magnitude) along the rays.
        # This is done individually for each ray, but then the mininal threshold is taken
        grad_star_mean = grad_mag_star.mean(1)
        grad_star_std = grad_mag_star.std(1)
        ThGrad = grad_star_mean + self.mfact_star_std * grad_star_std
        ThGrad = min(ThGrad.min(), CurrTh)
        (ir, ic) = where(grad_mag_star > ThGrad)
        if ir.shape[0] == 0 or ic.shape[0] == 0:
            raise Exception, \
                'In shoot rays to dx (1): No intersection with Pupil/CR boundary was found!'

        # Find intersections of rays wit the pupil boundary
        x_idx = arange(0, grad_mag_star.shape[1])
        ColIdxIn_grad_star = (ones((grad_mag_star.shape[0], 1))
                              * x_idx).astype(int)
        if FlagPrint:
            print '\n gradient =', grad_mag_star
            print '\n indexes =', ColIdxIn_grad_star
        # Points > Th to the RIGHT of pupil center
        (Iok, Jok) = where((grad_mag_star > ThGrad) & (ColIdxIn_grad_star
                           - i_shift > 0))
        if FlagPrint:
            print '\nIok=', Iok
            print '\nJok=', Jok
        if Iok.shape[0] == 0:
            raise Exception, \
                'In shoot rays to dx (2): No intersection with Pupil/CR boundary was found!'
        Istart_ray = (concatenate(([Iok[0] + 1], Iok[:len(Iok) - 1]))
                      - Iok).nonzero()
        Idx_ray = Iok[Istart_ray]
        if FlagPrint:
            print 'Idx_ray=', Idx_ray
            print 'Istart_ray=', Istart_ray
            print 'Indexes peaks right =', Jok[Istart_ray]
        i_peak_right = zeros(grad_mag_star.shape[0])
        i_peak_right[Idx_ray] = Jok[Istart_ray]
        Idx_ray_all = arange(0, grad_mag_star.shape[0])
        Inan = setdiff1d(Idx_ray_all, Idx_ray)
        i_peak_right[Inan] = NaN
        if FlagPrint:
            print 'i_peak finale right = ', i_peak_right

        # Set NaNs = 100000 in the vectors with intersection indexes (NaNs correspond to cases in which no edge was found)
        Inan_right = where(isnan(i_peak_right))
        i_peak_right[Inan_right] = 0
        i_peak_right = i_peak_right.astype(int)
        if FlagPrint:
            print 'Inan_right =', Inan_right
            print 'i peak finali (after removal of NaNs): right =', i_peak_right
        x_edge = x[arange(x.shape[0]), i_peak_right].astype(float)
        y_edge = y[arange(x.shape[0]), i_peak_right].astype(float)
        x_edge[Inan_right] = 100000
        y_edge[Inan_right] = 100000

        if FlagPlot:
            # Plot gradient along rays and intersection points
            figure()
            Iok_right = setdiff1d(arange(x.shape[0]), Inan_right[0])
            Col = [
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                ]
            plot(ray_ax.transpose(), grad_mag_star.transpose(), '.-')
            for i in arange(grad_mag_star.shape[0])[Iok_right]:
                plot([0, grad_mag_star.shape[1]], [ThGrad, ThGrad], '--k')
                Ith = Jok[where(Iok == i)]
#                 plot( ray_ax[i,Ith], grad_mag_star[i,Ith], 'ok' )
                ho = plot([ray_ax[i, i_peak_right[i]]], [grad_mag_star[i,
                          i_peak_right[i]]], '+k')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)

        return (x_edge, y_edge, ThGrad)

    # ======================== function: FindCircleEdgeAlongRays_tosx ===============================
    def find_edge_along_rays_to_left(self, im_grad_mag, x, y, i_shift,
                                     CurrTh=1000, FlagPlot=False,
                                     FlagPrint=False):
        """ Find the intersections between the pupil boundary and a set of rays.
        It starts from a starting point on each ray and looks to the left of it.

        ARGUMENTS:
        - im_grad_mag = gradient magnitude of the eye image
        - x[m,n] = x coordinates (n points) of the set of m rays
        - y[m,n] = y coordinates (n points) of the set of m rays
        - i_shift = index on each ray from which the intersections will be looked for
        - CurrTh = last value of the threshold used to detect the pupil edges

        RETURN:
        - x_edge, y_edge = intersection points
        """

        # Find gradient magnitude along the rays
        # x = x.astype(int)
        # y = y.astype(int)
        # if FlagPrint:
        #    print 'x =\n', x
        # #    print 'y =\n', y
        #    print 'shape gradient = ', im_grad_mag.shape
        #    print 'maximal difference between rays pixels and image boundary along the y axis = ', (y-im_grad_mag.shape[0]).max()
        #    print 'maximal difference between rays pixels and image boundary along the x axis = ', (x-im_grad_mag.shape[1]).max()
        # if (y-im_grad_mag.shape[0]).max() > 0 or (x-im_grad_mag.shape[1]).max() > 0 or x.min() < 0 or y.min() < 0:
        #    raise Exception, "Some rays shooted outside the image boundaries!"

        # grad_mag_star = im_grad_mag[y,x]
        # grad_mag_star = self._get_image_values_floor(im_grad_mag, x, y)
        grad_mag_star = self._get_image_values(im_grad_mag, x, y)

        ray_ax = ones((grad_mag_star.shape[0], 1)) \
            * arange(grad_mag_star.shape[1])
        if FlagPrint:
            print '\nIn FindPupEdgeAlongRays_sx: grad_mag_star.shape =', \
                grad_mag_star.shape

        # Set threshold to find the pupil's edge (e.g., the peak of gradient magnitude) along the rays
        grad_star_mean = grad_mag_star.mean(1)
        grad_star_std = grad_mag_star.std(1)
        ThGrad = grad_star_mean + self.mfact_star_std * grad_star_std
        ThGrad = min(ThGrad.min(), CurrTh)
        (ir, ic) = where(grad_mag_star > ThGrad)
        if ir.shape[0] == 0 or ic.shape[0] == 0:
            raise Exception, \
                'In shoot rays to sx (1):No intersection with Pupil/CR boundary was found!'

        # Find intersections of rays wit the pupil boundary
        x_idx = arange(0, grad_mag_star.shape[1])
        ColIdxIn_grad_star = (ones((grad_mag_star.shape[0], 1))
                              * x_idx).astype(int)

        if FlagPrint:
            print '\n gradient =', grad_mag_star
            print '\n indexes =', ColIdxIn_grad_star
        # Points > Th to the LEFT of pupil center
        (Iok, Jok) = where((grad_mag_star > ThGrad) & (ColIdxIn_grad_star
                           - (grad_mag_star.shape[1] - i_shift) < 0))
        if Iok.shape[0] == 0:
            raise Exception, \
                'In shoot rays to sx (2): No intersection with Pupil/CR boundary was found!'
        Iok = Iok[len(Iok)::-1]
        Jok = Jok[len(Jok)::-1]

        if FlagPrint:
            print '\n gradient =', grad_mag_star
            print '\n indexes =', ColIdxIn_grad_star
        Istart_ray = (concatenate(([Iok[0] + 1], Iok[:len(Iok) - 1]))
                      - Iok).nonzero()
        t_ray = (concatenate(([Iok[0] + 1], Iok[:len(Iok) - 1]))
                 - Iok).nonzero()
        Idx_ray = Iok[Istart_ray]

        if FlagPrint:
            print 'Idx_ray=', Idx_ray
            print 'Indexes peaks left =', Jok[Istart_ray]
        i_peak_left = zeros(grad_mag_star.shape[0])
        i_peak_left[Idx_ray] = Jok[Istart_ray]
        Idx_ray_all = arange(0, grad_mag_star.shape[0])
        Inan = setdiff1d(Idx_ray_all, Idx_ray)
        i_peak_left[Inan] = NaN

        # if FlagPrint: print 'i_peak finale left = ', i_peak

        # Set NaNs = 100000 in the vectors with intersection indexes (NaNs correspond to cases in which no edge was found)
        Inan_left = where(isnan(i_peak_left))
        i_peak_left[Inan_left] = 0
        i_peak_left = i_peak_left.astype(int)
        if FlagPrint:
            print 'Inan_left =', Inan_left
            print 'i peak finali: left =', i_peak_left
        x_edge = x[arange(x.shape[0]), i_peak_left].astype(float)
        y_edge = y[arange(x.shape[0]), i_peak_left].astype(float)
        x_edge[Inan_left] = 100000
        y_edge[Inan_left] = 100000

        if FlagPlot:
            # Plot gradient along rays and intersection points
            figure()
            Iok_left = setdiff1d(arange(x.shape[0]), Inan_left[0])
            Col = [
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                'b',
                'g',
                'r',
                'c',
                'm',
                'k',
                'y',
                ]
            plot(ray_ax.transpose(), grad_mag_star.transpose(), '.-')
            for i in arange(grad_mag_star.shape[0])[Iok_left]:
                plot([0, grad_mag_star.shape[1]], [ThGrad, ThGrad], '--k')
                Ith = Jok[where(Iok == i)]
#                 plot( ray_ax[i,Ith], grad_mag_star[i,Ith], 'ok' )
                ho = plot([ray_ax[i, i_peak_left[i]]], [grad_mag_star[i,
                          i_peak_left[i]]], '+k')
                setp(ho, 'markersize', 10, 'markeredgewidth', 2)

        return (x_edge, y_edge, ThGrad)


