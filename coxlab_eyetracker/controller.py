#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ctypes import *
import logging
import sys

import time
import httplib

from numpy import *
from scipy import *

from coxlab_eyetracker.util import *

from coxlab_eyetracker.image_processing import *
from coxlab_eyetracker.camera import *
from coxlab_eyetracker.led import *
from coxlab_eyetracker.motion import *
from coxlab_eyetracker.calibrator import *
from settings import global_settings

# load settings
loaded_config = load_config_file('~/.eyetracker/config.ini')
global_settings.update(loaded_config)

print global_settings

# boost.python wrapper for a MWorks interprocess conduit, if you're into
# that sort of thing
mw_enabled = False

if global_settings.get('enable_mw_conduit', True):

    try:
        sys.path.append('/Library/Application Support/MWorks/Scripting/Python')
        import mworks.conduit as mw_conduit
        GAZE_INFO = 100
        TRACKER_INFO = 101
        mw_enabled = True
    except Exception, e:
        print 'Unable to load MW conduit: %s' % e


# A decorator for calibration steps (stop continuous execution, resume on ret.)

def calibration_step(f):

    def wrapper(self):
        self.execute_calibration_step(f)

    return wrapper


# A catch-all class for controlling the eyetracking hardware

class EyeTrackerController(object):

    def __init__(self):

        self.test_binning = 3

        self.x_set = 0.5
        self.y_set = 0.5
        self.r_set = 0.5

        self.zoom_step = 20.
        self.focus_step = 20.

        self.x_current = 0.0
        self.y_current = 0.0
        self.r_current = 0.0
        self.d_current = 0.0
        self.rp_current = 0.0
        self.pixels_per_mm_current = 0.0
        self.zoom_current = 0.0
        self.focus_current = 0.0

        self.d_cntr_set = 0.0
        self.r_cntr_set = 0.0

        self.r_2align_pup_cr = None
        self.pupil_cr_diff = None

        self.IsetCh1 = 0.0
        self.IsetCh2 = 0.0
        self.IsetCh3 = 0.0
        self.IsetCh4 = 0.0

        self.pupil_position_x = 0.0
        self.pupil_position_y = 0.0
        self.pupil_radius = 0.0
        self.cr_position_x = 0.0
        self.cr_position_y = 0.0

        self.pupil_only = False

        self.gaze_azimuth = 0.0
        self.gaze_elevation = 0.0
        self.calibration_status = 0

        self.sobel_avg = 0.0

        self.simulated_eye_x = 0.0
        self.simulated_eye_y = 0.0
        self.simulated_pupil_radius = 0.2

        self.binning_factor = 1
        self.gain_factor = 1.

        # Added by DZ to deal with rigs without power zoom and focus
        self.no_powerzoom = False

        self.pupil_only = False

        self.feature_finder = None

        self.camera_device = None
        self.calibrator = None
        self.mw_conduit = None

        self.canvas_update_timer = None

        self.ui_queue = Queue(2)

        self.camera_locked = 0
        self.continuously_acquiring = 0

        self.calibrating = False

        self.use_simulated = global_settings.get('use_simulated', False)
        self.use_file_for_cam = global_settings.get('use_file_for_camera',
                False)

        # -------------------------------------------------------------
        # Stages
        # -------------------------------------------------------------

        logging.info('Initializing Motion Control Subsystem (Stages)...')
        if self.use_simulated:
            esp300 = SimulatedStageController()
        else:
            esp300 = ESP300StageController('169.254.0.9', 8001)

            try:
                esp300.connect()
            except Exception as E:
                print str(E)
                print 'Attempting to restart serial bridge (this can take ' \
                    + 'several tens of seconds)...'
                try:
                    kick_in_the_pants = httplib.HTTPConnection('169.254.0.9',
                            80, timeout=5)
                    kick_in_the_pants.request('GET', '/goforms/resetUnit?')
                    time.sleep(5)
                    esp300.connect()
                    del kick_in_the_pants
                except Exception:
                    self.simple_alert('Could not connect to serial bridge',
                                      "Attempts to 'kick' the serial bridge "
                                      + 'have failed.  '
                                      + 'Reverting to simulated mode.')
                    esp300 = SimulatedStageController()
                    self.use_simulated = True

        self.stages = EyeTrackerStageController(esp300)

        logging.info('Initializing Motion Control Subsystem (Focus and Zoom)')
        if self.no_powerzoom:
            esp300_2 = SimulatedStageController()
        else:
            if self.use_simulated:
                esp300_2 = SimulatedStageController()
            else:
                esp300_2 = ESP300StageController('169.254.0.9', 8002)
                esp300_2.connect()

        self.zoom_and_focus = FocusAndZoomController(esp300_2)

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

        # -------------------------------------------------------------
        # LED Controller
        # -------------------------------------------------------------
        logging.info('Initializing LED Control Subsystem')

        if self.use_simulated:
            self.leds = SimulatedLEDController(4)
        else:
            self.leds = MightexLEDController('169.254.0.9', 8006)
            self.leds.connect()

        # -------------------------------------------------------------
        # Camera and Image Processing
        # -------------------------------------------------------------

        logging.info('Initializing Image Processing')

        self.features = None
        self.frame_rates = []

        # set up real featutre finders (these won't be used if we use a
        # fake camera instead)

        nworkers = 0

        self.radial_ff = None
        self.starburst_ff = None

        if nworkers != 0:

            self.feature_finder = PipelinedFeatureFinder(nworkers)
            workers = self.feature_finder.workers

            for worker in workers:

                fr_ff = worker.FastRadialFeatureFinder()  # in worker process
                sb_ff = worker.StarBurstEyeFeatureFinder()  # in worker process

                self.radial_ff = fr_ff
                self.starburst_ff = sb_ff
                # self.radial_symmetry_feature_finder_adaptor.addFeatureFinder(fr_ff)
                # self.starburst_feature_finder_adaptor.addFeatureFinder(sb_ff)

                comp_ff = worker.FrugalCompositeEyeFeatureFinder(fr_ff, sb_ff)
                # self.composite_feature_finder_adaptor.addFeatureFinder(comp_ff)

                worker.set_main_feature_finder(comp_ff)  # create in worker process

            self.feature_finder.start()  # start the worker loops
        else:
            sb_ff = SubpixelStarburstEyeFeatureFinder()
            fr_ff = FastRadialFeatureFinder()

            comp_ff = FrugalCompositeEyeFeatureFinder(fr_ff, sb_ff)

            self.radial_ff = fr_ff
            self.starburst_ff = sb_ff

            self.feature_finder = comp_ff

        if True:
        # try:
            if not self.use_file_for_cam and not self.use_simulated:
                logging.info('Connecting to Camera...')
                self.camera_device = ProsilicaCameraDevice(self.feature_finder)

                self.binning = 4
                self.gain = 1
        # except Exception, e:
        #             print "Unexpected error:", e.message
        #             self.use_file_for_cam = 1

        if self.use_file_for_cam:
            self.camera_device = FakeCameraDevice(self.feature_finder,
                    '/Users/davidcox/Desktop/albino2/Snapshot2.bmp')
            self.camera_device.acquire_image()

        if self.use_simulated and self.camera_device == None:
            logging.info('Failing over to Simulated Camera')

            # use a POV-Ray simulated camera + a simpler feature finder
            # that works with it
            self.camera_device = POVRaySimulatedCameraDevice(
                self.feature_finder,
                self.stages,
                self.leds,
                -370.0,
                quiet=1,
                image_width=160,
                image_height=120,
                )
            self.camera_device.move_eye(array([10.0, -10.0, 0.0]))
            self.camera_device.acquire_image()

        logging.info('Acquiring initial image')

        self.start_continuous_acquisition()

        self.ui_interval = 1. / 15
        self.start_time = time.time()
        self.last_time = self.start_time

        # calibrator
        logging.info('Creating Calibrator Object')
        if self.use_simulated:
            r_dir = -1
            d_guess = -380
        else:
            r_dir = 1
            # d_guess = 280
            d_guess = 380
            # d_guess = 300 # use this with the rat and set d_halfrange=30

        self.calibrator = StahlLikeCalibrator(
            self.camera_device,
            self.stages,
            self.zoom_and_focus,
            self.leds,
            d_halfrange=30,
            ui_queue=self.ui_queue,
            r_stage_direction=r_dir,
            d_guess=d_guess,
            )

        if mw_enabled:
            logging.info('Instantiating mw conduit')
            self.mw_conduit = mw_conduit.IPCServerConduit('cobra1')
            print 'conduit = %s' % self.mw_conduit
        else:
            self.mw_conduit = None

        if self.mw_conduit != None:
            print 'Initializing conduit...'
            initialized = self.mw_conduit.initialize()
            print initialized
            if not initialized:
                print 'Failed to initialize conduit'

            logging.info('Sending dummy data (-1000,-1000,-1000)')
            self.mw_conduit.send_data(GAZE_INFO, (-1000, -1000, -1000))
            logging.info('Finished testing conduit')
        else:
            logging.warning('No conduit')

    def release(self):
        #print "Controller has %i refs" % sys.getrefcount(self)
        #self.camera_device.release()
        #print "Controller has %i refs" % sys.getrefcount(self)
        #self.stages.release()
        #print "Controller has %i refs" % sys.getrefcount(self)
        #self.zoom_and_focus.release()
        print "Controller has %i refs" % sys.getrefcount(self)
        self.calibrator.release()
        print "Controller has %i refs" % sys.getrefcount(self)

    def __del__(self):
        print "controller.__del__ called"
        sys.stdout.flush()

    def shutdown(self):

        if self.stages is not None:
            self.stages.disconnect()
        if self.zoom_and_focus is not None:
            self.zoom_and_focus.disconnect()
        if self.leds is not None:
            logging.info('Turning off LEDs')
            for i in xrange(4):
                self.leds.turn_off(i)
            self.leds = None
            # self.leds.shutdown()

        self.continuously_acquiring = False
        self.stop_continuous_acquisition()

        #self.camera_update_timer.invalidate()

        time.sleep(1)

        self.camera_device.shutdown()

        self.calibrator = None
        # self.camera = None
        self.camera_device = None

        return True

    def simple_alert(self, title, message):
        logging.info(message)

    def dump_info_to_conduit(self):
        print("Dumping info to conduit")
        try:
            if not mw_enabled:
                return

            info = {'stages': self.stages.info,
                    'calibration': self.calibrator.info}

            self.mw_conduit.send_data(TRACKER_INFO, info)
        except Exception as e:
            # these are all "nice-to-haves" at this point
            # so don't risk crashing, just yet
            print("Failed to dump info: %s" % e)
            return

    def start_continuous_acquisition(self):
        self.dump_info_to_conduit()

        logging.info('Starting continuous acquisition')
        self.continuously_acquiring = 1

        t = lambda: self.continuously_acquire_images()
        self.acq_thread = threading.Thread(target=t)
        self.acq_thread.start()

    def stop_continuous_acquisition(self):
        print 'Stopping continuous acquisition'
        self.continuously_acquiring = 0
        print "Joining...", self.acq_thread.join()
        print 'Stopped'

    # a method to actually run the camera
    # it will push images into a Queue object (in a non-blocking fashion)
    # so that the UI can have at them
    def continuously_acquire_images(self):

        logging.info('Started continuously acquiring')

        frame_rate = -1.
        frame_number = 0
        tic = time.time()
        features = None
        gaze_azimuth = 0.0
        gaze_elevation = 0.0
        calibration_status = 0

        self.last_ui_put_time = time.time()
        while self.continuously_acquiring:
            self.camera_locked = 1

            try:
                self.camera_device.acquire_image()
                new_features = \
                    self.camera_device.get_processed_image(self.features)

                if new_features.__class__ == dict and features.__class__ \
                    == dict and 'frame_number' in new_features \
                    and 'frame_number' in features \
                    and new_features['frame_number'] != features['frame_number'
                        ]:
                    frame_number += 1

                features = new_features
                check_interval = 100

                if frame_number % check_interval == 0:
                    toc = time.time() - tic
                    frame_rate = check_interval / toc
                    logging.info('Real frame rate: %f' % (check_interval / toc))
                    if features.__class__ == dict and 'frame_number' \
                        in features:
                        logging.info('frame number = %d'
                                     % features['frame_number'])
                    tic = time.time()

                if features == None:
                    logging.info('No features found... sleeping')
                    time.sleep(0.1)
                    continue

                if features['pupil_position'] != None and features['cr_position'
                        ] != None:

                    timestamp = features.get('timestamp', 0)

                    pupil_position = features['pupil_position']
                    cr_position = features['cr_position']

                    pupil_radius = 0.0
                    # get pupil radius in mm
                    if 'pupil_radius' in features and features['pupil_radius'] \
                        != None and self.calibrator is not None:

                        if self.calibrator.pixels_per_mm is not None:
                            pupil_radius = features['pupil_radius'] \
                                / self.calibrator.pixels_per_mm
                        else:
                            pupil_radius = -1 * features['pupil_radius']

                    if self.calibrator is not None:

                        if not self.pupil_only:

                            (gaze_elevation, gaze_azimuth,
                             calibration_status) = \
                                self.calibrator.transform(pupil_position,
                                    cr_position)
                        else:

                            (gaze_elevation, gaze_azimuth,
                             calibration_status) = \
                                self.calibrator.transform(pupil_position, None)

                        if self.mw_conduit != None:

                            # TODO: add calibration status
                            self.mw_conduit.send_data(GAZE_INFO,
                                (float(gaze_azimuth),
                                 float(gaze_elevation),
                                 float(pupil_radius),
                                 float(timestamp),
                                 float(calibration_status),
                                 float(pupil_position[1]),
                                 float(pupil_position[0]),
                                 float(cr_position[1]),
                                 float(cr_position[0]),
                                 float(self.leds.soft_status(self.calibrator.top_led)),
                                 float(self.leds.soft_status(self.calibrator.side_led))
                                 ))
                    else:

                        if self.mw_conduit != None:
                            pass

                    # set values for the bindings GUI
                    if frame_number % check_interval == 0:

                        print gaze_azimuth

                        self.pupil_position_x = pupil_position[1]
                        self.pupil_position_y = pupil_position[0]
                        self.pupil_radius = pupil_radius
                        self.cr_position_x = cr_position[1]
                        self.cr_position_y = cr_position[0]
                        self.gaze_azimuth = gaze_azimuth
                        self.gaze_elevation = gaze_elevation
                        self.calibration_status = calibration_status
                        self.frame_rate = frame_rate
            except Exception:

                print self.camera_device
                formatted = formatted_exception()
                print formatted[0], ': '
                for f in formatted[2]:
                    print f

            if time.time() - self.last_ui_put_time > self.ui_interval:
                try:
                    self.ui_queue.put_nowait(features)
                    self.last_ui_put_time = time.time()
                except:
                    pass

        self.camera_locked = 0

        logging.info('Stopped continuous acquiring')
        return


    def get_camera_attribute(self, a):
        if self.camera_device != None and getattr(self.camera_device, 'camera',
                None) is not None and self.camera_device.camera != None:
            return self.camera_device.camera.getUint32Attribute(a)
        else:
            return 0

    def set_camera_attribute(self, a, value):
        if getattr(self.camera_device, 'camera', None) is None:
            return

        self.camera_device.camera.setAttribute(a, int(value))
        # Why is this being set twice??
        #self.camera_device.camera.setAttribute(a, int(value))

    @property
    def binning(self):
        return self.get_camera_attribute('BinningX')

    @binning.setter
    def binning(self, value):
        self.set_camera_attribute('BinningX', int(value))
        self.set_camera_attribute('BinningY', int(value))

        time.sleep(0.1)

    @property
    def gain(self):
        return self.get_camera_attribute('GainValue')

    @gain.setter
    def gain(self, value):
        self.gain_factor = value
        self.set_camera_attribute('GainValue', int(value))

    @property
    def roi_width(self):
        return self.get_camera_attribute('Width')

    @roi_width.setter
    def roi_width(self, value):
        self.set_camera_attribute('Width', int(value))

    @property
    def roi_height(self):
        return self.get_camera_attribute('Height')

    @roi_height.setter
    def roi_height(self, value):
        self.set_camera_attribute('Height', int(value))

    @property
    def roi_offset_x(self):
        return self.get_camera_attribute('RegionX')

    @roi_offset_x.setter
    def roi_offset_x(self, value):
        self.set_camera_attribute('RegionX', int(value))

    @property
    def roi_offset_y(self):
        return self.get_camera_attribute('RegionY')

    @roi_offset_y.setter
    def roi_offset_y(self, value):
        self.set_camera_attribute('RegionY', int(value))

    def execute_calibration_step(self, f, wait=False):
        if self.calibrating:
            logging.warning('Already calibrating. '
                            + 'Please wait until the curent step is finished.')
            return
        self.calibrating = True
        self.stop_continuous_acquisition()
        t = lambda: self.execute_and_resume_acquisition(f)
        calibrate_thread = threading.Thread(target=t)
        calibrate_thread.start()

        if wait:
            calibrate_thread.join()

    def execute_and_resume_acquisition(self, f):

        f(self)
        print 'Finished calibration step'
        time.sleep(0.5)
        self.start_continuous_acquisition()
        self.read_pos()
        self.calibrating = False

    def load_calibration_parameters(self, filename):
        print("Loading: %s" % filename)
        d = None
        with open(filename, 'r') as f:
            d = pkl.load(f)

        if d is None:
            logging.warning('Error loading calibration file %s' % filename)
            return False

        candidate_pixels_per_mm = d['pixels_per_mm']

        # check to see if the pixels_per_mm matches up
        if global_settings.get('check_pixels_per_mm_when_loading', False):
            logging.warning('CHECKING pixels_per_mm as sanity check')
            self.execute_calibration_step(lambda x: self.calibrator.center_horizontal(), True)
            tolerance = global_settings.get('pixels_per_mm_tolerance', 0.01)
            deviation = (abs(self.calibrator.pixels_per_mm - candidate_pixels_per_mm) / self.calibrator.pixels_per_mm)
            if  deviation > tolerance:
                logging.warning('Calibration is not consistent with apparent pixels/mm')
                logging.warning('(loaded=%f, measured=%f' % (candidate_pixels_per_mm, self.calibrator.pixels_per_mm))
                logging.warning('deviation=%f, tolerance=%f' % (deviation, tolerance))
                return False
            else:
                logging.warning('Calibration is consistent with apparent pixels/mm')
                logging.warning('(loaded=%f, measured=%f' % (candidate_pixels_per_mm, self.calibrator.pixels_per_mm))
                logging.warning('deviation=%f, tolerance=%f' % (deviation, tolerance))

        print d
        return self.calibrator.load_parameters(d)

    @property
    def calibration_file(self):
        if not getattr(self, '_calibration_file', None):
            self._calibration_file = None
        return self._calibration_file

    @calibration_file.setter
    def calibration_file(self, new_file):

        status = self.load_calibration_parameters(new_file)
        if status:
            self._calibration_file = new_file

    def save_calibration(self, filename):
        self.calibrator.save_parameters(filename)

    @calibration_step
    def report_gaze(self, az=None, el=None):
        # TODO: fix for consistency
        if self.camera_device.__class__ == POVRaySimulatedCameraDevice:
            self.camera_device.move_eye(array([self.measurement_controller.azimuth_set,
                                        self.measurement_controller.elevation_set,
                                        0.0]))

        (mean_az, mean_el, std_az, std_el) = \
            self.calibrator.report_set_gaze_values()

        self.measurement_controller.add_measurement(
            mean_az,
            mean_el,
            std_az,
            std_el,
            az,
            el,
            )

    @calibration_step
    def collect_gaze_set(self):
        for h in range(-15, 16, 5):  # take this to 16, so that it actually gets to 15
            for v in range(-15, 16, 5):
                self.measurement_controller.azimuth_set = h
                self.measurement_controller.elevation_set = v
                self.report_gaze()

                time.sleep(0.25)

    @calibration_step
    def autofocus(self):
        self.calibrator.autofocus()

    @calibration_step
    def calibrate(self):
        self.calibrator.calibrate()

    @calibration_step
    def find_center_camera_frame(self):
        self.calibrator.find_center_camera_frame()

    @calibration_step
    def calibrate_center_horizontal(self):
        self.calibrator.center_horizontal()

    @calibration_step
    def calibrate_zoom(self):
        self.calibrator.calibrate_zoom()

    @calibration_step
    def calibrate_center_vertical(self):
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
            r_set = float(self.r_set)

            self.stages.move_composite_relative((self.stages.x_axis,
                    self.stages.y_axis, self.stages.r_axis),
                    (x_set, y_set, r_set))
        except:
            pass

        return

    def go_rel_r(self):
        try:
            r_set = float(self.r_set)

            self.stages.move_relative(self.stages.r_axis, r_set)
        except:
            pass

        return

    def go_rel_x(self):
        try:
            x_set = float(self.x_set)

            self.stages.move_relative(self.stages.x_axis, x_set)
        except:
            pass
        return

    def go_rel_y(self):
        try:
            y_set = float(self.y_set)

            self.stages.move_relative(self.stages.y_axis, y_set)
        except:
            pass

        return

    def go_x(self):
        try:
            x_set = float(self.x_set)

            self.stages.move_absolute(self.stages.x_axis, x_set)
        except:
            pass
        return

    def go_y(self):
        try:
            y_set = float(self.y_set)

            self.stages.move_absolute(self.stages.y_axis, y_set)
        except:
            pass
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

    # def off_ch1(self):
    #     self.leds.turn_off(self.leds.channel1)
    #     return
    #
    # def off_ch2(self):
    #     self.leds.turn_off(self.leds.channel2)
    #     return
    #
    # def off_ch3(self):
    #     self.leds.turn_off(self.leds.channel3)
    #     return
    #
    # def off_ch4(self):
    #     self.leds.turn_off(self.leds.channel4)
    #     return
    #
    # def on_ch1(self):
    #     self.leds.turn_on(self.leds.channel1, float(self.IsetCh1))
    #     return
    #
    #
    # def on_ch2(self):
    #     self.leds.turn_on(self.leds.channel2, float(self.IsetCh2))
    #     return
    #
    #
    # def on_ch3(self):
    #     self.leds.turn_on(self.leds.channel3, float(self.IsetCh3))
    #     return
    #
    #
    # def on_ch4(self):
    #     self.leds.turn_on(self.leds.channel4, float(self.IsetCh4))
    #     return

    def set_manual_calibration_(self):
        print 'a'
        if self.pixels_per_mm_current is None:
            if self.calibrator.pixels_per_mm is None:
                self.calibrator.pixels_per_mm = 0.0
            self.pixels_per_mm_current = self.calibrator.pixels_per_mm
        else:
            self.calibrator.pixels_per_mm = self.pixels_per_mm_current

        print 'b'
        self.calibrator.d = self.d_current

        print 'c'

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
        if self.calibrator.Rp is not None and self.calibrator.pixels_per_mm \
            is not None:
            self.rp_current = self.calibrator.Rp / self.calibrator.pixels_per_mm
        self.pupil_cr_diff = self.calibrator.pupil_cr_diff

        return

    def rot_about_abs(self):
        self.stages.composite_rotation_absolute(self.d_cntr_set,
                self.r_cntr_set)
        return

    def rot_about_rel_(self):
        self.stages.composite_rotation_relative(self.d_cntr_set,
                self.r_cntr_set)
        return

    def go_all(self):
        self.stages.move_composite_absolute((self.stages.x_axis,
                self.stages.y_axis, self.stages.r_axis), (self.x_set,
                self.y_set, self.r_set))

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
        print 'moving fake eye to: (%f, %f, 0.0)' % (self.simulated_eye_x,
                self.simulated_eye_y)
        if self.camera_device.__class__ == POVRaySimulatedCameraDevice:
            self.camera_device.move_eye(array([self.simulated_eye_x,
                                        self.simulated_eye_y, 0.0]))
            self.camera_device.set_pupil_radius(self.simulated_pupil_radius)

    def auto_validate(self):
        vs = linspace(-15., 15., 3)
        hs = vs

        for v in vs:
            for h in hs:
                self.camera_device.move_eye(array([v, h, 0.0]))
                self.report_gaze(h, v)
