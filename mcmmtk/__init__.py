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

# TODO: improve configuration directory path
CONFIG_DIR_PATH = os.path.expanduser("~/.ModellersColourMatcherMixer")
PGND_CONFIG_DIR_PATH = None
from . import sys_config
SYS_DATA_DIR_PATH = sys_config.get_sys_data_dir()
SYS_SAMPLES_DIR_PATH = sys_config.get_sys_samples_dir()
from . import recollect # Temporary until definitions get moved

ISSUES_URL = "<https://github.com/pwil3058/mcmmtk/issues>"
ISSUES_EMAIL = __author__
ISSUES_VERSION = __version__
