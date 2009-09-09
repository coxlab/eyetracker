#
#  main.py
#  EyeTracker
#
#  Created by David Cox on 11/13/08.
#  Copyright Harvard University 2008. All rights reserved.
#

#import modules required by application

import objc
import Foundation
import AppKit



from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import EyeTrackerController
from EyeTrackerController import *
import EyeTrackerAppDelegate
import TrackerCameraView

# pass control to AppKit
AppHelper.runEventLoop()
