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

from mcmmtk import options

CONFIG_DIR_PATH = options.get_user_config_dir()
SYS_DATA_DIR_PATH = options.get_sys_data_dir()

IDEAL_PAINTS_FILE_PATH = os.sep.join([SYS_DATA_DIR_PATH, "ideal.psd"])
SERIES_FILES_FILE_PATH = os.sep.join([CONFIG_DIR_PATH, "paint_series_files"])

def read_series_file_names():
    series_file_names = []
    if os.path.isfile(SERIES_FILES_FILE_PATH):
        for line in open(SERIES_FILES_FILE_PATH, 'r').readlines():
            sf_name = line.strip()
            if len(line) == 0:
                continue
            series_file_names.append(sf_name)
    return series_file_names

def write_series_file_names(sf_names):
    fobj = open(SERIES_FILES_FILE_PATH, 'w')
    for sf_name in sf_names:
        fobj.write(sf_name)
        fobj.write(os.linesep)
    fobj.close()
