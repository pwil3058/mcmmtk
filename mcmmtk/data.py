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

from gi.repository import Gtk

from . import options

class LexiconListStore(Gtk.ListStore):
    def __init__(self, lexicon):
        Gtk.ListStore.__init__(self, str)
        for word in lexicon:
            self.append([word])

# Words commonly used in paint names
_COLOUR_NAME_LEXICON = [
    # Colours
    _('Red'), _('Green'), _('Blue'),
    _('Cyan'), _('Magenta'), _('Yellow'),
    _('Black'), _('White'), _('Gray'),
    _('Violet'), _('Purple'), _('Umber'), _('Sienna'), _('Ochre'),
    _('Crimson'), _('Rose'), _('Scarlet'), _('Ultramarine'), _('Viridian'),
    _('Orange'),
    _("Earth"), _("Grey"), _("Brown"), _("Khaki"), _("Buff"), _("Flesh"),
    _("Tan"), _("Smoke"),
    # Qualifiers
    _('Raw'), _('Burnt'), _('French'), _('Mixing'), _('Permanent'),
    _('Light'), _('Medium'), _('Dark'), _('Deep'), _('Pale'), _('Lemon'),
    _('Olive'), _('Prussian'), _('Hue'), _('Shade'), _('Indian'),
    _('Payne\'s'), _('Ivory'), _('Lamp'), _('Naples'), _('Sap'),
    _("Drab"), _("Flat"), _("Hull"), _("J.N."), _("J.A."), _("Sea"),
    _("Sky"), _("RLM"), _("Field"), _("Neutral"), _("Deck"), _("Desert"),
    _("German"), _("NATO"), _("Cockpit"), _("IJN"), _("JGSDF"),
    _("Sasebo"), _("Wood"), _("Deck"), _("Arsenal"), _("Lino"), _("Royal"),
    _("Rubber"), _("RAF"), _("FS"), _("BS"), _("Metallic"), _("Gun"),
    _("Clear"), _("Leaf"),
    # Agents
    _('Cobalt'), _('Cadmium'), _('Alizarin'), _('Phthalo'), _('Dioxazine'),
    _('Zinc'), _('Titanium'), _('Cerulean'),
    _("Metal"), _("Iron"), _("Copper"), _("Aluminium"), _("Chrome"),
    _("Gold"), _("Bronze")
]

CONFIG_DIR_PATH = options.get_user_config_dir()

PAINT_WORDS_FILE_PATH = os.sep.join([CONFIG_DIR_PATH, "paint_words"])

def read_paint_words():
    paint_words = []
    if os.path.isfile(PAINT_WORDS_FILE_PATH):
        for line in open(PAINT_WORDS_FILE_PATH, 'r').readlines():
            paint_word = line.strip()
            if len(line) == 0:
                continue
            paint_words.append(paint_word)
    return paint_words

def append_paint_words(paint_words):
    fobj = open(PAINT_WORDS_FILE_PATH, 'a')
    for paint_word in paint_words:
        fobj.write(paint_word)
        fobj.write(os.linesep)
    fobj.close()

def new_paint_words_cb(widget, new_words):
    append_paint_words(new_words)

COLOUR_NAME_LEXICON = LexiconListStore(_COLOUR_NAME_LEXICON + read_paint_words())

_GENERAL_WORDS_LEXICON = [
    _("Tamiya"), _("Italeri")
]

PAINT_WORDS_FILE_PATH = os.sep.join([CONFIG_DIR_PATH, "general_words"])

def read_general_words():
    general_words = []
    if os.path.isfile(PAINT_WORDS_FILE_PATH):
        for line in open(PAINT_WORDS_FILE_PATH, 'r').readlines():
            paint_word = line.strip()
            if len(line) == 0:
                continue
            general_words.append(paint_word)
    return general_words

def append_general_words(general_words):
    fobj = open(PAINT_WORDS_FILE_PATH, 'a')
    for paint_word in general_words:
        fobj.write(paint_word)
        fobj.write(os.linesep)
    fobj.close()

def new_general_words_cb(widget, new_words):
    append_general_words(new_words)

GENERAL_WORDS_LEXICON = LexiconListStore(_GENERAL_WORDS_LEXICON + read_general_words())
