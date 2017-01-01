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

def wrap_in_scrolled_window(widget, policy=(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC), with_frame=True, label=None):
    scrw = Gtk.ScrolledWindow()
    scrw.set_policy(policy[0], policy[1])
    if isinstance(widget, Gtk.Container):
        scrw.add(widget)
    else:
        scrw.add_with_viewport(widget)
    if with_frame:
        frame = Gtk.Frame(label=label)
        frame.add(scrw)
        frame.show_all()
        return frame
    else:
        scrw.show_all()
        return scrw

def wrap_in_frame(widget, shadow_type=Gtk.ShadowType.NONE):
    """
    Wrap the widget in a frame with the requested shadow type
    """
    frame = Gtk.Frame()
    frame.set_shadow_type(shadow_type)
    frame.add(widget)
    return frame

### Useful Named Tuples

class WH(collections.namedtuple("WH", ["width", "height"])):
    __slots__ = ()
    # These operations are compatible with Gdk.Rectangle
    def __sub__(self, other):
        # don't assume other is WH just that it has width and height attributes
        return WH(width=self.width - other.width, height=self.height - other.height)
    def __rsub__(self, other):
        # don't assume other is WH just that it has width and height attributes
        return WH(width=other.width - self.width, height=other.height - self.height)
    def __eq__(self, other):
        # don't assume other is WH just that it has width and height attributes
        return other.width == self.width and other.height == self.height

class XY(collections.namedtuple("XY", ["x", "y"])):
    __slots__ = ()
    # These operations are compatible with Gdk.Rectangle
    def __add__(self, other):
        # don't assume other is XY just that it has x and y attributes
        return XY(x=self.x + other.x, y=self.y + other.y)
    def __sub__(self, other):
        # don't assume other is XY just that it has x and y attributes
        return XY(x=self.x - other.x, y=self.y - other.y)
    def __rsub__(self, other):
        # don't assume other is XY just that it has x and y attributes
        return XY(x=other.x - self.x, y=other.y - self.y)
    def __mul__(self, other):
        # allow scaling
        return XY(x=self.x * other, y=self.y * other)
    def __eq__(self, other):
        # don't assume other is XY just that it has x and y attributes
        return other.x == self.x and other.y == self.y

# A named tuple compatible with Gdk.Rectangle
class RECT(collections.namedtuple("XY", ["x", "y", "width", "height"])):
    __slots__ = ()
    @staticmethod
    def from_xy_wh(xy, wh):
        return RECT(x=xy.x, y=xy.y, width=wh.width, height=wh.height)

### Text Entry

class EntryCompletionMultiWord(Gtk.EntryCompletion):
    """
    Extend EntryCompletion to handle mult-word text.
    """
    def __init__(self, model=None):
        """
        model: an argument to allow the TreeModel to be set at creation.
        """
        Gtk.EntryCompletion.__init__(self)
        if model is not None:
            self.set_model(model)
        self.set_match_func(self.match_func)
        self.connect("match-selected", self.match_selected_cb)
        self.set_popup_set_width(False)
    @staticmethod
    def match_func(completion, key_string, model_iter, _data=None):
        """
        Does the (partial) word in front of the cursor match the item?
        """
        cursor_index = completion.get_entry().get_position()
        pword_start = utils.find_start_last_word(text=key_string, before=cursor_index)
        pword = key_string[pword_start:cursor_index].lower()
        if not pword:
            return False
        text_col = completion.get_text_column()
        model = completion.get_model()
        mword = model.get_value(model_iter, text_col)
        return mword and mword.lower().startswith(pword)
    @staticmethod
    def match_selected_cb(completion, model, model_iter):
        """
        Handle "match-selected" signal.
        """
        entry = completion.get_entry()
        cursor_index = entry.get_position()
        # just in case get_text() is overloaded e.g. to add learning
        text = Gtk.Entry.get_text(entry)
        #
        text_col = completion.get_text_column()
        mword = model.get_value(model_iter, text_col)
        new_text = utils.replace_last_word(text=text, new_word=mword, before=cursor_index)
        entry.set_text(new_text)
        # move the cursor behind the new word
        entry.set_position(cursor_index + len(new_text) - len(text))
        return True

