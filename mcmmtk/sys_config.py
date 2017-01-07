# Copyright: Peter Williams (2012) - All rights reserved
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Manage configurable options
"""

import os
import sys

from . import APP_NAME

def _find_sys_base_dir():
    sys_data_dir = os.path.join(sys.path[0], "data")
    if os.path.exists(sys_data_dir) and os.path.isdir(sys_data_dir):
        return os.path.dirname(sys_data_dir)
    else:
        _TAILEND = os.path.join("share", APP_NAME, "data")
        _prefix = sys.path[0]
        while _prefix:
            sys_data_dir = os.path.join(_prefix, _TAILEND)
            if os.path.exists(sys_data_dir) and os.path.isdir(sys_data_dir):
                return os.path.dirname(sys_data_dir)
            _prefix = os.path.dirname(_prefix)

_SYS_BASE_DIR = _find_sys_base_dir()
_SYS_DATA_DIR = os.path.join(_SYS_BASE_DIR, "data")
_SYS_SAMPLES_DIR = os.path.join(_SYS_BASE_DIR, "samples")

def get_sys_data_dir():
    return _SYS_DATA_DIR

def get_sys_samples_dir():
    return _SYS_SAMPLES_DIR
