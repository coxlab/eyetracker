#
#  StageController.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 5/25/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#

from Foundation import *
from AppKit import *
import objc
from objc import IBAction, IBOutlet
import time
import httplib

from TrackerMeasurementController import *

from Queue import Queue, Empty

from numpy import *
from scipy import *
from matplotlib.pylab import *

from EyetrackerUtilities import *
from CobraEyeTracker import *

# boost.python wrapper for a MonkeyWorks interprocess conduit
mw_enabled = False

try:
    sys.path.append("/Library/Application Support/MonkeyWorks/Scripting/Python")
    import monkeyworks.conduit as mw_conduit
    GAZE_H = 0
    GAZE_V = 1
    PUPIL_RADIUS = 2
    TIMESTAMP = 3
    GAZE_INFO = 4
    mw_enabled = True
except Exception, e:
    print("Unable to load MW conduit: %s" % e)

# no, actually turn it off...
#mw_enabled = False

class FeatureFinderAdaptor (NSObject):
        
    def addFeatureFinder(self,ff):
        if(not self.__dict__.has_key('ffs')):
            self.ffs = []
            
        self.ffs.append(ff)
        self.announceAll()
        
    def announceAll(self):
        for key in self.ffs[0].getKeys():
            self.willChangeValueForKey_(key)
            self.didChangeValueForKey_(key)
            pass
    
    def valueForKey_(self,key):
        
        if(not self.__dict__.has_key('ffs') or self.ffs == None):
            # not out of the Nib yet
            return
            
        val = self.ffs[0].getValue(key)
        if(val == None):
            return objc.nil
        else:
            return val
        
        
    def setValue_forKey_(self, value, key):
        if(not self.__dict__.has_key('ffs') or self.ffs == None):
            # not out of the Nib yet
            return
        
        for ff in self.ffs:
            ff.setValue(key, value)
            ff.update_parameters()
        self.announceAll()
    
            
        return

    @IBAction
    def reset_(self, sender):
        for ff in self.ffs:
            ff.reset()

    @IBAction
    def pippo_(self, sender):
        for ff in self.ffs:
            self.ff.reset()


