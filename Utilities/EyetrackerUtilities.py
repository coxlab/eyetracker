#
#  EyetrackerUtilities.py
#  EyeTracker
#
#  Created by David Cox on 3/11/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#

import sys
import traceback

from stopwatch import clockit

def formatted_exception(max_tb_level=5):
    cla, exc, trbk = sys.exc_info()
    exc_name = cla.__name__
    
    try:
        exc_args = exc.__dict__["args"]
    except KeyError:
        exc_args = "<no args>"
    
    exc_tb = traceback.format_tb(trbk, max_tb_level)
    return (exc_name, exc_args, exc_tb)