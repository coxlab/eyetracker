#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  DavesStarburstEyeFeatureFinder.py
#  EyeTracker
#
#  Created by David Cox on 3/9/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#

from numpy import *
# from EdgeDetection import *
from stopwatch import *
from EyeFeatureFinder import *
from scipy.weave import inline
# from scipy.weave import converters
import scipy.optimize
from coxlab_eyetracker.util import *

from WovenBackend import *


class SubpixelStarburstEyeFeatureFinder(EyeFeatureFinder):

    def __init__(self, **kwargs):
        self.parameters_updated = False

        self.backend = WovenBackend()

        self.shortcut_sobel = kwargs.get('shortcut_sobel', None)

        # following values in pixels
        self.cr_ray_length = kwargs.get('cr_ray_length', 10)
        self.pupil_ray_length = kwargs.get('pupil_ray_length', 25)
        self.cr_min_radius = kwargs.get('cr_min_radius', 2)
        self.pupil_min_radius = kwargs.get('pupil_min_radius', 3)  # 14

        # how many rays to shoot in the CR
        self.cr_n_rays = kwargs.get('cr_n_rays', 20)

        # how many rays to shoot in the pupil
        self.pupil_n_rays = kwargs.get('pupil_n_rays', 40)

        # how many pixels per sample along the ray
        self.cr_ray_sample_spacing = kwargs.get('cr_ray_sample_spacing', 0.5)
        self.pupil_ray_sample_spacing = kwargs.get('pupil_ray_sample_spacing',
                1)

        self.cr_threshold = kwargs.get('cr_threshold', 1.)
        self.pupil_threshold = kwargs.get('pupil_threshold', 2.5)

        self.ray_sampling_method = kwargs.get('ray_sampling_method', 'interp')

        self.fitting_algorithm = kwargs.get('fitting_algorithm',
                'circle_least_squares')

        self.pupil_rays = None
        self.cr_rays = None

        self.x_axis = 0
        self.y_axis = 1

        # rebuild parameters and cached constructs based on the current
        # parameter settings
        self.update_parameters()

    def update_parameters(self):
        """ Reconstruct internal representations in response to new parameters being set
            Recache rays, set method pointers, and clear storage for returned starburst parameters
        """

        if self.ray_sampling_method == 'interp':
            self._get_image_values = self._get_image_values_interp_faster
        else:
            self._get_image_values = self._get_image_values_nearest

        if self.fitting_algorithm == 'circle_least_squares':
            self._fit_points = self._fit_circle_to_points_lstsq
        elif self.fitting_algorithm == 'circle_least_squares_ransac':
            self._fit_points = self._fit_circle_to_points_lstsq_ransac
        elif self.fitting_algorithm == 'ellipse_least_squares':
            self._fit_points = self._fit_ellipse_to_points
        else:
            self._fit_points = self._fit_mean_to_points

        # how many samples per ray
        self.cr_ray_sampling = arange(0, self.cr_ray_length,
                                      self.cr_ray_sample_spacing)
        self.cr_ray_sampling = self.cr_ray_sampling[1:]  # don't need the zero sample
        self.cr_min_radius_ray_index = round(self.cr_min_radius
                / self.cr_ray_sample_spacing)

        self.pupil_ray_sampling = arange(0, self.pupil_ray_length,
                self.pupil_ray_sample_spacing)
        self.pupil_ray_sampling = self.pupil_ray_sampling[1:]  # don't need the zero sample
        self.pupil_min_radius_ray_index = round(self.pupil_min_radius
                / self.pupil_ray_sample_spacing)

        # ray BY ray samples BY x/y
        self.cr_rays = zeros((self.cr_n_rays, len(self.cr_ray_sampling), 2))
        self.pupil_rays = zeros((self.pupil_n_rays,
                                len(self.pupil_ray_sampling), 2))

        # Choose ray angles in the range [0, 2pi)
        self.cr_ray_angles = linspace(0, 2 * pi, self.cr_n_rays + 1)
        self.cr_ray_angles = self.cr_ray_angles[0:-1]

        self.pupil_ray_angles = linspace(0, 2 * pi, self.pupil_n_rays + 1)
        self.pupil_ray_angles = self.pupil_ray_angles[0:-1]

        for r in range(0, self.cr_n_rays):
            ray_angle = self.cr_ray_angles[r]

            self.cr_rays[r, :, self.x_axis] = self.cr_ray_sampling \
                * cos(ray_angle)
            self.cr_rays[r, :, self.y_axis] = self.cr_ray_sampling \
                * sin(ray_angle)

        for r in range(0, self.pupil_n_rays):
            ray_angle = self.pupil_ray_angles[r]

            self.pupil_rays[r, :, self.x_axis] = self.pupil_ray_sampling \
                * cos(ray_angle)
            self.pupil_rays[r, :, self.y_axis] = self.pupil_ray_sampling \
                * sin(ray_angle)

        self.cr_boundary_points = None
        self.pupil_boundary_points = None
        self.cr_ray_starts = None
        self.cr_ray_ends = None
        self.pupil_ray_starts = None
        self.pupil_ray_ends = None
        self.parameters_updated = True

    # @clockit
    def analyze_image(self, image, guess, **kwargs):
        """ Begin processing an image to find features
        """

        # print "sb"

        use_weave = False

        if 'weave' in kwargs:
            use_weave = kwargs['weave']

        # Clear the result
        self.result = None

        features = {}
        if guess is not None and 'frame_number' in guess:
            features['frame_number'] = guess['frame_number']

        if guess is not None and 'restrict_top' in guess:
            features['restrict_top'] = guess['restrict_top']
            features['restrict_bottom'] = guess['restrict_bottom']
            features['restrict_left'] = guess['restrict_left']
            features['restrict_right'] = guess['restrict_right']

        # This is the starting seed-point from which we will start
        cr_guess = guess['cr_position']
        pupil_guess = guess['pupil_position']

        if 'cached_sobel' in guess:
            self.shortcut_sobel = guess['cached_sobel']

        # image = double(image)

        # compute the image gradient
        if self.shortcut_sobel == None:
            (image_grad_mag, image_grad_x, image_grad_y) = \
                self.backend.sobel3x3(image)
        else:
            image_grad_mag = self.shortcut_sobel

        # Do the heavy lifting
        # try:
        if use_weave:
            cr_boundaries = self._find_ray_boundaries_woven(image_grad_mag,
                    cr_guess, self.cr_rays, self.cr_min_radius_ray_index,
                    self.cr_threshold)
        else:
            cr_boundaries = self._find_ray_boundaries(image_grad_mag, cr_guess,
                    self.cr_rays, self.cr_min_radius_ray_index,
                    self.cr_threshold)

        (cr_position, cr_radius, cr_err) = self._fit_points(cr_boundaries)

        # do a two-stage starburst fit for the pupil
        # stage 1, rough cut
        # self.pupil_min_radius_ray_index
        pupil_boundaries = self._find_ray_boundaries(
            image_grad_mag,
            pupil_guess,
            self.pupil_rays,
            self.pupil_min_radius_ray_index,
            self.pupil_threshold,
            exclusion_center=array(cr_position),
            exclusion_radius=2 * cr_radius,
            )

        (pupil_position, pupil_radius, pupil_err) = \
            self._fit_points(pupil_boundaries)

        # # stage 2: refine
        # minimum_pupil_guess = round(0.5 * pupil_radius
        #                             / self.pupil_ray_sample_spacing)

        # pupil_boundaries = self._find_ray_boundaries(
        #     image_grad_mag,
        #     pupil_position,
        #     self.pupil_rays,
        #     minimum_pupil_guess,
        #     self.pupil_threshold,
        #     exclusion_center=array(cr_position),
        #     exclusion_radius=2 * cr_radius,
        #     )

        # (pupil_position, pupil_radius, pupil_err) = \
        #     self._fit_points(pupil_boundaries)

