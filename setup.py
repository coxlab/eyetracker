#!/usr/bin/python
# -*- coding: utf-8 -*-

""" distribute- and pip-enabled setup.py for coxlab_eyetracker """

from distribute_setup import use_setuptools
use_setuptools()
from setuptools import setup, Extension, find_packages
import os
import sys

prosilica_module_dir = './coxlab_eyetracker/camera/prosilica'
prosilica_sdk_dir = os.path.join(prosilica_module_dir, 'ProsilicaGigESDK_mac')
prosilica_sdk_lib = os.path.join(prosilica_sdk_dir, 'lib-pc/x64/4.2/')
prosilica_sdk_inc = os.path.join(prosilica_sdk_dir, 'inc-pc/')
import numpy.distutils.misc_util
numpy_inc_dirs = numpy.distutils.misc_util.get_numpy_include_dirs()

prosilica_srcs = ['Prosilica.cxx', 'prosilica_cpp_wrap.cxx']
prosilica_src_paths = [os.path.join(prosilica_module_dir, x) for x in
                       prosilica_srcs]
prosilica_static_libs = [os.path.join(prosilica_sdk_lib, x) for x in
                         ['libImagelib.a', 'libPvAPI.a']]

if sys.platform == 'darwin':
    extra_link_args = ['-framework', 'CoreFoundation']
else:
    extra_link_args = []

prosilica_module = Extension(
    'coxlab_eyetracker.camera.prosilica._prosilica_cpp',
    define_macros=[('_x64', '1'), ('_OSX', '1')],
    include_dirs=['/usr/local/include', prosilica_sdk_inc] + numpy_inc_dirs,
    libraries=['m', 'c', 'PvAPI', 'Imagelib'],
    extra_link_args=extra_link_args,
    library_dirs=['/usr/local/lib', prosilica_sdk_lib],
    sources=prosilica_src_paths,
    )

setup(
    name='coxlab_eyetracker',
    version='dev',
    scripts=['scripts/coxlab_eyetracker'],
    include_package_data=True,
    ext_modules=[prosilica_module],
    packages=find_packages(exclude=['tests', 'scripts']),
    data_files=[(os.path.expanduser('~/.eyetracker'),
                ['config/config.ini'])]
    )
