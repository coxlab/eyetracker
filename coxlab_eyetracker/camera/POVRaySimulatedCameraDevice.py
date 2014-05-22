#
#  SimulatedCameraDevice.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 5/26/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

import coxlab_eyetracker.util.Povray as pov
from numpy import *
import os
import PIL.Image
#import matplotlib.pylab as pylab
import time

class POVRaySimulatedCameraDevice:



    def __init__(self, _feature_finder, _stages, _leds, _d, **kwargs):

        self.image_center = array([0,0])

        self.cr_position = array([0.,0.])
        self.pupil_position = array([0.,0.])

        self.l0_offset = array([0.,43., 0.])
        self.l1_offset = array([43., 0., 0.])

        # the stage has no concept of distance to the eye, so this must be spec'd
        self.d = None;

        self.thresh = 0.9

        # povray parameters
        self.cam_view_angle = 1.0# 2.5#4.6

        self.sclera_radius = 3
        self.Rp_int = self.sclera_radius - 0.1

        self.pupil_radius = 0
        self.Rp = self.Rp_int
        self.set_pupil_radius(0.2)

        self.pupil_color = (0,0,0)

        self.eye_rot = (0,30,0)

        self.tempdir = "/tmp/"


        self.stages = _stages
        self.leds = _leds
        self.d = _d
        self.feature_finder = _feature_finder
        self.w = 0.
        self.h = 0.

        self.w = kwargs.get("image_width", 320.)
        self.h = kwargs.get("image_height", 240.)

        self.quiet = kwargs.get("quiet", 0)

        self.droop_angle = 0.0
        self.tilt = 0.0

        self.image_center = (self.w/2, self.h/2)

        self.frame_number = 0

        self.add_noise = kwargs.get("add_noise", True)
        self.noise_level = kwargs.get("noise_level", 4.0)

        self.fake_camera_parameters = {'exposure': 5000,
            'binning': 4,
            'gain': 1}


    def shutdown(self):
        pass

    def acquire_image(self):

        tic = time.time()
        x = self.stages.current_position(self.stages.x_axis)
        y = self.stages.current_position(self.stages.y_axis)
        r = self.stages.current_position(self.stages.r_axis)

        if not self.quiet:
            print "====== Camera state-of-the-world ========"
            print "x: %g" % x
            print "y: %g" % y
            print "r: %g" % r

        l0 = self.leds.status(self.leds.channel2)
        l1 = self.leds.status(self.leds.channel1)

        cam_pos = array([x,y,self.d])
        cam_look = cam_pos + array([sin(radians(r)), sin(radians(self.droop_angle)), cos(radians(r))])
        cam_up = array([sin(radians(self.tilt)), cos(radians(self.tilt)), 0.0])
        cam_up = cam_up - dot(cam_up,cam_look) * cam_look
        cam_up = cam_up / linalg.norm(cam_up)
        #cam_right = array([cos(radians(self.tilt)), sin(radians(self.tilt)), 0.0])

        bg = pov.Background("rgb<0.5,0.5,0.5>")
        cam = pov.Camera(
            angle = self.cam_view_angle,
            location = tuple(cam_pos),
            look_at = tuple(cam_look))
            #sky = tuple(cam_up))

        light0 = None
        light1 = None

        if(l0):
            light0 = pov.LightSource(
                tuple(cam_pos + self.l0_offset + 0*self.l1_offset),
                "color rgbf<1,1,1,1>",
                "spotlight",
                point_at = tuple(cam_look + self.l0_offset + 0*self.l1_offset),
                radius = 5,
                tightness = 3)
        else:
            light0 = pov.Sphere((0,0,0),0)

        if(l1):
            light1 = pov.LightSource(
                tuple(cam_pos + self.l1_offset + 0*self.l0_offset),
                "color rgbf<1,1,1,1>",
                "spotlight",
                point_at = tuple(cam_look + self.l1_offset + 0*self.l0_offset),
                radius = 5,
                tightness = 3)
        else:
            light1 = pov.Sphere((0,0,0),0)


        sclera = pov.Sphere(
            (0,0,0), # center
            self.sclera_radius,
            pov.Pigment(color=(0.5,0.5,0.5,0.8)),
            pov.Finish(
                refraction=1,
                roughness=0.001,
                specular=1),
            pov.Finish(ambient = 1, diffuse = 0.6),
            rotate = tuple(self.eye_rot))

        base = (0,0, self.Rp)
        cap = (0,0, self.Rp - 0.0001)

        eye = pov.Cylinder(
            base,
            cap,
            self.pupil_radius,
            pov.Pigment(
                color=(self.pupil_color[0],
                    self.pupil_color[1],
                    self.pupil_color[2],0.2)),
            pov.Finish( refraction=0 ),
            pov.Finish(ambient = 2, diffuse = 0.6),
            rotate = tuple(self.eye_rot),
            )

        #eye = pov.Sphere(
        #    (0,0,-self.Rp), # center
        #    self.pupil_radius,
        #    pov.Pigment(
        #        color=(self.pupil_color[0],
        #            self.pupil_color[1],
        #            self.pupil_color[2],0.2)),
        #    pov.Finish( refraction=0 ),
        #    pov.Finish(ambient = 2, diffuse = 0.6),
        #    rotate = tuple(self.eye_rot),
        #    )

        f = pov.File(self.tempdir + "eyeball.pov")
        #f.include("colors.inc")
        f.write(bg, cam, light0, light1, sclera, eye)
        f.close()

