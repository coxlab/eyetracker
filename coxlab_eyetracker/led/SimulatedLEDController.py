#
#  SimulatedLEDController.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#


class SimulatedLEDController:

    channel1 = 0
    channel2 = 1
    channel3 = 2
    channel4 = 3

    def __init__(self, n_channels):
        self.n_channels = n_channels
        self.internal_status = []
        self.internal_current = []
        for i in range(0, n_channels):
            self.internal_status.append(0)
            self.internal_current.append(20)
    
    def current(self, channel):
        return self.internal_current[channel]
    soft_current = current
    
    def status(self, channel):
        return self.internal_status[channel]
    
    def set_status(self, channel, val):
        if val:
            self.turn_on(channel)
        else:
            self.turn_off(channel)
    
    def set_current(self, channel, current):
        self.internal_current[channel] = current
    
    def turn_on(self, channel, current = None):
        self.internal_status[channel] = 1
        
        if(current != None):
            self.internal_current[channel] = current
    
    def turn_off(self, channel):
        self.internal_status[channel] = 0
    
    def soft_status(self, channel):
        return self.status(channel)