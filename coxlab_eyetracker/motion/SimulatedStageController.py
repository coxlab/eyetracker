#
#  SimulatedStageController.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

import time
import random
import logging

class SimulatedStageController:

    x_axis = 0
    y_axis = 1
    r_axis = 2

    def __init__(self):
        self.positions = [0.0, 0.0, 0.0]
        
        flag_randomize_axes_location = False
        if flag_randomize_axes_location: 
            random.seed(time.time())
            self.positions[0] += random.uniform(-5,5)
            self.positions[1] += random.uniform(-5,5)
            self.positions[2] += random.uniform(-5,5)
    
    def disconnect(self):
        return
    
    def setup(self):
        return
    
    def send(self, message, dummy):
        return
    
    def home(self, axis):
        self.positions[axis] = 0.0
    
    def move_absolute(self, axis, pos):
        logging.debug("Move absolute: Axis = %s Pos = %s" % (axis, pos))
        self.positions[axis] = float(pos)
        time.sleep(.25)
    
    def move_relative(self, axis, pos):
        logging.debug("Move relative: Axis = %s Pos = %s" % (axis, pos))
        
        self.positions[axis] += float(pos)
        time.sleep(.25)
        

    def move_composite_absolute(self, axes, new_positions):
        for a in range(0, len(axes)):
            self.move_absolute(axes[a], new_positions[a])
    
    def move_composite_relative(self, axes, new_positions):
        for a in range(0, len(axes)):
            self.move_relative(axes[a], new_positions[a])

    def current_position(self, axis):
        return self.positions[axis]

    def wait_for_completion(self, axis):
        return

    def power_down(self, axis):
        return