class TextEntryAutoComplete(Gtk.Entry):
    def __init__(self, lexicon=None, learn=True, multiword=True, **kwargs):
        """
        multiword: if True use individual words in entry as the target of autocompletion
        """
        Gtk.Entry.__init__(self, **kwargs)
        self.__multiword = multiword
        if self.__multiword:
            completion = EntryCompletionMultiWord()
        else:
            completion = Gtk.EntryCompletion()
        self.set_completion(completion)
        cell = Gtk.CellRendererText()
        completion.pack_start(cell, expand=True)
        completion.set_text_column(0)
        self.set_lexicon(lexicon)
        self.set_learn(learn)
    def set_lexicon(self, lexicon):
        if lexicon is not None:
            self.get_completion().set_model(lexicon)
    def set_learn(self, enable):
        """
        Set whether learning should happen
        """
        self.learn = enable
    def get_text(self):
        text = Gtk.Entry.get_text(self)
        if self.learn:
            completion = self.get_completion()
            model = completion.get_model()
            text_col = completion.get_text_column()
            lexicon = [row[text_col] for row in model]
            lexicon.sort()
            if self.__multiword:
                new_words = []
                for word in utils.extract_words(text):
                    if not utils.contains(lexicon, word):
                        new_words.append(word)
                for word in new_words:
                    model.append([word])
                self.emit("new-words", new_words)
            else:
                text = text.strip()
                if text not in lexicon:
                    model.append([text])
                    self.emit("new-words", [text])
        return text
GObject.signal_new("new-words", TextEntryAutoComplete, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

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

class ColourableLabel(Gtk.EventBox):
    def __init__(self, label=""):
        Gtk.EventBox.__init__(self)
        self.label = Gtk.Label(label=label)
        self.add(self.label)
        self.show_all()
    def modify_base(self, state, colour):
        Gtk.EventBox.modify_base(self, state, colour)
        self.label.modify_base(state, colour)
    def modify_text(self, state, colour):
        Gtk.EventBox.modify_text(self, state, colour)
        self.label.modify_text(state, colour)
    def modify_fg(self, state, colour):
        Gtk.EventBox.modify_fg(self, state, colour)
        self.label.modify_fg(state, colour)

class ColouredLabel(ColourableLabel):
    def __init__(self, label, colour=None):
        ColourableLabel.__init__(self, label=label)
        if colour is not None:
            self.set_colour(colour)
    def set_colour(self, colour):
        bg_colour = Gdk.Color(*colour)
        fg_colour = best_foreground(colour)
        for state in [Gtk.StateType.NORMAL, Gtk.StateType.PRELIGHT, Gtk.StateType.ACTIVE]:
            self.modify_base(state, bg_colour)
            self.modify_bg(state, bg_colour)
            self.modify_fg(state, fg_colour)
            self.modify_text(state, fg_colour)

class ColouredButton(Gtk.EventBox):
    prelit_width = 2
    unprelit_width = 0
    state_value_ratio = {
        Gtk.StateType.NORMAL: fractions.Fraction(1),
        Gtk.StateType.ACTIVE: fractions.Fraction(1, 2),
        Gtk.StateType.PRELIGHT: fractions.Fraction(1),
        Gtk.StateType.SELECTED: fractions.Fraction(1),
        Gtk.StateType.INSENSITIVE: fractions.Fraction(1, 4)
    }
    def __init__(self, colour=None, label=None):
        self.label = ColouredLabel(label, colour)
        Gtk.EventBox.__init__(self)
        self.set_size_request(25, 25)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.LEAVE_NOTIFY_MASK|Gdk.EventMask.FOCUS_CHANGE_MASK)
        self.connect("button-press-event", self._button_press_cb)
        self.connect("button-release-event", self._button_release_cb)
        self.connect("enter-notify-event", self._enter_notify_cb)
        self.connect("leave-notify-event", self._leave_notify_cb)
        self.frame = Gtk.Frame()
        self.frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.frame.set_border_width(self.unprelit_width)
        self.frame.add(self.label)
        self.add(self.frame)
        if colour is not None:
            self.set_colour(colour)
        self.show_all()
    def _button_press_cb(self, widget, event):
        if event.button != 1:
            return False
        self.frame.set_shadow_type(Gtk.ShadowType.IN)
        self.set_state(Gtk.StateType.ACTIVE)
    def _button_release_cb(self, widget, event):
        if event.button != 1:
            return False
        self.frame.set_shadow_type(Gtk.ShadowType.OUT)
        self.set_state(Gtk.StateType.PRELIGHT)
        self.emit("clicked", int(event.get_state()))
    def _enter_notify_cb(self, widget, event):
        self.frame.set_shadow_type(Gtk.ShadowType.OUT)
        self.frame.set_border_width(self.prelit_width)
        self.set_state(Gtk.StateType.PRELIGHT)
    def _leave_notify_cb(self, widget, event):
        self.frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.frame.set_border_width(self.unprelit_width)
        self.set_state(Gtk.StateType.NORMAL)
    def set_colour(self, colour):
        self.colour = colour
        for state, value_ratio in self.state_value_ratio.items():
            rgb = [min(int(colour[i] * value_ratio), 65535) for i in range(3)]
            bg_gcolour = Gdk.Color(*rgb)
            fg_gcolour = best_foreground(rgb)
            self.modify_base(state, bg_gcolour)
            self.modify_bg(state, bg_gcolour)
            self.modify_fg(state, fg_gcolour)
            self.modify_text(state, fg_gcolour)
        self.label.set_colour(colour)