class EyeTrackerController (NSObject):


    # These are class variables because of vagaries in how PyObjC interacts 
    # with python object instantiated from Nibs
    # Consequently, there can only be one of these
    
    x_set = objc.ivar(u"x_set")
    y_set = objc.ivar(u"y_set")
    r_set = objc.ivar(u"r_set")
    
    zoom_step = objc.ivar(u"zoom_step")
    focus_step = objc.ivar(u"focus_step")
    
    x_current = objc.ivar(u"x_current")
    y_current = objc.ivar(u"y_current")
    r_current = objc.ivar(u"r_current")
    d_current = objc.ivar(u"d_current")
    rp_current = objc.ivar(u"rp_current")
    zoom_current = objc.ivar(u"zoom_current")
    focus_current = objc.ivar(u"focus_current")

    d_cntr_set = objc.ivar(u"d_cntr_rot")
    r_cntr_set = objc.ivar(u"r_cntr_rot")

    r_2align_pup_cr = objc.ivar(u"r_2align_pup_cr")
    pupil_cr_diff = objc.ivar(u"pupil_cr_diff")

    IsetCh1 = objc.ivar(u"IsetCh1")
    IsetCh2 = objc.ivar(u"IsetCh2")
    IsetCh3 = objc.ivar(u"IsetCh3")
    IsetCh4 = objc.ivar(u"IsetCh4")
    
    pupil_position_x = objc.ivar(u"pupil_position_x")
    pupil_position_y = objc.ivar(u"pupil_position_y")
    pupil_radius = objc.ivar(u"pupil_radius")
    cr_position_x = objc.ivar(u"cr_position_x")
    cr_position_y = objc.ivar(u"cr_position_y")
    
    gaze_azimuth = objc.ivar(u"gaze_azimuth")
    gaze_elevation = objc.ivar(u"gaze_elevation")
    
    show_feature_map = objc.ivar(u"show_feature_map")
    
    display_starburst = objc.ivar(u"display_starburst")
    
    frame_rate = objc.ivar(u"frame_rate")
    
    sobel_avg = objc.ivar(u"sobel_avg")
    
    simulated_eye_x = objc.ivar(u"simulated_eye_x")
    simulated_eye_y = objc.ivar(u"simulated_eye_y")
    simulated_pupil_radius = objc.ivar(u"simulated_pupil_radius")
    
    measurement_controller = objc.IBOutlet()
    
    feature_finder = None
    
    radial_symmetry_feature_finder_adaptor = objc.IBOutlet()
    starburst_feature_finder_adaptor = objc.IBOutlet()
    
    camera_device = None
    
    #calibrator = CalibratorDZ(stage_device, camera_device,  led_device)
    
    camera_canvas = objc.IBOutlet()
    
    canvas_update_timer = None
    
    frame_count = 0
    n_frames = 0
    start_time = None
    last_time = 0
    
    frame_rate_accum = 0
    
    binning_factor = 1
    gain_factor = 1
    
    ui_queue = Queue(2)
    
    camera_locked = 0
    continuously_acquiring = 0
    
    
    def applicationShouldTerminate_(self, application):
        NSLog(u"Application should terminate called...")

        if(self.stages is not None):
            self.stages.disconnect()
        if(self.zoom_and_focus is not None):
            self.zoom_and_focus.disconnect()
        if(self.leds is not None):
            self.leds = None
            #self.leds.shutdown()
        
        self.continuously_acquiring = False
        self.camera_update_timer.invalidate()
        
        time.sleep(5)
        
        self.calibrator = None
        self.camera = None
        
        return True
        
    def awakeFromNib(self):
        
        # Added by DZ to deal with rigs without power zoom and focus
        self.no_powerzoom = False
        
        self.use_simulated = False


        use_file_for_cam = False
        
        self.simulated_eye_x = 0.0
        self.simulated_eye_y = 0.0
        self.simulated_pupil_radius = 0.2
                
        self.display_starburst = False
    
        self.last_update_time = time.time()
    
        # stages
        NSLog("Initializing Motion Control Subsystem (Stages)")
        if self.use_simulated:
            esp300 = SimulatedStageController()
        else:
            esp300 = ESP300StageController("169.254.0.9", 8001)

            try:
                esp300.connect()
            except Exception as e:
                print("Restarting serial bridge")
                kick_in_the_pants = httplib.HTTPConnection('169.254.0.9', 80, timeout=10)
                kick_in_the_pants.request("GET", "/goforms/resetUnit?")
                time.sleep(5)
                esp300.connect()
                del kick_in_the_pants
                
        self.stages = EyeTrackerStageController(esp300)


        NSLog("Initializing Motion Control Subsystem (Focus and Zoom)")
        if self.no_powerzoom:
            esp300_2 = SimulatedStageController()
        else:
            if self.use_simulated:
                esp300_2 = SimulatedStageController()
            else:
                esp300_2 = ESP300StageController("169.254.0.9", 8002)
                esp300_2.connect()
        
        self.zoom_and_focus = FocusAndZoomController(esp300_2)

    
        self.x_set = 0.5
        self.y_set = 0.5
        self.r_set = 0.5
        self.x_current = self.stages.current_position(self.stages.x_axis)
        self.y_current = self.stages.current_position(self.stages.y_axis)
        self.r_current = self.stages.current_position(self.stages.r_axis)
        
        self.sobel_avg = 0
        
        self.r_cntr_set = 0
        self.d_cntr_set = 0
        
        self.zoom_step = 20.
        self.focus_step = 20.
        
        self.IsetCh1 = 0
        self.IsetCh2 = 0
        self.IsetCh3 = 0
        self.IsetCh4 = 0
        
        # Manual aligment of pupil and CR
        self.r_2align_pup_cr = 0
        
        # led controller
        NSLog("Initializing LED Control Subsystem")
        
        if(self.use_simulated):
            self.leds = SimulatedLEDController(4)
        else:
            self.leds = MightexLEDController("169.254.0.9", 8006)
            self.leds.connect()
        
        # camera and feature finders 
        NSLog("Initializing Image Processing")       
        
        self.features = None
        self.frame_rates = []
        
        #self.azimuth_set = 0.0
        #self.elevation_set = 0.0
        
        # set up real featutre finders (these won't be used if we use a fake camera instead)
        nworkers = 0
        if(nworkers != 0):
            
            self.feature_finder = PipelinedFeatureFinder(nworkers)
            workers = self.feature_finder.workers
            
            for worker in workers:
                sb_ff = worker.StarBurstEyeFeatureFinder_() # create in worker process
                fr_ff = worker.FastRadialFeatureFinder_() # create in worker process
                
                self.radial_symmetry_feature_finder_adaptor.addFeatureFinder(fr_ff)
                self.starburst_feature_finder_adaptor.addFeatureFinder(sb_ff)
                
                worker.set_main_feature_finder(worker.CompositeEyeFeatureFinder_(fr_ff, sb_ff)) # create in worker process
            
            self.feature_finder.start()  # start the worker loops  
        else:
            sb_ff = SubpixelStarburstEyeFeatureFinder()
            fr_ff = FastRadialFeatureFinder()
            
            self.radial_symmetry_feature_finder_adaptor.addFeatureFinder(fr_ff)
            self.starburst_feature_finder_adaptor.addFeatureFinder(sb_ff)
                
            self.feature_finder = CompositeEyeFeatureFinder(fr_ff, sb_ff)
        
        try:
            if(not use_file_for_cam and not self.use_simulated):
                NSLog("Connecting to Camera...")
                self.camera_device = ProsilicaCameraDevice(self.feature_finder)
                
                self.setBinning_(4)
                self.setGain_(1)
        except Exception, e:
            print "Unexpected error:", e.message
            use_file_for_cam = 1
        
        if use_file_for_cam:
            #self.camera_device = FakeCameraDevice(self.feature_finder, "/Users/davidcox/Repositories/svn.coxlab.org/eyetracking/code/EyeTracker/Snapshot.bmp")
            self.camera_device = FakeCameraDevice(self.feature_finder, "/Users/labuser/Development/eyetracking/code/EyeTracker/Snapshot.bmp")
            self.camera_device.acquire_image()
        
        if self.use_simulated and self.camera_device == None:
            NSLog("Failing over to Simulated Camera")
            
            # use a POV-Ray simulated camera + a simpler feature finder that works with it
            self.camera_device = POVRaySimulatedCameraDevice(self.feature_finder, self.stages, self.leds, -370.0, quiet = 1, image_width=160, image_height=120)
            self.camera_device.move_eye(array([10.0, -10.0, 0.0]))
            self.camera_device.acquire_image()
            
        NSLog("Acquiring initial image")
        #self.camera_device.acquire_image()
        
        self.start_continuous_acquisition()
        
        update_display_selector = objc.selector(self.updateCameraCanvas,signature='v@:')
        self.ui_interval = 1./15
        self.camera_update_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.ui_interval, self, update_display_selector,None,True)
        self.start_time = time.time()
        self.last_time = self.start_time
        
        self.announceCameraParameters()
        
        # calibrator
        NSLog("Creating Calibrator Object")
        if(self.use_simulated):
            r_dir = -1
            d_guess = -380
        else:
            r_dir = 1
            #d_guess = 280
            d_guess = 380
            #d_guess = 300 # use this with the rat and set d_halfrange=30
            
        self.calibrator = StahlLikeCalibrator(self.camera_device, self.stages, self.zoom_and_focus, self.leds, d_halfrange=30, ui_queue=self.ui_queue, r_stage_direction=r_dir, d_guess=d_guess)
        
        if(mw_enabled):
            print("Creating mw conduit")
            self.mw_conduit = mw_conduit.IPCServerConduit("cobra1")
            print("conduit = %s" % self.mw_conduit)
        else:
            self.mw_conduit = None
        
        if(self.mw_conduit != None):
            print("Initializing conduit")
            self.mw_conduit.initialize()
            self.mw_conduit.send_data(GAZE_INFO, (-1000, -1000, -1000))
        else:
            print "no conduit"
        
        
        
        
    
    def start_continuous_acquisition(self):
        print "Starting continuous acquisition"
        self.continuously_acquiring = 1
        acquire_selector = objc.selector(self.continuouslyAcquireImages,signature='v@:');
        NSThread.detachNewThreadSelector_toTarget_withObject_(acquire_selector, self, objc.nil)
        
    
    def stop_continuous_acquisition(self):
        print "Stopping continuous acquisition"
        self.continuously_acquiring = 0
        time.sleep(0.5)
    
    def announceCameraParameters(self):
        if(self.camera_device.__class__ == ProsilicaCameraDevice):
            self.willChangeValueForKey_("binning")
            self.didChangeValueForKey_("binning")
            self.willChangeValueForKey_("roiHeight")
            self.didChangeValueForKey_("roiHeight")
            self.willChangeValueForKey_("roiWidth")
            self.didChangeValueForKey_("roiWidth")
            self.willChangeValueForKey_("roiOffsetX")
            self.didChangeValueForKey_("roiOffsetX")
            self.willChangeValueForKey_("roiOffsetY")
            self.didChangeValueForKey_("roiOffsetY")
        
    
    # a method to actually run the camera
    # it will push images into a Queue object (in a non-blocking fashion)
    # so that the UI can have at them
    def continuouslyAcquireImages(self):
    
        print "Started continuously acquiring"
        pool = NSAutoreleasePool.alloc().init()

        frame_number = 0
        tic = time.time()
        features = None
        
        self.last_ui_put_time = time.time()
        while(self.continuously_acquiring):
            self.camera_locked = 1
            
            try:
                
                self.camera_device.acquire_image()
                new_features = self.camera_device.get_processed_image(self.features)
                
                if(new_features.__class__ == dict and features.__class__ == dict 
                                                  and "frame_number" in new_features
                                                  and "frame_number" in features
                                                  and new_features["frame_number"] != features["frame_number"]):
                    frame_number += 1
                features = new_features
                check_interval = 100
                if(frame_number % check_interval == 0):
                    toc = time.time() - tic
                    self.frame_rate = check_interval / toc
                    print("Real frame rate: %f" % (check_interval / toc))
                    if features.__class__ == dict and "frame_number" in features:
                        print("frame number = %d" % features["frame_number"])
                    tic = time.time()
                    
                if(features == None):
                    print("No features found... sleeping")
                    time.sleep(0.1)
                    continue
                    
                
                #features["im_array"] = self.camera_device.im_array
                #features["frame_time"] = toc
                
                if(features["pupil_position"] != None and features["cr_position"] != None):
                    
                    timestamp = features.get("timestamp", 0)
                    
                    pupil_position = features["pupil_position"]
                    cr_position = features["cr_position"]
                    
                    pupil_radius = 0.0
                    # get pupil radius in mm
                    if("pupil_radius" in features and features["pupil_radius"] != None and self.calibrator is not None and self.calibrator.pixels_per_mm is not None):
                        pupil_radius = features["pupil_radius"] / self.calibrator.pixels_per_mm
                    
                    
                    if(self.calibrator is not None and self.calibrator.calibrated):
                        #pupil_coordinates = [self.pupil_position_x, self.pupil_position_y]
                        #cr_coordinates = [self.cr_position_x, self.cr_position_y]
                        self.gaze_elevation, self.gaze_azimuth = self.calibrator.transform( pupil_position, cr_position)
                        
                        if(self.mw_conduit != None):
                            #print "filling conduit:", (float(self.gaze_azimuth), float(self.gaze_elevation), float(pupil_radius), int(timestamp))
                            self.mw_conduit.send_data(GAZE_INFO, (float(self.gaze_azimuth), float(self.gaze_elevation), float(pupil_radius), float(timestamp)));
                            
                            #self.mw_conduit.sendFloat(GAZE_H, self.gaze_elevation)
                            #self.mw_conduit.sendFloat(GAZE_V, self.gaze_azimuth)
                            pass
                    else:
                        if(self.mw_conduit != None):
                            pass
                    
                    # set values for the bindings GUI
                    if(frame_number % check_interval == 0):
                        self._.pupil_position_x = pupil_position[1]
                        self._.pupil_position_y = pupil_position[0]
                        self._.pupil_radius = pupil_radius
                        self._.cr_position_x = cr_position[1]
                        self._.cr_position_y = cr_position[0]
                        self._.gaze_azimuth = self.gaze_azimuth
                        self._.gaze_elevation = self.gaze_elevation
                        self._.frame_rate = self.frame_rate
                        
            except Exception, e:
                print e.message
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
        
        
        del pool
        print "Stopped continuous acquiring"
        return
    
    def updateCameraCanvas(self):
        if(self.camera_device == None):
            return
        
        try:
            features = self.ui_queue.get_nowait()
            
        except Empty, e:
            #self.camera_canvas.performSelectorOnMainThread_withObject_waitUntilDone_(objc.selector(self.camera_canvas.scheduleRedisplay,signature='v@:'), objc.nil, False)
            
            self.camera_canvas.setNeedsDisplay_(True)
            return
        
        if("frame_time" in features):
            toc = features["frame_time"]
        else:
            toc = 1
        
        
        
        #tic = time.time()
        #self.camera_device.acquireImage()
        #features = self.camera_device.processImage(self.features)
        #self.features = features
        #toc = time.time() - tic
        #if(self.features == None):
        #    print "No features returned by feature finder"
        #    return
        
        #features["im_array"] = self.camera_device.im_array
        
        if(self.show_feature_map):
            transform_im = features['transform']
        
            transform_im -=  min(ravel(transform_im))
            transform_im = transform_im * 255 /  max(ravel(transform_im))
            ravelled = ravel(transform_im);
            self.camera_canvas.im_array = transform_im.astype(uint8)
        else:
            self.camera_canvas.im_array = features['im_array']
        
        if('pupil_position_stage1' in features):
            self.camera_canvas.stage1_pupil_position = features['pupil_position_stage1']

        if('cr_position_stage1' in features):
            self.camera_canvas.stage1_cr_position = features['cr_position_stage1']
        
        if('cr_radius' in features):
            self.camera_canvas.cr_radius = features['cr_radius']

        if('pupil_radius' in features):
            self.camera_canvas.pupil_radius = features['pupil_radius']

        if('pupil_position' in features):
            self.camera_canvas.pupil_position = features['pupil_position']
        
        if('cr_position' in features):
            self.camera_canvas.cr_position = features['cr_position']
        
        if('starburst' in features and self.display_starburst):
            self.camera_canvas.starburst = features['starburst']
        else:
            self.camera_canvas.starburst = None
            
        if 'is_calibrating' in features:
            self.camera_canvas.is_calibrating = features['is_calibrating']
        else:
            self.camera_canvas.is_calibrating =  0
            
        self.camera_canvas.setNeedsDisplay_(True)
        #self.camera_canvas.performSelectorOnMainThread_withObject_waitUntilDone_(objc.selector(self.camera_canvas.scheduleRedisplay,signature='v@:'), objc.nil, False)
            
        self.n_frames += 1
        self.frame_count += 1
        
        time_between_updates = 0.4
        
        self.frame_rate_accum += (1. / toc)
        
        self.frame_rates.append(1. / toc)
        
        time_since_last_update =  time.time() - self.last_update_time
        if(time_since_last_update > time_between_updates):
            self.last_update_time = time.time()
            #print "N Frames: ", self.frame_count
            self.frame_rate = mean(array(self.frame_rates))
            self.frame_rates = []
            self.frame_rate_accum = 0
            #self.frame_rate = self.n_frames / (time.time() - self.last_time)
            self.last_time = time.time()
            self.n_frames = 0
            self.radial_symmetry_feature_finder_adaptor.announceAll()
            self.starburst_feature_finder_adaptor.announceAll()
            if("sobel_avg" in features):
                self.sobel_avg = features["sobel_avg"]
            

    
    def setBinning_(self, value):
        self.willChangeValueForKey_("binning")
        #self.binning_factor = value
        self.camera_device.camera.setAttribute("BinningX", int(value))
        self.camera_device.camera.setAttribute("BinningY", int(value))
        
        time.sleep(0.1)
        self.didChangeValueForKey_("binning")
    
    def binning(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("BinningX")
        else:
            return objc.nil

    def setGain_(self, value):
        self.willChangeValueForKey_("gain")
        self.gain_factor = value
        self.camera_device.camera.setAttribute("GainValue", int(value))
        self.didChangeValueForKey_("gain")
    
    def gain(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("GainValue")
        else:
            return objc.nil
            
    def setRoiWidth_(self, value):
        self.willChangeValueForKey_("roi_width")
        self.camera_device.camera.setAttribute("Width", int(value))
        self.didChangeValueForKey_("roi_width")
    
    def roiWidth(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("Width")
        else:
            return objc.nil
            
    def setRoiHeight_(self, value):
        self.willChangeValueForKey_("roi_height")
        self.camera_device.camera.setAttribute("Height", int(value))
        self.didChangeValueForKey_("roi_height")
    
    def roiHeight(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("Height")    
        else:
            return objc.nil
            
    def setRoiOffsetX_(self, value):
        self.willChangeValueForKey_("roi_offset_x")
        self.camera_device.camera.setAttribute("RegionX", int(value))
        self.didChangeValueForKey_("roi_offset_x")
    
    def roiOffsetX(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("RegionX")
        else:
            return objc.nil

    def setRoiOffsetY_(self, value):
        self.willChangeValueForKey_("roi_offset_y")
        self.camera_device.camera.setAttribute("RegionY", int(value))
        self.didChangeValueForKey_("roi_offset_y")
    
    def roiOffsetY(self):
        if(self.camera_device != None and self.camera_device.camera != None):
            return self.camera_device.camera.getUint32Attribute("RegionY")
        else:
            return objc.nil
            
    def displayNoiseImage(self):
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
        pool = NSAutoreleasePool.alloc().init()
        
        function()
        print "Finished calibration step"
        time.sleep(0.5)
        self.start_continuous_acquisition()
        del pool
        self.readPos_(objc.nil)


    def report_gaze(self, az=None, el=None):
        # TODO: fix for consistency
        if(self.camera_device.__class__ == POVRaySimulatedCameraDevice):
            self.camera_device.move_eye(array([self.measurement_controller.azimuth_set, self.measurement_controller.elevation_set, 0.0]))
        
        mean_az, mean_el, std_az, std_el = self.calibrator.report_set_gaze_values()
        
        self.measurement_controller.add_measurement(mean_az, mean_el, std_az, std_el,az,el)
        

    @IBAction
    def reportgaze_(self, sender):
        print "pippo----------------------------------------"
        self.execute_calibration_step( self.report_gaze )
    
        #features = self.execute_calibration_step( self.calibrator.acquire_averaged_features(4) )
        #cr_position = features["cr_position"]
        #pupil_position = features["pupil_position"]
        #print "pupil position in pixels =", pupil_position
        #elevation, azimuth = self.execute_calibration_step( self.calibrator.transform(pupil_position, cr_position) )
        #print "azimuth = ", azimuth
    
    @IBAction
    def collectgazeset_(self, sender):
        self.execute_calibration_step( self.collect_gaze_set_blocking )
        
        
    def collect_gaze_set_blocking(self):
        for h in range(-15,16,5): # take this to 16, so that it actually gets to 15
            for v in range(-15,16,5):
                self.measurement_controller._.azimuth_set = h
                self.measurement_controller._.elevation_set = v
                self.report_gaze()
                
                time.sleep(0.25)
    
    @IBAction
    def autofocus_(self, sender):
        self.execute_calibration_step(self.calibrator.autofocus)
    
    @IBAction
    def calibrate_(self, sender):
        self.execute_calibration_step(self.calibrator.calibrate)
    
    @IBAction
    def findCenterCameraFrame_(self, sender):
        print "CENTER CAMERA FRAME"
        self.execute_calibration_step(self.calibrator.find_center_camera_frame)
    
    @IBAction
    def calibrateCenterHoriztonal_(self, sender):
        print "CENTER HORIZONTAL"
        self.execute_calibration_step(self.calibrator.center_horizontal)
    
    @IBAction
    def calibrateZoom_(self, sender):
        print "CALIBRATE_ZOOM"
        self.execute_calibration_step(self.calibrator.calibrate_zoom)
    
    @IBAction
    def calibrateCenterVertical_(self, sender):
        print "CENTER VERTICAL"        
        self.execute_calibration_step(self.calibrator.center_vertical)
        
    @IBAction
    def calibrateCenterDepth_(self, sender):
        print "CENTER DEPTH"
        self.execute_calibration_step(self.calibrator.center_depth_faster)
    
    @IBAction
    def calibrateAlignPupilAndCR_(self, sender):
        print "ALIGN PUPIL AND CR"
        self.execute_calibration_step(self.calibrator.align_pupil_and_CR)
        
    @IBAction
    def calibrateAlignPupilAndCRmanualCW_(self, sender):
        print "MANUALLY ALIGN PUPIL AND CR"
        
        try:
            r_2align_pup_cr = float(self.r_2align_pup_cr)
        except:
            return
        self.execute_calibration_step( lambda: self.calibrator.align_pupil_and_CR_manual(r_2align_pup_cr) )
        
        
    @IBAction
    def calibrateAlignPupilAndCRmanualCC_(self, sender):
        print "MANUALLY ALIGN PUPIL AND CR"
        
        try:
            r_2align_pup_cr = float(self.r_2align_pup_cr)
        except:
            return
        self.execute_calibration_step( lambda: self.calibrator.align_pupil_and_CR_manual(-r_2align_pup_cr) )
        
                        
    @IBAction
    def calibrateFindPupilRadius_(self, sender):
        print "FIND PUPIL RADIUS"
        self.execute_calibration_step(self.calibrator.find_pupil_radius)        

    @IBAction
    def goR_(self, sender):
        self.stages.move_absolute(self.stages.r_axis, self.r_set)
        return

    @IBAction
    def goRelAll_(self, sender):
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

    @IBAction
    def goRelR_(self, sender):
        try:
            x_set = float(self.r_set)
        except:
            return
            
        self.stages.move_relative(self.stages.r_axis, self.r_set)
        return

    @IBAction
    def goRelX_(self, sender):
        try:
            x_set = float(self.x_set)
        except:
            return
            
        self.stages.move_relative(self.stages.x_axis, x_set)
        return

    @IBAction
    def goRelY_(self, sender):
        try:
            y_set = float(self.y_set)
        except:
            return
        
        self.stages.move_relative(self.stages.y_axis, y_set)
        return

    @IBAction
    def goX_(self, sender):
        try:
            x_set = float(self.x_set)
        except:
            return
        self.stages.move_absolute(self.stages.x_axis, x_set)
        return

    @IBAction
    def goY_(self, sender):
        try:
            y_set = float(self.y_set)
        except:
            return
        self.stages.move_absolute(self.stages.y_axis, self.y_set)
        return

    @IBAction
    def homeAll_(self, sender):
        self.stages.home(self.stages.x_axis)
        self.stages.home(self.stages.y_axis)
        self.stages.home(self.stages.r_axis)
        return

    @IBAction
    def homeR_(self, sender):
        self.stages.home(self.stages.r_axis)
        return

    @IBAction
    def homeX_(self, sender):
        self.stages.home(self.stages.x_axis)
        return

    @IBAction
    def homeY_(self, sender):
        self.stages.home(self.stages.y_axis)
        return

    @IBAction
    def focusPlus_(self, sender):
        self.zoom_and_focus.focus_relative(self.focus_step)
    
    @IBAction
    def focusMinus_(self, sender):
        self.zoom_and_focus.focus_relative(-float(self.focus_step))
    
    @IBAction
    def zoomPlus_(self, sender):
        self.zoom_and_focus.zoom_relative(self.zoom_step)
    
    @IBAction
    def zoomMinus_(self, sender):
        self.zoom_and_focus.zoom_relative(-float(self.zoom_step))

    @IBAction
    def offCh1_(self, sender):
        self.leds.turn_off(self.leds.channel1)
        return

    @IBAction
    def offCh2_(self, sender):
        self.leds.turn_off(self.leds.channel2)
        return

    @IBAction
    def offCh3_(self, sender):
        self.leds.turn_off(self.leds.channel3)
        return

    @IBAction
    def offCh4_(self, sender):
        self.leds.turn_off(self.leds.channel4)
        return

    @IBAction
    def onCh1_(self, sender):
        self.leds.turn_on(self.leds.channel1, float(self.IsetCh1))
        return

    @IBAction
    def onCh2_(self, sender):
        self.leds.turn_on(self.leds.channel2, float(self.IsetCh2))
        return

    @IBAction
    def onCh3_(self, sender):
        self.leds.turn_on(self.leds.channel3, float(self.IsetCh3))
        return

    @IBAction
    def onCh4_(self, sender):
        self.leds.turn_on(self.leds.channel4, float(self.IsetCh4))
        return

    @IBAction
    def readPos_(self, sender):
        self._.x_current = self.stages.current_position(self.stages.x_axis)
        self._.y_current = self.stages.current_position(self.stages.y_axis)
        self._.r_current = self.stages.current_position(self.stages.r_axis)
        
        self._.focus_current = self.zoom_and_focus.current_focus()
        self._.zoom_current = self.zoom_and_focus.current_zoom()
#        if(self.calibrator.calibrated):
        self._.d_current = self.calibrator.d
        if self.calibrator.Rp is not None and self.calibrator.pixels_per_mm is not None:
            self._.rp_current = self.calibrator.Rp / self.calibrator.pixels_per_mm
        self._.pupil_cr_diff = self.calibrator.pupil_cr_diff
        
        #else:
        #    self.d_current = objc.nil
        #    self.rp_current = objc.nil
        return

    @IBAction
    def rotAboutAbs_(self, sender):
        self.stages.composite_rotation_absolute(self.d_cntr_set, self.r_cntr_set)
        return

    @IBAction
    def rotAboutRel_(self, sender):
        self.stages.composite_rotation_relative(self.d_cntr_set, self.r_cntr_set)
        return

    @IBAction
    def goAll_(self, sender): 
        self.stages.move_composite_absolute((self.stages.x_axis,
                                             self.stages.y_axis,
                                             self.stages.r_axis),
                                            (self.x_set,
                                             self.y_set,
                                             self.r_set))
   
    @IBAction
    def up_(self, sender):
        try:
            y_set = float(self.y_set)
        except:
            return
        
        self.stages.move_relative(self.stages.y_axis, y_set)
    
    @IBAction
    def down_(self, sender):
        try:
            y_set = float(self.y_set)
        except:
            return
        
        self.stages.move_relative(self.stages.y_axis, -y_set)
    
    @IBAction
    def left_(self, sender):
        try:
            x_set = float(self.x_set)
        except:
            return
        
        self.stages.move_relative(self.stages.x_axis, x_set)
    
    @IBAction
    def right_(self, sender):
        try:
            x_set = float(self.x_set)
        except:
            return
        
        self.stages.move_relative(self.stages.x_axis, -x_set)
    
    @IBAction
    def clockwise_(self, sender):
        try:
            r_set = float(self.r_set)
        except:
            return
        
        self.stages.move_relative(self.stages.r_axis, r_set)

    @IBAction
    def counterclockwise_(self, sender):
        try:
            r_set = float(self.r_set)
        except:
            return
        
        self.stages.move_relative(self.stages.r_axis, -r_set)
    
    
    @IBAction
    def moveSimulatedEye_(self, sender):
        print("moving fake eye to: (%f, %f, 0.0)" % (self.simulated_eye_x, self.simulated_eye_y))
        if(self.camera_device.__class__ == POVRaySimulatedCameraDevice):
            self.camera_device.move_eye(array([self.simulated_eye_x, self.simulated_eye_y, 0.0]))
            self.camera_device.set_pupil_radius(self.simulated_pupil_radius)
            
    @IBAction
    def autoValidate_(self, sender):
        vs = linspace(-15., 15., 3)
        hs = vs
        
        for v in vs:
            for h in hs:
                self.camera_device.move_eye(array([v, h, 0.0]))
                self.report_gaze(h,v)
        