#            if(False and use_weave):
#                pupil_boundaries = self._find_ray_boundaries_woven(image_grad_mag, pupil_guess, self.pupil_rays, self.pupil_min_radius_ray_index, self.pupil_threshold, exclusion_center=array(cr_position), exclusion_radius= 1.2 * cr_radius)
#            else:
#                pupil_boundaries = self._find_ray_boundaries(image_grad_mag, pupil_guess, self.pupil_rays, self.pupil_min_radius_ray_index, self.pupil_threshold, exclusion_center=array(cr_position), exclusion_radius= 1.2 * cr_radius)
#
#            pupil_position, pupil_radius, pupil_err = self._fit_points(pupil_boundaries)

        # except Exception, e:
        #    print "Error analyzing image: %s" % e.message
        #     formatted = formatted_exception()
        #     print formatted[0], ": "
        #     for f in formatted[2]:
        #         print f
        #     cr_position = cr_guess
        #     cr_radius = 0.0
        #     pupil_position = pupil_guess
        #     pupil_radius = 0.0

        # Pack up the results

        try:

            features['transform'] = guess.get('transform', None)
            features['cr_position'] = cr_position
            features['pupil_position'] = pupil_position
            features['cr_radius'] = cr_radius
            features['pupil_radius'] = pupil_radius

            starburst = {}
            starburst['cr_boundary'] = cr_boundaries
            starburst['pupil_boundary'] = pupil_boundaries
            starburst['cr_rays_start'] = self.cr_rays[:, 0, :] + cr_guess
            starburst['cr_rays_end'] = self.cr_rays[:, -1, :] + cr_guess
            starburst['pupil_rays_start'] = self.pupil_rays[:, 0, :] \
                + pupil_guess
            starburst['pupil_rays_end'] = self.pupil_rays[:, -1, :] \
                + pupil_guess
            starburst['cr_err'] = cr_err
            starburst['pupil_err'] = pupil_err

            features['starburst'] = starburst
        except Exception, e:
            print 'Error packing up results of image analysis'
            print e.message
            formatted = formatted_exception()
            print formatted[0], ': '
            for f in formatted[2]:
                print f
            # raise

        self.result = features

    def get_result(self):
        """ Get the result of a previous call to analyze_image.
            This call is separate from analyze_image so that analysis
            can be done asyncronously on multiple processors/cores
        """

        return self.result

    # @clockit
    def _find_ray_boundaries(self, im, seed_point, zero_referenced_rays,
                             cutoff_index, threshold, **kwargs):
        """ Find where a set off rays crosses a threshold in an image

            Arguments:
            im -- An image (usually a gradient magnitude image) in which crossing will be found
            seed_point -- the origin from which rays will be projected
            zero_referenced_rays -- the set of rays (starting at zero) to sample.  nrays x ray_sampling x image_dimension
            cutoff_index -- the index along zero_referenced_rays below which we are sure that we are
                                    still within the feature.  Used to normalize threshold.
            threshold -- the threshold to cross, expressed in standard deviations across the ray samples
        """

        boundary_points = []

        # create appropriately-centered rays
        rays_x = zero_referenced_rays[:, :, self.x_axis] \
            + seed_point[self.x_axis]
        rays_y = zero_referenced_rays[:, :, self.y_axis] \
            + seed_point[self.y_axis]

        # get the values from the image at each of the points
        vals = self._get_image_values(im, rays_x, rays_y)

        cutoff_index = int(cutoff_index)

        if cutoff_index != 0:

            vals_reshaped = vals[:, 0:cutoff_index]
            vals_reshaped = vals_reshaped[where(~isnan(vals_reshaped))]
            vals_reshaped.shape = [prod(vals_reshaped.shape)]
            mean_val = mean(vals_reshaped)
            std_val = std(vals_reshaped)

            normalized_threshold = threshold * std_val + mean_val
        else:
            normalized_threshold = threshold * std(vals[:]) + mean(vals[:])

        vals_slope = hstack((2 * ones([vals.shape[0], 1]), diff(vals, 1)))
        vals_slope[where(isnan(vals_slope))] = 0

        # figure()
        #         vals_display = vals
        #         vals_display[where(isnan(vals_display))] = 0
        #         imshow((vals - mean_val) / normalized_threshold, interpolation='nearest')
        #         colorbar()
        #
        #         figure()
        #         imshow(vals_slope, interpolation='nearest')
        #         colorbar()
        #         hold(True)
        #

        # scan inward-to-outward to find the first threshold crossing
        for r in range(0, vals.shape[0]):
            crossed = False

            for v in range(cutoff_index, vals.shape[1]):
                if isnan(v):
                    # print "end of ray"
                    break

                val = vals[r, v]
                # print "comparing val %f to threshold %f" % (val, normalized_threshold)
                if val > normalized_threshold:
                    crossed = True

                if crossed and vals_slope[r, v] <= 0:
                    boundary_points.append(array([rays_x[r, v - 1], rays_y[r, v
                            - 1]]))
                    break

        if 'exclusion_center' in kwargs:
            final_boundary_points = []
            exclusion_center = kwargs['exclusion_center']
            exclusion_radius = kwargs['exclusion_radius']

            for bp in boundary_points:
                if exclusion_center == None or linalg.norm(exclusion_center
                        - bp) > exclusion_radius:
                    final_boundary_points.append(bp)
            return final_boundary_points
        else:

            return boundary_points

    # #@clockit
    def _find_ray_boundaries_woven(self, im, seed_point, zero_referenced_rays,
                                   cutoff_index, threshold, **kwargs):
        """ Find where a set off rays crosses a threshold in an image

            Arguments:
            im -- An image (usually a gradient magnitude image) in which crossing will be found
            seed_point -- the origin from which rays will be projected
            zero_referenced_rays -- the set of rays (starting at zero) to sample.  nrays x ray_sampling x image_dimension
            cutoff_index -- the index along zero_referenced_rays below which we are sure that we are
                                    still within the feature.  Used to normalize threshold.
            threshold -- the threshold to cross, expressed in standard deviations across the ray samples
        """

        #assert False

        if 'exclusion_center' in kwargs:
            exclusion_center = kwargs['exclusion_center']
        else:
            exclusion_center = None

        if 'exclusion_radius' in kwargs:
            exclusion_radius = kwargs['exclusion_radius']
        else:
            exclusion_radius = None

        # create appropriately-centered rays
        rays_x = zero_referenced_rays[:, :, self.x_axis] \
            + seed_point[self.x_axis]
        rays_y = zero_referenced_rays[:, :, self.y_axis] \
            + seed_point[self.y_axis]

        # get the values from the image at each of the points
        vals = self._get_image_values(im, rays_x, rays_y)

        # We will return up to n_rays return indices
        returned_points = -1 * ones([zero_referenced_rays.shape[0], 2])
        n_returned_points = len(returned_points)
        # n_returned_points = 0

        vals_slope = hstack((2 * ones([vals.shape[0], 1]), diff(vals, 1)))
        vals_slope[where(isnan(vals_slope))] = 0
        if not vals_slope.flags['C_CONTIGUOUS']:
            vals_slope = vals_slope.copy()

        code = \
            """

            // Get some array sizes

            int n_rays = Nrays_x[0];
            int n_ray_samples = Nrays_x[1];


            // Compute normalization factors
            int n_vals = 0;
            double mean_val = 0;
            double var_val = 0;
            double old_mean = 0;
            double old_var = 0;


            // See Knuth TAOCP vol 2, 3rd edition, page 232
            // via http://www.johndcook.com/standard_deviation.html
            for(int r=0; r < n_rays; r++){
                for(int s=0; s < cutoff_index; s++){
                    int index = r*n_ray_samples + s;
                    double val = vals[index];
                    if(val != NAN){
                        n_vals++;
                        if(n_vals == 1){
                            old_mean = mean_val = val;
                            old_var = 0.0;
                        } else {
                            mean_val = old_mean + (val - old_mean)/n_vals;
                            var_val = old_var + (val - old_mean) * (val - mean_val);

                            old_mean = mean_val;
                            old_var = var_val;
                        }
                    }
                }
            }

            double std_val = sqrt(var_val/(n_vals-1));

            double normalized_threshold = std_val * threshold + mean_val;

            for(int r=0; r < n_rays; r++){
                short crossed = 0;
                for(int s=cutoff_index; s < n_ray_samples; s++){
                    int index = r*n_ray_samples + s;
                    double val = vals[index];

                    if(val == NAN){
                        break; // end of ray
                    }

                    if(val > normalized_threshold){
                        crossed = 1;

                    }

                    if(crossed && vals_slope[index] <= 0){

                        returned_points[n_returned_points*2 + 0] = rays_x[r*n_ray_samples + s-1];
                        returned_points[n_returned_points*2 + 1] = rays_y[r*n_ray_samples + s-1];
                        n_returned_points++;
                        break;
                    }
                }
            }
        """

        # inline(code_test, [n_returned_points])

        inline(code, [
            'vals',
            'vals_slope',
            'rays_x',
            'rays_y',
            'cutoff_index',
            'threshold',
            'n_returned_points',
            'returned_points',
            ])
        boundary_points = []

        for p in range(0, returned_points.shape[0]):
            if returned_points[p, 0] != -1.:
                bp = returned_points[p, :]
                if exclusion_center == None or linalg.norm(exclusion_center
                        - bp) > exclusion_radius:
                    boundary_points.append(bp)

        return boundary_points

    def _get_image_values_nearest(self, im, x_, y_):
        """ Sample an image at a set of x and y coordinates, using nearest neighbor interpolation.
        """

        x = x_.round()
        y = y_.round()

        # trim out-of-bounds elements
        bad_elements = where((x < 0) | (x >= im.shape[1]) | (y < 0) | (y
                             >= im.shape[0]))

        x[bad_elements] = 0
        y[bad_elements] = 0

        vals = im[x.astype(int), y.astype(int)]
        vals[bad_elements] = nan
        return vals

    # ##@clockit
    def _get_image_values_interp(self, im, x, y):
        """ Samples an image at a set of x and y coordinates, using bilinear interpolation
        """

        vals = zeros(x.shape)
        floor_x = floor(x).astype(int)
        floor_y = floor(y).astype(int)
        ceil_x = ceil(x).astype(int)
        ceil_y = ceil(y).astype(int)

        x_frac = 1 - (x - floor_x)
        y_frac = 1 - (y - floor_y)

        for i in range(0, x.shape[0]):
            for j in range(0, x.shape[1]):
                if floor_x[i, j] < 0 or floor_y[i, j] < 0 or ceil_x[i, j] \
                    > im.shape[0] or ceil_y[i, j] > im.shape[1]:
                    vals[i, j] = nan
                    continue

                a = im[floor_x[i, j], floor_y[i, j]]
                b = im[ceil_x[i, j], floor_y[i, j]]
                c = im[floor_x[i, j], ceil_y[i, j]]
                d = im[ceil_x[i, j], ceil_y[i, j]]

                val = x_frac[i, j] * y_frac[i, j] * a + (1 - x_frac[i, j]) \
                    * y_frac[i, j] * b + x_frac[i, j] * (1 - y_frac[i, j]) * c \
                    + (1 - x_frac[i, j]) * (1 - y_frac[i, j]) * d

                vals[i, j] = val
        return vals

    # #@clockit
    def _get_image_values_interp_faster(self, im, x, y):
        """ Samples an image at a set of x and y coordinates, using bilinear interpolation (using no loops)
        """

        # trim out-of-bounds elements
        bad_elements = where((x < 0) | (x >= im.shape[0] - 1) | (y < 0) | (y
                             >= im.shape[1] - 1))

        # for now, put in zeros so that the computation doesn't fail
        x[bad_elements] = 0
        y[bad_elements] = 0

        vals = zeros(x.shape)
        floor_x = floor(x).astype(int)
        floor_y = floor(y).astype(int)
        ceil_x = ceil(x).astype(int)
        ceil_y = ceil(y).astype(int)

        x_frac = 1 - (x - floor_x)
        y_frac = 1 - (y - floor_y)

        a = im[floor_x, floor_y]
        b = im[ceil_x, floor_y]
        c = im[floor_x, ceil_y]
        d = im[ceil_x, ceil_y]

        vals = x_frac * y_frac * a + (1 - x_frac) * y_frac * b + x_frac * (1
                - y_frac) * c + (1 - x_frac) * (1 - y_frac) * d

        # invalidate out-of-bounds elements
        vals[bad_elements] = nan
        return vals

    def _fit_mean_to_points(self, points):
        """ Fit the center and radius of a set of points using the mean and std of the point cloud
        """

        if points == None or len(points) == 0:
            return (array([-1., -1.]), 0.0, Inf)

        center = mean(points, 0)

        centered = array(points)
        centered[:, 0] -= center[0]
        centered[:, 1] -= center[1]
        distances = sqrt(centered[:, 0] ** 2 + centered[:, 1] ** 2)
        radius = mean(distances)

        return (center, radius, 0.0)

    #@clockit
    def _fit_circle_to_points_lstsq(self, points):
        """ Fit a circle algebraicly to a set of points, using least squares optimization
        """

        if points == None or len(points) == 0:
            # print "_fit_circle_to_points_lstsq: no boundary points, bailing: ", points
            return (array([-1., -1.]), 0.0, Inf)

        if len(points) <= 3:
            return self._fit_mean_to_points(points)

        points_array = array(points)
        points_x = points_array[:, 0]
        points_x.shape = [prod(points_x.shape)]
        points_y = points_array[:, 1]
        points_y.shape = [prod(points_y.shape)]

        (center_guess, radius_guess, dummy) = self._fit_mean_to_points(points)

        a0 = -2 * center_guess[0]
        b0 = -2 * center_guess[1]
        c0 = center_guess[0] ** 2 + center_guess[1] ** 2 - (points_array[:, 0]
                - center_guess[0]).mean() ** 2
        p0 = array([a0, b0, c0])

        output = scipy.optimize.leastsq(self._residuals_circle, p0,
                                        args=(points_x, points_y))

        (a, b, c) = output[0]

        # Calculate the location of center and radius
        center_fit = array([-a / 2, -b / 2])
        radius_fit = sqrt(center_fit[0] ** 2 + center_fit[1] ** 2 - c)
        err = sum(self._residuals_circle(array([a, b, c]), points_x, points_y)
                  ** 2)
        # print(err)
        return (center_fit, radius_fit, err)

    # ##@clockit
    def _fit_ellipse_to_points(self, points):

        if points == None or len(points) == 0:
            # print "_fit_ellipse_to_points_lstsq: no boundary points, bailing"
            return (array([-1., -1.]), 0.0, Inf)

        if len(points) < 5:
            return self._fit_mean_to_points(points)

        # initialize
        orientation_tolerance = 1e-3
        points_array = array(points)

        # remove bias of the ellipse - to make matrix inversion more accurate. (will be added later on).
        x = points_array[:, 0]
        y = points_array[:, 1]
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

        fit_err = 0
        try:
            A = dot(sum(X, axis=0), linalg.inv(dot(X.transpose(), X)))
        except linalg.LinAlgError:

            print 'A linear algebra error has occurred while ellipse fitting'
            return (array([-1., -1.]), 0.0, Inf)
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

            center_fit = array([X0_in[0], Y0_in[0]])

            # determine the fit error
            centered_points = points_array - ones((points_array.shape[0], 1)) \
                * center_fit
            r_data = sqrt(centered_points[:, 0] ** 2 + centered_points[:, 1]
                          ** 2)
            thetas = arctan(centered_points[:, 1] / centered_points[:, 0])
            r_fit = a * b / sqrt((b * cos(thetas)) ** 2 + a * sin(thetas) ** 2)
            fit_err = sum((r_fit - r_data) ** 2)

            # print "Estimated Ellipse center =", X0_in, Y0_in
            return (center_fit, long_axis / 2.0, fit_err)
        elif test == 0:

            print 'Error in ellipse fitting: parabola found instead of ellipse'
            # return self._fit_circle_to_points_lstsq(points)
            return (array([-1., -1.]), 0.0, Inf)
        elif test < 0:
            print 'Error in ellipse fitting: hyperbola found instead of ellipse'
            # return self._fit_circle_to_points_lstsq(points)
            return (array([-1., -1.]), 0.0, Inf)

    # ##@clockit
    def _fit_circle_to_points_lstsq_ransac(self, points):
        max_iter = 20
        min_consensus = 8
        good_fit_consensus = round(len(points) / 2)
        pointwise_error_threshold = 0.05

        if len(points) < min_consensus:
            return self._fit_circle_to_points_lstsq(points)

        iter = 0
        # want to do better than this
        (center_fit, radius_fit, best_err) = \
            self._fit_circle_to_points_lstsq(points)

        while iter < max_iter:
            (maybe_inliers_i, the_rest_i) = self._random_split(len(points),
                    min_consensus)
            maybe_inliers = []
            the_rest = []
            for i in maybe_inliers_i:
                maybe_inliers.append(points[i])
            for i in the_rest_i:
                the_rest.append(points[i])

            (maybe_center, maybe_radius, maybe_err) = \
                self._fit_circle_to_points_lstsq(maybe_inliers)

            for p in the_rest:
                dist = linalg.norm(p - maybe_center)
                point_err = abs(dist - maybe_radius)
                if point_err < pointwise_error_threshold * maybe_radius:
                    maybe_inliers.append(p)

            if len(maybe_inliers) > good_fit_consensus:
                (candidate_center, candidate_radius, candidate_err) = \
                    self._fit_circle_to_points_lstsq(array(maybe_inliers))
                if candidate_err < best_err:
                    center_fit = candidate_center
                    radius_fit = candidate_radius
                    best_err = candidate_err

            iter += 1

        return (center_fit, radius_fit, best_err)

    def _random_split(self, n, k):
        r = random.rand(n)
        indices = argsort(r).astype(int)
        return (indices[0:k], indices[k + 1:])

    def _residuals_circle(self, p, x, y):
        """ An objective function for fitting a circle function
        """

        (a, b, c) = p

        err = x ** 2 + y ** 2 + a * x + b * y + c
        return err