#        if(self.quiet):
#            command_string = "/sw/bin//povray -D +A +O/tmp/eyeball.png +W%d +H%d /tmp/eyeball.pov  >& /dev/null" % (self.w, self.h);
#        else:
#            command_string = "/sw/bin//povray +O/tmp/eyeball.png +A +W%d +H%d /tmp/eyeball.pov" % (self.w, self.h);
#            print "Command = " + command_string

        if(self.quiet):
            command_string = "/usr/local/bin/povray -D +A +O/tmp/eyeball.png +W%d +H%d /tmp/eyeball.pov  >& /dev/null" % (self.w, self.h);
        else:
            command_string = "/usr/local/bin/povray +O/tmp/eyeball.png +A +W%d +H%d /tmp/eyeball.pov" % (self.w, self.h);
            print "Command = " + command_string

        os.popen(command_string);

        im = PIL.Image.open("/tmp/eyeball.png")
        #print im
        a = asarray(im.convert("RGB"))
        #print a
        a = a.mean(2)

        self.im_array = a.astype(float32)


        if self.add_noise:
            im_shape = self.im_array.shape
            self.im_array += self.noise_level * random.randn(im_shape[0], im_shape[1])

        self.frame_number += 1

        toc = time.time() - tic
        #print("Actual acquire time: %f" % toc)


        timestamp = int(1000*time.time())
        # start the analysis process
        self.feature_finder.analyze_image(self.im_array.copy(), {"pupil_position":self.pupil_position, "cr_position": self.cr_position, "frame_number" : self.frame_number, "timestamp" : timestamp})
        return

    def	get_processed_image(self, guess = None):

        #self.feature_finder.analyze_image(self.im_array,None)
        features = self.feature_finder.get_result()

        if(features == None):
            return features

        if "cr_position" in features:
            self.cr_position = features["cr_position"]
        if "pupil_position" in features:
            self.pupil_position = features["pupil_position"]

        return features

    def move_eye(self, new_position):
        self.eye_rot = array([new_position[1], new_position[0], 0.0])

    def set_pupil_radius(self, new_radius):
        self.pupil_radius = new_radius
        #self.Rp = sqrt(self.Rp_int**2 - new_radius**2)
        print "Rp = %f, radius = %f" % (self.Rp, self.pupil_radius)
