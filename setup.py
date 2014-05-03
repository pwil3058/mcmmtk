#! /bin/env python
### Copyright: Peter Williams (2012) - All rights reserved
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 of the License only.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import glob
import os
import sys

from distutils.core import setup

for_windows = sys.platform in ['win32', 'cygwin'] or 'bdist_wininst' in sys.argv or 'bdist_msi' in sys.argv

NAME = 'ModellersColourMatcherMixer'

VERSION = '0.07'

DESCRIPTION = 'A set of tools for painters to experiment with mixing colours.'

LONG_DESCRIPTION =\
'''
This software is a set of tools for painters who wish to experiment with
mixing paints and plan palettes (electronically) before beginning a
painting.
'''

LICENSE = 'GNU General Public License (GPL) Version 2.0'

CLASSIFIERS = [
    'Development Status :: Pre-Alpha',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: %s' % LICENSE,
    'Programming Language :: Python',
    'Topic :: Artistic Software',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
]

AUTHOR = 'Peter Williams'

AUTHOR_EMAIL = 'pwil3058@bigpond.net.au'

URL = 'http://sourceforge.net/projects/pcatk/'

SCRIPTS = ['pcatk_palette.py', 'pcatk_editor.py']

PACKAGES = ['pcatk']

tubes = glob.glob('data/*.tsd')

TUBES = [(os.path.join('share', NAME, 'data'), tubes)]

samples = glob.glob('samples/*.jpg')

SAMPLES = [(os.path.join('share', NAME, 'samples'), samples)]

if for_windows:
    SCRIPTS.append('win_post_install.py')
    DESKTOP = []
    PIXMAPS = [('share/pixmaps', ['pixmaps/pcatk.png', 'pixmaps/pcatk.ico'])]
else:
    DESKTOP = [('share/applications', ['pcatk_editor.desktop', 'pcatk_palette.desktop'])]
    PIXMAPS = [('share/pixmaps', ['pixmaps/pcatk.png'])]

setup(
    name = NAME,
    version = VERSION,
    description = DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    classifiers = CLASSIFIERS,
    license = LICENSE,
    author = AUTHOR,
    author_email = AUTHOR_EMAIL,
    url = URL,
    scripts = SCRIPTS,
    packages = PACKAGES,
    data_files = DESKTOP + PIXMAPS + TUBES + SAMPLES
)
