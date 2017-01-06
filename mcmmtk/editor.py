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
Edit/create paint colours
'''

import math
import os
import hashlib
import fractions

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import GLib

from .bab import mathx

from .epaint import paint
from .epaint import rgbh

from .gtx import actions
from .gtx import coloured
from .gtx import dialogue
from .gtx import entries
from .gtx import gutils
from .gtx import iview
from .gtx import recollect
from .gtx import screen

from . import options
from . import gpaint
from . import data
from . import icons

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

class UnacceptedChangesDialogue(dialogue.Dialog):
    # TODO: make a better UnacceptedChangesDialogue()
    ACCEPT_CHANGES_AND_CONTINUE, CONTINUE_DISCARDING_CHANGES = range(1, 3)
    def __init__(self, parent, message):
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        buttons += (_('Accept and Continue'), UnacceptedChangesDialogue.ACCEPT_CHANGES_AND_CONTINUE)
        buttons += (_('Continue (Discarding Changes)'), UnacceptedChangesDialogue.CONTINUE_DISCARDING_CHANGES)
        dialogue.Dialog.__init__(self,
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=buttons,
        )
        self.vbox.pack_start(Gtk.Label(message), expand=True, fill=True, padding=0)
        self.show_all()

class UnaddedNewColourDialogue(dialogue.Dialog):
    # TODO: make a better UnaddedNewColourDialogue()
    DISCARD_AND_CONTINUE = 1
    def __init__(self, parent, message):
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        buttons += (_('Discard and Continue'), UnaddedNewColourDialogue.DISCARD_AND_CONTINUE)
        dialogue.Dialog.__init__(self,
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=buttons,
        )
        self.vbox.pack_start(Gtk.Label(message), expand=True, fill=True, padding=0)
        self.show_all()

class PaintSeriesEditor(Gtk.HPaned, actions.CAGandUIManager, dialogue.ReporterMixin):
    UI_DESCR = '''
    <ui>
      <menubar name='paint_series_editor_menubar'>
        <menu action='paint_series_editor_file_menu'>
          <menuitem action='new_paint_series'/>
          <menuitem action='open_paint_series_file'/>
          <menuitem action='save_paint_series_to_file'/>
          <menuitem action='save_paint_series_as_file'/>
          <menuitem action='close_colour_editor'/>
        </menu>
        <menu action='paint_series_editor_samples_menu'>
          <menuitem action='take_screen_sample'/>
          <menuitem action='open_sample_viewer'/>
        </menu>
      </menubar>
    </ui>
    '''
    AC_HAS_COLOUR, AC_NOT_HAS_COLOUR, AC_HAS_FILE, AC_ID_READY, AC_MASK = actions.ActionCondns.new_flags_and_mask(4)
    def __init__(self):
        Gtk.HPaned.__init__(self)
        actions.CAGandUIManager.__init__(self)
        #
        self.set_file_path(None)
        self.set_current_colour(None)
        self.saved_hash = None
        self.__closed = False

        # First assemble the parts
        self.paint_editor = PaintEditor()
        self.paint_editor.connect('changed', self._paint_editor_change_cb)
        self.paint_editor.colour_matcher.sample_display.connect('samples-changed', self._sample_change_cb)
        self.buttons = self.action_groups.create_action_button_box([
            'add_colour_into_series',
            'accept_colour_changes',
            'reset_colour_editor',
            'take_screen_sample',
            'automatch_sample_images_raw',
        ])
        self.paint_colours = PaintColourNotebook()
        self.paint_colours.set_size_request(480, 480)
        self.paint_colours.paint_list.action_groups.connect_activate('edit_selected_colour', self._edit_selected_colour_cb)
        # as these are company names don't split them up for autocompletion
        self.manufacturer_name = entries.TextEntryAutoComplete(data.GENERAL_WORDS_LEXICON, multiword=False)
        self.manufacturer_name.connect('new-words', data.new_general_words_cb)
        self.manufacturer_name.connect('changed', self._id_changed_cb)
        mnlabel = Gtk.Label(label=_('Manufacturer:'))
        self.series_name = entries.TextEntryAutoComplete(data.GENERAL_WORDS_LEXICON)
        self.series_name.connect('new-words', data.new_general_words_cb)
        self.series_name.connect('changed', self._id_changed_cb)
        snlabel = Gtk.Label(label=_('Series:'))
        self.set_current_colour(None)
        # Now arrange them
        vbox = Gtk.VBox()
        table = Gtk.Table(rows=2, columns=2, homogeneous=False)
        table.attach(mnlabel, 0, 1, 0, 1, xoptions=0)
        table.attach(snlabel, 0, 1, 1, 2, xoptions=0)
        table.attach(self.manufacturer_name, 1, 2, 0, 1)
        table.attach(self.series_name, 1, 2, 1, 2)
        vbox.pack_start(table, expand=False, fill=True, padding=0)
        vbox.pack_start(self.paint_colours, expand=True, fill=True, padding=0)
        self.pack1(vbox, resize=True, shrink=False)
        vbox = Gtk.VBox()
        vbox.pack_start(self.paint_editor, expand=True, fill=True, padding=0)
        vbox.pack_start(self.buttons, expand=False, fill=True, padding=0)
        self.pack2(vbox, resize=True, shrink=False)
        self.set_position(recollect.get("editor", "hpaned_position"))
        self.connect("notify", self._notify_cb)
        self.show_all()
    def _notify_cb(self, widget, parameter):
        if parameter.name == "position":
            recollect.set("editor", "hpaned_position", str(widget.get_position()))
    def populate_action_groups(self):
        self.action_groups[gpaint.ColourSampleArea.AC_SAMPLES_PASTED].add_actions([
            ('automatch_sample_images_raw', None, _('Auto Match'), None,
            _('Auto matically match the colour to the sample images.'),
            self._automatch_sample_images_raw_cb),
        ])
        self.action_groups[PaintEditor.AC_READY|self.AC_NOT_HAS_COLOUR].add_actions([
            ('add_colour_into_series', None, _('Add'), None,
            _('Accept this colour and add it to the series.'),
            self._add_colour_into_series_cb),
        ])
        self.action_groups[PaintEditor.AC_READY|self.AC_HAS_COLOUR].add_actions([
            ('accept_colour_changes', None, _('Accept'), None,
            _('Accept the changes made to this colour.'),
            self._accept_colour_changes_cb),
        ])
        self.action_groups[self.AC_HAS_FILE|self.AC_ID_READY].add_actions([
            ('save_paint_series_to_file', Gtk.STOCK_SAVE, None, None,
            _('Save the current series definition to file.'),
            self._save_paint_series_to_file_cb),
        ])
        self.action_groups[self.AC_ID_READY].add_actions([
            ('save_paint_series_as_file', Gtk.STOCK_SAVE_AS, None, None,
            _('Save the current series definition to a user chosen file.'),
            self._save_paint_series_as_file_cb),
        ])
        # TODO: make some of these conditional
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ('paint_series_editor_file_menu', None, _('File')),
            ('paint_series_editor_samples_menu', None, _('Samples')),
            ('reset_colour_editor', None, _('Reset'), None,
            _('Reset the colour editor to its default state.'),
            self._reset_colour_editor_cb),
            ('open_paint_series_file', Gtk.STOCK_OPEN, None, None,
            _('Load a paint series from a file for editing.'),
            self._open_paint_series_file_cb),
            ('take_screen_sample', None, _('Take Sample'), None,
            _('Take a sample of an arbitrary selected section of the screen and add it to the clipboard.'),
            lambda _action: screen.take_screen_sample()),
            ('open_sample_viewer', None, _('Open Sample Viewer'), None,
            _('Open a graphics file containing colour samples.'),
            self._open_sample_viewer_cb),
            ('close_colour_editor', Gtk.STOCK_CLOSE, None, None,
            _('Close this window.'),
            self._close_colour_editor_cb),
            ('new_paint_series', Gtk.STOCK_NEW, None, None,
            _('Start a new paint colour series.'),
            self._new_paint_series_cb),
        ])
    def get_masked_condns(self):
        condns = 0
        if self.current_colour is None:
            condns |= self.AC_NOT_HAS_COLOUR
        else:
            condns |= self.AC_HAS_COLOUR
        if self.file_path is not None:
            condns |= self.AC_HAS_FILE
        if self.manufacturer_name.get_text_length() > 0 and self.series_name.get_text_length() > 0:
            condns |= self.AC_ID_READY
        return actions.MaskedCondns(condns, self.AC_MASK)
    def unsaved_changes_ok(self):
        """
        Check that the last saved definition is up to date
        """
        if not self.colour_edit_state_ok():
            return False
        manl = self.manufacturer_name.get_text_length()
        serl = self.series_name.get_text_length()
        coll = len(self.paint_colours)
        if manl == 0 and serl == 0 and coll == 0:
            return True
        dtext = self.get_definition_text()
        if hashlib.sha1(dtext.encode()).digest() == self.saved_hash:
            return True
        parent = self.get_toplevel()
        dlg = UnsavedChangesDialogue(
            parent=parent if isinstance(parent, Gtk.Window) else None,
            message=_("The series definition has unsaved changes.")
        )
        response = dlg.run()
        dlg.destroy()
        if response == Gtk.ResponseType.CANCEL:
            return False
        elif response == UnsavedChangesDialogue.CONTINUE_UNSAVED:
            return True
        elif self.file_path is not None:
            self.save_to_file(None)
        else:
            self._save_paint_series_as_file_cb(None)
        return True
    def _paint_editor_change_cb(self, widget, *args):
        """
        Update actions' "enabled" statuses based on paint editor condition
        """
        self.action_groups.update_condns(widget.get_masked_condns())
    def _sample_change_cb(self, widget, *args):
        """
        Update actions' "enabled" statuses based on sample area condition
        """
        self.action_groups.update_condns(widget.get_masked_condns())
    def _id_changed_cb(self, widget, *args):
        """
        Update actions' "enabled" statuses based on manufacturer and
        series name state
        """
        if self.manufacturer_name.get_text_length() == 0:
            condns = 0
        elif self.series_name.get_text_length() == 0:
            condns = 0
        else:
            condns = self.AC_ID_READY
        self.action_groups.update_condns(actions.MaskedCondns(condns, self.AC_ID_READY))
    def set_current_colour(self, colour):
        """
        Set a reference to the colour currently being edited and
        update action conditions for this change
        """
        self.current_colour = colour
        mask = self.AC_NOT_HAS_COLOUR + self.AC_HAS_COLOUR
        condns = self.AC_NOT_HAS_COLOUR if colour is None else self.AC_HAS_COLOUR
        self.action_groups.update_condns(actions.MaskedCondns(condns, mask))
    def set_file_path(self, file_path):
        """
        Set the file path for the paint colour series currently being
        edited and update action conditions for this change
        """
        self.file_path = file_path
        condns = 0 if file_path is None else self.AC_HAS_FILE
        self.action_groups.update_condns(actions.MaskedCondns(condns, self.AC_HAS_FILE))
        if condns:
            recollect.set("editor", "last_file", file_path)
        self.emit("file_changed", self.file_path)
    def colour_edit_state_ok(self):
        if self.current_colour is None:
            if self.paint_editor.colour_name.get_text_length() > 0:
                parent = self.get_toplevel()
                msg = _("New colour \"{0}\" has not been added to the series.").format(self.paint_editor.colour_name.get_text())
                dlg = UnaddedNewColourDialogue(parent=parent if isinstance(parent, Gtk.Window) else None,message=msg)
                response = dlg.run()
                dlg.destroy()
                return response == UnaddedNewColourDialogue.DISCARD_AND_CONTINUE
        else:
            edit_colour = self.paint_editor.get_colour()
            changed = False
            if edit_colour.name != self.current_colour.name:
                changed = True
            elif edit_colour.rgb != self.current_colour.rgb:
                changed = True
            elif edit_colour.finish != self.current_colour.finish:
                changed = True
            elif edit_colour.transparency != self.current_colour.transparency:
                changed = True
            if changed:
                parent = self.get_toplevel()
                msg = _("Colour \"{0}\" has changes that have not been accepted.").format(edit_colour.name)
                dlg = UnacceptedChangesDialogue(parent=parent if isinstance(parent, Gtk.Window) else None,message=msg)
                response = dlg.run()
                dlg.destroy()
                if response == UnacceptedChangesDialogue.ACCEPT_CHANGES_AND_CONTINUE:
                    self._accept_colour_changes_cb()
                    return True
                else:
                    return response == UnacceptedChangesDialogue.CONTINUE_DISCARDING_CHANGES
        return True
    def _edit_selected_colour_cb(self, _action):
        """
        Load the selected paint colour into the editor
        """
        colour = self.paint_colours.paint_list.get_selected_colours()[0]
        self.paint_editor.set_colour(colour.name, colour.rgb, colour.transparency, colour.finish)
        self.set_current_colour(colour)
    def _ask_overwrite_ok(self, name):
        title = _('Duplicate Colour Name')
        msg = _('A colour with the name "{0}" already exists.\n Overwrite?').format(name)
        dlg = dialogue.CancelOKDialog(title=title, parent=self.get_toplevel())
        dlg.get_content_area().pack_start(Gtk.Label(msg), expand=True, fill=True, padding=0)
        dlg.show_all()
        response = dlg.run()
        dlg.destroy()
        return response == Gtk.ResponseType.OK
    def _accept_colour_changes_cb(self, _widget=None):
        edited_colour = self.paint_editor.get_colour()
        if edited_colour.name != self.current_colour.name:
            # there's a name change so check for duplicate names
            other_colour = self.paint_colours.get_colour_with_name(edited_colour.name)
            if other_colour is not None:
                if self._ask_overwrite_ok(edited_colour.name):
                    self.paint_colours.remove_colour(other_colour)
                else:
                    return
        self.current_colour.name = edited_colour.name
        self.current_colour.set_rgb(edited_colour.rgb)
        self.current_colour.set_finish(edited_colour.finish)
        self.current_colour.set_transparency(edited_colour.transparency)
        self.paint_colours.queue_draw()
    def _reset_colour_editor_cb(self, _widget):
        if self.colour_edit_state_ok():
            self.paint_editor.reset()
            self.set_current_colour(None)
    def _new_paint_series_cb(self, _action):
        """
        Throw away the current data and prepare to create a new series
        """
        if not self.unsaved_changes_ok():
            return
        self.paint_editor.reset()
        self.paint_colours.clear()
        self.manufacturer_name.set_text('')
        self.series_name.set_text('')
        self.set_file_path(None)
        self.set_current_colour(None)
        self.saved_hash = None
    def _add_colour_into_series_cb(self, _widget):
        new_colour = self.paint_editor.get_colour()
        old_colour = self.paint_colours.get_colour_with_name(new_colour.name)
        if old_colour is not None:
            if not self._ask_overwrite_ok(new_colour.name):
                return
            old_colour.set_rgb(new_colour.rgb)
            old_colour.set_finish(new_colour.finish)
            old_colour.set_transparency(new_colour.transparency)
            self.paint_colours.queue_draw()
            self.set_current_colour(old_colour)
        else:
            self.paint_colours.add_colour(new_colour)
            self.set_current_colour(new_colour)
    def _automatch_sample_images_raw_cb(self, _widget):
        self.paint_editor.auto_match_sample(raw=True)
    def load_fm_file(self, filepath):
        try:
            fobj = open(filepath, 'r')
            text = fobj.read()
            fobj.close()
        except IOError as edata:
            return self.report_io_error(edata)
        try:
            series = paint.Series.fm_definition(text)
        except paint.Series.ParseError as edata:
            return self.alert_user(_("Format Error:  {}: {}").format(edata, filepath))
        # All OK so clear the paint editor and ditch the current colours
        self.paint_editor.reset()
        self.set_current_colour(None)
        self.paint_colours.clear()
        # and load the new ones
        for colour in series.paint_colours.values():
            self.paint_colours.add_colour(colour)
        self.manufacturer_name.set_text(series.series_id.maker)
        self.series_name.set_text(series.series_id.name)
        self.set_file_path(filepath)
        self.saved_hash = hashlib.sha1(text.encode()).digest()
    def _open_paint_series_file_cb(self, _action):
        """
        Ask the user for the name of the file then open it.
        """
        if not self.unsaved_changes_ok():
            return
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title=_('Load Paint Series Description'),
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        if self.file_path:
            lastdir = os.path.dirname(self.file_path)
            dlg.set_current_folder(lastdir)
        else:
            last_file = recollect.get("editor", "last_file")
            if last_file:
                lastdir = os.path.dirname(last_file)
                dlg.set_current_folder(lastdir)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            self.load_fm_file(filepath)
        dlg.destroy()
    def _open_sample_viewer_cb(self, _action):
        """
        Launch a window containing a sample viewer
        """
        SampleViewer(self.get_toplevel()).show()
    def get_definition_text(self):
        """
        Get the text sefinition of the current series
        """
        maker = self.manufacturer_name.get_text()
        name = self.series_name.get_text()
        series = paint.Series(maker=maker, name=name, colours=self.paint_colours.get_colours())
        return series.definition_text()
    def save_to_file(self, filepath=None):
        if filepath is None:
            filepath = self.file_path
        definition = self.get_definition_text()
        try:
            fobj = open(filepath, 'w')
            fobj.write(definition)
            fobj.close()
            # save was successful so set our filepath
            self.set_file_path(filepath)
            self.saved_hash = hashlib.sha1(definition.encode()).digest()
        except IOError as edata:
            return self.report_io_error(edata)
    def _save_paint_series_to_file_cb(self, _action):
        """
        Save the paint series to the current file
        """
        self.save_to_file(None)
    def _save_paint_series_as_file_cb(self, _action):
        """
        Ask the user for the name of the file then open it.
        """
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title='Save Paint Series Description',
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        dlg.set_do_overwrite_confirmation(True)
        if self.file_path:
            lastdir = os.path.dirname(self.file_path)
            dlg.set_current_folder(lastdir)
        else:
            last_file = recollect.get("editor", "last_file")
            if last_file:
                lastdir = os.path.dirname(last_file)
                dlg.set_current_folder(lastdir)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            self.save_to_file(filepath)
        dlg.destroy()
    def _close_colour_editor_cb(self, _action):
        """
        Close the Paint Series Editor
        """
        if not self.unsaved_changes_ok():
            return
        self.__closed = True
        self.get_toplevel().destroy()
    def _exit_colour_editor_cb(self, _action):
        """
        Exit the Paint Series Editor
        """
        if not self.__closed and not self.unsaved_changes_ok():
            return
        Gtk.main_quit()
GObject.signal_new('file_changed', PaintSeriesEditor, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

class PaintEditor(Gtk.VBox):
    AC_READY, AC_NOT_READY, AC_MASK = actions.ActionCondns.new_flags_and_mask(2)

    def __init__(self):
        Gtk.VBox.__init__(self)
        #
        table = Gtk.Table(rows=3, columns=2, homogeneous=False)
        # Colour Name
        stext =  Gtk.Label(label=_('Colour Name:'))
        table.attach(stext, 0, 1, 0, 1, xoptions=0)
        self.colour_name = entries.TextEntryAutoComplete(data.COLOUR_NAME_LEXICON)
        self.colour_name.connect('new-words', data.new_paint_words_cb)
        self.colour_name.connect('changed', self._changed_cb)
        table.attach(self.colour_name, 1, 2, 0, 1)
        # Colour Transparence
        stext =  Gtk.Label(label=_('Transparency:'))
        table.attach(stext, 0, 1, 1, 2, xoptions=0)
        self.colour_transparency = gpaint.TransparencyChoice()
        self.colour_transparency.connect('changed', self._changed_cb)
        table.attach(self.colour_transparency, 1, 2, 1, 2)
        # Colour Finish
        stext =  Gtk.Label(label=_('Finish:'))
        table.attach(stext, 0, 1, 2, 3, xoptions=0)
        self.colour_finish = gpaint.FinishChoice()
        self.colour_finish.connect('changed', self._changed_cb)
        table.attach(self.colour_finish, 1, 2, 2, 3)
        self.pack_start(table, expand=False, fill=True, padding=0)
        # Matcher
        self.colour_matcher = ColourSampleMatcher()
        self.pack_start(self.colour_matcher, expand=True, fill=True, padding=0)
        #
        self.show_all()
    def _changed_cb(self, widget):
        # pass on any change signals (including where they came from)
        self.emit('changed', widget)
    def reset(self):
        self.colour_matcher.sample_display.erase_samples()
        self.colour_matcher.set_colour(None)
        self.colour_name.set_text('')
        self.colour_finish.set_active(-1)
        self.colour_transparency.set_active(-1)
    def get_colour(self):
        name = self.colour_name.get_text()
        rgb = self.colour_matcher.colour.rgb
        transparency = self.colour_transparency.get_selection()
        finish = self.colour_finish.get_selection()
        return paint.NamedColour(name=name, rgb=rgb, transparency=transparency, finish=finish)
    def set_colour(self, name, rgb, transparency, finish):
        self.colour_matcher.set_colour(rgb)
        self.colour_name.set_text(name)
        self.colour_finish.set_selection(str(finish))
        self.colour_transparency.set_selection(str(transparency))
    def auto_match_sample(self, raw=False):
        self.colour_matcher.auto_match_sample(raw)
    def get_masked_condns(self):
        if self.colour_name.get_text_length() == 0:
            return actions.MaskedCondns(self.AC_NOT_READY, self.AC_MASK)
        if self.colour_transparency.get_active() == -1:
            return actions.MaskedCondns(self.AC_NOT_READY, self.AC_MASK)
        if self.colour_transparency.get_active() == -1:
            return actions.MaskedCondns(self.AC_NOT_READY, self.AC_MASK)
        return actions.MaskedCondns(self.AC_READY, self.AC_MASK)
GObject.signal_new('changed', PaintEditor, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

class ColourSampleMatcher(Gtk.VBox):
    HUE_DISPLAY_SPAN =  math.pi / 10
    VALUE_DISPLAY_INCR = fractions.Fraction(1, 10)
    DEFAULT_COLOUR = paint.Colour(paint.RGB.WHITE / 2)
    DELTA_HUE = [mathx.Angle(math.pi / x) for x in [200, 100, 50]]
    DELTA_VALUE = [0.0025, 0.005, 0.01]
    DELTA_CHROMA = [0.0025, 0.005, 0.01]
    DEFAULT_AUTO_MATCH_RAW = True
    class HueClockwiseButton(coloured.ColouredButton):
        def __init__(self):
            coloured.ColouredButton.__init__(self, label='->')
        def set_colour(self, colour):
            if options.get('colour_wheel', 'red_to_yellow_clockwise'):
                new_colour = colour.hcv.get_rotated_rgb(ColourSampleMatcher.HUE_DISPLAY_SPAN)
            else:
                new_colour = colour.hcv.get_rotated_rgb(-ColourSampleMatcher.HUE_DISPLAY_SPAN)
            coloured.ColouredButton.set_colour(self, new_colour)
    class HueAntiClockwiseButton(coloured.ColouredButton):
        def __init__(self):
            coloured.ColouredButton.__init__(self, label='<-')
        def set_colour(self, colour):
            if options.get('colour_wheel', 'red_to_yellow_clockwise'):
                new_colour = colour.hcv.get_rotated_rgb(-ColourSampleMatcher.HUE_DISPLAY_SPAN)
            else:
                new_colour = colour.hcv.get_rotated_rgb(ColourSampleMatcher.HUE_DISPLAY_SPAN)
            coloured.ColouredButton.set_colour(self, new_colour)
    class IncrValueButton(coloured.ColouredButton):
        def __init__(self):
            coloured.ColouredButton.__init__(self, label=_('Value')+'++')
        def set_colour(self, colour):
            value = min(colour.hcv.value + ColourSampleMatcher.VALUE_DISPLAY_INCR, fractions.Fraction(1))
            coloured.ColouredButton.set_colour(self, colour.hcv.hue_rgb_for_value(value))
    class DecrValueButton(coloured.ColouredButton):
        def __init__(self):
            coloured.ColouredButton.__init__(self, label=_('Value')+'--')
        def set_colour(self, colour):
            value = max(colour.hcv.value - ColourSampleMatcher.VALUE_DISPLAY_INCR, fractions.Fraction(0))
            coloured.ColouredButton.set_colour(self, colour.hcv.hue_rgb_for_value(value))
    class IncrGraynessButton(coloured.ColouredButton):
        def __init__(self):
            coloured.ColouredButton.__init__(self, label=_('Grayness') + '++')
        def set_colour(self, colour):
            coloured.ColouredButton.set_colour(self, colour.value_rgb())
    class DecrGraynessButton(coloured.ColouredButton):
        def __init__(self):
            coloured.ColouredButton.__init__(self, label=_('Grayness') + '--')
        def set_colour(self, colour):
            coloured.ColouredButton.set_colour(self, colour.hcv.hue_rgb_for_value())
    def __init__(self, auto_match_on_paste=False):
        Gtk.VBox.__init__(self)
        self._delta = 256 # must be a power of two
        self.auto_match_on_paste = auto_match_on_paste
        # Add RGB entry field
        self.rgb_entry = gpaint.RGBEntryBox()
        self.rgb_entry.connect("colour-changed", self._rgb_entry_changed_cb)
        self.pack_start(self.rgb_entry, expand=False, fill=True, padding=0)
        self.hcv_display = gpaint.HCVDisplay()
        self.pack_start(self.hcv_display, expand=False, fill=True, padding=0)
        # Add value modification buttons
        # Lighten
        hbox = Gtk.HBox()
        self.incr_value_button = self.IncrValueButton()
        hbox.pack_start(self.incr_value_button, expand=True, fill=True, padding=0)
        self.incr_value_button.connect('clicked', self.incr_value_cb)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        # Add anti clockwise hue angle modification button
        hbox = Gtk.HBox()
        self.hue_acw_button = self.HueAntiClockwiseButton()
        hbox.pack_start(self.hue_acw_button, expand=False, fill=True, padding=0)
        self.hue_acw_button.connect('clicked', self.modify_hue_acw_cb)
        # Add the sample display panel
        self.sample_display = gpaint.ColourSampleArea()
        self.sample_display.connect("samples_changed", self._sample_change_cb)
        hbox.pack_start(self.sample_display, expand=True, fill=True, padding=0)
        # Add anti clockwise hue angle modification button
        self.hue_cw_button = self.HueClockwiseButton()
        hbox.pack_start(self.hue_cw_button, expand=False, fill=True, padding=0)
        self.hue_cw_button.connect('clicked', self.modify_hue_cw_cb)
        self.pack_start(hbox, expand=True, fill=True, padding=0)
        # Darken
        hbox = Gtk.HBox()
        self.decr_value_button = self.DecrValueButton()
        hbox.pack_start(self.decr_value_button, expand=True, fill=True, padding=0)
        self.decr_value_button.connect('clicked', self.decr_value_cb)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        # Grayness
        hbox = Gtk.HBox()
        self.decr_grayness_button = self.DecrGraynessButton()
        hbox.pack_start(self.decr_grayness_button, expand=True, fill=True, padding=0)
        self.decr_grayness_button.connect('clicked', self.decr_grayness_cb)
        self.incr_grayness_button = self.IncrGraynessButton()
        hbox.pack_start(self.incr_grayness_button, expand=True, fill=True, padding=0)
        self.incr_grayness_button.connect('clicked', self.incr_grayness_cb)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        #
        self.set_colour(None)
        #
        self.show_all()
    def set_colour(self, colour):
        colour = paint.Colour(colour) if colour is not None else self.DEFAULT_COLOUR
        self.rgb_manipulator = rgbh.RGBManipulator(colour.rgb)
        self._set_colour(colour)
    def _set_colour_fm_manipulator(self):
        self._set_colour(paint.Colour(self.rgb_manipulator.get_rgb(paint.RGB)))
    def _set_colour(self, colour):
        self.colour = colour
        self.rgb_entry.set_colour(self.colour)
        self.sample_display.set_bg_colour(self.colour.rgb)
        self.hue_cw_button.set_colour(self.colour)
        self.hue_acw_button.set_colour(self.colour)
        self.incr_value_button.set_colour(self.colour)
        self.decr_value_button.set_colour(self.colour)
        self.incr_grayness_button.set_colour(self.colour)
        self.decr_grayness_button.set_colour(self.colour)
        self.hcv_display.set_colour(self.colour)
    def _auto_match_sample(self, samples, raw):
        total = [0, 0, 0]
        npixels = 0
        for sample in samples:
            assert sample.get_bits_per_sample() == 8
            nc = sample.get_n_channels()
            rs = sample.get_rowstride()
            width = sample.get_width()
            n_rows = sample.get_height()
            data = list(sample.get_pixels())
            for row_num in range(n_rows):
                row_start = row_num * rs
                for j in range(width):
                    offset = row_start + j * nc
                    for i in range(3):
                        total[i] += data[offset + i]
            npixels += width * n_rows
        rgb = paint.RGB(*(paint.RGB.ROUND((total[i] << 8) / npixels) for i in range(3)))
        if raw:
            self.set_colour(rgb)
        else:
            self.set_colour(paint.HCV(rgb).hue_rgb_for_value())
    def auto_match_sample(self, raw):
        samples = self.sample_display.get_samples()
        if samples:
            self._auto_match_sample(samples, raw)
    def _sample_change_cb(self, widget, *args):
        if self.auto_match_on_paste:
            self.auto_match_sample(raw=self.DEFAULT_AUTO_MATCH_RAW)
    def _rgb_entry_changed_cb(self, entry):
        self.set_colour(entry.get_colour())
    def _get_delta_index(self, modifier_button_states):
        if modifier_button_states & Gdk.ModifierType.CONTROL_MASK:
            return 0
        elif modifier_button_states & Gdk.ModifierType.SHIFT_MASK:
            return 2
        else:
            return 1
    def incr_grayness_cb(self, button, state):
        if self.rgb_manipulator.decr_chroma(self.DELTA_CHROMA[self._get_delta_index(state)]):
            self._set_colour_fm_manipulator()
        else:
            # let the user know that we're at the limit
            Gdk.beep()
    def decr_grayness_cb(self, button, state):
        if self.rgb_manipulator.incr_chroma(self.DELTA_CHROMA[self._get_delta_index(state)]):
            self._set_colour_fm_manipulator()
        else:
            # let the user know that we're at the limit
            Gdk.beep()
    def incr_value_cb(self, button, state):
        if self.rgb_manipulator.incr_value(self.DELTA_VALUE[self._get_delta_index(state)]):
            self._set_colour_fm_manipulator()
        else:
            # let the user know that we're at the limit
            Gdk.beep()
    def decr_value_cb(self, button, state):
        if self.rgb_manipulator.decr_value(self.DELTA_VALUE[self._get_delta_index(state)]):
            self._set_colour_fm_manipulator()
        else:
            # let the user know that we're at the limit
            Gdk.beep()
    def modify_hue_acw_cb(self, button, state):
        if not options.get('colour_wheel', 'red_to_yellow_clockwise'):
            if self.rgb_manipulator.rotate_hue(self.DELTA_HUE[self._get_delta_index(state)]):
                self._set_colour_fm_manipulator()
            else:
                Gdk.beep()
        else:
            if self.rgb_manipulator.rotate_hue(-self.DELTA_HUE[self._get_delta_index(state)]):
                self._set_colour_fm_manipulator()
            else:
                Gdk.beep()
    def modify_hue_cw_cb(self, button, state):
        if not options.get('colour_wheel', 'red_to_yellow_clockwise'):
            if self.rgb_manipulator.rotate_hue(-self.DELTA_HUE[self._get_delta_index(state)]):
                self._set_colour_fm_manipulator()
            else:
                Gdk.beep()
        else:
            if self.rgb_manipulator.rotate_hue(self.DELTA_HUE[self._get_delta_index(state)]):
                self._set_colour_fm_manipulator()
            else:
                Gdk.beep()

class PaintColourNotebook(gpaint.HueWheelNotebook):
    class ColourListView(gpaint.ColourListView):
        UI_DESCR = '''
            <ui>
                <popup name='colour_list_popup'>
                    <menuitem action='edit_selected_colour'/>
                    <menuitem action='remove_selected_colours'/>
                </popup>
            </ui>
            '''
        def populate_action_groups(self):
            """
            Populate action groups ready for UI initialization.
            """
            self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
                [
                    ('edit_selected_colour', Gtk.STOCK_EDIT, None, None,
                     _('Load the selected colour into the paint editor.'), ),
                ]
            )
    def __init__(self):
        gpaint.HueWheelNotebook.__init__(self)
        self.paint_list = PaintColourNotebook.ColourListView()
        self.append_page(gutils.wrap_in_scrolled_window(self.paint_list), Gtk.Label(label=_('Paint Colours')))
        self.paint_list.get_model().connect('colour-removed', self._colour_removed_cb)
    def __len__(self):
        """
        Return the number of colours currently held
        """
        return len(self.paint_list.model)
    def _colour_removed_cb(self, model, colour):
        """
        Delete colour deleted from the list from the wheels also.
        """
        gpaint.HueWheelNotebook.del_colour(self, colour)
    def add_colour(self, new_colour):
        gpaint.HueWheelNotebook.add_colour(self, new_colour)
        self.paint_list.get_model().append_colour(new_colour)
    def remove_colour(self, colour):
        # 'colour-removed' callback will get the wheels
        self.paint_list.get_model().remove_colour(colour)
    def clear(self):
        """
        Remove all colours from the notebook
        """
        for colour in self.paint_list.get_model().get_colours():
            gpaint.HueWheelNotebook.del_colour(self, colour)
        self.paint_list.get_model().clear()
    def get_colour_with_name(self, colour_name):
        """
        Return the colour with the given name of None if not found
        """
        return self.paint_list.get_model().get_colour_with_name(colour_name)
    def get_colours(self):
        """
        Return all colours as a list in the current order
        """
        return self.paint_list.get_model().get_colours()

class TopLevelWindow(dialogue.MainWindow):
    """
    A top level window wrapper around a palette
    """
    def __init__(self):
        dialogue.MainWindow.__init__(self)
        self.parse_geometry(recollect.get("editor", "last_geometry"))
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.editor = PaintSeriesEditor()
        self.editor.action_groups.get_action('close_colour_editor').set_visible(False)
        self.editor.connect("file_changed", self._file_changed_cb)
        self.editor.set_file_path(None)
        self._menubar = self.editor.ui_manager.get_widget('/paint_series_editor_menubar')
        self.connect("destroy", self.editor._exit_colour_editor_cb)
        self.connect("configure-event", self._configure_event_cb)
        vbox = Gtk.VBox()
        vbox.pack_start(self._menubar, expand=False, fill=True, padding=0)
        vbox.pack_start(self.editor, expand=True, fill=True, padding=0)
        self.add(vbox)
        self.show_all()
    def _file_changed_cb(self, widget, file_path):
        self.set_title(_('mcmmtk: Paint Series Editor: {0}').format(file_path))
    def _configure_event_cb(self, widget, event):
        recollect.set("editor", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))

class SampleViewer(Gtk.Window, actions.CAGandUIManager):
    """
    A top level window for a colour sample file
    """
    UI_DESCR = '''
    <ui>
      <menubar name='colour_sample_menubar'>
        <menu action='colour_sample_file_menu'>
          <menuitem action='open_colour_sample_file'/>
          <menuitem action='close_colour_sample_viewer'/>
        </menu>
      </menubar>
    </ui>
    '''
    TITLE_TEMPLATE = _('mcmmtk: Colour Sample: {}')
    def __init__(self, parent):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        actions.CAGandUIManager.__init__(self)
        last_size = recollect.get("sample_viewer", "last_size")
        if last_size:
            self.set_default_size(*eval(last_size))
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_size_request(300, 200)
        last_samples_file = recollect.get('sample_viewer', 'last_file')
        if os.path.isfile(last_samples_file):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(last_samples_file)
            except GLib.GError:
                pixbuf = None
                last_samples_file = None
        else:
            pixbuf = None
            last_samples_file = None
        self.set_title(self.TITLE_TEMPLATE.format(None if last_samples_file is None else os.path.relpath(last_samples_file)))
        self.pixbuf_view = iview.PixbufView()
        self._menubar = self.ui_manager.get_widget('/colour_sample_menubar')
        self.buttons = self.pixbuf_view.action_groups.create_action_button_box([
            'zoom_in',
            'zoom_out',
        ])
        vbox = Gtk.VBox()
        vbox.pack_start(self._menubar, expand=False, fill=True, padding=0)
        vbox.pack_start(self.pixbuf_view, expand=True, fill=True, padding=0)
        vbox.pack_start(self.buttons, expand=False, fill=True, padding=0)
        self.add(vbox)
        self.connect("size-allocate", self._size_allocation_cb)
        self.show_all()
        self.pixbuf_view.set_pixbuf(pixbuf)
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ('colour_sample_file_menu', None, _('File')),
            ('open_colour_sample_file', Gtk.STOCK_OPEN, None, None,
            _('Load a colour sample file.'),
            self._open_colour_sample_file_cb),
            ('close_colour_sample_viewer', Gtk.STOCK_CLOSE, None, None,
            _('Close this window.'),
            self._close_colour_sample_viewer_cb),
        ])
    def _size_allocation_cb(self, widget, allocation):
        recollect.set("sample_viewer", "last_size", "({0.width}, {0.height})".format(allocation))
    def _open_colour_sample_file_cb(self, _action):
        """
        Ask the user for the name of the file then open it.
        """
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title=_('Open Colour Sample File'),
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        last_samples_file = recollect.get('sample_viewer', 'last_file')
        last_samples_dir = None if last_samples_file is None else os.path.dirname(last_samples_file)
        if last_samples_dir:
            dlg.set_current_folder(last_samples_dir)
        gff = Gtk.FileFilter()
        gff.set_name(_('Image Files'))
        gff.add_pixbuf_formats()
        dlg.add_filter(gff)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            dlg.destroy()
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(filepath)
            except GLib.GError:
                msg = _('{}: Problem extracting image from file.').format(filepath)
                dialogue.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text=msg).run()
                return
            recollect.set('sample_viewer', 'last_file', filepath)
            self.set_title(self.TITLE_TEMPLATE.format(None if filepath is None else os.path.relpath(filepath)))
            self.pixbuf_view.set_pixbuf(pixbuf)
        else:
            dlg.destroy()
    def _close_colour_sample_viewer_cb(self, _action):
        self.get_toplevel().destroy()

def get_avg_rgb_for_samples(samples):
    total = [0, 0, 0]
    npixels = 0
    for sample in samples:
        assert sample.get_bits_per_sample() == 8
        nc = sample.get_n_channels()
        rs = sample.get_rowstride()
        width = sample.get_width()
        n_rows = sample.get_height()
        data = [ord(b) for b in sample.get_pixels()]
        for row_num in range(n_rows):
            row_start = row_num * rs
            for j in range(width):
                offset = row_start + j * nc
                for i in range(3):
                    total[i] += data[offset + i]
        npixels += width * n_rows
    return paint.RGB(*((total[i] / npixels) << 8 for i in range(3)))
