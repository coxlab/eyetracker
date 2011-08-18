#
#  eye_tracker.py
#
#  Created by David Cox on 5/25/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

import glumpy
import glumpy.atb as atb
from ctypes import *
import logging
import sys

import OpenGL.GL as gl, OpenGL.GLUT as glut

import time
import httplib

from numpy import *
from scipy import *
from matplotlib.pylab import *

from eyetracker.util import *

from eyetracker.image_processing import *
from eyetracker.camera import *
from eyetracker.led import *
from eyetracker.motion import *
from eyetracker.calibrator import *
from eyetracker.display import *

from eyetracker.settings import global_settings

from Queue import Queue, Empty


# boost.python wrapper for a MonkeyWorks interprocess conduit
mw_enabled = False

if global_settings.get("enable_mw_conduit", True):
    
    try:
        sys.path.append("/Library/Application Support/MWorks/Scripting/Python")
        import mworks.conduit as mw_conduit
        GAZE_H = 0
        GAZE_V = 1
        PUPIL_RADIUS = 2
        TIMESTAMP = 3
        GAZE_INFO = 4
        PING = 5
        mw_enabled = True
    except Exception, e:
        print("Unable to load MW conduit: %s" % e)



# class FeatureFinderAdaptor:
#         
#     def addFeatureFinder(self,ff):
#         if(not self.__dict__.has_key('ffs')):
#             self.ffs = []
#             
#         self.ffs.append(ff)
#         self.announceAll()
#         
#     def announceAll(self):
#         for key in self.ffs[0].getKeys():
#             self.willChangeValueForKey_(key)
#             self.didChangeValueForKey_(key)
#             pass
#     
#     def valueForKey_(self,key):
#         
#         if(not self.__dict__.has_key('ffs') or self.ffs == None):
#             # not out of the Nib yet
#             return
#             
#         val = self.ffs[0].getValue(key)
#         if(val == None):
#             return objc.nil
#         else:
#             return val
#         
#         
#     def setValue_forKey_(self, value, key):
#         if(not self.__dict__.has_key('ffs') or self.ffs == None):
#             # not out of the Nib yet
#             return
#         
#         for ff in self.ffs:
#             ff.setValue(key, value)
#             ff.update_parameters()
#         self.announceAll()
#     
#             
#         return
# 
#     
#     def reset_(self):
#         for ff in self.ffs:
#             ff.reset()
# 
#     
#     def pippo_(self):
#         for ff in self.ffs:
#             self.ff.reset()
# 


def calibration_step(f):
    def wrapper(self):
        self.execute_calibration_step(f(self))

    return wrapper


