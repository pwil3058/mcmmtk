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

import os
import sys

# find the icons directory
# first look in the source directory (so that we can run uninstalled)

_libdir = os.path.join(sys.path[0], 'pixmaps')
if not os.path.exists(_libdir) or not os.path.isdir(_libdir):
    _TAILEND = os.path.join('share', 'pixmaps')
    _prefix = sys.path[0]
    while _prefix:
        _libdir = os.path.join(_prefix, _TAILEND)
        if os.path.exists(_libdir) and os.path.isdir(_libdir):
            break
        _prefix = os.path.dirname(_prefix)

APP_ICON = 'mcmmtk'
APP_ICON_FILE = os.path.join(_libdir, APP_ICON + os.extsep + 'png')
