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

import os, sys
import locale
import gettext

APP_NAME = "ModellersColourMatcherMixer"

# find the locale directory
# first look in the source directory (so that we can run uninstalled)
LOCALE_DIR = os.path.join(sys.path[0], 'locale')
if not os.path.exists(LOCALE_DIR) or not os.path.isdir(LOCALE_DIR):
    # if we get here it means we're installed and we assume that the
    # locale files were installed under the same prefix as the
    # application.
    _TAILEND = os.path.join('share', 'locale')
    _prefix = sys.path[0]
    _last_prefix = None # needed to prevent possible infinite loop
    while _prefix and _prefix != _last_prefix:
        LOCALE_DIR = os.path.join(_prefix, _TAILEND)
        if os.path.exists(LOCALE_DIR) and os.path.isdir(LOCALE_DIR):
            break
        _last_prefix = _prefix
        _prefix = os.path.dirname(_prefix)
    # As a last resort, try the usual place
    if not (os.path.exists(LOCALE_DIR) and os.path.isdir(LOCALE_DIR)):
        LOCALE_DIR = os.path.join(sys.prefix, 'share', 'locale')

# Lets tell those details to gettext
gettext.install(APP_NAME, localedir=LOCALE_DIR)
