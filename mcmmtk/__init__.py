### Copyright: Peter Williams (2014) - All rights reserved
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

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gtk

# Importing i18n here means that _() is defined for all package modules
from . import i18n

__all__ = []
__author__ = "Peter Williams <pwil3058@gmail.com>"
__version__ = "0.0"

APP_NAME = "mcmmtk"

CONFIG_DIR_PATH = os.path.expanduser(os.path.join("~", ".config", APP_NAME))
PGND_CONFIG_DIR_PATH = None

if not os.path.exists(CONFIG_DIR_PATH):
    old_config_dir_path = os.path.expanduser(os.path.join("~", ".ModellersColourMatcherMixer"))
    if os.path.exists(old_config_dir_path):
        os.rename(old_config_dir_path, CONFIG_DIR_PATH)
    else:
        os.mkdir(CONFIG_DIR_PATH)

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

SYS_BASE_DIR_PATH = _find_sys_base_dir()
SYS_DATA_DIR_PATH = os.path.join(SYS_BASE_DIR_PATH, "data")
SYS_SAMPLES_DIR_PATH = os.path.join(SYS_BASE_DIR_PATH, "samples")

ISSUES_URL = "<https://github.com/pwil3058/mcmmtk/issues>"
ISSUES_EMAIL = __author__
ISSUES_VERSION = __version__
