#
# The Python Imaging Library.
# $Id: ImageGL.py,v 1.1.1.1 2007/09/26 00:00:35 chrism Exp $
#
# OpenGL pixmap/texture interface (requires imToolkit OpenGL extensions)
#
# History:
# 2003-09-13 fl   Added
#
# Copyright (c) Secret Labs AB 2003.
#
# See the README file for information on usage and redistribution.
#

##
# OpenGL pixmap/texture interface (requires imToolkit OpenGL
# extensions.)
##

import _imaginggl

##
# Texture factory.

class TextureFactory:
    pass # overwritten by the _imaginggl module

from _imaginggl import *
