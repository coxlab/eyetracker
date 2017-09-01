#
#  MightexLEDController.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

import logging

from coxlab_eyetracker.util import IPSerialBridge

class MightexLEDController (IPSerialBridge):

    channel1 = 1
    channel2 = 2
    channel3 = 3
    channel4 = 4
    
    channelIs = [channel1, channel2, channel3, channel4]
    
    n_channels = 4
    Imax = 500
    
    def __init__(self, address, port):
        IPSerialBridge.__init__(self, address, port)
        self.internal_status = {}
        self.internal_current = {}
        for ch in self.channelIs:
            self.internal_status[ch] = 0#self.status(ch)
            self.internal_current[ch] = 0#self.current(ch)
        #for i in range(0, self.n_channels):
        #    self.internal_status.append(0)#self.status(i)
    
    def connect(self):
        IPSerialBridge.connect(self)
        for ch in self.channelIs:
            self.internal_status[ch] = self.status(ch)
            self.internal_current[ch] = self.current(ch)
    
    def parse_response(self, response):
        return response.strip('>\r\n #')
    
    def __del__(self):
        logging.debug("Shutting down LEDS")
        for c in range(0, self.n_channels):
            self.turn_off(c)
        
        IPSerialBridge.__del__(self)
        #self.disconnect()
    
    def soft_current(self, channel):
        return self.internal_current[channel]
    
    def current(self, channel):
        
        result_string = self.send("?CURRENT %i" % channel)
        tokens = result_string.split()
        if len(tokens):
            try:
                return int(tokens[-1])
            except ValueError as E:
                logging.warning("Exception(%s) on int conversion of %s" % (str(E), tokens[-1]))
                return 0
        else:
            return 0
    
    def status(self, channel):
        result_string = self.send("?MODE %d" % channel)
        #print result_string
        #return self.internal_status[channel]#int(result_string)
        if result_string in ['0','1','2','3']:
            return int(result_string)
        else:
            logging.warning("Status query for channel %i failed: %s" % (channel, result_string))
            return 0
    
    def set_status(self, channel, val):
        if val:
            self.turn_on(channel)
        else:
            self.turn_off(channel)
    
    def set_current(self, channel, current):
        #print channel, current
        #return
        #self.send("NORMAL %d %d %d" % (channel, self.Imax, current))
        self.send("CURRENT %d %d" % (channel, current))
        self.internal_current[channel] = self.current(channel)
        
    def turn_on(self, channel, current = None):
        
        # Set channel into "normal" mode
        self.send("MODE %d 1" % channel)
        
        current = self.internal_current[channel] if current is None else current
        self.send("NORMAL %d %d %d" % (channel, self.Imax, current))
        self.send("CURRENT %d %d" % (channel, current))
        self.internal_current[channel] = self.current(channel)
        #if(current is not None):
        #    # set the "normal" mode parameters
        #    self.send("NORMAL %d %d %d" % (channel, self.Imax, current))
        #
        #    # set the current (turning on the led)
        #    #self.send("CURRENT %d %d" % (channel, current))
        #    
        #    self.internal_current[channel] = self.current(channel)
    
        self.internal_status[channel] = 1#self.status(channel)
        self.status(channel)
    
    def turn_off(self, channel):
    
        # set channel to "disable" mode
        self.send("MODE %d 0" % channel)
        self.internal_status[channel] = 0#self.status(channel)
        self.status(channel)

    def soft_status(self, channel):
        return self.internal_status[channel]
        #return self.status(channel)

