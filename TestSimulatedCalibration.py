#!/usr/bin/env python2.5
#
#  TestSimulatedCalibration.py
#  EyeTracker
#
#  Created by David Cox on 12/4/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#


from CobraEyeTracker import *

# tests to perform
test_camera_basic = 0
test_camera_rotation = 0
test_composite_rotation = 0
test_calibration_basic = 1

#ff = FastRadialFeatureFinder()
ff = SimpleEyeFeatureFinder()

simulated_stage_controller = SimulatedStageController()
stages = EyeTrackerStageController(simulated_stage_controller)
leds = SimulatedLEDController(4)
camera = POVRaySimulatedCameraDevice(ff, stages, leds, -140.)

# take the camera for a quick spin
if test_camera_basic:
    n = 3
    for x in map(None, linspace(-3.,3.,n), linspace(40.,-40.,n)):
        for i in [0,1]:
            if i:
                leds.turn_on(0, 20.)
                leds.turn_off(1)
            else:
                leds.turn_on(1, 20.)
                leds.turn_off(0)
                        
            camera.acquire_image()
            stages.move_absolute(0,x[0])



if test_camera_rotation:

    leds.turn_on(0,20.)
    leds.turn_off(1)

    camera.acquire_image()
    stages.move_relative(stages.r_axis, .5)
    camera.acquire_image()
    stages.move_relative(stages.r_axis, .5)
    #camera.acquire_image()

if test_composite_rotation:

    leds.turn_on(0,20.)
    leds.turn_off(1)
    
    d_new, reversal_function = stages.composite_rotation_relative(140., 60)
    camera.acquire_image()
    reversal_function()
    camera.acquire_image()



if test_calibration_basic:
    calibrator = StahlLikeCalibrator(camera, stages, leds, y_stage_direction = -1., d_halfrange=10)
    xyrs = ( (1, 1, 0), (1, -1, 0), (-1, -1, 0), (-1, 1, 0) )
    #       no,         yes,        yes,            no
    for xyr in xyrs:
        stages.home(stages.x_axis)
        stages.home(stages.y_axis)
        stages.home(stages.r_axis)
        stages.move_relative(stages.x_axis, xyr[0])
        stages.move_relative(stages.y_axis, xyr[1])
        stages.move_relative(stages.r_axis, xyr[2])
        calibrator.calibrate()