GObject.signal_new("clicked", ColouredButton, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_INT,))

### Dialogues

class UnsavedChangesDialogue(dialogue.Dialog):
    # TODO: make a better UnsavedChangesDialogue()
    SAVE_AND_CONTINUE, CONTINUE_UNSAVED = range(1, 3)
    def __init__(self, parent, message):
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        buttons += (_("Save and Continue"), UnsavedChangesDialogue.SAVE_AND_CONTINUE)
        buttons += (_("Continue Without Saving"), UnsavedChangesDialogue.CONTINUE_UNSAVED)
        dialogue.Dialog.__init__(self,
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=buttons,
        )
        self.vbox.pack_start(Gtk.Label(message), expand=True, fill=True, padding=0)
        self.show_all()

class Key:
    ESCAPE = Gdk.keyval_from_name("Escape")
    RETURN = Gdk.keyval_from_name("Return")
    TAB = Gdk.keyval_from_name("Tab")
    UP_ARROW = Gdk.keyval_from_name("Up")
    DOWN_ARROW = Gdk.keyval_from_name("Down")

class ArrowButton(Gtk.Button):
    def __init__(self, arrow_type, shadow_type, width=-1, height=-1):
        Gtk.Button.__init__(self)
        self.set_size_request(width, height)
        self.add(Gtk.Arrow(arrow_type, shadow_type))

