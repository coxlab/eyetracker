#
#  TrackerMeasurementController.py
#  EyeTracker
#
#  Created by David Cox on 3/11/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#


from Foundation import *
from AppKit import *
import objc
from objc import IBAction, IBOutlet
import matplotlib
matplotlib.use("module://cocoa_backend")
from matplotlib.pylab import *

from CobraEyeTracker import *

from processing import *

from TrackerMeasurement import *

class TrackerMeasurementController(NSArrayController):

    azimuth_set = objc.ivar(u"azimuth_set")
    elevation_set = objc.ivar(u"elevation_set")

    overall_controller = IBOutlet()

    def awakeFromNib(self):
        self._.azimuth_set = 0.0
        self._.elevation_set = 0.0
        
    def add_measurement(self, mean_az, mean_el, std_az, std_el, true_az=None, true_el=None):
        
        print TrackerMeasurement
        measurement = TrackerMeasurement.alloc().init()
        
        az_set = true_az
        el_set = true_el
        if(true_az == None or true_el == None):
            az_set = self.azimuth_set
            el_set = self.elevation_set
            
        measurement.set_values(az_set, el_set, mean_az, mean_el, std_az, std_el)
        
        self.addObject_(measurement)
    
    @IBAction
    def plotPoints_(self, sender):
        azimuths = []
        elevations = []
        az_errs = []
        el_errs = []
        true_azs = []
        true_els = []
        
        measurements = self.arrangedObjects()
        measurement_enumerator = measurements.objectEnumerator()
        
        m = measurement_enumerator.nextObject()
        while m != objc.nil:
            azimuths.append(m.mean_az)
            elevations.append(m.mean_el)
            az_errs.append(m.std_az)
            el_errs.append(m.std_el)
            true_azs.append(m.azimuth)
            true_els.append(m.elevation)
            m = measurement_enumerator.nextObject()
        
            
        figure()
        
        errorbar(azimuths, elevations, az_errs, el_errs,  'bx')
        grid(alpha=0.5)
        
        # calculate errors and plot them
        for i in xrange(len(azimuths)):
            # calculate nearest grid intersection
            x = round(azimuths[i]/5.0) * 5.0
            y = round(elevations[i]/5.0) * 5.0
            # calculate error
            xErr = azimuths[i] - x
            yErr = elevations[i] - y
            t = "%.2f,%.2f" % (xErr, yErr)
            if max(abs(xErr), abs(yErr)) >= 0.5:
                tSize = 'x-small'
            else:
                tSize = 'xx-small'
            # draw line from nearest intersection to the measured point
            plot([x,azimuths[i]],[y,elevations[i]],'r')
            # label the point with the azimuth and elevation error
            text(azimuths[i], elevations[i], t, size=tSize)
            
        
        meansq_az = mean((array(azimuths) - array(true_azs))**2)
        meansq_el = mean((array(elevations) - array(true_els))**2)
        title("Mean sq error (az) = %f, Mean sq error (el) = %f" % (meansq_az, meansq_el))
#        ax = gca()
#        ax.set_xticks(range(-35,15,1))
#        ax.set_yticks(range(-15,15,1))
#        grid(True)
    
    @IBAction
    def printPoints_(self, sender):
        measurements = self.arrangedObjects()
        measurement_enumerator = measurements.objectEnumerator()
        
        print "-"*50
        print "Measurement set: "
        print "-"*50
        m = measurement_enumerator.nextObject()
        while m != objc.nil:
            print "%f\t%f\t%f\t%f\t%f\t%f" % (float(m.azimuth), float(m.elevation), float(m.mean_az), float(m.mean_el), float(m.std_az), float(m.std_el))
            m = measurement_enumerator.nextObject()
            