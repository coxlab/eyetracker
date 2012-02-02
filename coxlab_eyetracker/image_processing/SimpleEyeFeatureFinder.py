#
#  SimpleEyeFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 7/29/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

from numpy import *


class SimpleEyeFeatureFinder:

    # analyze the image and return dictionary of features gleaned
    # from it
    def analyze_image(self, image, guess, **kwargs):

        # simple strategy: highest intensity is CR, lowest is pupil
        # obviously, not very robust

        if(len(image.shape) == 3):
            im = mean(image, 2)
        else:
            im = image

        maxes = where(im == amax(im))
        mins = where(im == amin(im))

        cr = array([maxes[0][0], maxes[1][0]])
        pupil = array([mins[0][0], mins[1][0]])

        self.features = {'pupil_position_stage1': pupil,
                         'cr_position_stage1': cr,
                         'pupil_position': pupil,
                         'cr_position': cr,
                         'im_shape': image.shape,
                         'pupil_size': None,
                         'cr_size': None
                        }

    def get_result(self):
        return self.features
