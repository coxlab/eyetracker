#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  EyeTrackerStages.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

from numpy import *


class EyeTrackerStageController:

    def __init__(self, controller):
        self.controller = controller
        self.x_axis = controller.x_axis
        self.y_axis = controller.y_axis
        self.r_axis = controller.r_axis
        self.controller.setup()
        self.setup()

    @property
    def info(self):
        return {'x_current': self.controller.current_position(self.x_axis),
                'y_current': self.controller.current_position(self.y_axis),
                'r_current': self.controller.current_position(self.r_axis)}

    def disconnect(self):
        if self.controller is not None:
            self.controller.disconnect()

    def setup(self):

        # self.send("1VA5.0",1)
        # self.send("2VA5.0",1)
        self.controller.send('3VA4.0', 1)
        self.controller.send('3AC16.0', 1)

        self.controller.send('1HN%d,%d,%d' % (self.x_axis, self.y_axis,
                             self.r_axis), 1)
        self.controller.send('1HO', 1)
        self.controller.send('1HX', 1)

        # self.send("%dFE500.0" % self.x_axis,1)
        self.controller.send('%dFE2.0' % self.x_axis, 1)
        self.controller.send('%dFE10.0' % self.r_axis, 1)

    # ==========================
    # Delegated control methods
    # ==========================

    def home(self, axis):
        self.controller.home(axis)

    def move_absolute(self, axis, pos):
        return self.controller.move_absolute(axis, pos)

    def move_relative(self, axis, pos):
        return self.controller.move_relative(axis, pos)

    def move_composite_absolute(self, axes, new_positions):
        return self.controller.move_composite_absolute(axes, new_positions)

    def move_composite_relative(self, axes, new_positions):
        return self.controller.move_composite_relative(axes, new_positions)

    def current_position(self, axis):
        return self.controller.current_position(axis)

    def wait_for_completion(self, axis):
        return self.controller.wait_for_completion(axis)

    def power_down(self, axis):
        return self.controller.power_down(axis)

    # ===================
    # Precompute motion functions, recipes for moving to a given configuration
    # without actually going there
    # ===================
    def precompute_return_motion(self):
        """Returns a function that will always return the stages to their current positions
        """

        x = self.current_position(self.x_axis)
        y = self.current_position(self.y_axis)
        r = self.current_position(self.r_axis)
        return lambda: self.move_composite_absolute((self.x_axis, self.y_axis,
                                                     self.r_axis), (x, y, r))

    def precompute_composite_rotation_relative(self, d, r_rel):
        r_rel = float(r_rel)
        d = float(d)

        # initial absolute stage values
        self.controller.wait_for_completion(self.x_axis)
        x0_abs = self.current_position(self.x_axis)
        self.controller.wait_for_completion(self.r_axis)
        r0_abs = self.current_position(self.r_axis)

        # Compute target absolute stage values
        r_abs = r0_abs + r_rel
        x_abs = x0_abs - d * sin(r0_abs * math.pi / 180) + d * cos(r0_abs
                * math.pi / 180) * tan(r_abs * math.pi / 180)

        # Compute the new distance of the rotation center from the camera (following the current relative rotation)
        d_new = d * cos(r0_abs * math.pi / 180) / cos(r_abs * math.pi / 180)

        # Move the axes
        return (lambda: self.controller.move_composite_absolute((self.x_axis,
                self.r_axis), (x_abs, r_abs)), d_new)

    # ===================
    # Composite motions
    # ===================

    # Make an ABSOLUTE composite (rotation + x translation) movement about a point some distance away from the origin of the stages.
    # NOTE: this is an ABSOLUTE displacement. This means that the center of rotation entered by the user (i.e., "d") is always measured relative to the origin,
    # no matter what the current position/rotation of the x stage and rotary stage is.
    def composite_rotation_absolute(self, d, r):
        r = float(r)
        d = float(d)
        x = sqrt(-(d ** 2 * sin(r * math.pi / 180) ** 2) / (sin(r * math.pi
                 / 180) ** 2 - 1))

        if r < 0:
            x = -x

        self.controller.move_composite_absolute((self.x_axis, self.r_axis), (x,
                r))

    # Make a RELATIVE composite (rotation + x translation) movement about a point some distance away from the original of the stages.
    def composite_rotation_relative(self, d, r_rel):
        r_rel = float(r_rel)
        d = float(d)

        # initial absolute stage values
        self.controller.wait_for_completion(self.x_axis)
        x0_abs = self.current_position(self.x_axis)
        self.controller.wait_for_completion(self.r_axis)
        r0_abs = self.current_position(self.r_axis)

        # Compute target absolute stage values
        r_abs = r0_abs + r_rel
        x_abs = x0_abs - d * sin(r0_abs * math.pi / 180) + d * cos(r0_abs
                * math.pi / 180) * tan(r_abs * math.pi / 180)

        # Move the axes
        self.controller.move_composite_absolute((self.x_axis, self.r_axis),
                (x_abs, r_abs))

        # Compute the new distance of the rotation center from the camera (following the current relative rotation)
        d_new = d * cos(r0_abs * math.pi / 180) / cos(r_abs * math.pi / 180)

        # return a function call to undo this movement
        return (d_new, lambda: self.controller.move_composite_absolute((self.x_axis, self.r_axis),
                                                                       (x0_abs, r0_abs)))

    # Make a RELATIVE composite (rotation + x translation) movement about a point some distance away from the original of the stages.
    def composite_rotation_relative_old(self, d, r):
        r = float(r)
        d = float(d)

        # Compute relative stage displacements
        Dr = r
        Dx = sqrt(-(d ** 2 * sin(r * math.pi / 180) ** 2) / (sin(r * math.pi
                  / 180) ** 2 - 1))

        if r < 0:
            Dx = -Dx

        # Dx = d * tan(radians(r))

        # Davide's code
        # r_target = r0 + r;
        # h = d * cos(r0 * degs_to_rads)
        # Dx0 = d * sin(r0 * degs_to_rads)
        # d_target = h/cos(r * degs_to_rads)
        # Dx_target = d_target * sin(r_target * degs_to_rads)
        # Dx = Dx0 - Dx_target;
        # x_target = x0 - Dx;

        self.controller.move_composite_relative((self.x_axis, self.r_axis),
                (Dx, Dr))

        # return a function call to undo this movement
        return lambda: self.controller.move_composite_relative((self.x_axis, self.r_axis),
                                                               (-Dx, -Dr))

    def power_down_all(self):
        self.power_down(self.x_axis)
        self.power_down(self.y_axis)
        self.power_down(self.z_axis)


