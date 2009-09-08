#
#  EyeTrackerAppDelegate.py
#  EyeTracker
#
#  Created by David Cox on 11/13/08.
#  Copyright Harvard University 2008. All rights reserved.
#

from Foundation import *
from AppKit import *

class EyeTrackerAppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, sender):
        NSLog("Application did finish launching.")
