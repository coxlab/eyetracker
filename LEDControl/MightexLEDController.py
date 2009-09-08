#
#  MightexLEDController.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

from IPSerialBridge import *

class MightexLEDController (IPSerialBridge):

    channel1 = 1
    channel2 = 2
    channel3 = 3
    channel4 = 4
    
    n_channels = 4
    Imax = 500

    def __init__(self, address, port):
        IPSerialBridge.__init__(self, address, port)
        
    def __del__(self):
        for c in range(0, n_channels):
            self.turn_off(c)
    
    def current(self, channel):
        
        result_string = self.send("CURRENT %d" % channel)
        return double(result_string)
    
    def status(self, channel):
        
        result_string = self.send("MODE %d" % channel)
        return int(result_string)
    
    def turn_on(self, channel, current = None):
        
        # Set channel into "normal" mode
        self.send("MODE %d 1" % channel)

        if(current != None):
            # set the "normal" mode parameters
            self.send("NORMAL %d %d %d" % (channel, self.Imax, current))
        
            # set the current (turning on the led)
            self.send("CURRENT %d %d" % (channel, current))
    
    
    def turn_off(self, channel):
    
        # set channel to "disable" mode
        self.send("MODE %d 0" % channel)
        
