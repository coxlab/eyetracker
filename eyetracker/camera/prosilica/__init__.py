#
#  prosilica.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 6/19/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

import prosilica_cpp
from prosilica_cpp import *
import numpy


class Camera (prosilica_cpp.ProsilicaCamera):


    def acquireOneFrame():
        frame = self.getOnePvFrame()
        frame_1D = prosilica_cpp._frameTo1DArray(frame.Width * frame.Height)
        
        frame_2D = frame_1D.reshape(frame.Width, frame.Height)
        
        return frame_2D
