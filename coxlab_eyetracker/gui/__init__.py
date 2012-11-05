#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tracker_view import *
import glumpy
import glumpy.atb as atb
from ctypes import *
from Queue import Empty
import os
import sys
import re
from coxlab_eyetracker.settings import global_settings

import logging

try:
    from collections import OrderedDict
except:
    from ordereddict import OrderedDict


# Utility functions for use with atb

def binding_getter(o, key):

    def get_wrapper():
        val = getattr(o, key)
        if val is None:
            val = 0
        return val

    return get_wrapper


def binding_setter(o, key):

    def ff_wrapper(val):
        setattr(o, key, val)
        o.update_parameters()

    def regular_wrapper(val):
        setattr(o, key, val)

    if hasattr(o, 'update_parameters') and callable(getattr(o,
            'update_parameters')):
        return ff_wrapper
    else:
        return regular_wrapper


# Do a tiny bit of trickiness to make glumpy.atb less tiresome

def new_add_var(self, name=None, value=None, **kwargs):
    t = kwargs.pop('target', None)
    p = kwargs.pop('attr', None)

    if t is not None and p is not None:
        kwargs['getter'] = binding_getter(t, p)
        kwargs['setter'] = binding_setter(t, p)
    return self.old_add_var(name, value, **kwargs)


atb.Bar.old_add_var = atb.Bar.add_var
atb.Bar.add_var = new_add_var


