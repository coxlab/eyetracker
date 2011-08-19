#
#  StahlLikeCalibrator.py
#  EyeTracker
#
#  Created by David Cox on 12/2/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

from math import *
from numpy import *
from scipy import *
import scipy.optimize
from scipy import stats
import time
from Queue import Queue, Full

class StahlLikeCalibrator:

    uncalibrated = 0
    pupil_only_uncalibrated = 1
    pupil_only = 2
    calibrated = 3
    
    no_led = -1
    both_leds = -2

    def __init__(self, camera, stages, focus_and_zoom, leds, **kwargs):
        # handles to real-world objects
        self.camera = camera
        self.stages = stages
        self.leds = leds
        self.focus_and_zoom = focus_and_zoom
    
        self.default_Rp = kwargs.get("default_Rp", 3.2)

        self.ui_queue = kwargs.get("ui_queue", None)
        self.x_image_axis = kwargs.get("x_image_axis", 1)
        self.y_image_axis = kwargs.get("y_image_axis", 0)
        self.x_stage_axis = kwargs.get("x_stage_axis", stages.x_axis)
        self.x_stage_direction = kwargs.get("x_stage_direction", -1)
        self.y_stage_axis = kwargs.get("y_stage_axis", stages.y_axis)
        self.y_stage_direction = kwargs.get("y_stage_direction", -1)
        self.r_stage_direction = kwargs.get("r_stage_direction", 1)
        self.top_led = kwargs.get("top_led", leds.channel2)
        self.side_led = kwargs.get("side_led", leds.channel1)
        self.visible_led = kwargs.get("visible_led", leds.channel3)
        self.d_guess = kwargs.get("d_guess", 260)
                
        self.d = self.d_guess
            
        self.jog_angle = kwargs.get("jog_angle", 3.)
        self.z_delta = kwargs.get("z_delta", 1.)
        self.cr_diff_threshold = kwargs.get("cr_diff_threshold", 0.1)
        self.d_halfrange = kwargs.get("d_halfrange", 50.)  # 0.5 * max range of uncertainty of distance from cam to target
        
        self.default_cr_positions = {}
        
        self.pupil_cr_diff = None
        
        self.zoom_factor = None
        
        self.n_calibration_samples = 10
        # internal calibration parameters (initialize to None)
        self.offset = None
        #self.d = None      # distance to center of corneal curvature
        self.Rp = None      # radius to pupil, from center of corneal curvature
        self.y_equator = None
        self.y_topCR_ref = None
        self.pixels_per_mm = None
        # center of the camera frame
        self.center_camera_frame = None
        
        self.quiet = 1    
        
        self.CompLensDistor = CompensateLensDistorsion()
        
    
    def _get_is_calibrated(self):
        return (self.d != None and self.Rp != None and self.y_equator != None and self.y_topCR_ref != None)
        
    # define a property instance attribute (outside any method)
    calibrated = property(_get_is_calibrated)
    
    
    def report_set_gaze_values(self):
        
        # Acquire first n gaze values
        n = 20
        retry = 40
        features = self.acquire_averaged_features(n, retry)
        
        # Swip columns in the arrays with gaze values
        flag_swip_cols = 0
        if flag_swip_cols:
            cr_array = features["cr_position_array"]
            tmp = cr_array[:,1].copy()
            cr_array[:,1] = cr_array[:,0]
            cr_array[:,0] = tmp
            pupil_array = features["pupil_position_array"]
            tmp = pupil_array[:,1].copy()
            pupil_array[:,1] = pupil_array[:,0]
            pupil_array[:,0] = tmp
            #print "set of pupil measurements (pix) =\n", pupil_array
        else:
            cr_array = features["cr_position_array"]
            pupil_array = features["pupil_position_array"]
        
        # Convert pixel arrays to degree
        elevation, azimuth = self.transform( pupil_array, cr_array)
        
        print "#########  Set of pupil measurements (deg): ##########\n"
        print "Azimuth =\n", azimuth
        print "Elevation =\n", elevation
                
        print "#########  Set of top CR measurements (pix): ##########\n"
        print "x =\n", cr_array[:,0]
        print "y =\n", cr_array[:,1]
        
        return mean(azimuth), mean(elevation), std(azimuth), std(elevation)
                

        
    def acquire_averaged_features(self, n, retry = 200):

        # ###### Start of Davide's implementation ######

        # Flush queue (somehow a buffer of images is stored during acquisition and must be flushed)
        for i in range(0, 3):
            self.camera.acquire_image()
            features = self.camera.get_processed_image()
        
        pupil_radius = array([])
        cr_radius = array([])
        pupil_position = zeros( (1,2) ) # this first row is just for initialization (it should be removed once the array is filled)
        cr_position = zeros( (1,2) )
        n_count = 0
        n_attempt = 0
        while n_count < n and n_attempt < retry:
            self.camera.acquire_image()
            features = self.camera.get_processed_image()
            # Testing on the key 'pupil_position' is enough to guarantee that all other relevant parameters exist
            if features is not None and features['pupil_position'] is not None:
                pupil_radius = hstack( (pupil_radius, features['pupil_radius']) )
                cr_radius = hstack( (cr_radius, features['cr_radius']) )
                pupil_position = vstack( (pupil_position, features['pupil_position']) )
                cr_position = vstack( (cr_position, features['cr_position']) )            
                n_count += 1
            n_attempt += 1
        # Remove first row
        pupil_position = delete( pupil_position, 0, 0 )
        cr_position = delete( cr_position, 0, 0 )
        
        if pupil_radius.shape[0] > 0:
        
            ## Compensate for lens distorsions
            #cr_position = cr_position.transpose()
            #cr_position = self.CompLensDistor.fully_compensate( cr_position, None )
            #cr_position = cr_position.transpose()
            #pupil_position = pupil_position.transpose()
            #pupil_position = self.CompLensDistor.fully_compensate( pupil_position, None )
            #pupil_position = pupil_position.transpose()
            
            med_features = features
            med_features["is_calibrating"] = 1
            # Replace coordinates/radiuses with the median
            med_features['pupil_radius'] = median(pupil_radius)
            med_features['cr_radius'] = median(cr_radius)
            med_features['pupil_position'] = median(pupil_position, 0)
            med_features['cr_position'] = median(cr_position, 0)
            med_features['pupil_position_array'] = pupil_position
            med_features['cr_position_array'] = cr_position
            
            if not self.quiet:
                print "\n"
                print "ARRAY cr position = ", cr_position
                print "\n"
                print "ARRAY cr position transposed = ", cr_position.transpose()
                print "\n"
                print "MEDIAN pupil radius = ", median(pupil_radius)
                print "MEDIAN cr radius = ", median(cr_radius)
                print "MEDIAN pupil position = ", median(pupil_position, 0)
                print "MEDIAN cr position = ", median(cr_position, 0)
                print "\n"
                print "LAST pupil radius = ", med_features['pupil_radius']
                print "LAST cr radius = ", med_features['cr_radius']
                print "LAST pupil position = ", med_features['pupil_position']
                print "LAST cr position = ", med_features['cr_position']
                print "\n"
        else:
            med_features = None
            raise Exception, "Features median (average) could not be computed: NO features acquired!" 

        if(self.ui_queue != None):
            try:
                self.ui_queue.put_nowait(med_features)
                #print "!@#$!@#$!@#$!@#$!@#$ used median features"
            except Full, e:
                print "Calibrator: unable to communicate with GUI"
                pass
                
        return med_features
        # ######### End of Davide's implementation #########


        # ######### Start of Dave's implementation #########
        for i in range(0, n):
            self.camera.acquire_image()
            avg_features = self.camera.get_processed_image()
        avg_features["is_calibrating"] = 1

        
        # Shortcut until I figure this out
        while (avg_features == None or 
              avg_features["cr_position"] == None or
              avg_features["pupil_position"] == None or
              avg_features["im_array"] == None):
            self.camera.acquire_image()
            avg_features = self.camera.get_processed_image()
        
        if(self.ui_queue != None):
            try:
                self.ui_queue.put_nowait(avg_features)
            except Full, e:
                print "Calibrator: unable to communicate with GUI"
                pass
                
        return avg_features
        # End shortcut
        
        avg_features = features
        averagable_keys = ['cr_position', 'pupil_position']
        for key in averagable_keys:
            if(avg_features[key] == None):
                if(retry < 10):
                    return self.acquire_averaged_features(n,retry+1)
                else:
                    raise Exception, "invalid feature dictionary"
            else:
                avg_features[key] /= float(n)
        
        for i in range(1, n):
            self.camera.acquire_image()
            features = self.camera.get_processed_image()
            for key in averagable_keys:
                if(avg_features[key] == None):
                    avg_features[key] += features[key] / float(n)
        
        if(self.ui_queue != None):
            try:
                self.ui_queue.put_nowait(avg_features)
            except Full, e:
                pass
        return avg_features
        # ######### End of Dave's implementation #########
        
    
    def calibrate(self):
        """Calibrate the eye tracker manipulating stages and leds as needed.
            
            Following this call, the transform method will convert image coordinates
            to degrees"""
        
        # calibrate the eye tracker in five steps
        print "CENTER HORIZONTAL"
        self.center_horizontal()
        
        print "CENTER VERTICAL"
        self.center_vertical()
        
        print "CENTER DEPTH"
        self.center_depth_faster()
        
        #print "ALIGN PUPIL AND CR"
        #self.align_pupil_and_CR()
        
        print "FIND PUPIL RADIUS"
        self.find_pupil_radius()
        
        print "d = ", self.d
        print "Rp = ", self.Rp
        
        
        
    def transform(self, pupil_coordinates, cr_coordinates):
        """Convert image (pixel) coordinates to degrees of visual angle"""
        
        transform_vector = True
    
        which_led = self.no_led
        
        # check which LED is on
        if self.leds.soft_status(self.top_led):
            which_led = self.top_led
        
        if self.leds.soft_status(self.side_led):
            which_led = self.side_led
            
        # check if both LEDs are on.
        if self.leds.soft_status(self.side_led) and self.leds.soft_status(self.top_led):
            which_led = self.both_leds
            cr_coordinates = None       # these are junk if both are on
        
    
        
        # establish the calibration status, this will be forwarded
        # on so that a decision can be made about how to treat this data
        calibration_status = self.uncalibrated
        if cr_coordinates is None and not self.calibrated:
            calibration_status = self.pupil_only_uncalibrated
        elif cr_coordinates is None and self.calibrated:
            calibration_status = self.pupil_only
        elif self.calibrated:
            calibration_status = self.calibrated        
        
        if calibration_status is self.uncalibrated:
            return pupil_coordinates[0], pupil_coordinates[1], calibration_status
        
        # if we have no cr_coordinates, assume virtual ones
        if cr_coordinates is None:
            which_led = self.top_led
            cr_coordinates = self.default_cr_positions[self.top_led]
        
        if(pupil_coordinates.ndim == 1):
            transform_vector = False
            pupil_coordinates = array([pupil_coordinates])
            cr_coordinates = array([cr_coordinates])
            
        # create a "virtual" top led, if the side one is on
        if which_led == self.side_led:
            cr_coordinates = cr_coordinates - self.default_cr_positions[self.side_led] + self.default_cr_positions[self.top_led]
            
        y_equator = self.y_equator + (cr_coordinates[:,self.y_image_axis] - self.y_topCR_ref)
        
        if self.Rp is None:
            Rp = self.default_Rp
        else:
            Rp = self.Rp
        
        
        y_displacement = pupil_coordinates[:,self.y_image_axis] - y_equator
        
        elevation = -arcsin( y_displacement / Rp ) * 180/pi
        azimuth = arcsin( (pupil_coordinates[:,self.x_image_axis] - cr_coordinates[:,self.x_image_axis]) / sqrt( Rp**2 - y_displacement**2 ) ) * 180/pi                
        
        
        if(transform_vector):
            return (elevation, azimuth, calibration_status)
        
        return elevation[0], azimuth[0], calibration_status

    def center_horizontal(self):
        """Horizontally align the camera with the eye"""
        print "Calibrator: centering horizontal"
        self.center_axis(self.x_stage_axis)

        # Save the position of the CR spot with the light on the top: this is the displacement 
        # y coordinate of the equator when running with the top LED on
        if self.top_led in self.default_cr_positions:
            self.y_topCR_ref = self.default_cr_positions[self.top_led][self.y_image_axis]
    

    def center_vertical(self):
        """Vertically align the camera with the eye"""
        self.center_axis(self.y_stage_axis)
    
        # Save the position of the CR spot with the light on the side: this is the y coordinate of the equator
        if self.side_led in self.default_cr_positions:
            self.y_equator = self.default_cr_positions[self.side_led][self.y_image_axis]

    def center_axis(self, stage_axis):
        """Align the camera with the eye along the specified axis"""
        
        Dx = 1.  # a quantum of stage displacement
        
        if(stage_axis == self.x_stage_axis):
            chosen_led = self.top_led
            other_led = self.side_led
            im_axis = self.x_image_axis
            stage_direction = self.x_stage_direction
        else:
            chosen_led = self.side_led
            other_led = self.top_led
            im_axis = self.y_image_axis
            stage_direction = self.y_stage_direction
        
        # 1. Turn on the {top|side} LED, turn off the {side|top} LED
        self.leds.turn_on(chosen_led)
        self.leds.turn_off(other_led)
        
        # 2. Get the first CR and Pupil Positions
        
        # we'll be grabbing a few measurements, so start a list
        cr_pos = []
        pupil_pos = []
        
        #time.sleep(1)
        
        # acquire, analyze
        features = self.acquire_averaged_features(self.n_calibration_samples)

        original_cr = features["cr_position"]
        original_pupil = features["pupil_position"]
        
        if self.center_camera_frame is not None:
            print "ALIGN TO THE CENTER OF CAMERA FRAME"
            im_center = self.center_camera_frame
        else:
            print "ALIGN TO THE CENTER OF ACQUIRED IMAGE"
            im_shape = features["im_shape"]
            im_center = array(self.camera.im_array.shape) / 2.
        
        self.y_equator = im_center[self.y_image_axis]
        
        print("ORIGINAL CR POSITION = %f, %f" % tuple(original_cr))
        print("ORIGINAL PUPIL POSITION = %f, %f" % tuple(original_pupil))
        print("IMAGE CENTER = %f, %f" % tuple(im_center))
        
        # 3. Move the stage towards the center in the {X|Y} direction
        Dx_sign = 1.
        if(original_cr[im_axis] < im_center[im_axis]):
            Dx_sign = -1.
        Dx_actual = stage_direction * Dx_sign * Dx
        
        if not self.quiet:
            print "Axis original position:", self.stages.current_position(stage_axis)
            print "planned displacement:", Dx_actual

        self.stages.move_relative(stage_axis,  Dx_actual)
        
        if not self.quiet:
            print "Axis new position:", self.stages.current_position(stage_axis)
        
        # 4. Get the CR and Pupil Positions again
        features = self.acquire_averaged_features(self.n_calibration_samples)
        
        cr = features["cr_position"]
        pupil = features["pupil_position"]
        
        print("CR POSITION = %f, %f" % tuple(cr))
        print("PUPIL POSITION = %f, %f" % tuple(pupil))
        
        # 5. Compute the slope (pixels / mm)
        slope = (cr[im_axis] - original_cr[im_axis]) / Dx_actual;
        print("Slope = %f" % slope)
        
        self.pixels_per_mm = abs(slope)
        
        # 6. Move to center in the {X|Y} direction
        Dx_actual = stage_direction * (cr[im_axis] - im_center[im_axis]) / slope
        if not self.quiet:
            print "planned displacement:", Dx_actual
        #self.stages.move_relative(stage_axis, self.x_stage_direction * (im_center[im_axis] - cr[im_axis]) / slope) # Dave's
        self.stages.move_relative(stage_axis, Dx_actual)
        if not self.quiet:
            print "Axis final position:", self.stages.current_position(stage_axis)
            
        # 7. (Optional) Report the CR and Pupil Positions, as well as the stage position
        # not right now
        features = self.acquire_averaged_features(self.n_calibration_samples)
        
        self.default_cr_positions[chosen_led] = features["cr_position"]
        
        print("FINAL CR POSITION = %f, %f" % tuple(features["cr_position"]))
        print("FINAL PUPIL POSITION = %f, %f" % tuple(features["pupil_position"]))
        
        return
      
    def calibrate_zoom(self):
        zoom_quantum = -10.0
        zoom_steps = 5
        zoom_level = 0
        
        steps = []
        pixels_per_mm_measured = []
        
        self.center_horizontal()
        steps.append(zoom_level)
        pixels_per_mm_measured.append(self.pixels_per_mm)
        
        for s in range(0,zoom_steps):
            self.focus_and_zoom.zoom_relative(zoom_quantum)
            zoom_level += zoom_quantum
            self.center_horizontal()
            pixels_per_mm_measured.append(self.pixels_per_mm)
            steps.append(zoom_level)
        
        self.focus_and_zoom.zoom_relative(-zoom_level)

        params = stats.linregress(array(steps), array(pixels_per_mm_measured))
    
        self.zoom_factor = params[0]

        self.center_horizontal()
        print "Before: %g, After: %g" % (pixels_per_mm_measured[0], self.pixels_per_mm)
        print "Zoom factor: %g" % (self.zoom_factor)
    
    def _jogged_cr_difference(self, d, rs, axis):
        
        cr_pos = []
        for i in range(0,2):
            d_new, reversal_function = self.stages.composite_rotation_relative(d, rs[i])
            
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos.append(features["cr_position"])
            reversal_function()
        
        print "########## in _jogged_cr_difference:" 
        print "cr pos 1st =", cr_pos[0][axis], "cr pos 2nd =", cr_pos[1][axis]
        print "DIFFERENCE CRs =", cr_pos[0][axis] - cr_pos[1][axis]
        return cr_pos[0][axis] - cr_pos[1][axis]


    def _jogged_pupil_cr_difference(self, d, r, axis):
        
        d_new, reversal_function = self.stages.composite_rotation_relative(d, r)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]
        reversal_function()
        
        print "########## in _jogged_pupil_cr_difference:"
        print "cr pos =", cr_pos[axis], "pupil pos =", pupil_pos[axis]
        print "DIFFERENCE CR - PUPIL =", cr_pos[axis] - pupil_pos[axis]
        return cr_pos[axis] - pupil_pos[axis]
    

    def center_depth_faster(self):
        """" Fit a linear function to the depth vs. cr-displacement data to find the zero point in a hurry
        """
        
        print "Centering depth (faster)"
        # 1. Turn on the top LED, turn off the side LED
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        
        # 2. Sample some distances in the range self.d_guess +/- self.d_half_range
        n_points_to_sample = 4
        ds = linspace(self.d_guess - self.d_halfrange, self.d_guess + self.d_halfrange, n_points_to_sample)
        measured_cr_displacements_pos = []
        measured_cr_displacements_neg = []
        
        # set the "default" cr position
        features = self.acquire_averaged_features(self.n_calibration_samples)
        base_cr = features["cr_position"]
        
        # precompute the movements, so we can do them quickly and in succession
        precomputed_motions_pos = []
        precomputed_motions_neg = []
        for d in ds:
            motion_func, d_new = self.stages.precompute_composite_rotation_relative(d, self.jog_angle)
            precomputed_motions_pos.append(motion_func)
            
            motion_func, d_new = self.stages.precompute_composite_rotation_relative(d, -self.jog_angle)
            precomputed_motions_neg.append(motion_func)
        
        return_motion = self.stages.precompute_return_motion()
        
        # make the movements and acquire images
        for precomputed_motion in precomputed_motions_pos:
            precomputed_motion()
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos = features["cr_position"]
            measured_cr_displacements_pos.append(cr_pos[1])

        for precomputed_motion in precomputed_motions_neg:
            precomputed_motion()
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos = features["cr_position"]
            measured_cr_displacements_neg.append(cr_pos[1])

        measured_cr_displacements = array(measured_cr_displacements_pos) - array(measured_cr_displacements_neg)

        # return to our original position
        return_motion()
        
        print "ds = ", ds
        print "cr_diffs = ", array(measured_cr_displacements)
        
        X = hstack((array([ds]).T, ones_like(array([ds]).T)))
        cr_diff_vector = array([measured_cr_displacements]).T
        
        params = dot(linalg.pinv(X), cr_diff_vector)
        self.d = double(-params[1] / params[0])
        
        print("=====================================")
        print("D (faster) = %f" % self.d)
        print("=====================================")
        

    def center_depth(self):
        """" Vary the radius of rotation of the camera, untill the CR spot is stable in the image (i.e., it does not move when the camera rotates to the left or to the right). 
        
             This is achieved with an adaptive search loop that stops when the CR difference is small enough or a maximum # of loops are executed.
        """
        
        # 1. Turn on the top LED, turn off the side LED
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        
        # 2. Adaptively optimize (this actually moves the stages) 
        rs = self.r_stage_direction * array([-self.jog_angle, self.jog_angle])
        range = [self.d_guess - self.d_halfrange, self.d_guess + self.d_halfrange]
         
        objective_function = lambda x: abs(self._jogged_cr_difference(x, rs, self.x_image_axis))
        self.d = scipy.optimize.fminbound(objective_function, range[0], range[1], (), self.cr_diff_threshold, 30)
        
        self.d = self.d[0]
        print("=====================================")
        print("D = %f" % self.d)
        print("=====================================")
        

    def sharpness_objective(self, abs_focus):
        self.focus_and_zoom.focus_absolute(abs_focus)
        features = self.acquire_averaged_features(4)
        sharpness = -features["sobel_avg"]
        print "Sharpness: ", sharpness
        return sharpness
    

    def autofocus(self):
    
        current_focus = self.focus_and_zoom.current_focus()
        focus_range = (current_focus - 100, current_focus + 100)
        focus_target = scipy.optimize.fminbound(self.sharpness_objective, focus_range[0], focus_range[1], (), 0.1, 20)
        
        self.focus_and_zoom.focus_absolute(focus_target) 
        

    def center_depth_old(self):
        """" Vary the radius of rotation of the camera, untill the CR spot is stable in the image (i.e., it does not move when the camera rotates to the left or to the right). 
        
             This is achieved with an adaptive search loop that stops when the CR difference is small enough or a maximum # of loops are executed.
        """
        
        # 1. Turn on the top LED, turn off the side LED
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        
        # 2. Adaptive loop 
        #   a. Rotate the camera left/right and compute the difference in the x location of the CR
        #   b. Compute the new value of the rotation radius (d) - closer to the center of the eye
        #   c. Move the stages to correct
        
        d = self.z_delta
        d = self.d_guess  # initialize the distance to the approximate (from config_dict
        rs = [-self.jog_angle, self.jog_angle]
        
        # jog the camera back and forth r degrees, rotating about a point dist away
        CR_diff_last = self._jogged_cr_difference(d, rs, self.x_image_axis)

        if CR_diff_last < 0:
            d += delta
        else:
            d -= delta

        CR_diff = self._jogged_cr_difference(d, rs, self.x_image_axis)

        i_max = 20  # at most, do 20 iterations
        for i in range(0, i_max):
            if abs(CR_diff) < self.cr_diff_threshold:
                # good enough, break
                break
            
            # recompute how much delta to move
            slope = (CR_diff - CR_diff_last) / delta
            delta = - CR_diff / slope
            
            d += delta
            
            CR_diff_last = CR_diff
            
            # jog the camera again
            CR_diff = self._jogged_cr_difference(d, rs, self.x_image_axis)

        return
    

    def align_pupil_and_CR(self):
        """ Vary the angle of rotation of the camera, untill the CR and the pupil are horizontally aligned. 
        
            This is achieved with an adaptive search loop that stops when the difference 
            between the x coordinate of the CR and pupil is smallenough or a maximum # of loops 
            are executed.
            
            Side effects: camera will be moved so that the CR and pupil are on top of each other
        """
        
        # 1. Turn on the top LED, turn off the side LED
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
                
        # 2. Adaptively optimize (this actually moves the stages) 
        range = [-20., 20.]
        objective_function = lambda x: abs(self._jogged_pupil_cr_difference(self.d, x, self.x_image_axis))
        r = scipy.optimize.fminbound(objective_function, range[0], range[1], (), self.cr_diff_threshold, 30)
       
        # 3. Move the camera in the final position with pupil and CR aligned
        self.d, reversal_function = self.stages.composite_rotation_relative(self.d, r)
        
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]
        
        print("=====================================")
        print "Final CR position =", cr_pos
        print "Final Pupil position =", pupil_pos
        print("D = ", self.d)
        print("=====================================")
        
        return
        
        
    def align_pupil_and_CR_manual(self, r):
        
        # 1. Turn on the top LED, turn off the side LED
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        
        self.d, reversal_function = self.stages.composite_rotation_relative(self.d, r)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]
        
        self.pupil_cr_diff = cr_pos[self.x_image_axis] - pupil_pos[self.x_image_axis]
        print "cr pos =", cr_pos[self.x_image_axis], "pupil pos =", pupil_pos[self.x_image_axis]
        print "DIFFERENCE CR - PUPIL =", self.pupil_cr_diff
        
        
        
    def find_pupil_radius(self):
        """
            Compute Rp, the distance from the center of the corneal curvature to the pupil
            
            This is accomplished by rotating the camera around the eye and measuring the image displacement
            of the stationary pupil
            
            Side effects: self.Rp is set to the computer Radius of the pupil's rotation about the center of
            the corneal curvature
        """
        
        # 1. Turn on the top LED, turn off the side LED
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        
        # 1.b Take one measurement at the zero angle
        features = self.acquire_averaged_features(self.n_calibration_samples)
        pupil_pos_0 = features["pupil_position"]
        
        # 2. Take measurements of x displacement while moving camera
        #    This is sort of like "manually" rotating the eye, since, at this
        #    point in the calibration we are able to rotate the camera about the 
        #    center of the eye
        n_angle_samples = 5
        x_displacements = []
        pup_radiuses = []
        rs = linspace(-self.jog_angle, self.jog_angle, n_angle_samples)
        
        # precompute the movements so that we can make them faster and in succession
        precomputed_motions = []
        true_distances = []
        for r in rs:
            motion_func, d_new = self.stages.precompute_composite_rotation_relative(self.d, r)
            precomputed_motions.append(motion_func)
            true_distances.append(d_new)
        return_motion = self.stages.precompute_return_motion()
        
        for i in range(0, len(precomputed_motions)):
            precomputed_motion = precomputed_motions[i]
            distance = true_distances[i]
            print "-----> distance =", distance
            
            # take one measurement
            precomputed_motion()
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos = features["cr_position"]
            pupil_pos = features["pupil_position"]
                        
            relative_magnification = distance / self.d
            #relative_magnification = 1.
            #relative_magnification = 1.012
            print "relative_magnification =", relative_magnification

            displacement = (cr_pos[self.x_image_axis] - pupil_pos[self.x_image_axis]) * relative_magnification
            x_displacements.append(displacement)
            pup_radiuses.append(features["pupil_radius"] / relative_magnification)
        
        return_motion()
        
      
        # 3. We now need to take a measurement to see how far off of the
        #    "equator" the pupil currently is.
        #    To do this, we'll turn on the "side" LED
        self.leds.turn_off(self.top_led)
        self.leds.turn_on(self.side_led)
        
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]
        
        y_displacement = pupil_pos[self.y_image_axis] - cr_pos[self.y_image_axis]
        
        # Save the position of the CR spot with the light on the side: this is the y coordinate of the equator
        self.y_equator = cr_pos[self.y_image_axis]
        
        
        # Now compute the Rp, based on the displacements
        self.Rp = self._compute_Rp(x_displacements, radians(rs), y_displacement)
        	    
        
                
        print("=====================================")
        print("Rp = ", self.Rp)
        print("=====================================")
        
        # 4. Turn back on the top LED to prepare for eye tracking
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        # Save the final y value of the CR as a reference to measure how much y displacement we get during eye tracking
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        self.y_topCR_ref = cr_pos[self.y_image_axis]
        
        #pupil_radius = features["pupil_radius"]
        
        print pup_radiuses
        pupil_radius = mean(pup_radiuses)
        
        cornea_curvature_radius = sqrt( pupil_radius**2 + self.Rp**2 )
        print("================== EYE MEASUREMENTS IN PIXELS ===================")
        print("pupil size = ", pupil_radius)
        print("Rp = ", self.Rp)
        print("Cornea curvature radius = ", cornea_curvature_radius)
        print("=====================================")
        
        print("================== EYE MEASUREMENTS IN MM ===================")
        print("pupil size = ", pupil_radius/self.pixels_per_mm)
        print("Rp = ", self.Rp/self.pixels_per_mm)
        print("Cornea curvature radius = ", cornea_curvature_radius/self.pixels_per_mm)
        print("=====================================")
        return
     
    def _compute_Rp(self, x_displacements, angle_displacements, y_displacement):
        # compute "Rp_prime", which is the "in-plane" Rp, which doesn't
        # take into account that the pupil may not currently be on the 
        # eye's "equator"
        p0 = (6.0, radians(0))
        leastsq_results = scipy.optimize.leastsq(self.residuals_sine, p0, (x_displacements, angle_displacements)) 
        p = leastsq_results[0]
        Rp_prime = p[0]
        angle_offset = p[1]

        print("Rp_prime = %g" % Rp_prime)
        print("Angle Offset = %g" % angle_offset) 
        
        # now correct Rp taking this vertical offset into account
        return sqrt( Rp_prime**2 + y_displacement**2 );

        
    def residuals_sine(self, p, y, x): 
        A,theta = p 
        err = y - A*sin(x+theta) 
        return err 
    
    
    def find_center_camera_frame(self):
        
        zoom_step = 60
        
        # 1) Measure the CR position (top and side) at the current zoom level
        
        # Turn on the top LED and take one measurement
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_top = features["cr_position"]
        # Turn on the side LED and take another measurement
        self.leds.turn_off(self.top_led)
        self.leds.turn_on(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_side = features["cr_position"]
        
        print "INITIAL ZOOM"
        print "CR top =", cr_pos_top
        print "CR side =", cr_pos_side
        
        # 2) Change the focus and measure again the CR position (top and side)
        self.focus_and_zoom.zoom_relative(zoom_step)
        # Turn on the top LED and take one measurement
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_top_zoom = features["cr_position"]
        # Turn on the side LED and take another measurement
        self.leds.turn_off(self.top_led)
        self.leds.turn_on(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_side_zoom = features["cr_position"]
        
        print "FINAL ZOOM"
        print "CR top =", cr_pos_top_zoom
        print "CR side =", cr_pos_side_zoom
        
        # Find the straight lines through the pairs of top and side CR values
        m_top = (cr_pos_top_zoom[0] - cr_pos_top[0]) / (cr_pos_top_zoom[1] - cr_pos_top[1])
        p_top = cr_pos_top[0] - m_top * cr_pos_top[1]
        m_side = (cr_pos_side_zoom[0] - cr_pos_side[0]) / (cr_pos_side_zoom[1] - cr_pos_side[1])
        p_side = cr_pos_side[0] - m_side * cr_pos_side[1]
        
        # Find the intersection of the lines
        x_cross = (p_side - p_top) / (m_top - m_side)
        y_cross = p_top + m_top * x_cross
        
        self.center_camera_frame = array( [y_cross, x_cross] )
        print "CENTER OF THE CAMERA FRAME =", self.center_camera_frame
        
        
    def fit_pupil_radius_size(self):
        """
            Repeat the computation of Rp for different intensities of the visible light (i.e., puil sizes)
            
            A linear fit between measured Rps and pupil sizes is performed to obtain the relationship
            between these variables.
        """
        
        pass




# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  class: CompensateLensDistorsion  @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 
class CompensateLensDistorsion:
    
    # ==================================== method: __init__ ========================================
    def __init__( self ):
        
        #-- Focal length:
        self.fc = matrix( [ 6599.034515358368481, 7284.138084589575556 ] ).transpose();

        #-- Principal point:
        self.cc = matrix( [ 329.000000000000000, 246.500000000000000 ] ).transpose();

        #-- Skew coefficient:
        self.alpha_c = 0.000000000000000;

        #-- Distortion coefficients:
        self.kc = matrix( [ -15.229429242857810, 3684.210775878747427, -0.244109807331619, 0.153912004435507, 0.000000000000000 ] ).transpose();
        
        self.quiet = True
        
        
    # ==================================== method: test ========================================
    def test( self, FileName ):
        
        im = Image.open(FileName)        
        X, Y = meshgrid( arange(5,650,25), arange(5,490,25))
        X.shape = ( 1, X.shape[0]*X.shape[1])
        Y.shape = ( 1, Y.shape[0]*Y.shape[1])
        
        x_kk = vstack(  (X, Y) )
        print 'x_kk shape =', x_kk.shape
        
        # Recover normalized coordinates (use default calibration parameters)
        xn = self.normalize( x_kk, None )
        print 'xn shape =', xn.shape
        
        
        # Transform them into pixels
        x_pix = self.map_cameraframe2pix( xn )
        print 'x_pix shape =', x_pix.shape
        
        # Display result
        figure();
        imshow(im);
        hold('on')
        plot( x_kk[0,:], x_kk[1,:], 'xr')
        plot( x_pix[0,:], x_pix[1,:], 'og')
        
        
    # ==================================== method: normalize ========================================
    def normalize( self, x_kk, calib_params ):
        """
            Computes the normalized coordinates xn given the pixel coordinates x_kk
            and the intrinsic camera parameters fc, cc and kc.
        
            INPUT: x_kk: Feature locations on the images
                   fc: Camera focal length
                   cc: Principal point coordinates
                   kc: Distortion coefficients
                   alpha_c: Skew coefficient
        
            OUTPUT: xn: Normalized feature locations on the image plane (a 2XN matrix)
        
            Important methods called within that program:
        
            comp_distortion_oulu: undistort pixel coordinates.
        """
        
        if calib_params is not None:
            if('alpha_c' not in calib_params or calib_params['alpha_c'] is None):
                self.alpha_c = 0
            if('kc' not in calib_params or calib_params['kc'] is None):
                self.kc = matrix([0,0,0,0,0]).transpose()
            if('cc' not in calib_params or calib_params['cc'] is None):
                self.cc = matrix([0,0]).transpose()
            if('cc' not in calib_params or calib_params['cc'] is None):
                self.fc = matrix([1,1]).transpose()
        
        # First: Subtract principal point, and divide by the focal length:
        x_distort = array( [ (x_kk[0,:] - self.cc[0,0])/self.fc[0,0], (x_kk[1,:] - self.cc[1,0])/self.fc[1,0] ] )
        
        # Second: undo skew
        x_distort[0,:] = x_distort[0,:] - self.alpha_c * x_distort[1,:]
        
        if linalg.norm(self.kc) is not 0:
        	# Third: Compensate for lens distortion:
        	xn = self.comp_distortion_oulu( x_distort, self.kc )
        else:
            xn = x_distort;
        
        return xn
        
        
    # ==================================== method: comp_distortion_oulu ========================================
    def comp_distortion_oulu( self, xd, k ):
        """
            Compensates for radial and tangential distortion. Model From Oulu university.
            For more informatino about the distortion model, check the forward projection mapping function:
            project_points.m
        
            INPUT: xd: distorted (normalized) point coordinates in the image plane (2xN matrix)
                   k: Distortion coefficients (radial and tangential) (4x1 vector)
        
            OUTPUT: x: undistorted (normalized) point coordinates in the image plane (2xN matrix)
        
            Method: Iterative method for compensation.
        
            NOTE: This compensation has to be done after the subtraction
                  of the principal point, and division by the focal length.
        """
        
        # k has has only one element
        if k.shape[0] == 1:

            radius_2 = sum(xd**2,0)
            radial_distortion = 1 + ones((2,1)) * (k * radius_2)
            radius_2_comp = (xd[0,:]**2 + xd[1,:]**2) / radial_distortion[0,:]
            radial_distortion = 1 + ones((2,1)) * (k2 * radius_2_comp)
            x = xd / radial_distortion

        # k has more than one element
        else:

            k1 = k[0,0];
            k2 = k[1,0];
            k3 = k[4,0];
            p1 = k[2,0];
            p2 = k[3,0];

            # initial guess
            x = xd; 				

            for kk in arange(0,20):
                r_2 = sum(x**2,0)
                k_radial =  1 + k1 * r_2 + k2 * r_2**2 + k3 * r_2**3
                delta_x = array( [ 2*p1*x[0,:]*x[1,:] + p2*(r_2 + 2*x[0,:]**2), p1 * (r_2 + 2*x[1,:]**2)+2*p2*x[0,:]*x[1,:] ] )
                x = (xd - delta_x) / (ones((2,1))*k_radial)
                
        return x


    # ==================================== method: map_cameraframe2pix ========================================
    def map_cameraframe2pix( self, xn ):
        """
            Map back from camera frame normalized coordinates to pixels
        """

        D = array( [ [self.fc[0,0], 0], [0, self.fc[1,0]] ] )
        Uo = array( [ [self.cc[0,0], 0], [0, self.cc[1,0]] ] )
        
        if not self.quiet:
            print 'D shape =', D.shape
            print 'xn shape =', xn.shape
            print 'D*xn shape =', dot(D,xn).shape
            print 'Uo*ones shape =', dot(Uo, ones( (2,xn.shape[1]) ) ).shape
         
        x_pix = dot(D,xn) + dot( Uo, ones( (2,xn.shape[1]) ) )
        
        if not self.quiet:
            print 'x_pix shape =', x_pix.shape
        
        return x_pix
        
        
    # ==================================== method: fully_compensate ========================================
    def fully_compensate( self, x_kk, calib_params ):
        """
            Do the full compensation of lens distorsion:
            x_kk -> xn -> x_pix
        """

        # Recover normalized coordinates (x_kk -> xn)
        xn = self.normalize( x_kk, None )        
        
        # Transform them into pixels (xn -> x_pix)
        x_pix = self.map_cameraframe2pix( xn )

        return x_pix

        