class EyeTrackerController:
    
    def __init__(self):
        
        self.x_set = c_float(0.5)
        self.y_set = c_float(0.5)
        self.r_set = c_float(0.5)
        
        self.zoom_step = c_float()
        self.focus_step = c_float()
        
        self.x_current = c_float()
        self.y_current = c_float()
        self.r_current = c_float()
        self.d_current = c_float()
        self.rp_current = c_float()
        self.pixels_per_mm_current = c_float()
        self.zoom_current = c_float()
        self.focus_current = c_float()
        
        self.d_cntr_set = c_float()
        self.r_cntr_set = c_float()
        
        self.r_2align_pup_cr = c_float()
        self.pupil_cr_diff = c_float()

        self.IsetCh1 = c_float()
        self.IsetCh2 = c_float()
        self.IsetCh3 = c_float()
        self.IsetCh4 = c_float()
                
        self.pupil_position_x = c_float()
        self.pupil_position_y = c_float()
        self.pupil_radius = c_float()
        self.cr_position_x = c_float()
        self.cr_position_y = c_float()

        self.pupil_only = c_float()
    
        self.gaze_azimuth = c_float()
        self.gaze_elevation = c_float()
    
        self.show_feature_map = c_bool()
    
        self.display_starburst = c_bool()
    
        self.frame_rate = c_float()
    
        self.sobel_avg = c_float()
    
        self.simulated_eye_x = c_float()
        self.simulated_eye_y = c_float()
        self.simulated_pupil_radius = c_float()

        # self.measurement_controller = objc.IBOutlet()
    
        self.feature_finder = None
    
        # self.radial_symmetry_feature_finder_adaptor = objc.IBOutlet()
        # self.starburst_feature_finder_adaptor = objc.IBOutlet()
        # self.composite_feature_finder_adaptor = objc.IBOutlet()
    
        self.camera_device = None
        self.calibrator = None
        self.mw_conduit = None
    
        # self.tracker_view = objc.IBOutlet()
        self.tracker_view = TrackerView()
        self.canvas_update_timer = None
    
        self.frame_count = 0
        self.n_frames = 0
        self.start_time = None
        self.last_time = 0
    
        self.frame_rate_accum = 0
    
        self.binning_factor = 1
        self.gain_factor = 1
    
        self.ui_queue = Queue(2)
    
        self.camera_locked = 0
        self.continuously_acquiring = 0
        
        # Added by DZ to deal with rigs without power zoom and focus
        self.no_powerzoom = False
        
        self.use_simulated = global_settings.get("use_simulated", False)
        self.use_file_for_cam = global_settings.get("use_file_for_camera", False)
        
        self.simulated_eye_x = 0.0
        self.simulated_eye_y = 0.0
        self.simulated_pupil_radius = 0.2
                
        self.display_starburst = False
    
        self.last_update_time = time.time()
    
        self.pupil_only = False
        
        self.setup_tracker()
        self.setup_gui()
        
    
    
    def shutdown(self):
        
        if(self.stages is not None):
            self.stages.disconnect()
        if(self.zoom_and_focus is not None):
            self.zoom_and_focus.disconnect()
        if(self.leds is not None):
            logging.info("Turning off LEDs")
            for i in xrange(4):
                self.leds.turn_off(i)
            self.leds = None
            #self.leds.shutdown()
        
        self.continuously_acquiring = False
        self.camera_update_timer.invalidate()
        
        time.sleep(1)
        
        self.calibrator = None
        #self.camera = None
        self.camera_device = None
        
        return True

    def simple_alert(self, title, message):
        logging.info(message) 
       

    # This is where all of the initialization takes place
    def setup_tracker(self):
        
        # -------------------------------------------------------------
        # Stages
        # -------------------------------------------------------------

        logging.info("Initializing Motion Control Subsystem (Stages)...")
        if self.use_simulated:
            esp300 = SimulatedStageController()
        else:
            esp300 = ESP300StageController("169.254.0.9", 8001)

            try:
                esp300.connect()
            except Exception as e:
                print("Attempting to restart serial bridge (this can take " +
                      "several tens of seconds)...")
                try:
                    kick_in_the_pants = httplib.HTTPConnection('169.254.0.9', 
                                                                80, timeout=5)
                    kick_in_the_pants.request("GET", "/goforms/resetUnit?")
                    time.sleep(5)
                    esp300.connect()
                    del kick_in_the_pants
                except Exception as e2:
                    self.simple_alert("Could not connect to serial bridge", 
                                      "Attempts to 'kick' the serial bridge "+
                                      "have failed.  "+
                                      "Reverting to simulated mode.")
                    esp300 = SimulatedStageController()
                    self.use_simulated = True
                    
                
        self.stages = EyeTrackerStageController(esp300)


        logging.info("Initializing Motion Control Subsystem (Focus and Zoom)")
        if self.no_powerzoom:
            esp300_2 = SimulatedStageController()
        else:
            if self.use_simulated:
                esp300_2 = SimulatedStageController()
            else:
                esp300_2 = ESP300StageController("169.254.0.9", 8002)
                esp300_2.connect()
        
        self.zoom_and_focus = FocusAndZoomController(esp300_2)

    
        self.x_current.value = self.stages.current_position(self.stages.x_axis)
        self.y_current.value = self.stages.current_position(self.stages.y_axis)
        self.r_current.value = self.stages.current_position(self.stages.r_axis)
        
        self.sobel_avg = 0
        
        self.r_cntr_set.value = 0
        self.d_cntr_set.value = 0
        
        self.zoom_step.value = 20.
        self.focus_step.value = 20.
        
        self.IsetCh1.value = 0
        self.IsetCh2.value = 0
        self.IsetCh3.value = 0
        self.IsetCh4.value = 0
        
        # Manual aligment of pupil and CR
        self.r_2align_pup_cr.value = 0
        

        # -------------------------------------------------------------
        # LED Controller
        # -------------------------------------------------------------
        logging.info("Initializing LED Control Subsystem")
        
        if(self.use_simulated):
            self.leds = SimulatedLEDController(4)
        else:
            self.leds = MightexLEDController("169.254.0.9", 8006)
            self.leds.connect()
        

        # -------------------------------------------------------------
        # Camera and Image Processing
        # -------------------------------------------------------------

        logging.info("Initializing Image Processing")       
        
        self.features = None
        self.frame_rates = []
        
       
        # set up real featutre finders (these won't be used if we use a 
        # fake camera instead)

        nworkers = 0

        if(nworkers != 0):
            
            self.feature_finder = PipelinedFeatureFinder(nworkers)
            workers = self.feature_finder.workers
            
            
            for worker in workers:

                fr_ff = worker.FastRadialFeatureFinder() # in worker process
                sb_ff = worker.StarBurstEyeFeatureFinder() # in worker process
                                
                #self.radial_symmetry_feature_finder_adaptor.addFeatureFinder(fr_ff)
                #self.starburst_feature_finder_adaptor.addFeatureFinder(sb_ff)
                
                comp_ff = worker.FrugalCompositeEyeFeatureFinder(fr_ff, sb_ff)
                #self.composite_feature_finder_adaptor.addFeatureFinder(comp_ff)
                
                worker.set_main_feature_finder(comp_ff) # create in worker process
            
            self.feature_finder.start()  # start the worker loops  
        else:
            sb_ff = SubpixelStarburstEyeFeatureFinder()
            fr_ff = FastRadialFeatureFinder()
            
            comp_ff = FrugalCompositeEyeFeatureFinder(fr_ff, sb_ff)
            
            #self.radial_symmetry_feature_finder_adaptor.addFeatureFinder(fr_ff)
            #self.starburst_feature_finder_adaptor.addFeatureFinder(sb_ff)
             
            #self.composite_feature_finder_adaptor.addFeatureFinder(comp_ff)
            self.feature_finder = comp_ff
        
        try:
            if(not self.use_file_for_cam and not self.use_simulated):
                logging.info("Connecting to Camera...")
                self.camera_device = ProsilicaCameraDevice(self.feature_finder)
                
                self.setBinning_(4)
                self.setGain_(1)
        except Exception, e:
            print "Unexpected error:", e.message
            self.use_file_for_cam = 1
        
        if self.use_file_for_cam:
            self.camera_device = FakeCameraDevice(self.feature_finder, 
                            "/Users/davidcox/Desktop/albino2/Snapshot2.bmp")
            self.camera_device.acquire_image()
        
        if self.use_simulated and self.camera_device == None:
            logging.info("Failing over to Simulated Camera")
            
            # use a POV-Ray simulated camera + a simpler feature finder 
            # that works with it
            self.camera_device = POVRaySimulatedCameraDevice(
                                            self.feature_finder, self.stages, 
                                            self.leds, -370.0, quiet = 1, 
                                            image_width=160, image_height=120)
            self.camera_device.move_eye(array([10.0, -10.0, 0.0]))
            self.camera_device.acquire_image()
            
        logging.info("Acquiring initial image")
        
        self.start_continuous_acquisition()
        
        # TODO
        #update_display_selector = objc.selector(self.updateCameraCanvas,signature='v@:')
        #self.camera_update_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.ui_interval, self, update_display_selector,None,True)
        
        self.ui_interval = 1./15
        self.start_time = time.time()
        self.last_time = self.start_time
        
        # TODO
        #self.announceCameraParameters()
        
        # calibrator
        logging.info("Creating Calibrator Object")
        if(self.use_simulated):
            r_dir = -1
            d_guess = -380
        else:
            r_dir = 1
            #d_guess = 280
            d_guess = 380
            #d_guess = 300 # use this with the rat and set d_halfrange=30
            
        self.calibrator = StahlLikeCalibrator(self.camera_device, self.stages, 
                                              self.zoom_and_focus, 
                                              self.leds, 
                                              d_halfrange=30, 
                                              ui_queue=self.ui_queue, 
                                              r_stage_direction=r_dir, 
                                              d_guess=d_guess)
        
        if(mw_enabled):
            logging.info("Instantiating mw conduit")
            self.mw_conduit = mw_conduit.IPCServerConduit("cobra1")
            print("conduit = %s" % self.mw_conduit)
        else:
            self.mw_conduit = None
        
        if(self.mw_conduit != None):
            print("Initializing conduit...")
            initialized = self.mw_conduit.initialize()
            print initialized
            if not initialized:
                print("Failed to initialize conduit")
            
            logging.info("Sending dummy data (-1000,-1000,-1000)")
            self.mw_conduit.send_data(GAZE_INFO, (-1000, -1000, -1000))
            self.mw_conduit.send_data(PING, 0)
            logging.info("Finished testing conduit")
        else:
            logging.warning("No conduit")
            
    
    def start_continuous_acquisition(self):
        logging.info("Starting continuous acquisition")
        self.continuously_acquiring = 1
        
        t = lambda: self.continuously_acquire_images()
        self.acq_thread = threading.Thread(target = t)
        self.acq_thread.start()
                
    
    def stop_continuous_acquisition(self):
        print "Stopping continuous acquisition"
        self.continuously_acquiring = 0
        time.sleep(0.5)
    
    # def announceCameraParameters(self):
    #     if(self.camera_device.__class__ == ProsilicaCameraDevice):
    #         self.willChangeValueForKey_("binning")
    #         self.didChangeValueForKey_("binning")
    #         self.willChangeValueForKey_("roiHeight")
    #         self.didChangeValueForKey_("roiHeight")
    #         self.willChangeValueForKey_("roiWidth")
    #         self.didChangeValueForKey_("roiWidth")
    #         self.willChangeValueForKey_("roiOffsetX")
    #         self.didChangeValueForKey_("roiOffsetX")
    #         self.willChangeValueForKey_("roiOffsetY")
    #         self.didChangeValueForKey_("roiOffsetY")
        
    
    # a method to actually run the camera
    # it will push images into a Queue object (in a non-blocking fashion)
    # so that the UI can have at them
    def continuously_acquire_images(self):
    
        logging.info("Started continuously acquiring")
        
        frame_rate = -1.0
        frame_number = 0
        tic = time.time()
        features = None
        gaze_azimuth = 0.0
        gaze_elevation = 0.0
        
        
        self.last_ui_put_time = time.time()
        while(self.continuously_acquiring):
            self.camera_locked = 1
            
            try:
                self.camera_device.acquire_image()
                new_features = self.camera_device.get_processed_image(self.features)
                
                if(new_features.__class__ == dict and 
                      features.__class__ == dict and 
                      "frame_number" in new_features and 
                      "frame_number" in features and 
                      new_features["frame_number"] != features["frame_number"]):
                    frame_number += 1
                    
                features = new_features
                check_interval = 100
                
                if(frame_number % check_interval == 0):
                    toc = time.time() - tic
                    frame_rate = check_interval / toc
                    logging.info("Real frame rate: %f" % (check_interval / toc))
                    if features.__class__ == dict and "frame_number" in features:
                        logging.info("frame number = %d" % features["frame_number"])
                    tic = time.time()
                    
                if(features == None):
                    logging.info("No features found... sleeping")
                    time.sleep(0.1)
                    continue
                    
                                
                if(features["pupil_position"] != None and 
                   features["cr_position"] != None):
                    
                    timestamp = features.get("timestamp", 0)
                    
                    pupil_position = features["pupil_position"]
                    cr_position = features["cr_position"]
                    
                    pupil_radius = 0.0
                    # get pupil radius in mm
                    if("pupil_radius" in features and 
                       features["pupil_radius"] != None and 
                       self.calibrator is not None and 
                       self.calibrator.pixels_per_mm is not None):
                       
                        pupil_radius = features["pupil_radius"] / self.calibrator.pixels_per_mm
                    
                    
                    if self.calibrator is not None:
                    
                        if not self.pupil_only:
                            (gaze_elevation,gaze_azimuth,calibration_status) = self.calibrator.transform(pupil_position, 
                                                          cr_position)
                        else:
                            (gaze_elevation,gaze_azimuth,calibration_status) = self.calibrator.transform(pupil_position,
                                                          None)
                            
                        if(self.mw_conduit != None):
                        
                            # TODO: add calibration status
                            self.mw_conduit.send_data(GAZE_INFO, 
                                                      (float(gaze_azimuth), 
                                                      float(gaze_elevation), 
                                                      float(pupil_radius), 
                                                      float(timestamp)));
                            
                    else:
                        if(self.mw_conduit != None):
                            pass
                    
                    # set values for the bindings GUI
                    if(frame_number % check_interval == 0):
                    
                        print gaze_azimuth
                        
                        self.pupil_position_x = pupil_position[1]
                        self.pupil_position_y = pupil_position[0]
                        self.pupil_radius = pupil_radius
                        self.cr_position_x = cr_position[1]
                        self.cr_position_y = cr_position[0]
                        self.gaze_azimuth = gaze_azimuth
                        self.gaze_elevation = gaze_elevation
                        self.frame_rate = frame_rate
                        
            except Exception, e:
                print self.camera_device
                formatted = formatted_exception()
                print formatted[0], ": "
                for f in formatted[2]:
                    print f
            
            if (time.time() - self.last_ui_put_time) > self.ui_interval:
                try:
                    self.ui_queue.put_nowait(features)
                    self.last_ui_put_time = time.time()
                except:
                    pass
            
            
        self.camera_locked = 0
        
        
        logging.info("Stopped continuous acquiring")
        return
    
    def update_tracker_view(self):
        if(self.camera_device == None):
            return
        
        try:
            features = self.ui_queue.get_nowait()
            
        except Empty, e:
            return
        
        if("frame_time" in features):
            toc = features["frame_time"]
        else:
            toc = 1
                
        if(self.show_feature_map):
            transform_im = features['transform']
            if transform_im is not None:        
                transform_im -=  min(ravel(transform_im))
                transform_im = transform_im * 255 /  max(ravel(transform_im))
                ravelled = ravel(transform_im);
                self.tracker_view.im_array = transform_im.astype(uint8)
        else:
            self.tracker_view.im_array = features['im_array']
        
        
        if 'pupil_position_stage1' in features:
            self.tracker_view.stage1_pupil_position = features['pupil_position_stage1']

        if 'cr_position_stage1' in features:
            self.tracker_view.stage1_cr_position = features['cr_position_stage1']
        
        if 'cr_radius' in features:
            self.tracker_view.cr_radius = features['cr_radius']

        if 'pupil_radius' in features:
            self.tracker_view.pupil_radius = features['pupil_radius']

        if 'pupil_position' in features:
            self.tracker_view.pupil_position = features['pupil_position']
        
        if 'cr_position' in features:
            self.tracker_view.cr_position = features['cr_position']
        

        self.tracker_view.starburst = features.get('starburst', None)
        self.tracker_view.is_calibrating = features.get('is_calibrating', False)
        
        self.tracker_view.restrict_top = features.get('restrict_top', None)
        self.tracker_view.restrict_bottom = features.get('restrict_bottom', None)
        self.tracker_view.restrict_left = features.get('restrict_left', None)
        self.tracker_view.restrict_right = features.get('restrict_right', None)
            
        # setNeedsDisplay            
        
        self.n_frames += 1
        self.frame_count += 1
        
        time_between_updates = 0.4
        
        self.frame_rate_accum += (1. / toc)
        
        self.frame_rates.append(1. / toc)
        
        time_since_last_update =  time.time() - self.last_update_time
        if(time_since_last_update > time_between_updates):
            self.last_update_time = time.time()
            #print "N Frames: ", self.frame_count
            frame_rate = mean(array(self.frame_rates))
            self.frame_rates = []
            self.frame_rate_accum = 0
            #self.frame_rate = self.n_frames / (time.time() - self.last_time)
            self.last_time = time.time()
            self.n_frames = 0
            #self.radial_symmetry_feature_finder_adaptor.announceAll()
            #self.starburst_feature_finder_adaptor.announceAll()
            if("sobel_avg" in features):
                self.sobel_avg = features["sobel_avg"]
            

    def setup_gui(self):
        print "setup gui"
        atb.init()
        self.window = glumpy.Window(900,600)
        self.manual_control_bar = atb.Bar(name="Manual", 
                                       label="Manual Controls", 
                                       help="Controls for adjusting hardware", 
                                       position=(10,10), size=(150,200))
        self.manual_control_bar.add_var("PositionSet/x", self.x_set)
        self.manual_control_bar.add_var("PositionSet/y", self.y_set)
        self.manual_control_bar.add_var("PositionSet/r", self.r_set)
        
        self.manual_control_bar.add_var("LEDs/Ch1_mA", self.IsetCh1)
        self.manual_control_bar.add_var("LEDs/Ch1_status",
                                    vtype = atb.TW_TYPE_BOOL8,
                                    getter=lambda: self.leds.status(0),
                                    setter=lambda x: self.leds.set_status(0,x))
                                        
        self.manual_control_bar.add_var("LEDs/Ch2_mA", self.IsetCh2)
        self.manual_control_bar.add_var("LEDs/Ch2_status",
                            vtype = atb.TW_TYPE_BOOL8,
                            getter=lambda: self.leds.status(1),
                            setter=lambda x: self.leds.set_status(1,x))
                            
        self.manual_control_bar.add_var("LEDs/Ch3_mA", self.IsetCh3)
        self.manual_control_bar.add_var("LEDs/Ch3_status",
                                    vtype = atb.TW_TYPE_BOOL8,
                                    getter=lambda: self.leds.status(2),
                                    setter=lambda x: self.leds.set_status(2,x))
                                    
        self.manual_control_bar.add_var("LEDs/Ch4_mA", self.IsetCh4)
        self.manual_control_bar.add_var("LEDs/Ch4_status",
                                    vtype = atb.TW_TYPE_BOOL8,
                                    getter=lambda: self.leds.status(3),
                                    setter=lambda x: self.leds.set_status(3,x))
        
        
        self.radial_ff_bar = atb.Bar(name="RadialFF", 
                                       label="Radial Symmetry Feature Finder", 
                                       help="Parameters for initial (symmetry-based) image processing", 
                                       position=(10,210), size=(150,340))
        
        self.radial_ff_bar.add_var("Blah/Bleep", self.IsetCh4)
        
        #self.manual_control_bar.add_separator("")
        # self.manual_control_bar.add_button("Quit", quit, key="ESCAPE", 
        #                                            help="Quit application")

        # Event Handlers    
        def on_init():
            self.tracker_view.prepare_opengl()
            
        def on_draw():
            self.manual_control_bar.update()
            self.window.clear()
            self.tracker_view.draw((self.window.width, self.window.height))
            
        def on_idle(dt):
            if dt < 0.02:
                return
            self.update_tracker_view()
            self.window.draw()
            
        def on_key_press(symbol, modifiers):
            if symbol == glumpy.key.ESCAPE:
                self.continuously_acquiring= False
                self.acq_thread.join()
                sys.exit()

        self.window.push_handlers(atb.glumpy.Handlers(self.window))                
        self.window.push_handlers(on_init, on_draw, on_key_press, on_idle)
        self.window.draw()
        
    def gui_mainloop(self):
        print "mainloop"
        self.window.mainloop()

    
    def set_binning(self, value):
        self.willChangeValueForKey_("binning")
        #self.binning_factor = value
        self.camera_device.camera.setAttribute("BinningX", int(value))
        self.camera_device.camera.setAttribute("BinningY", int(value))
        
        time.sleep(0.1)
    
    def get_binning(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("BinningX")
        else:
            return objc.nil

    def set_gain(self, value):
        self.willChangeValueForKey_("gain")
        self.gain_factor = value
        self.camera_device.camera.setAttribute("GainValue", int(value))
    
    def get_gain(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("GainValue")
        else:
            return objc.nil
            
    def set_roi_width_(self, value):
        self.camera_device.camera.setAttribute("Width", int(value))
        
    def get_roi_width(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("Width")
        else:
            return objc.nil
            
    def set_roi_height(self, value):
        self.camera_device.camera.setAttribute("Height", int(value))
        
    def get_roi_height(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("Height")    
        else:
            return objc.nil
            
    def set_roi_offsetX(self, value):
        self.camera_device.camera.setAttribute("RegionX", int(value))
        
    def get_roi_offsetX(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("RegionX")
        else:
            return objc.nil

    def set_roi_offsetY(self, value):
        self.camera_device.camera.setAttribute("RegionY", int(value))
        
    def get_roi_offsetY(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("RegionY")
        else:
            return objc.nil
            
    def display_noise_image(self):
        noise = random.rand(640,480)
        
    # Note of DZ based on conversation with DDC:
    # When a new IBAction is defined, wathever function/method is called within the action must be passed as an argument to 
    # "execute_calibration_step", in order to stop the continuous acquisition, deal with the threads, etc
    def execute_calibration_step(self, function):
        self.stop_continuous_acquisition()
        
        t = lambda: self.execute_and_resume_acquisition(function)
        calibrate_thread = threading.Thread(target = t)
        calibrate_thread.start()
    
    def execute_and_resume_acquisition(self, function):
        
        function()
        print "Finished calibration step"
        time.sleep(0.5)
        self.start_continuous_acquisition()
        self.read_position()


    @calibration_step
    def report_gaze(self, az=None, el=None):
        # TODO: fix for consistency
        if(self.camera_device.__class__ == POVRaySimulatedCameraDevice):
            self.camera_device.move_eye(array([self.measurement_controller.azimuth_set, self.measurement_controller.elevation_set, 0.0]))
        
        mean_az, mean_el, std_az, std_el = self.calibrator.report_set_gaze_values()
        
        self.measurement_controller.add_measurement(mean_az, mean_el, std_az, std_el,az,el)
        

    
    @calibration_step  
    def collect_gaze_set(self):
        for h in range(-15,16,5): # take this to 16, so that it actually gets to 15
            for v in range(-15,16,5):
                self.measurement_controller.azimuth_set = h
                self.measurement_controller.elevation_set = v
                self.report_gaze()
                
                time.sleep(0.25)
    
    @calibration_step
    def autofocus_(self):
        self.calibrator.autofocus()
    
    @calibration_step
    def calibrate_(self):
        self.calibrator.calibrate()
    
    @calibration_step
    def find_center_camera_frame(self):
        self.calibrator.find_center_camera_frame()
    
    @calibration_step
    def calibrate_center_horiztonal(self):
        self.calibrator.center_horizontal()
    
    @calibration_step
    def calibrate_zoom(self):
        self.calibrator.calibrate_zoom()
    
    @calibration_step
    def calibrateCenterVertical_(self):
        self.calibrator.center_vertical()
        
    @calibration_step
    def calibrate_center_depth(self):
        self.calibrator.center_depth_faster()
    
    @calibration_step
    def calibrate_align_pupil_and_cr(self):
        self.calibrator.align_pupil_and_CR()
        
    @calibration_step
    def calibrate_align_pupil_and_cr_manual_cw(self):
        try:
            r_2align_pup_cr = float(self.r_2align_pup_cr)
        except:
            return
        self.calibrator.align_pupil_and_CR_manual(r_2align_pup_cr)
        
        
    @calibration_step
    def calibrate_align_pupil_and_cr_manual_cc(self):
        
        try:
            r_2align_pup_cr = float(self.r_2align_pup_cr)
        except:
            return
        self.calibrator.align_pupil_and_CR_manual(-r_2align_pup_cr)
        
                        
    @calibration_step
    def calibrate_find_pupil_radius(self):
        self.calibrator.find_pupil_radius()        

    def go_r(self):
        self.stages.move_absolute(self.stages.r_axis, self.r_set)
        return

    def go_rel_all(self):
        try:
            x_set = float(self.x_set)
            y_set = float(self.y_set)
            r_ret = float(self.r_set)
        except:
            return
        
        self.stages.move_composite_relative((self.stages.x_axis,
                                             self.stages.y_axis,
                                             self.stages.r_axis),
                                            (self.x_set,
                                             self.y_set,
                                             self.r_set))
        return

    def go_rel_r(self):
        try:
            x_set = float(self.r_set)
        except:
            return
            
        self.stages.move_relative(self.stages.r_axis, self.r_set)
        return

    def go_rel_x(self):
        try:
            x_set = float(self.x_set)
        except:
            return
            
        self.stages.move_relative(self.stages.x_axis, x_set)
        return

    def go_rel_y(self):
        try:
            y_set = float(self.y_set)
        except:
            return
        
        self.stages.move_relative(self.stages.y_axis, y_set)
        return

    def go_x(self):
        try:
            x_set = float(self.x_set)
        except:
            return
        self.stages.move_absolute(self.stages.x_axis, x_set)
        return

    def go_y(self):
        try:
            y_set = float(self.y_set)
        except:
            return
        self.stages.move_absolute(self.stages.y_axis, self.y_set)
        return

    def home_all(self):
        self.stages.home(self.stages.x_axis)
        self.stages.home(self.stages.y_axis)
        self.stages.home(self.stages.r_axis)
        return

    def home_r(self):
        self.stages.home(self.stages.r_axis)
        return

    def home_x(self):
        self.stages.home(self.stages.x_axis)
        return

    def home_y(self):
        self.stages.home(self.stages.y_axis)
        return

    def focus_plus(self):
        self.zoom_and_focus.focus_relative(self.focus_step)
    
    def focus_minus(self):
        self.zoom_and_focus.focus_relative(-float(self.focus_step))
    
    def zoom_plus(self):
        self.zoom_and_focus.zoom_relative(self.zoom_step)
    
    def zoom_minus(self):
        self.zoom_and_focus.zoom_relative(-float(self.zoom_step))

    def off_ch1(self):
        self.leds.turn_off(self.leds.channel1)
        return

    def off_ch2(self):
        self.leds.turn_off(self.leds.channel2)
        return

    def off_ch3(self):
        self.leds.turn_off(self.leds.channel3)
        return

    def off_ch4(self):
        self.leds.turn_off(self.leds.channel4)
        return

    def on_ch1(self):
        self.leds.turn_on(self.leds.channel1, float(self.IsetCh1))
        return

    
    def on_ch2(self):
        self.leds.turn_on(self.leds.channel2, float(self.IsetCh2))
        return

    
    def on_ch3(self):
        self.leds.turn_on(self.leds.channel3, float(self.IsetCh3))
        return

    
    def on_ch4(self):
        self.leds.turn_on(self.leds.channel4, float(self.IsetCh4))
        return

    
    def set_manual_calibration_(self):
        print "a"
        if self.pixels_per_mm_current is None:
            if self.calibrator.pixels_per_mm is None:
                self.calibrator.pixels_per_mm = 0.0
            self.pixels_per_mm_current = self.calibrator.pixels_per_mm
        else:
            self.calibrator.pixels_per_mm = self.pixels_per_mm_current
    
        
        print "b"        
        self.calibrator.d = self.d_current
        
        print "c"

        self.calibrator.Rp = self.rp_current * self.pixels_per_mm_current
        
    
    
    def read_pos(self):
        self.x_current = self.stages.current_position(self.stages.x_axis)
        self.y_current = self.stages.current_position(self.stages.y_axis)
        self.r_current = self.stages.current_position(self.stages.r_axis)
        

        
        self.focus_current = self.zoom_and_focus.current_focus()
        self.zoom_current = self.zoom_and_focus.current_zoom()
#        if(self.calibrator.calibrated):
        self.d_current = self.calibrator.d
        self.pixels_per_mm_current = self.calibrator.pixels_per_mm
        if self.calibrator.Rp is not None and self.calibrator.pixels_per_mm is not None:
            self.rp_current = self.calibrator.Rp / self.calibrator.pixels_per_mm
        self.pupil_cr_diff = self.calibrator.pupil_cr_diff
        
        return

    
    def rot_about_abs(self):
        self.stages.composite_rotation_absolute(self.d_cntr_set, self.r_cntr_set)
        return

    
    def rot_about_rel_(self,):
        self.stages.composite_rotation_relative(self.d_cntr_set, self.r_cntr_set)
        return

    
    def go_all(self): 
        self.stages.move_composite_absolute((self.stages.x_axis,
                                             self.stages.y_axis,
                                             self.stages.r_axis),
                                            (self.x_set,
                                             self.y_set,
                                             self.r_set))
   
    
    def up(self):
        try:
            y_set = float(self.y_set)
        except:
            return
        
        self.stages.move_relative(self.stages.y_axis, y_set)
    
    
    def down(self):
        try:
            y_set = float(self.y_set)
        except:
            return
        
        self.stages.move_relative(self.stages.y_axis, -y_set)
    
    
    def left(self):
        try:
            x_set = float(self.x_set)
        except:
            return
        
        self.stages.move_relative(self.stages.x_axis, x_set)
    
    
    def right(self):
        try:
            x_set = float(self.x_set)
        except:
            return
        
        self.stages.move_relative(self.stages.x_axis, -x_set)
    
    
    def clockwise(self):
        try:
            r_set = float(self.r_set)
        except:
            return
        
        self.stages.move_relative(self.stages.r_axis, r_set)

    
    def counterclockwise(self):
        try:
            r_set = float(self.r_set)
        except:
            return
        
        self.stages.move_relative(self.stages.r_axis, -r_set)
    
    
    
    def move_simulated_eye(self):
        print("moving fake eye to: (%f, %f, 0.0)" % (self.simulated_eye_x, self.simulated_eye_y))
        if(self.camera_device.__class__ == POVRaySimulatedCameraDevice):
            self.camera_device.move_eye(array([self.simulated_eye_x, self.simulated_eye_y, 0.0]))
            self.camera_device.set_pupil_radius(self.simulated_pupil_radius)
            
    
    def auto_validate(self):
        vs = linspace(-15., 15., 3)
        hs = vs
        
        for v in vs:
            for h in hs:
                self.camera_device.move_eye(array([v, h, 0.0]))
                self.report_gaze(h,v)
        
if __name__ == "__main__":
    
    et = EyeTrackerController()
    
    print "ready"
    et.gui_mainloop()
    
    # gui_thread = threading.Thread(target = et.gui_mainloop)
    #     gui_thread.start()
    