class HexSpinButton(Gtk.HBox, dialogue.ReporterMixin):
    OFF, INCR, DECR = range(3)
    PAUSE = 500
    INTERVAL = 5
    def __init__(self, max_value, label=None):
        Gtk.HBox.__init__(self)
        if label:
            self.pack_start(label, expand=True, fill=True, padding=0)
        self.__dirn = self.OFF
        self.__value = 0
        self.__max_value = max_value
        self.__current_step = 1
        self.__max_step = max(1, max_value // 32)
        width = 0
        while max_value:
            width += 1
            max_value //= 16
        self.format_str = "0x{0:0>" + str(width) + "X}"
        self.entry = Gtk.Entry(width_chars=width + 2)
        self.pack_start(self.entry, expand=False, fill=True, padding=0)
        self._update_text()
        self.entry.connect("key-press-event", self._key_press_cb)
        self.entry.connect("key-release-event", self._key_release_cb)
        eh = self.entry.size_request().height
        bw = eh * 2 / 3
        bh = eh / 2 -1
        vbox = Gtk.VBox()
        self.pack_start(vbox, expand=False, fill=True, padding=0)
        self.up_arrow = ArrowButton(Gtk.ArrowType.UP, Gtk.ShadowType.NONE, bw, bh)
        self.up_arrow.connect("button-press-event", self._arrow_pressed_cb, self.INCR)
        self.up_arrow.connect("button-release-event", self._arrow_released_cb)
        self.up_arrow.connect("leave-notify-event", self._arrow_released_cb)
        vbox.pack_start(self.up_arrow, expand=True, fill=True, padding=0)
        self.down_arrow = ArrowButton(Gtk.ArrowType.DOWN, Gtk.ShadowType.NONE, bw, bh)
        self.down_arrow.connect("button-press-event", self._arrow_pressed_cb, self.DECR)
        self.down_arrow.connect("button-release-event", self._arrow_released_cb)
        self.down_arrow.connect("leave-notify-event", self._arrow_released_cb)
        vbox.pack_start(self.down_arrow, expand=True, fill=True, padding=0)
    def get_value(self):
        return self.__value
    def set_value(self, value):
        if value < 0 or value > self.__max_value:
            raise ValueError("{0:#X}: NOT in range 0X0 to {1:#X}".format(value, self.__max_value))
        self.__value = value
        self._update_text()
    def _arrow_pressed_cb(self, arrow, event, dirn):
        self.__dirn = dirn
        if self.__dirn is self.INCR:
            if self._incr_value():
                GObject.timeout_add(self.PAUSE, self._iterate_steps)
        elif self.__dirn is self.DECR:
            if self._decr_value():
                GObject.timeout_add(self.PAUSE, self._iterate_steps)
    def _arrow_released_cb(self, arrow, event):
        self.__dirn = self.OFF
    def _incr_value(self, step=1):
        if self.__value >= self.__max_value:
            return False
        self.__value = min(self.__value + step, self.__max_value)
        self._update_text()
        self.emit("value-changed", False)
        return True
    def _decr_value(self, step=1):
        if self.__value <= 0:
            return False
        self.__value = max(self.__value - step, 0)
        self._update_text()
        self.emit("value-changed", False)
        return True
    def _update_text(self):
        self.entry.set_text(self.format_str.format(self.__value))
    def _bump_current_step(self, exponential=True):
        if exponential:
            self.__current_step = min(self.__current_step * 2, self.__max_step)
        else:
            self.__current_step = min(self.__current_step + 1, self.__max_step)
    def _reset_current_step(self):
        self.__current_step = 1
    def _iterate_steps(self):
        keep_going = False
        if self.__dirn is self.INCR:
            keep_going = self._incr_value(self.__current_step)
        elif self.__dirn is self.DECR:
            keep_going = self._decr_value(self.__current_step)
        if keep_going:
            self._bump_current_step()
        else:
            self._reset_current_step()
        return keep_going
    def _key_press_cb(self, entry, event):
        if event.keyval in [Key.RETURN, Key.TAB]:
            try:
                self.set_value(int(entry.get_text(), 16))
                self.emit("value-changed", event.keyval == Key.TAB)
            except ValueError as edata:
                self.report_exception_as_error(edata)
                self._update_text()
            return True # NOTE: this will nobble the "activate" signal
        elif event.keyval == Key.UP_ARROW:
            if self._incr_value(self.__current_step):
                self._bump_current_step(False)
            return True
        elif event.keyval == Key.DOWN_ARROW:
            if self._decr_value(self.__current_step):
                self._bump_current_step(False)
            return True
    def _key_release_cb(self, entry, event):
        if event.keyval in [Key.UP_ARROW, Key.DOWN_ARROW]:
            self._reset_current_step()
            return True
GObject.signal_new("value-changed", HexSpinButton, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_BOOLEAN,))
