#
#  FocusAndZoomController.py
#  EyeTracker
#
#  Created by David Cox on 4/28/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#

from numpy import *

class FocusAndZoomController:

    def __init__(self, controller):
        self.controller = controller
        self.focus_axis = controller.y_axis
        self.zoom_axis = controller.x_axis
        self.controller.setup()
        self._init_esp300()

    def disconnect(self):
        if(self.controller is not None):
            self.controller.disconnect()

    # ==========================
    # Delegated control methods
    # ==========================
    @property
    def info(self):
        return {'focus_current': self.controller.current_position(self.focus_axis),
                'zoom_current': self.controller.current_position(self.zoom_axis)}
    
    def home(self, axis):
        self.controller.home(axis)
    
    def move_absolute(self, axis, pos):
        return self.controller.move_absolute(axis, pos)

    def current_position(self, axis):
        return self.controller.current_position(axis)

    def current_zoom(self):
        return self.controller.current_position(self.zoom_axis)
    
    def current_focus(self):
        return self.controller.current_position(self.focus_axis)
        
    def zoom_relative(self, pos):
        return self.controller.move_relative(self.zoom_axis, pos)

    def focus_relative(self, pos):
        return self.controller.move_relative(self.focus_axis, pos)

    def zoom_absolute(self, pos):
        return self.controller.move_absolute(self.zoom_axis, pos)

    def focus_absolute(self, pos):
        return self.controller.move_absolute(self.focus_axis, pos)
    
    def wait_for_completion(self, axis):
        return self.controller.wait_for_completion(axis)

    def power_down(self, axis):
        return self.controller.power_down(axis)
        
    def power_down_all(self):
        self.power_down(self.focus_axis)
        self.power_down(self.zoom_axis)
    
    
    def _init_esp300(self):
    
        max_vel = 120.0
        max_acc = 50.0
        max_jerk = 50.0
        set_vel = 100.0
        
        motion_params =  (max_vel, set_vel, max_acc, max_acc, max_acc, max_acc + 20., max_jerk);
        command_string = """1QM3
            1SN7
            1SU1.0000000000
            1FR0.05000000000
            1QS10
            1QV3.5000
            1QI0.2500
            1QG0
            1QT0
            1SL-200.0000
            1SR200.0000
            1TJ1
            1OM4
            1VU%g
            1VA%g
            1JH20.00
            1JW10.00
            1OH2.500000
            1VB0
            1AU%g
            1AC%g
            1AG%g
            1AE%g
            1JK%g
            1KP0.0000
            1KI0.0000
            1KD0.0000
            1VF0.0000
            1AF0.0000
            1KS0.0000
            1FE1.0000
            1DB0
            1CL0
            1SS1
            1GR1
            1SI1
            1SK0,0
            1ZA123H
            1ZB0H
            1ZE3H
            1ZF2H
            1ZH5H
            1ZS4H""" % motion_params
        
        stride = 5
        lines = command_string.splitlines()
        for command in lines:
            self.controller.send(command, 1)
                    
        command_string = """2QM3
            2SN7
            2SU1.0000000000
            2FR0.05000000000
            2QS10
            2QV3.5000
            2QI0.2500
            2QG0
            2QT0
            2SL-200.0000
            2SR200.0000
            2TJ1
            2OM3
            2VU%g
            2VA%g
            2JH20.00
            2JW10.00
            2OH2.500000
            2VB0
            2AU%g
            2AC%g
            2AG%g
            2AE%g
            2JK%g
            2KP0.0000
            2KI0.0000
            2KD0.0000
            2VF0.0000
            2AF0.0000
            2KS0.0000
            2FE1.0000
            2DB0
            2CL0
            2SS1
            2GR1
            2SI1
            2SK0,0
            2ZA123H
            2ZB0H
            2ZE3H
            2ZF2H
            2ZH5H
            2ZS4H""" % motion_params
        lines = command_string.splitlines()
        for command in lines:
            
            self.controller.send(command, 1)

        self.controller.send("1MO",1)
        self.controller.send("2MO",1)
        