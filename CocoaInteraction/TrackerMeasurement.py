#
#  TrackerMeasurement.py
#  EyeTracker
#
#  Created by David Cox on 3/11/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#

from Foundation import *
from AppKit import *
import objc
from objc import IBAction, IBOutlet

class TrackerMeasurement (NSObject):

    azimuth = objc.ivar(u"azimuth")
    elevation = objc.ivar(u"elevation")
    
    mean_az = objc.ivar(u"mean_az")
    mean_el = objc.ivar(u"mean_el")

    std_az = objc.ivar(u"std_az")
    std_el = objc.ivar(u"std_el")

   
    def set_values(self, az, el, mean_az, mean_el, std_az, std_el):
        self.azimuth = az
        self.elevation = el
        self.mean_az = mean_az
        self.mean_el = mean_el
        self.std_az = std_az
        self.std_el = std_el
        
    