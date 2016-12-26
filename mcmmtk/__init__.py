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

import sys

# Importing i18n here means that _() is defined for all package modules
from . import i18n

# We can also check PyGTK versions here to avoid duplication in other
# modules.
import pygtk
pygtk.require('2.0')

import gtk
REQUIRED_VERSION = (2, 24, 0)
if gtk.pygtk_version < REQUIRED_VERSION:
    msg = 'Unusable PyGTK version {0} found.\nVersion {1} or later is required'.format(gtk.pygtk_version, REQUIRED_VERSION)
    gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE, message_format=msg).run()
    sys.exit(1)
