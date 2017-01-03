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

"""
GTK extensions and wrappers
"""

import collections
import fractions
import sys
import math

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Pango

from .gtx import dialogue

# TODO: make gtkpwx.py pure
from . import utils

BITS_PER_CHANNEL = 16
ONE = (1 << BITS_PER_CHANNEL) - 1

### Utility Functions

def best_foreground(rgb, threshold=0.5):
    wval = (rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114)
    if wval > ONE * threshold:
        return Gdk.Color(0, 0, 0)
    else:
        return Gdk.Color(ONE, ONE, ONE)

def best_foreground_rgb(rgb, threshold=0.5):
    return gdk_color_to_rgb(best_foreground(rgb=rgb, threshold=threshold))

def gdk_color_to_rgb(gcol):
    gcol_str = gcol.to_string()[1:]
    if len(gcol_str) == 3:
        return [int(gcol_str[i:(i+1)] * 4, 16) for i in range(3)]
    elif len(gcol_str) == 6:
        return [int(gcol_str[i*2:(i+1) * 2] * 2, 16) for i in range(3)]
    return [int(gcol_str[i*4:(i+1) * 4], 16) for i in range(3)]

### Useful Named Tuples

### Text Entry

### Miscellaneous Data Entry

class Choice(Gtk.ComboBox):
    def __init__(self, choices):
        Gtk.ComboBox.__init__(self, model=Gtk.ListStore(str))
        cell = Gtk.CellRendererText()
        self.pack_start(cell, expand=True)
        self.add_attribute(cell, "text", 0)
        for choice in choices:
            self.get_model().append([choice])
    def get_selection(self):
        index = self.get_active()
        return index if index >= 0 else None
    def set_selection(self, index):
        self.set_active(index if index is not None else -1)