class EyeTrackerGUI:

    def __init__(self, c):

        self.controller = c
        self.tracker_view = TrackerView()

        self.show_feature_map = c_bool(False)
        self.display_starburst = c_bool(False)
        self.n_frames = 0
        self.frame_count = 0
        self.frame_rate_accum = 0.0
        self.frame_rates = []
        self.start_time = None
        self.last_time = 0
        self.last_update_time = time.time()

        self.calibration_file = ''

        atb.init()
        self.window = glumpy.Window(900, 600)

        # ---------------------------------------------------------------------
        #   STAGE CONTROLS
        # ---------------------------------------------------------------------

        self.gaze_bar = atb.Bar(
            name='gaze',
            label='Gaze Info',
            iconified='false',
            help='Current Gaze',
            position=(10, 10),
            size=(100, 200))

        self.gaze_bar.add_var('Gaze/Status', label='Calibration Status',
                            target=c, attr='calibration_status', readonly=True)
        self.gaze_bar.add_var('Gaze/H', label='Horizontal Gaze', target=c,
                            attr='gaze_azimuth', readonly=True)
        self.gaze_bar.add_var('Gaze/V', label='Vertical Gaze', target=c,
                            attr='gaze_elevation', readonly=True)
        self.gaze_bar.add_var('FPS', label='FPS', target=c,
                            attr='conduit_fps', readonly=True)

        self.stages_bar = atb.Bar(
            name='stages',
            label='Stage Controls',
            iconified='true',
            help='Controls for adjusting stages',
            position=(10, 10),
            size=(200, 300),
            )

        self.stages_bar.add_var('X/x_set', label='set value', target=c,
                                attr='x_set')
        self.stages_bar.add_button('go_rel_x', lambda: c.go_rel_x(), group='X',
                                   label='move relative')
        self.stages_bar.add_button('go_abs_x', lambda: c.go_x(), group='X',
                                   label='move absolute')

        self.stages_bar.add_var('Y/y_set', label='set value', target=c,
                                attr='y_set')
        self.stages_bar.add_button('go_rel_y', lambda: c.go_rel_y(), group='Y',
                                   label='move relative')
        self.stages_bar.add_button('go_abs_y', lambda: c.go_y(), group='Y',
                                   label='move absolute')

        self.stages_bar.add_var('R/r_set', label='set value', target=c,
                                attr='r_set')
        self.stages_bar.add_button('go_rel_r', lambda: c.go_rel_r(), group='R',
                                   label='move relative')
        self.stages_bar.add_button('go_abs_r', lambda: c.go_r(), group='R',
                                   label='move absolute')

        self.stages_bar.add_button('up', lambda: c.up(), group='Jog',
                                   label='up')
        self.stages_bar.add_button('down', lambda: c.down(), group='Jog',
                                   label='down')
        self.stages_bar.add_button('left', lambda: c.left(), group='Jog',
                                   label='left')

        self.stages_bar.add_button('right', lambda: c.right(), group='Jog',
                                   label='right')

        # ---------------------------------------------------------------------
        #   FOCUS AND ZOOM CONTROLS
        # ---------------------------------------------------------------------

        self.focus_zoom_bar = atb.Bar(
            name='focus_and_zoom',
            label='Focus/Zoom Controls',
            iconified='true',
            help='Controls for adjusting power focus and zoom',
            position=(10, 10),
            size=(200, 300),
            )

        self.focus_zoom_bar.add_var('Focus/focus_step', label='focus step',
                                    target=c, attr='focus_step')
        self.focus_zoom_bar.add_button('focus_plus', lambda: c.focus_plus(),
                                       group='Focus', label='focus plus')
        self.focus_zoom_bar.add_button('focus_minus', lambda: c.focus_minus(),
                                       group='Focus', label='focus minus')

        self.focus_zoom_bar.add_var('Zoom/zoom_step', label='zoom step',
                                    target=c, attr='zoom_step')
        self.focus_zoom_bar.add_button('zoom_plus', lambda: c.zoom_plus(),
                                       group='Zoom', label='zoom plus')
        self.focus_zoom_bar.add_button('zoom_minus', lambda: c.zoom_minus(),
                                       group='Zoom', label='zoom minus')

        # ---------------------------------------------------------------------
        #   LED CONTROLS
        # ---------------------------------------------------------------------

        self.led_bar = atb.Bar(
            name='leds',
            label='LED Controls',
            iconified='true',
            help='Controls for adjusting illumination',
            position=(20, 20),
            size=(200, 180),
            )

        self.led_bar.add_var(
            'Side/Ch1_mA',
            #target=c,
            #attr='IsetCh1',
            label='I Ch1 (mA)',
            vtype=atb.TW_TYPE_UINT32,
            setter=lambda x: c.leds.set_current(1, x),
            getter=lambda: c.leds.soft_current(1),
            min=0,
            max=1000,
            )

        self.led_bar.add_var('Side/Ch1_status', label='Ch1 status',
                             vtype=atb.TW_TYPE_BOOL8,
                             getter=lambda: c.leds.soft_status(1),
                             setter=lambda x: c.leds.set_status(1, x))

        self.led_bar.add_var(
            'Top/Ch2_mA',
            #target=c,
            #attr='IsetCh2',
            label='I Ch2 (mA)',
            vtype=atb.TW_TYPE_UINT32,
            setter=lambda x: c.leds.set_current(2, x),
            getter=lambda: c.leds.soft_current(2),
            min=0,
            max=1000,
            )
        self.led_bar.add_var('Top/Ch2_status', vtype=atb.TW_TYPE_BOOL8,
                             getter=lambda: c.leds.soft_status(2),
                             setter=lambda x: c.leds.set_status(2, x))

        #self.led_bar.add_var(
        #    'Channel3/Ch3_mA',
        #    target=c,
        #    attr='IsetCh3',
        #    label='I Ch3 (mA)',
        #    setter=lambda x: c.leds.set_current(3,x),
        #    min=0,
        #    max=250,
        #    )
        # self.led_bar.add_var('Channel3/Ch3_status', label='Ch3 status',
        #                              vtype=atb.TW_TYPE_BOOL8,
        #                              getter=lambda: c.leds.soft_status(3),
        #                              setter=lambda x: c.leds.set_status(3, x))
        #
        #         self.led_bar.add_var(
        #             'Channel4/Ch4_mA',
        #             target=c,
        #             attr='IsetCh4',
        #             label='I Ch4 (mA)',
        #             setter=lambda x: c.leds.set_current(4,x),
        #             min=0,
        #             max=250,
        #             )
        #         self.led_bar.add_var('Channel4/Ch4_status', label='Ch4 status',
        #                              vtype=atb.TW_TYPE_BOOL8,
        #                              getter=lambda: c.leds.soft_status(4),
        #                              setter=lambda x: c.leds.set_status(4, x))

        # ---------------------------------------------------------------------
        #   RADIAL FEATURE FINDER
        # ---------------------------------------------------------------------
        radial_ff = c.radial_ff

        self.radial_ff_bar = atb.Bar(
            name='RadialFF',
            label='Radial Symmetry',
            help='Parameters for initial (symmetry-based) image processing',
            iconified='true',
            position=(30, 30),
            size=(250, 180),
            )

        self.radial_ff_bar.add_var(
            'target_kpixels',
            label='Target kPixels',
            vtype=atb.TW_TYPE_FLOAT,
            min=50.,
            max=1000.,
            step=10.,
            target=radial_ff,
            attr='target_kpixels',
            )
        self.radial_ff_bar.add_var(
            'min_radius_fraction',
            label='Min. radius (fraction)',
            vtype=atb.TW_TYPE_FLOAT,
            min=0.01,
            max=0.5,
            step=0.01,
            target=radial_ff,
            attr='min_radius_fraction',
            )
        self.radial_ff_bar.add_var(
            'max_radius_fraction',
            label='Max. radius (fraction)',
            vtype=atb.TW_TYPE_FLOAT,
            min=0.1,
            max=0.8,
            step=0.01,
            target=radial_ff,
            attr='max_radius_fraction',
            )
        self.radial_ff_bar.add_var(
            'radius_steps',
            label='Radius steps',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=10,
            step=1,
            target=radial_ff,
            attr='radius_steps',
            )
        self.radial_ff_bar.add_var(
            'alpha',
            label='Alpha',
            vtype=atb.TW_TYPE_FLOAT,
            min=1.,
            max=50.,
            step=1.,
            target=radial_ff,
            attr='alpha',
            )

        self.radial_ff_bar.add_var('show_transform', label='Show Transform',
                                   vtype=atb.TW_TYPE_BOOL8, target=self,
                                   attr='show_feature_map')

        self.radial_ff_bar.add_var('Albino/albino_mode_enable',
                                   label='Mode Enabled',
                                   vtype=atb.TW_TYPE_BOOL8, target=radial_ff,
                                   attr='albino_mode')
        self.radial_ff_bar.add_var(
            'Albino/albino_threshold',
            label='Threshold',
            vtype=atb.TW_TYPE_FLOAT,
            min=0.1,
            max=50.,
            step=1.,
            target=radial_ff,
            attr='albino_threshold',
            )

        self.radial_ff_bar.add_var(
            'RestrictRegion/top',
            label='top',
            vtype=atb.TW_TYPE_UINT32,
            min=0,
            max=300,
            step=1,
            target=radial_ff,
            attr='restrict_top',
            )
        self.radial_ff_bar.add_var(
            'RestrictRegion/left',
            label='left',
            vtype=atb.TW_TYPE_UINT32,
            min=0,
            max=300,
            step=1,
            target=radial_ff,
            attr='restrict_left',
            )

        self.radial_ff_bar.add_var(
            'RestrictRegion/right',
            label='right',
            vtype=atb.TW_TYPE_UINT32,
            min=0,
            max=300,
            step=1,
            target=radial_ff,
            attr='restrict_right',
            )

        self.radial_ff_bar.add_var(
            'RestrictRegion/bottom',
            label='bottom',
            vtype=atb.TW_TYPE_UINT32,
            min=0,
            max=300,
            step=1,
            target=radial_ff,
            attr='restrict_bottom',
            )

        # ---------------------------------------------------------------------
        #   STARBURST FEATURE FINDER
        # ---------------------------------------------------------------------

        self.sb_ff_bar = atb.Bar(
            name='StarburstFF',
            label='Starburst',
            iconified='true',
            help="Parameters for the refinement phase ('starburst') image processing",
            position=(40, 40),
            size=(200, 250),
            )

        sb_ff = c.starburst_ff

        self.sb_ff_bar.add_var(
            'Pupil/n_pupil_rays',
            label='n rays',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=100,
            step=1,
            target=sb_ff,
            attr='pupil_n_rays',
            )

        self.sb_ff_bar.add_var(
            'Pupil/pupil_min_radius',
            label='min radius',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=100,
            step=1,
            target=sb_ff,
            attr='pupil_min_radius',
            )

        self.sb_ff_bar.add_var(
            'Pupil/pupil_threshold',
            label='edge detect threshold',
            vtype=atb.TW_TYPE_FLOAT,
            min=0.1,
            max=5.0,
            step=0.1,
            target=sb_ff,
            attr='pupil_threshold',
            )

        self.sb_ff_bar.add_var(
            'CR/n_cr_rays',
            label='n rays',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=100,
            step=1,
            target=sb_ff,
            attr='cr_n_rays',
            )

        self.sb_ff_bar.add_var(
            'CR/cr_min_radius',
            label='min radius',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=100,
            step=1,
            target=sb_ff,
            attr='cr_min_radius',
            )

        self.sb_ff_bar.add_var(
            'CR/cr_threshold',
            label='edge detect threshold',
            vtype=atb.TW_TYPE_FLOAT,
            min=0.1,
            max=5.0,
            step=0.1,
            target=sb_ff,
            attr='cr_threshold',
            )

        fit_algos = {0: 'circle_least_squares',
                     1: 'circle_least_squares_ransac',
                     2: 'ellipse_least_squares'}

        fit_algos_rev = dict([(val, key) for (key, val) in fit_algos.items()])

        FittingAlgorithm = atb.enum('FittingAlgorithm', {'circle lst sq': 0,
                                    'circle ransac': 1, 'ellipse lst sq': 2})
        self.sb_ff_bar.add_var('Fitting/circle_fit', label='circle fit method',
                               vtype=FittingAlgorithm, getter=lambda: \
                               fit_algos_rev[sb_ff.fitting_algorithm],
                               setter=lambda x: \
                               sb_ff.__dict__.__setitem__('fitting_algorithm',
                               fit_algos[x]))

        self.sb_ff_bar.add_var('Display/show_rays', self.display_starburst)

        # ---------------------------------------------------------------------
        #   CALIBRATION
        # ---------------------------------------------------------------------
        self.cal_bar = atb.Bar(
            name='Calibration',
            label='Calibration',
            iconified='true',
            help='Auto-calibration steps',
            position=(50, 50),
            size=(250, 300),
            refresh=0.5
            )

        self.cal_bar.add_button('calibrate', lambda: c.calibrate(),
                                label='Calibrate (full)')

        self.cal_bar.add_separator('Sub-phases')
        self.cal_bar.add_button('cal_center_h', lambda: \
                                c.calibrate_center_horizontal(),
                                label='Center Horizontal')
        self.cal_bar.add_button('cal_center_v', lambda: \
                                c.calibrate_center_vertical(),
                                label='Center Vertical')
        self.cal_bar.add_button('cal_center_d', lambda: \
                                c.calibrate_center_depth(), label='Center Depth'
                                )
        #self.cal_bar.add_button('align_pupil_cr', lambda: \
        #                        c.calibrate_align_pupil_and_cr(),
        #                        label='Align Pupil and CR')
        self.cal_bar.add_button('cal_pupil_rad', lambda: \
                                c.calibrate_find_pupil_radius(),
                                label='Find Pupil Radius')

        self.cal_bar.add_separator('Info')
        self.cal_bar.add_var('d', label='Distance to CR curv. center',
                             vtype=atb.TW_TYPE_FLOAT, target=c.calibrator,
                             attr='d')  # readonly = True,
        self.cal_bar.add_var('Rp', label='Pupil rotation radius (Rp)[mm]',
                             vtype=atb.TW_TYPE_FLOAT, target=c.calibrator,
                             attr='Rp_mm')  # readonly = True,

        # Calibration Files
        try:
            self.refresh_calibration_file_list()

            self.cal_bar.add_separator('Calibration Files')

            self.cal_bar.add_var('current_calibration_file',
                                 vtype=self.cal_enum, label='Calibration File',
                                 getter=lambda: \
                                 self.get_calibration_file_atb(),
                                 setter=lambda x: \
                                 self.set_calibration_file_atb(x))
                                  # setter = lambda x: sb_ff.__dict__.__setitem__('fitting_algorithm', fit_algos[x]))
                                  # getter=lambda: self.get_calibration_file_atb,
                                  # setter=lambda x: self.set_calibration_file_atb(x))

            self.cal_bar.add_separator('Calibration Save')
            self.cal_file_save_name = ctypes.c_char_p('')

            self.cal_bar.add_var('calibration_file_save_name',
                                 vtype=atb.TW_TYPE_CDSTRING, target=self,
                                 attr='cal_file_save_name')
            self.cal_bar.add_button('save_calibration', lambda: \
                                    self.save_calibration_file_atb(self.cal_file_save_name))
        except Exception as E:
            logging.warning("Error setting calibration file list: %s" % E)
            logging.warning("""Unable to use calibration-file saving
                               infrastructure.  A patched version of glumpy
                               is required to enable this feature.""")

        # --------------------------------------------------------------------
        #   CAMERA
        # --------------------------------------------------------------------

        self.cam_bar = atb.Bar(
            name='Camera',
            label='Camera',
            iconified='true',
            help='Camera acquisition parameters',
            position=(60, 60),
            size=(200, 180),
            )

        self.cam_bar.add_var(
            'binning',
            label='binning',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=16,
            step=1,
            target=c,
            attr='binning',
            )

        self.cam_bar.add_var(
            'gain',
            label='gain',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=16,
            step=1,
            target=c,
            attr='gain',
            )

        self.cam_bar.add_var(
            'exposure',
            label='exposure',
            vtype=atb.TW_TYPE_UINT32,
            min=5000,
            max=30000,
            step=1000,
            target=c,
            attr='exposure',
            )

        self.cam_bar.add_var(
            'ROI/roi_width',
            label='width',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=800,
            step=1,
            target=c,
            attr='roi_width',
            )

        self.cam_bar.add_var(
            'ROI/roi_height',
            label='height',
            vtype=atb.TW_TYPE_UINT32,
            min=1,
            max=800,
            step=1,
            target=c,
            attr='roi_height',
            )

        self.cam_bar.add_var(
            'ROI/roi_offset_x',
            label='offset x',
            vtype=atb.TW_TYPE_UINT32,
            min=0,
            max=800,
            step=1,
            target=c,
            attr='roi_offset_x',
            )

        self.cam_bar.add_var(
            'ROI/roi_offset_y',
            label='offset y',
            vtype=atb.TW_TYPE_UINT32,
            min=0,
            max=800,
            step=1,
            target=c,
            attr='roi_offset_y',
            )

        # Event Handlers
        def on_init():
            self.tracker_view.prepare_opengl()

        def on_draw():
            self.window.clear()
            self.tracker_view.draw((self.window.width, self.window.height))

        def on_idle(dt):
            # if dt < 0.02:
            #    return
            self.update_tracker_view()
            self.window.draw()

        def on_key_press(symbol, modifiers):
            if symbol == glumpy.key.ESCAPE:
                c.stop_continuous_acquisition()
                print "Controller has %i refs" % sys.getrefcount(c)
                c.release()
                self.controller = None
                print "Controller has %i refs" % sys.getrefcount(c)
                c.shutdown()
                #print "Shutting down controller..."
                #print "Shut down controller", c.shutdown()
                #c.continuously_acquiring = False
                #c.acq_thread.join()
                sys.exit()

        self.window.push_handlers(atb.glumpy.Handlers(self.window))
        self.window.push_handlers(on_init, on_draw, on_key_press, on_idle)
        self.window.draw()

    def __del__(self):
        print "GUI __del__ called"
        self.controller.stop_continuous_acquisition()
        self.controller.release()
        self.controller.shutdown()
        self.controller = None

    def mainloop(self):
        self.window.mainloop()

    def get_calibration_file_atb(self):
        # return 0
        # return ctypes.c_int(0)
        if self.controller.calibration_file is None:
            calibration_filename = None
        else:
            calibration_filename = os.path.split(self.controller.calibration_file)[-1]
            calibration_filename = os.path.splitext(calibration_filename)[0]
        return self.cal_enum_dict.get(calibration_filename, 0)

        # return self.cal_enum_dict.get(self.controller.calibration_file,0)

    def set_calibration_file_atb(self, x):
        if self.cal_lookup_dict[x] == 'None':
            return
        self.calibration_file = self.cal_lookup_dict[x]
        base_path = os.path.expanduser(global_settings['calibration_path'])
        cal_path = os.path.join(base_path, '%s.pkl' % self.calibration_file)
        self.controller.calibrator.load_parameters(cal_path, self.controller)

        # self.controller.calibration_file = self.cal_lookup_dict[x]

    def refresh_calibration_file_list(self):

        # read in saved calibration files
        try:
            cal_path = os.path.expanduser(global_settings['calibration_path'])
        except KeyError:
            logging.warning('A calibration_path was not found in the config file')
            logging.warning('Loaded global settings: %s' % global_settings)

        if not os.path.exists(cal_path):
            os.makedirs(cal_path)

        cal_files = os.listdir(cal_path)
        cal_files = filter(lambda x: re.match(r'.*\.pkl', x), cal_files)

        cal_names = [x.split('.')[0] for x in cal_files]
        cal_names.insert(0, 'None')

        # add back in the rest of the path
        cal_files = [os.path.join(cal_path, x) for x in cal_files]
        cal_files.insert(0, '<none>')

        cal_ids = range(0, len(cal_names))
        self.cal_enum_dict = OrderedDict(zip(cal_names, cal_ids))
        self.cal_lookup_dict = OrderedDict(zip(cal_ids, cal_names))

        print self.cal_enum_dict
        print self.cal_lookup_dict

        self.cal_enum = atb.enum('CalibrationFile', self.cal_enum_dict)

    def save_calibration_file_atb(self, cal_name):
        base_path = os.path.expanduser(global_settings['calibration_path'])
        cal_path = os.path.join(base_path, '%s.pkl' % cal_name)
        self.controller.save_calibration(cal_path)
        #self.controller.calibrator.save_parameters(cal_path, self.controller)
        # self.controller.save_calibration(cal_path)
        self.refresh_calibration_file_list()

    def update_tracker_view(self):
        if (self.controller is None) or (self.controller.camera_device is None):
            return

        try:
            features = self.controller.ui_queue.get_nowait()
        except Empty:
            return

        if 'frame_time' in features:
            toc = features['frame_time']
        else:
            toc = 1

        if self.show_feature_map:
            transform_im = features['transform']
            if transform_im is not None:
                transform_im -= min(ravel(transform_im))
                transform_im = transform_im * 255 / max(ravel(transform_im))
                # ravelled = ravel(transform_im)
                self.tracker_view.im_array = transform_im.astype(uint8)
        else:
            self.tracker_view.im_array = features['im_array']

        if 'pupil_position_stage1' in features:
            self.tracker_view.stage1_pupil_position = \
                features['pupil_position_stage1']

        if 'cr_position_stage1' in features:
            self.tracker_view.stage1_cr_position = features['cr_position_stage1'
                    ]

        if 'cr_radius' in features:
            self.tracker_view.cr_radius = features['cr_radius']

        if 'pupil_radius' in features:
            self.tracker_view.pupil_radius = features['pupil_radius']

        if 'pupil_position' in features:
            self.tracker_view.pupil_position = features['pupil_position']

        if 'cr_position' in features:
            self.tracker_view.cr_position = features['cr_position']

        if self.display_starburst:
            self.tracker_view.starburst = features.get('starburst', None)
        else:
            self.tracker_view.starburst = None

        self.tracker_view.is_calibrating = features.get('is_calibrating', False)

        self.tracker_view.restrict_top = features.get('restrict_top', None)
        self.tracker_view.restrict_bottom = features.get('restrict_bottom',
                None)
        self.tracker_view.restrict_left = features.get('restrict_left', None)
        self.tracker_view.restrict_right = features.get('restrict_right', None)

        self.n_frames += 1
        self.frame_count += 1

        time_between_updates = 0.4

        self.frame_rate_accum += 1. / toc

        self.frame_rates.append(1. / toc)

        time_since_last_update = time.time() - self.last_update_time

        if time_since_last_update > time_between_updates:
            self.last_update_time = time.time()

            self.frame_rate = mean(array(self.frame_rates))
            self.frame_rates = []
            self.frame_rate_accum = 0

            self.last_time = time.time()
            self.n_frames = 0

            if 'sobel_avg' in features:
                self.sobel_avg = features['sobel_avg']
