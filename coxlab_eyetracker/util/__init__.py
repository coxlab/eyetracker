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
import re

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
        print(cp.items(section))
        d.update(dict(cp.items(section)))

    # a bit hacky: covert from strings to values
    for (key, val) in d.items():
        if re.match(r'true', val, re.IGNORECASE):
            d[key] = True
        if re.match(r'false', val, re.IGNORECASE):
            d[key] = False
    print('d: %s' % d)
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
