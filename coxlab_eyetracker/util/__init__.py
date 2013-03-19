#
#  EyetrackerUtilities.py
#  EyeTracker
#
#  Created by David Cox on 3/11/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#

from IPSerialBridge import *

import sys
import traceback
import os
import logging
import re

from multiprocessing.managers import BaseProxy

from ConfigParser import SafeConfigParser
from StringIO import StringIO


def formatted_exception(max_tb_level=5):
    cla, exc, trbk = sys.exc_info()
    exc_name = cla.__name__

    try:
        exc_args = exc.__dict__["args"]
    except KeyError:
        exc_args = "<no args>"

    exc_tb = traceback.format_tb(trbk, max_tb_level)
    return (exc_name, exc_args, exc_tb)


default_config = '''
[simulation]

use_simulated=False
use_file_for_camera=False,


[calibration]

calibration_path=~/.eyetracker/calibration


[mworks]

enable_mw_conduit=true
'''


def config_to_dict(cp, d={}):

    for section in cp.sections():
        logging.debug('config_to_dict section %s: %s' % (section, cp.items(section)))
        d.update(dict(cp.items(section)))

    # a bit hacky: covert from strings to values
    for (key, val) in d.items():
        if re.match(r'true', val, re.IGNORECASE):
            d[key] = True
        if re.match(r'false', val, re.IGNORECASE):
            d[key] = False
    logging.debug('config_to_dict: %s' % d)
    return d


def load_default_config():
    cp = SafeConfigParser()
    sio = StringIO(default_config)
    cp.read(sio)
    return config_to_dict(cp)


def load_config_file(cfg_path):
    cp = SafeConfigParser()

    cp.read(os.path.expanduser(cfg_path))
    return config_to_dict(cp, load_default_config())


class ParamExpose(object):
    def __init__(self, objs, params):
        object.__setattr__(self, 'objs', objs)
        object.__setattr__(self, 'params', params)
        if not all([type(objs[0]) == type(o) for o in objs]):
            raise ValueError("All objs must be same type: %s" % objs)
        if isinstance(objs[0], BaseProxy):
            object.__setattr__(self, 'get_from_objs', object.__getattribute__(self, 'get_from_proxy_objs'))
            object.__setattr__(self, 'set_to_objs', object.__getattribute__(self, 'set_to_proxy_objs'))
        else:
            object.__setattr__(self, 'get_from_objs', object.__getattribute__(self, 'get_from_regular_objs'))
            object.__setattr__(self, 'set_to_objs', object.__getattribute__(self, 'set_to_regular_objs'))
    
    def get_from_proxy_objs(self, param):
        values = [o._callmethod('get_param', (param, )) for o in self.objs]
        if not all([v == values[0] for v in values]):
            raise ValuError("All obj params must match: %s, %s" % (param, values))
        return values[0]
    
    def get_from_regular_objs(self, param):
        values = [getattr(o, param) for o in self.objs]
        if not all([v == values[0] for v in values]):
            raise ValueError("All obj params must match: %s, %s" % (param, values))
        return values[0]
    
    def set_to_proxy_objs(self, param, value):
        for o in self.objs:
            o._callmethod('set_param', (param, value))

    def set_to_regular_objs(self, param, value):
        for o in self.objs:
            setattr(o, param, value)

    def __getattr__(self, attr):
        if attr in self.params:
            return self.get_from_objs(attr)
        return object.__getattr__(self, attr)
    
    def __setattr__(self, attr, value):
        if attr in self.params:
            return self.set_to_objs(attr, value)
        return object.__setattr__(self, attr, value)