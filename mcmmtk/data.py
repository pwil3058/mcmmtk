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

'''Interface to persistent data'''

import os
import sys

import gtk

# Words commonly used in paint names
_COLOUR_NAME_LEXICON = [
    # Colours
    _('Red'), _('Green'), _('Blue'),
    _('Cyan'), _('Magenta'), _('Yellow'),
    _('Black'), _('White'), _('Gray'),
    _('Violet'), _('Purple'), _('Umber'), _('Sienna'), _('Ochre'),
    _('Crimson'), _('Rose'), _('Scarlet'), _('Ultramarine'), _('Viridian'),
    _('Orange'),
    # Qualifiers
    _('Raw'), _('Burnt'), _('French'), _('Mixing'), _('Permanent'),
    _('Light'), _('Medium'), _('Dark'), _('Deep'), _('Pale'), _('Lemon'),
    _('Olive'), _('Prussian'), _('Hue'), _('Shade'), _('Indian'),
    _('Payne\'s'), _('Ivory'), _('Lamp'), _('Naples'), _('Sap'),
    # Agents
    _('Cobalt'), _('Cadmium'), _('Alizarin'), _('Phthalo'), _('Dioxazine'),
    _('Zinc'), _('Titanium'), _('Cerulean'),
]

class LexiconListStore(gtk.ListStore):
    def __init__(self, lexicon):
        gtk.ListStore.__init__(self, str)
        for word in lexicon:
            self.append([word])

COLOUR_NAME_LEXICON = LexiconListStore(_COLOUR_NAME_LEXICON)
