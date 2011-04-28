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
        self.internal_status = []
        for i in range(0, self.n_channels):
            self.internal_status.append(0)#self.status(i)

    
    def __del__(self):
        print("Shutting down LEDS")
        for c in range(0, self.n_channels):
            self.turn_off(c)
        
        IPSerialBridge.__del__(self)
        #self.disconnect()
    
    def current(self, channel):
        
        result_string = self.send("?CURRENT %d" % channel)
        return double(result_string)
    
    def status(self, channel):
        result_string = self.send("?MODE %d" % channel)
        #print result_string
        return self.internal_status[channel]#int(result_string)
    
    def turn_on(self, channel, current = None):
        
        # Set channel into "normal" mode
        self.send("MODE %d 1" % channel)

        if(current != None):
            # set the "normal" mode parameters
            self.send("NORMAL %d %d %d" % (channel, self.Imax, current))
        
            # set the current (turning on the led)
            self.send("CURRENT %d %d" % (channel, current))
    
        self.internal_status[channel] = 1#self.status(channel)
        self.status(channel)
    
    def turn_off(self, channel):
    
        # set channel to "disable" mode
        self.send("MODE %d 0" % channel)
        self.internal_status[channel] = 0#self.status(channel)
        self.status(channel)

    def soft_status(self, channel):
        return self.internal_status[channel]

