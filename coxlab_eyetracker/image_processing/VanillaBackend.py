#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ImageProcessingBackend import *
from scipy.signal import sepfir2d, convolve2d
from stopwatch import *


class VanillaBackend(ImageProcessingBackend):

    def sobel3x3(self, im, **kwargs):
        if 'naive' in kwargs:
            return sobel3x3_naive(im)

        return self.sobel3x3_separable(im)

    def sobel3x3_separable(self, image, **kwargs):

        sobel_c = array([-1., 0., 1.])
        sobel_r = array([1., 2., 1.])

        imgx = self.separable_convolution2d(image, sobel_c, sobel_r)
        imgy = self.separable_convolution2d(image, sobel_r, sobel_c)

        mag = sqrt(imgx ** 2 + imgy ** 2) + 1e-16

        return (mag, imgx, imgy)

    def sobel3x3_naive(self, image):
        sobel_x = array([[-1., 0., 1.], [-2., 0., 2.], [1., 0., -1]])
        sobel_y = array([[1., 2., -1.], [0., 0., 0.], [-1., -2., 1]])
        imgx = convolve2d(image, sobel_x, mode='same', boundary='symm')
        imgy = convolve2d(image, sobel_y, mode='same', boundary='symm')
        mag = sqrt(imgx ** 2 + imgy ** 2) + 2e-16

        return (mag, imgx, imgy)

    # @clockit
    def separable_convolution2d(self, im, row, col, **kwargs):
        print im.shape
        print row.shape
        print col.shape
        return sepfir2d(array(im), row, col)

    # borrowed with some translation from Peter Kovesi's fastradial.m
    def fast_radial_transform(self, image, radii, alpha, **kwargs):

        gaussian_kernel_cheat = 1.

        (rows, cols) = image.shape

        use_cached_sobel = False
        cached_mag = None
        cached_x = None
        cached_y = None
        if 'cached_sobel' in kwargs:
            (cached_mag, cached_x, cached_y) = kwargs['cached_sobel']
            (sobel_rows, sobel_cols) = cached_sobel_mag.shape

            if sobel_rows == rows or sobel_cols == cols:
                use_cached_sobel = True

        if use_cached_sobel:
            mag = cached_mag
            imgx = cached_x
            imgy = cached_y
        else:
            (mag, imgx, imgy) = self.sobel3x3(image)

        # Normalise gradient values so that [imgx imgy] form unit
        # direction vectors.
        imgx = imgx / mag
        imgy = imgy / mag

        Ss = list(radii)

        (y, x) = mgrid[0:rows, 0:cols]  # meshgrid(1:cols, 1:rows);

        S = zeros_like(image)

        for r in range(0, len(radii)):

            n = radii[r]

            M = zeros_like(image)
            O = zeros_like(image)
            F = zeros_like(image)

            # Coordinates of 'positively' and 'negatively' affected pixels
            posx = x + n * imgx
            posy = y + n * imgy

            negx = x - n * imgx
            negy = y - n * imgy

            # Clamp Orientation projection matrix values to a maximum of
            # +/-kappa,  but first set the normalization parameter kappa to the
            # values suggested by Loy and Zelinski
            kappa = 9.9
            if n == 1:
                kappa = 8

            posx = posx.round()
            posy = posy.round()
            negx = negx.round()
            negy = negy.round()

            # Clamp coordinate values to range [1 rows 1 cols]
            posx[where(posx < 0)] = 0
            posx[where(posx > cols - 1)] = cols - 1
            posy[where(posy < 0)] = 0
            posy[where(posy > rows - 1)] = rows - 1

            negx[where(negx < 0)] = 0
            negx[where(negx > cols - 1)] = cols - 1
            negy[where(negy < 0)] = 0
            negy[where(negy > rows - 1)] = rows - 1

            for r in range(0, rows):
                for c in range(0, cols):
                    O[posy[r, c], posx[r, c]] += 1
                    O[negy[r, c], negx[r, c]] -= 1

                    M[posy[r, c], posx[r, c]] += mag[r, c]
                    M[negy[r, c], negx[r, c]] -= mag[r, c]

            O[where(O > kappa)] = kappa
            O[where(O < -kappa)] = -kappa

            # Unsmoothed symmetry measure at this radius value
            F = M / kappa * (abs(O) / kappa) ** alpha

            # Generate a Gaussian of size proportional to n to smooth and spread
            # the symmetry measure.  The Gaussian is also scaled in magnitude
            # by n so that large scales do not lose their relative weighting.
            # A = fspecial('gaussian',[n n], 0.25*n) * n;
            # S = S + filter2(A,F);
            width = round(gaussian_kernel_cheat * n)
            # print width
            if mod(width, 2) == 0:
                width += 1
            gauss1d = scipy.signal.gaussian(width, 0.25 * n)

            thisS = self.separable_convolution2d(F, gauss1d, gauss1d)
            S += thisS

        S = S / len(radii)  # Average

        return S

    def find_minmax(self, image, **kwargs):

        # print "here (vanilla)"
        if image == None:
            return ([0, 0], [0])

        min_coord = nonzero(image == min(image.ravel()))
        max_coord = nonzero(image == max(image.ravel()))

        # print image.shape
        # print image
        # print min_coord
        # print max_coord
        return ([min_coord[0][0], min_coord[1][0]], [max_coord[0][0],
                max_coord[1][0]])
