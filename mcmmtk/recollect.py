### Copyright (C) 2010-2016 Peter Williams <pwil3058@gmail.com>
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

"""Keep track of various GUI information that the user would like to
be persistent but is too fiddly to put in "user options" e.g. the last
workspace used, window placement, layout, size, etc.
"""

import collections
import configparser
import os
import sys

from .gtx import recollect

from .import sys_config

# TODO: move recollect definitions to where they're used

recollect.define('sample_viewer', 'last_file', recollect.Defn(str, os.path.join(sys_config.get_sys_samples_dir(), 'example.jpg')))
recollect.define('sample_viewer', 'last_size', recollect.Defn(str, ""))

recollect.define("paint_colour_information", "last_size", recollect.Defn(str, ""))
recollect.define("mixed_colour_information", "last_size", recollect.Defn(eval, ""))

recollect.define("paint_colour_selector", "hpaned_position", recollect.Defn(int, -1))
recollect.define("paint_colour_selector", "last_size", recollect.Defn(str, ""))

recollect.define("paint_series_selector", "last_file", recollect.Defn(str, os.path.join(sys_config.get_sys_data_dir(), 'ideal.psd')))

recollect.define("editor", "last_file", recollect.Defn(str, ""))
recollect.define("editor", "last_geometry", recollect.Defn(str, ""))
recollect.define("editor", "hpaned_position", recollect.Defn(int, -1))

recollect.define('reference_image_viewer', 'last_file', recollect.Defn(str, ''))
recollect.define('reference_image_viewer', 'last_size', recollect.Defn(str, ''))

recollect.define("mixer", "last_geometry", recollect.Defn(str, ""))
recollect.define("mixer", "hpaned_position", recollect.Defn(int, -1))
recollect.define("mixer", "vpaned_position", recollect.Defn(int, -1))