# A test script to see stuff in action
if __name__ == '__main__':

    import PIL.Image
    from numpy import *
    from scipy import *
    from matplotlib import *

    from CompositeEyeFeatureFinder import *
    from FastRadialFeatureFinder import *

    test_images = ['Snapshot_test.bmp', 'Snapshot.bmp', 'Snapshot2.bmp']

    if False:

        def test_ff_on_image(test_image_name):

            print test_image_name
            test_image = double(asarray(PIL.Image.open(test_image_name)))
            if len(test_image.shape) == 3:
                test_image = mean(test_image, 2)
            (sobelified, x, y) = sobel3x3_separable(test_image)

            radial_ff = FastRadialFeatureFinder()
            radial_ff.target_kpixels = 3.0
            radial_ff.correct_downsampling = True
            radial_ff.radius_steps = 20
            radial_ff.min_radius_fraction = 1. / 200
            radial_ff.max_radius_fraction = 1. / 5
            starburst_ff = \
                SubpixelStarburstEyeFeatureFinder(cached_sobel=sobelified)
            composite_ff = CompositeEyeFeatureFinder(radial_ff, starburst_ff)

            composite_ff.analyze_image(test_image)
            features = composite_ff.get_result()

            # do it twice to allow compilation
            composite_ff.analyze_image(test_image)
            features = composite_ff.get_result()

            figure()
            imshow(test_image, interpolation='nearest')
            gray()
            hold(True)
            cr_position = features['cr_position']
            pupil_position = features['pupil_position']

            plot([cr_position[1]], [cr_position[0]], 'g+')
            plot([pupil_position[1]], [pupil_position[0]], 'g+')

            sb = features['starburst']
            cr_bounds = sb['cr_boundary']
            pupil_bounds = sb['pupil_boundary']

            for b in cr_bounds:
                plot([b[1]], [b[0]], 'rx')

            for b in pupil_bounds:
                plot([b[1]], [b[0]], 'rx')

            # pw = 20;
            # axis((cr_position[1]+pw, cr_position[0]+pw, cr_position[1]-pw, cr_position[0]-pw))

            figure()

            imshow(sobelified, interpolation='nearest')
            cr_ray_start = sb['cr_rays_start']
            cr_ray_end = sb['cr_rays_end']

            pupil_ray_start = sb['pupil_rays_start']
            pupil_ray_end = sb['pupil_rays_end']

            for i in range(0, len(cr_ray_start)):
                plot([cr_ray_start[i][1], cr_ray_end[i][1]],
                     [cr_ray_start[i][0], cr_ray_end[i][0]], 'r-')
            for i in range(0, len(pupil_ray_start)):
                plot([pupil_ray_start[i][1], pupil_ray_end[i][1]],
                     [pupil_ray_start[i][0], pupil_ray_end[i][0]], 'b-')

            for b in cr_bounds:
                plot([b[1]], [b[0]], 'rx')
            for b in pupil_bounds:
                plot([b[1]], [b[0]], 'rx')


            # axis((cr_position[1]+pw, cr_position[0]+pw, cr_position[1]-pw, cr_position[0]-pw))

        for im in test_images:
            test_ff_on_image(im)

        show()
