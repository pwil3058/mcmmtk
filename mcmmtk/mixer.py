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

'''
Mix paint colours
'''

import os
import cgi
import time
import collections

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from .bab import mathx

from .epaint import gpaint
from .epaint import lexicon
from .epaint import vpaint
from .epaint import pedit
from .epaint import pmix
from .epaint import pseries

from .gtx import actions
from .gtx import coloured
from .gtx import dialogue
from .gtx import entries
from .gtx import gutils
from .gtx import printer
from .gtx import recollect
from .gtx import screen
from .gtx import tlview

from .pixbufx import iview

from . import icons

class ModelPaintMixer(pmix.PaintMixer):
    PAINT = vpaint.ModelPaint
    MATCHED_PAINT_LIST_VIEW = pmix.MatchedModelPaintListView
    PAINT_SERIES_MANAGER = pseries.ModelPaintSeriesManager
    MIXED_PAINT_INFORMATION_DIALOGUE = pmix.MixedModelPaintInformationDialogue
    MIXTURE = pmix.ModelMixture
    MIXED_PAINT = pmix.MixedModelPaint

recollect.define("mixer", "last_geometry", recollect.Defn(str, ""))

class TopLevelWindow(dialogue.MainWindow):
    """
    A top level window wrapper around a mixer
    """
    def __init__(self):
        dialogue.MainWindow.__init__(self)
        self.parse_geometry(recollect.get("mixer", "last_geometry"))
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_title('mcmmtk: Mixer')
        self.mixer = ModelPaintMixer()
        self.connect("destroy", lambda _widget: self.mixer._quit_mixer())
        self.connect("configure-event", self._configure_event_cb)
        self.add(self.mixer)
        self.show_all()
    def _configure_event_cb(self, widget, event):
        recollect.set("mixer", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))
