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

from .epaint import paint

from .gtx import actions
from .gtx import coloured
from .gtx import dialogue
from .gtx import entries
from .gtx import gutils
from .gtx import iview
from .gtx import printer
from .gtx import recollect
from .gtx import screen
from .gtx import tlview

from . import gpaint
from . import icons
from . import data
from . import editor
from . import config

def pango_rgb_str(rgb, bits_per_channel=16):
    """
    Convert an rgb to a Pango colour description string
    """
    string = '#'
    for i in range(3):
        string += '{0:02X}'.format(rgb[i] >> (bits_per_channel - 8))
    return string

class Mixer(Gtk.VBox, actions.CAGandUIManager, dialogue.AskerMixin):
    UI_DESCR = '''
    <ui>
        <menubar name='mixer_menubar'>
            <menu action='mixer_file_menu'>
                <menuitem action='print_mixer'/>
                <menuitem action='quit_mixer'/>
            </menu>
            <menu action='reference_resource_menu'>
                <menuitem action='open_reference_image_viewer'/>
            </menu>
        </menubar>
    </ui>
    '''
    AC_HAVE_MIXTURE, AC_MASK = actions.ActionCondns.new_flags_and_mask(1)
    AC_HAVE_TARGET, AC_DONT_HAVE_TARGET, AC_TARGET_MASK = actions.ActionCondns.new_flags_and_mask(2)
    def __init__(self):
        Gtk.VBox.__init__(self)
        actions.CAGandUIManager.__init__(self)
        self.action_groups.update_condns(actions.MaskedCondns(self.AC_DONT_HAVE_TARGET, self.AC_TARGET_MASK))
        # Components
        self.notes = entries.TextEntryAutoComplete(data.GENERAL_WORDS_LEXICON)
        self.notes.connect("new-words", data.new_general_words_cb)
        self.next_name_label = Gtk.Label(label=_("#???:"))
        self.current_target_colour = None
        self.current_colour_description = entries.TextEntryAutoComplete(data.COLOUR_NAME_LEXICON)
        self.current_colour_description.connect("new-words", data.new_paint_words_cb)
        self.mixpanel = gpaint.ColourMatchArea()
        self.mixpanel.set_size_request(240, 240)
        self.hcvw_display = gpaint.HCVDisplay()
        self.paint_colours = ColourPartsSpinButtonBox()
        self.paint_colours.connect('remove-colour', self._remove_paint_colour_cb)
        self.paint_colours.connect('contributions-changed', self._contributions_changed_cb)
        self.mixed_colours = MatchedColourListStore()
        self.mixed_colours_view = MatchedColourListView(self.mixed_colours)
        self.mixed_colours_view.action_groups.connect_activate('remove_selected_colours', self._remove_mixed_colours_cb)
        self.mixed_count = 0
        self.wheels = gpaint.HueWheelNotebook()
        self.wheels.set_size_request(360, 360)
        self.wheels.set_wheels_colour_info_acb(self._show_wheel_colour_details_cb)
        self.buttons = self.action_groups.create_action_button_box([
            'new_mixed_colour',
            'accept_mixed_colour',
            'simplify_contributions',
            'reset_contributions',
            'remove_unused_paints'
        ])
        menubar = self.ui_manager.get_widget('/mixer_menubar')
        # Lay out components
        self.pack_start(menubar, expand=False, fill=True, padding=0)
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_('Notes:')), expand=False, fill=True, padding=0)
        hbox.pack_start(self.notes, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        hpaned = Gtk.HPaned()
        hpaned.pack1(self.wheels, resize=True, shrink=False)
        vbox = Gtk.VBox()
        vhbox = Gtk.HBox()
        vhbox.pack_start(self.next_name_label, expand=False, fill=True, padding=0)
        vhbox.pack_start(self.current_colour_description, expand=True, fill=True, padding=0)
        vbox.pack_start(vhbox, expand=False, fill=True, padding=0)
        vbox.pack_start(self.hcvw_display, expand=False, fill=True, padding=0)
        vbox.pack_start(gutils.wrap_in_frame(self.mixpanel, Gtk.ShadowType.ETCHED_IN), expand=True, fill=True, padding=0)
        hpaned.pack2(vbox, resize=True, shrink=False)
        vpaned = Gtk.VPaned()
        vpaned.pack1(hpaned, resize=True, shrink=False)
        vbox = Gtk.VBox()
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_('Paints:')), expand=False, fill=True, padding=0)
        hbox.pack_start(self.paint_colours, expand=True, fill=True, padding=0)
        vbox.pack_start(hbox, expand=False, fill=True, padding=0)
        vbox.pack_start(self.buttons, expand=False, fill=True, padding=0)
        vbox.pack_start(gutils.wrap_in_scrolled_window(self.mixed_colours_view), expand=True, fill=True, padding=0)
        vpaned.pack2(vbox, resize=True, shrink=False)
        self.pack_start(vpaned, expand=True, fill=True, padding=0)
        vpaned.set_position(recollect.get("mixer", "vpaned_position"))
        hpaned.set_position(recollect.get("mixer", "hpaned_position"))
        vpaned.connect("notify", self._paned_notify_cb)
        hpaned.connect("notify", self._paned_notify_cb)
        self.paint_series_manager = PaintSeriesManager()
        self.paint_series_manager.connect('add-paint-colours', self._add_colours_to_mixer_cb)
        menubar.insert(self.paint_series_manager.menu, 1)
        self.show_all()
        self.recalculate_colour([])
    def _paned_notify_cb(self, widget, parameter):
        if parameter.name == "position":
            if isinstance(widget, Gtk.HPaned):
                recollect.set("mixer", "hpaned_position", str(widget.get_position()))
            else:
                recollect.set("mixer", "vpaned_position", str(widget.get_position()))
    def populate_action_groups(self):
        """
        Set up the actions for this component
        """
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ('mixer_file_menu', None, _('File')),
            ('reference_resource_menu', None, _('Reference Resources')),
            ('remove_unused_paints', None, _('Remove Unused Paints'), None,
            _('Remove all unused paints from the mixer.'),
            self._remove_unused_paints_cb),
            ('quit_mixer', Gtk.STOCK_QUIT, None, None,
            _('Quit this program.'),
            self._quit_mixer_cb),
            ('open_reference_image_viewer', None, _('Open Image Viewer'), None,
            _('Open a tool for viewing reference images.'),
            self._open_reference_image_viewer_cb),
            ('print_mixer', Gtk.STOCK_PRINT, None, None,
            _('Print a text description of the mixer.'),
            self._print_mixer_cb),
        ])
        self.action_groups[self.AC_HAVE_MIXTURE].add_actions([
            ('simplify_contributions', None, _('Simplify'), None,
            _('Simplify all paint contributions (by dividing by their greatest common divisor).'),
            self._simplify_contributions_cb),
            ('reset_contributions', None, _('Reset'), None,
            _('Reset all paint contributions to zero.'),
            self._reset_contributions_cb),
        ])
        self.action_groups[self.AC_HAVE_MIXTURE|self.AC_HAVE_TARGET].add_actions([
            ('accept_mixed_colour', None, _('Accept'), None,
            _('Accept/finalise this colour and add it to the list of  mixed colours.'),
            self._accept_mixed_colour_cb),
        ])
        self.action_groups[self.AC_DONT_HAVE_TARGET].add_actions([
            ('new_mixed_colour', None, _('New'), None,
            _('Start working on a new mixed colour.'),
            self._new_mixed_colour_cb),
        ])
    def _show_wheel_colour_details_cb(self, _action, wheel):
        colour = wheel.popup_colour
        if isinstance(colour, paint.NamedMixedColour):
            MixedColourInformationDialogue(colour, self.mixed_colours.get_target_colour(colour)).show()
        else:
            gpaint.PaintColourInformationDialogue(colour).show()
        return True
    def __str__(self):
        paint_colours = self.paint_colours.get_colours()
        if len(paint_colours) == 0:
            return _('Empty Mix/Match Description')
        string = _('Paint Colours:\n')
        for pcol in paint_colours:
            string += '{0}: {1}: {2}\n'.format(pcol.name, pcol.series.series_id.maker, pcol.series.series_id.name)
        num_mixed_colours = len(self.mixed_colours)
        if num_mixed_colours == 0:
            return string
        # Print the list in the current order chosen by the user
        string += _('Mixed Colours:\n')
        for mc in self.mixed_colours.get_colours():
            string += '{0}: {1}\n'.format(mc.name, round(mc.value, 2))
            for cc, parts in mc.blobs:
                if isinstance(cc, paint.PaintColour):
                    string += '\t {0}:\t{1}: {2}: {3}\n'.format(parts, cc.name, cc.series.series_id.maker, cc.series.series_id.name)
                else:
                    string += '\t {0}:\t{1}\n'.format(parts, cc.name)
        return string
    def pango_markup_chunks(self):
        """
        Format the palette description as a list of Pango markup chunks
        """
        paint_colours = self.paint_colours.get_colours()
        if len(paint_colours) == 0:
            return [cgi.escape(_('Empty Mix/Match Description'))]
        # TODO: add paint series data in here
        string = '<b>' + cgi.escape(_('Mix/Match Description:')) + '</b> '
        string += cgi.escape(time.strftime('%X: %A %x')) + '\n'
        if self.notes.get_text_length() > 0:
            string += '\n{0}\n'.format(cgi.escape(self.notes.get_text()))
        chunks = [string]
        string = '<b>' + cgi.escape(_('Paint Colours:')) + '</b>\n\n'
        for pcol in paint_colours:
            string += '<span background="{0}">\t</span> '.format(pango_rgb_str(pcol))
            string += '{0}\n'.format(cgi.escape(pcol.name))
        chunks.append(string)
        string = '<b>' + cgi.escape(_('Mixed Colours:')) + '</b>\n\n'
        for tmc in self.mixed_colours.named():
            mc = tmc.colour
            tc = tmc.target_colour
            string += '<span background="{0}">\t</span>'.format(pango_rgb_str(mc))
            string += '<span background="{0}">\t</span>'.format(pango_rgb_str(mc.value_rgb()))
            string += '<span background="{0}">\t</span>'.format(pango_rgb_str(mc.hue_rgb))
            string += ' {0}: {1}\n'.format(cgi.escape(mc.name), cgi.escape(mc.notes))
            string += '<span background="{0}">\t</span>'.format(pango_rgb_str(tc.rgb))
            string += '<span background="{0}">\t</span>'.format(pango_rgb_str(tc.value_rgb()))
            string += '<span background="{0}">\t</span> Target Colour\n'.format(pango_rgb_str(tc.hue.rgb))
            for blob in mc.blobs:
                string += '{0: 7d}:'.format(blob.parts)
                string += '<span background="{0}">\t</span>'.format(pango_rgb_str(blob.colour))
                string += ' {0}\n'.format(cgi.escape(blob.colour.name))
            chunks.append(string)
            string = '' # Necessary because we put header in the first chunk
        return chunks
    def _contributions_changed_cb(self, _widget, contributions):
        self.recalculate_colour(contributions)
    def recalculate_colour(self, contributions):
        new_colour = paint.MixedColour(contributions)
        self.mixpanel.set_bg_colour(new_colour.rgb)
        self.hcvw_display.set_colour(new_colour)
        if len(contributions) > 0:
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_MIXTURE, self.AC_MASK))
        else:
            self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_MASK))
    def _accept_mixed_colour_cb(self,_action):
        self.simplify_parts()
        paint_contribs = self.paint_colours.get_contributions()
        if len(paint_contribs) < 1:
            return
        self.mixed_count += 1
        name = _('Mix #{:03d}').format(self.mixed_count)
        notes = self.current_colour_description.get_text()
        new_colour = paint.NamedMixedColour(blobs=paint_contribs, name=name, notes=notes)
        self.mixed_colours.append_colour(new_colour, self.current_target_colour)
        self.wheels.add_colour(new_colour)
        self.reset_parts()
        self.paint_colours.set_sensitive(False)
        self.mixpanel.clear()
        self.current_colour_description.set_text("")
        self.wheels.add_target_colour(name, self.current_target_colour)
        self.current_target_colour = None
        self.hcvw_display.set_target_colour(None)
        self.wheels.unset_crosshair()
        self.paint_series_manager.unset_target_colour()
        self.action_groups.update_condns(actions.MaskedCondns(self.AC_DONT_HAVE_TARGET, self.AC_TARGET_MASK))
        self.next_name_label.set_text(_("#???:"))
        self.current_colour_description.set_text("")
    def _new_mixed_colour_cb(self,_action):
        dlg = NewMixedColourDialogue(self.mixed_count + 1, self.get_parent())
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            descr = dlg.colour_description.get_text()
            assert len(descr) > 0
            self.mixpanel.set_target_colour(dlg.colour_specifier.colour)
            self.current_colour_description.set_text(descr)
            self.current_target_colour = dlg.colour_specifier.colour
            self.hcvw_display.set_target_colour(self.current_target_colour)
            self.wheels.set_crosshair(self.current_target_colour)
            self.paint_series_manager.set_target_colour(self.current_target_colour)
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_TARGET, self.AC_TARGET_MASK))
            self.next_name_label.set_text(_("#{:03d}:").format(self.mixed_count + 1))
            self.paint_colours.set_sensitive(True)
        dlg.destroy()
    def reset_parts(self):
        self.paint_colours.reset_parts()
    def _reset_contributions_cb(self, _action):
        self.reset_parts()
    def simplify_parts(self):
        self.paint_colours.simplify_parts()
    def _simplify_contributions_cb(self, _action):
        self.simplify_parts()
    def add_paint(self, paint_colour):
        self.paint_colours.add_colour(paint_colour)
        self.wheels.add_colour(paint_colour)
    def del_paint(self, paint_colour):
        self.paint_colours.del_colour(paint_colour)
        self.wheels.del_colour(paint_colour)
    def del_mixed(self, mixed):
        self.mixed_colours.remove_colour(mixed)
        self.wheels.del_colour(mixed)
        self.wheels.del_target_colour(mixed.name)
    def _add_colours_to_mixer_cb(self, selector, colours):
        for pcol in colours:
            if not self.paint_colours.has_colour(pcol):
                self.add_paint(pcol)
    def _remove_paint_colour_cb(self, widget, colour):
        """
        Respond to a request from a paint colour to be removed
        """
        users = self.mixed_colours.get_colour_users(colour)
        if len(users) > 0:
            string = _('Colour: "{0}" is used in:\n').format(colour)
            for user in users:
                string += '\t{0}\n'.format(user.name)
            dlg = dialogue.ScrolledMessageDialog(text=string)
            Gdk.beep()
            dlg.run()
            dlg.destroy()
        else:
            self.del_paint(colour)
    def _remove_mixed_colours_cb(self, _action):
        colours = self.mixed_colours_view.get_selected_colours()
        if len(colours) == 0:
            return
        msg = _("The following mixed colours are about to be deleted:\n")
        for colour in colours:
            msg += "\t{0}: {1}\n".format(colour.name, colour.notes)
        msg += _("and will not be recoverable. OK?")
        if self.ask_ok_cancel(msg):
            for colour in colours:
                self.del_mixed(colour)
    def _remove_unused_paints_cb(self, _action):
        colours = self.paint_colours.get_colours_with_zero_parts()
        for colour in colours:
            if len(self.mixed_colours.get_colour_users(colour)) == 0:
                self.del_paint(colour)
    def _print_mixer_cb(self, _action):
        """
        Print the mixer as simple text
        """
        # TODO: make printing more exotic
        printer.print_markup_chunks(self.pango_markup_chunks())
    def _open_reference_image_viewer_cb(self, _action):
        """
        Launch a window containing a reference image viewer
        """
        ReferenceImageViewer(self.get_toplevel()).show()
    def _quit_mixer_cb(self, _action):
        """
        Exit the program
        """
        # TODO: add checks for unsaved work in mixer before exiting
        Gtk.main_quit()

def colour_parts_adjustment():
    return Gtk.Adjustment(0, 0, 999, 1, 10, 0)

class ColourPartsSpinButton(Gtk.EventBox, actions.CAGandUIManager):
    UI_DESCR = '''
        <ui>
            <popup name='colour_spinner_popup'>
                <menuitem action='paint_colour_info'/>
                <menuitem action='remove_me'/>
            </popup>
        </ui>
        '''
    def __init__(self, colour, sensitive=False, *kwargs):
        Gtk.EventBox.__init__(self)
        actions.CAGandUIManager.__init__(self, popup='/colour_spinner_popup')
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.set_size_request(85, 40)
        self.colour = colour
        self.entry = Gtk.SpinButton()
        self.entry.set_adjustment(colour_parts_adjustment())
        self.entry.set_numeric(True)
        self.entry.connect('button_press_event', self._button_press_cb)
        self.set_tooltip_text(str(colour))
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        hbox = Gtk.HBox()
        hbox.pack_start(coloured.ColouredLabel(self.colour.name, self.colour), expand=True, fill=True, padding=0)
        vbox = Gtk.VBox()
        vbox.pack_start(gpaint.ColouredRectangle(self.colour), expand=True, fill=True, padding=0)
        vbox.pack_start(self.entry, expand=False, fill=True, padding=0)
        vbox.pack_start(gpaint.ColouredRectangle(self.colour), expand=True, fill=True, padding=0)
        hbox.pack_start(vbox, expand=False, fill=True, padding=0)
        hbox.pack_start(gpaint.ColouredRectangle(self.colour, (5, -1)), expand=False, fill=True, padding=0)
        frame.add(hbox)
        self.add(frame)
        self.set_sensitive(sensitive)
        self.show_all()
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_DONT_CARE].add_actions(
            [
                ('paint_colour_info', Gtk.STOCK_INFO, None, None,
                 _('Detailed information for this paint colour.'),
                 self._paint_colour_info_cb
                ),
                ('remove_me', Gtk.STOCK_REMOVE, None, None,
                 _('Remove this paint colour from the mixer.'),
                ),
            ]
        )
    def get_parts(self):
        return self.entry.get_value_as_int()
    def set_parts(self, parts):
        return self.entry.set_value(parts)
    def divide_parts(self, divisor):
        return self.entry.set_value(self.entry.get_value_as_int() / divisor)
    def get_blob(self):
        return paint.BLOB(self.colour, self.get_parts())
    def set_sensitive(self, sensitive):
        self.entry.set_sensitive(sensitive)
    def _paint_colour_info_cb(self, _action):
        gpaint.PaintColourInformationDialogue(self.colour).show()

class ColourPartsSpinButtonBox(Gtk.VBox):
    """
    A dynamic array of coloured spinners
    """
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.__spinbuttons = []
        self.__hboxes = []
        self.__count = 0
        self.__ncols = 6
        self.__sensitive = False
        self.__suppress_change_notification = False
    def set_sensitive(self, sensitive):
        self.__sensitive = sensitive
        for sb in self.__spinbuttons:
            sb.set_sensitive(sensitive)
    def add_colour(self, colour):
        """
        Add a spinner for the given colour to the box
        """
        spinbutton = ColourPartsSpinButton(colour, self.__sensitive)
        spinbutton.action_groups.connect_activate('remove_me', self._remove_me_cb, spinbutton)
        spinbutton.entry.connect('value-changed', self._spinbutton_value_changed_cb)
        self.__spinbuttons.append(spinbutton)
        self._pack_append(spinbutton)
        self.show_all()
    def _pack_append(self, spinbutton):
        if self.__count % self.__ncols == 0:
            self.__hboxes.append(Gtk.HBox())
            self.pack_start(self.__hboxes[-1], expand=False, fill=True, padding=0)
        self.__hboxes[-1].pack_start(spinbutton, expand=True, fill=True, padding=0)
        self.__count += 1
    def _unpack_all(self):
        """
        Unpack all the spinbuttons and hboxes
        """
        for hbox in self.__hboxes:
            for child in hbox.get_children():
                hbox.remove(child)
            self.remove(hbox)
        self.__hboxes = []
        self.__count = 0
    def _remove_me_cb(self, _action, spinbutton):
        """
        Signal anybody who cares that spinbutton.colour should be removed
        """
        self.emit('remove-colour', spinbutton.colour)
    def _spinbutton_value_changed_cb(self, spinbutton):
        """
        Signal those interested that our contributions have changed
        """
        if not self.__suppress_change_notification:
            self.emit('contributions-changed', self.get_contributions())
    def del_colour(self, colour):
        # do this the easy way by taking them all out and putting back
        # all but the one to be deleted
        self._unpack_all()
        for spinbutton in self.__spinbuttons[:]:
            if spinbutton.colour == colour:
                self.__spinbuttons.remove(spinbutton)
            else:
                self._pack_append(spinbutton)
        self.show_all()
    def get_colours(self):
        return [spinbutton.colour for spinbutton in self.__spinbuttons]
    def get_colours_with_zero_parts(self):
        return [spinbutton.colour for spinbutton in self.__spinbuttons if spinbutton.get_parts() == 0]
    def has_colour(self, colour):
        """
        Do we already contain the given colour?
        """
        for spinbutton in self.__spinbuttons:
            if spinbutton.colour == colour:
                return True
        return False
    def get_contributions(self):
        """
        Return a list of paint colours with non zero parts
        """
        return [spinbutton.get_blob() for spinbutton in self.__spinbuttons if spinbutton.get_parts() > 0]
    def simplify_parts(self):
        gcd = mathx.gcd(*[sb.get_parts() for sb in self.__spinbuttons])
        if gcd is not None and gcd > 1:
            self.__suppress_change_notification = True
            for spinbutton in self.__spinbuttons:
                spinbutton.divide_parts(gcd)
            self.__suppress_change_notification = False
            self.emit('contributions-changed', self.get_contributions())
    def reset_parts(self):
        """
        Reset all spinbutton values to zero
        """
        self.__suppress_change_notification = True
        for spinbutton in self.__spinbuttons:
            spinbutton.set_parts(0)
        self.__suppress_change_notification = False
        self.emit('contributions-changed', self.get_contributions())
GObject.signal_new('remove-colour', ColourPartsSpinButtonBox, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))
GObject.signal_new('contributions-changed', ColourPartsSpinButtonBox, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

class PartsColourListStore(gpaint.ColourListStore):
    ROW = paint.BLOB
    TYPES = ROW(colour=object, parts=int)

    def append_colour(self, colour):
        self.append(self.ROW(parts=0, colour=colour))
    def get_parts(self, colour):
        """
        Return the number of parts selected for the given colour
        """
        model_iter = self.find_named(lambda x: x.colour == colour)
        if model_iter is None:
            raise LookupError()
        return self.get_value_named(model_iter, 'parts')
    def reset_parts(self):
        """
        Reset the number of parts for all colours to zero
        """
        model_iter = self.get_iter_first()
        while model_iter is not None:
            self.set_value_named(model_iter, 'parts', 0)
            model_iter = self.iter_next(model_iter)
        self.emit('contributions-changed', [])
    def get_contributions(self):
        """
        Return a list of MODEL.ROW() tuples where parts is greater than zero
        """
        return [row for row in self.named() if row.parts > 0]
    def get_colour_users(self, colour):
        return [row.colour for row in self.named() if row.colour.contains_colour(colour)]
    def process_parts_change(self, blob):
        """
        Work out contributions with modifications in blob.
        This is necessary because the parts field in the model hasn't
        been updated yet as it causes a "jerky" appearance in the
        CellRendererSpin due to SpinButton being revreated every time
        an edit starts and updating the model causes restart of edit.
        """
        contributions = []
        for row in self.named():
            if row.colour == blob.colour:
                if blob.parts > 0:
                    contributions.append(blob)
            elif row.parts > 0:
                contributions.append(row)
        self.emit('contributions-changed', contributions)
    def _parts_value_changed_cb(self, cell, path, spinbutton):
        """
        Change the model for a change to a spinbutton value
        """
        new_parts = spinbutton.get_value_as_int()
        row = self.get_row(self.get_iter(path))
        self.process_parts_change(paint.BLOB(colour=row.colour, parts=new_parts))
    def _notes_edited_cb(self, cell, path, new_text):
        self[path][0].notes = new_text
GObject.signal_new('contributions-changed', PartsColourListStore, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT, ))

def notes_cell_data_func(column, cell, model, model_iter, *args):
    colour = model.get_value_named(model_iter, 'colour')
    cell.set_property('text', colour.notes)
    cell.set_property('background-gdk', colour.to_gdk_color())
    cell.set_property('foreground-gdk', colour.best_foreground_gdk_color())

def generate_colour_parts_list_spec(view, model):
    """
    Generate the specification for a paint colour parts list
    """
    parts_col_spec = tlview.ColumnSpec(
        title =_('Parts'),
        properties={},
        sort_key_function=lambda row: row.parts,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=tlview.CellRendererSpin,
                    expand=None,
                    properties={'editable' : True, 'adjustment' : colour_parts_adjustment(), 'width-chars' : 8},
                    signal_handlers = {"value-changed" : model._parts_value_changed_cb},
                    start=False
                ),
                cell_data_function_spec=None,
                attributes={'text' : model.col_index('parts')}
            ),
        ]
    )
    notes_col_spec = tlview.ColumnSpec(
        title =_('Notes'),
        properties={'resizable' : True, 'expand' : True},
        sort_key_function=lambda row: row.colour.notes,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties={'editable' : True, },
                    signal_handlers = {"edited" : model._notes_edited_cb},
                    start=False
                ),
                cell_data_function_spec=tlview.CellDataFunctionSpec(
                    function=notes_cell_data_func,
                ),
                attributes={}
            ),
        ]
    )
    name_col_spec = gpaint.colour_attribute_column_spec(gpaint.TNS(_('Name'), 'name', {}, lambda row: row.colour.name))
    attr_cols_specs = [gpaint.colour_attribute_column_spec(tns) for tns in gpaint.COLOUR_ATTRS[1:]]
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.MULTIPLE,
        columns=[parts_col_spec, name_col_spec, notes_col_spec] + attr_cols_specs
    )

class PartsColourListView(gpaint.ColourListView):
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='show_colour_details'/>
            <menuitem action='remove_selected_colours'/>
        </popup>
    </ui>
    '''
    MODEL = PartsColourListStore
    SPECIFICATION = generate_colour_parts_list_spec
    def __init__(self, *args, **kwargs):
        gpaint.ColourListView.__init__(self, *args, **kwargs)
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
            [
                ('show_colour_details', Gtk.STOCK_INFO, None, None,
                 _('Show a detailed description of the selected colour.'),
                self._show_colour_details_cb),
            ],
        )
        #self.action_groups[actions.AC_SELN_MADE].add_actions(
            #[
                #('remove_selected_colours', Gtk.STOCK_REMOVE, None, None,
                 #_('Remove the selected colours from the list.'), ),
            #]
        #)
    def _show_colour_details_cb(self, _action):
        colour = self.get_selected_colours()[0]
        gpaint.PaintColourInformationDialogue(colour).show()

MATCH = collections.namedtuple('MATCH', ['colour', 'target_colour'])

class MatchedColourListStore(gpaint.ColourListStore):
    ROW = MATCH
    TYPES = ROW(colour=object, target_colour=object)

    def append_colour(self, colour, target_colour):
        self.append(self.ROW(target_colour=target_colour, colour=colour))
    def get_colour_users(self, colour):
        return [row.colour for row in self.named() if row.colour.contains_colour(colour)]
    def get_target_colour(self, colour):
        """
        Return the target colour for the given colour
        """
        model_iter = self.find_named(lambda x: x.colour == colour)
        if model_iter is None:
            raise LookupError()
        return self.get_value_named(model_iter, 'target_colour')
    def _notes_edited_cb(self, cell, path, new_text):
        self[path][0].notes = new_text

def match_cell_data_func(column, cell, model, model_iter, attribute):
    colour = model.get_value_named(model_iter, 'target_colour')
    cell.set_property('background-gdk', colour.to_gdk_color())

def generate_matched_colour_list_spec(view, model):
    """
    Generate the specification for a paint colour parts list
    """
    matched_col_spec = tlview.ColumnSpec(
        title =_('Matched'),
        properties={},
        sort_key_function=lambda row: row.target_colour.hue,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties=None,
                    start=False
                ),
                cell_data_function_spec=tlview.CellDataFunctionSpec(
                    function=match_cell_data_func,
                ),
                attributes={}
            ),
        ]
    )
    notes_col_spec = tlview.ColumnSpec(
        title =_('Notes'),
        properties={'resizable' : True, 'expand' : True},
        sort_key_function=lambda row: row.colour.notes,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties={'editable' : True, },
                    signal_handlers = {"edited" : model._notes_edited_cb},
                    start=False
                ),
                cell_data_function_spec=tlview.CellDataFunctionSpec(
                    function=notes_cell_data_func,
                ),
                attributes={}
            ),
        ]
    )
    name_col_spec = gpaint.colour_attribute_column_spec(gpaint.TNS(_('Name'), 'name', {}, lambda row: row.colour.name))
    attr_cols_specs = [gpaint.colour_attribute_column_spec(tns) for tns in gpaint.COLOUR_ATTRS[1:]]
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.MULTIPLE,
        columns=[name_col_spec, matched_col_spec, notes_col_spec] + attr_cols_specs
    )

class MatchedColourListView(gpaint.ColourListView):
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='show_colour_details'/>
            <menuitem action='remove_selected_colours'/>
        </popup>
    </ui>
    '''
    MODEL = MatchedColourListStore
    SPECIFICATION = generate_matched_colour_list_spec
    def __init__(self, *args, **kwargs):
        gpaint.ColourListView.__init__(self, *args, **kwargs)
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
            [
                ('show_colour_details', Gtk.STOCK_INFO, None, None,
                 _('Show a detailed description of the selected colour.'),
                self._show_colour_details_cb),
            ],
        )
        #self.action_groups[actions.AC_SELN_MADE].add_actions(
            #[
                #('remove_selected_colours', Gtk.STOCK_REMOVE, None, None,
                 #_('Remove the selected colours from the list.'), ),
            #]
        #)
    def _show_colour_details_cb(self, _action):
        selected_rows = self.MODEL.get_selected_rows(self.get_selection())
        colour = selected_rows[0].colour
        if isinstance(colour, paint.NamedMixedColour):
            MixedColourInformationDialogue(colour, selected_rows[0].target_colour).show()
        else:
            gpaint.PaintColourInformationDialogue(colour).show()

class SelectColourListView(gpaint.ColourListView):
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='show_colour_details'/>
            <menuitem action='add_colours_to_mixer'/>
        </popup>
    </ui>
    '''
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
            [
                ('show_colour_details', Gtk.STOCK_INFO, None, None,
                 _('Show a detailed description of the selected colour.'),),
            ]
        )
        self.action_groups[actions.AC_SELN_MADE].add_actions(
            [
                ('add_colours_to_mixer', Gtk.STOCK_ADD, None, None,
                 _('Add the selected colours to the mixer.'),),
            ]
        )

class PaintColourSelector(Gtk.VBox):
    """
    A widget for adding paint colours to the mixer
    """
    def __init__(self, paint_series):
        Gtk.VBox.__init__(self)
        # components
        self.wheels = gpaint.HueWheelNotebook(popup='/colour_wheel_AI_popup')
        self.wheels.set_wheels_add_colour_acb(self._add_wheel_colour_to_mixer_cb)
        self.paint_colours_view = SelectColourListView()
        self.paint_colours_view.set_size_request(240, 360)
        model = self.paint_colours_view.get_model()
        for colour in paint_series.paint_colours.values():
            model.append_colour(colour)
            self.wheels.add_colour(colour)
        maker = Gtk.Label(label=_('Manufacturer: {0}'.format(paint_series.series_id.maker)))
        sname = Gtk.Label(label=_('Series Name: {0}'.format(paint_series.series_id.name)))
        # make connections
        self.paint_colours_view.action_groups.connect_activate('show_colour_details', self._show_colour_details_cb)
        self.paint_colours_view.action_groups.connect_activate('add_colours_to_mixer', self._add_colours_to_mixer_cb)
        # lay the components out
        self.pack_start(sname, expand=False, fill=True, padding=0)
        self.pack_start(maker, expand=False, fill=True, padding=0)
        hpaned = Gtk.HPaned()
        hpaned.pack1(self.wheels, resize=True, shrink=False)
        hpaned.pack2(gutils.wrap_in_scrolled_window(self.paint_colours_view), resize=True, shrink=False)
        self.pack_start(hpaned, expand=True, fill=True, padding=0)
        hpaned.set_position(recollect.get("paint_colour_selector", "hpaned_position"))
        hpaned.connect("notify", self._hpaned_notify_cb)
        self.show_all()
    def set_target_colour(self, target_colour):
        if target_colour is None:
            self.wheels.unset_crosshair()
        else:
            self.wheels.set_crosshair(target_colour)
    def unset_target_colour(self):
        self.wheels.unset_crosshair()
    def _hpaned_notify_cb(self, widget, parameter):
        if parameter.name == "position":
            recollect.set("paint_colour_selector", "hpaned_position", str(widget.get_position()))
    def _show_colour_details_cb(self, _action):
        colour = self.paint_colours_view.get_selected_colours()[0]
        gpaint.PaintColourInformationDialogue(colour).show()
    def _add_colours_to_mixer_cb(self, _action):
        """
        Add the currently selected colours to the mixer.
        """
        self.emit('add-paint-colours', self.paint_colours_view.get_selected_colours())
    def _add_wheel_colour_to_mixer_cb(self, _action, wheel):
        """
        Add the currently selected colours to the mixer.
        """
        self.emit('add-paint-colours', [wheel.popup_colour])
GObject.signal_new('add-paint-colours', PaintColourSelector, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

class PaintSeriesManager(GObject.GObject, dialogue.ReporterMixin):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.__target_colour = None
        self.__series_dict = dict()
        self._load_series_data()
        open_menu, remove_menu = self._build_submenus()
        menu = Gtk.Menu()
        # Open
        self.__open_item = Gtk.MenuItem(_("Open"))
        self.__open_item.set_submenu(open_menu)
        self.__open_item.set_tooltip_text(_("Open a paint series paint selector."))
        self.__open_item.show()
        menu.append(self.__open_item)
        # Add
        add_menu = Gtk.MenuItem(_("Load"))
        add_menu.set_tooltip_text(_("Load a paint series from a file."))
        add_menu.show()
        add_menu.connect("activate", self._add_paint_series_cb)
        menu.append(add_menu)
        # Remove
        self.__remove_item = Gtk.MenuItem(_("Remove"))
        self.__remove_item.set_submenu(remove_menu)
        self.__remove_item.set_tooltip_text(_("Remove a paint series from the application."))
        self.__remove_item.show()
        menu.append(self.__remove_item)
        #
        self.__menu = Gtk.MenuItem(_("Paint Colour Series"))
        self.__menu.set_submenu(menu)
    @property
    def menu(self):
        return self.__menu
    def set_target_colour(self, colour):
        self.__target_colour = colour
        for sdata in self.__series_dict.values():
            sdata["selector"].set_target_colour(colour)
    def unset_target_colour(self):
        self.__target_colour = None
        for sdata in self.__series_dict.values():
            sdata["selector"].unset_target_colour()
    def _add_series_from_file(self, filepath):
        # Check and see if this file is already loaded
        for series, sdata in self.__series_dict.items():
            if filepath == sdata["filepath"]:
                self.alert_user(_("File \"{0}\" is already loaded providing series \"{1.series_id.maker}: {1.series_id.name}\".\nAborting.").format(filepath, series))
                return None
        # We let the clients handle any exceptions
        fobj = open(filepath, 'r')
        text = fobj.read()
        fobj.close()
        series = paint.Series.fm_definition(text)
        # All OK so we can add this series to our dictionary
        selector = PaintColourSelector(series)
        selector.set_target_colour(self.__target_colour)
        selector.connect('add-paint-colours', self._add_colours_to_mixer_cb)
        self.__series_dict[series] = { "selector" : selector, "filepath" : filepath }
        return series
    def _load_series_data(self):
        assert len(self.__series_dict) == 0
        io_errors = []
        format_errors = []
        for filepath in config.read_series_file_names():
            try:
                self._add_series_from_file(filepath)
            except IOError as edata:
                io_errors.append(edata)
                continue
            except paint.Series.ParseError as edata:
                format_errors.append((edata, filepath))
                continue
        if io_errors or format_errors:
            msg = _("The following errors occured loading paint series data:\n")
            for edata in io_errors:
                msg += "\t{0}: {1}\n".format(edata.filename, edata.strerror)
            for edata, filepath in format_errors:
                msg += "\t{0}: Format Error: {1}\n".format(filepath, str(edata))
            self.alert_error(msg)
            # Remove the offending files from the saved list
            config.write_series_file_names([value["filepath"] for value in self.__series_dict.values()])
    def _build_submenus(self):
        open_menu = Gtk.Menu()
        remove_menu = Gtk.Menu()
        for series in sorted(self.__series_dict.keys()):
            label = "{0.maker}: {0.name}".format(series.series_id)
            for menu, cb in [(open_menu, self._open_paint_series_cb), (remove_menu, self._remove_paint_series_cb)]:
                menu_item = Gtk.MenuItem(label)
                menu_item.connect("activate", cb, series)
                menu_item.show()
                menu.append(menu_item)
        return (open_menu, remove_menu)
    def _rebuild_submenus(self):
        open_menu, remove_menu = self._build_submenus()
        self.__open_item.remove_submenu()
        self.__open_item.set_submenu(open_menu)
        self.__remove_item.remove_submenu()
        self.__remove_item.set_submenu(remove_menu)
    def _add_paint_series_cb(self, widget):
        dlg = Gtk.FileChooserDialog(
            title='Select Paint Series Description File',
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        last_paint_file = recollect.get('paint_series_selector', 'last_file')
        last_paint_dir = None if last_paint_file is None else os.path.dirname(last_paint_file)
        if last_paint_dir:
            dlg.set_current_folder(last_paint_dir)
        response = dlg.run()
        filepath = dlg.get_filename()
        dlg.destroy()
        if response != Gtk.ResponseType.OK:
            return
        try:
            series = self._add_series_from_file(filepath)
        except IOError as edata:
            return self.report_io_error(edata)
        except paint.Series.ParseError as edata:
            return self.alert_user(_("Format Error:  {}: {}").format(edata, filepath))
        if series is None:
            return
        # All OK this series is in our dictionary
        last_paint_file = recollect.set('paint_series_selector', 'last_file', filepath)
        config.write_series_file_names([value["filepath"] for value in self.__series_dict.values()])
        self._rebuild_submenus()
        self._open_paint_series_cb(None, series)
    def _open_paint_series_cb(self, widget, series):
        sdata = self.__series_dict[series]
        presenter = sdata.get("presenter", None)
        if presenter is not None:
            presenter.present()
            return
        # put it in a window and show it
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        last_size = recollect.get("paint_colour_selector", "last_size")
        if last_size:
            window.set_default_size(*eval(last_size))
        window.set_icon_from_file(icons.APP_ICON_FILE)
        window.set_title(_("Paint Series: {0.maker}: {0.name}").format(series.series_id))
        window.add(sdata["selector"])
        window.connect('destroy', self._destroy_selector_cb, series)
        window.connect('size-allocate', self._selector_size_allocation_cb)
        sdata["presenter"] = window
        window.show()
        return True
    def _selector_size_allocation_cb(self, widget, allocation):
        recollect.set("paint_colour_selector", "last_size", "({0.width}, {0.height})".format(allocation))
    def _destroy_selector_cb(self, widget, series):
        del self.__series_dict[series]["presenter"]
        widget.remove(self.__series_dict[series]["selector"])
        widget.destroy()
    def _remove_paint_series_cb(self, widget, series):
        sde = self.__series_dict[series]
        del self.__series_dict[series]
        config.write_series_file_names([value["filepath"] for value in self.__series_dict.values()])
        self._rebuild_submenus()
        if "presenter" in sde:
            sde["presenter"].destroy()
        sde["selector"].destroy()
    def _add_colours_to_mixer_cb(self, widget, paint_colours):
        # pass the parcel :-)
        self.emit('add-paint-colours', paint_colours)
GObject.signal_new('add-paint-colours', PaintSeriesManager, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

class TopLevelWindow(dialogue.MainWindow):
    """
    A top level window wrapper around a mixer
    """
    def __init__(self):
        dialogue.MainWindow.__init__(self)
        self.parse_geometry(recollect.get("mixer", "last_geometry"))
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_title('mcmmtk: Mixer')
        self.mixer = Mixer()
        self.connect("destroy", self.mixer._quit_mixer_cb)
        self.connect("configure-event", self._configure_event_cb)
        self.add(self.mixer)
        self.show_all()
    def _configure_event_cb(self, widget, event):
        recollect.set("mixer", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))

class ReferenceImageViewer(Gtk.Window, actions.CAGandUIManager):
    """
    A top level window for a colour sample file
    """
    UI_DESCR = '''
    <ui>
      <menubar name='reference_image_menubar'>
        <menu action='reference_image_file_menu'>
          <menuitem action='open_reference_image_file'/>
          <menuitem action='close_reference_image_viewer'/>
        </menu>
      </menubar>
    </ui>
    '''
    TITLE_TEMPLATE = _('mcmmtk: Reference Image: {}')
    def __init__(self, parent):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        actions.CAGandUIManager.__init__(self)
        last_size = recollect.get("reference_image_viewer", "last_size")
        if last_size:
            self.set_default_size(*eval(last_size))
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_size_request(300, 200)
        last_image_file = recollect.get('reference_image_viewer', 'last_file')
        if os.path.isfile(last_image_file):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(last_image_file)
            except GLib.GError:
                pixbuf = None
                last_image_file = None
        else:
            pixbuf = None
            last_image_file = None
        self.set_title(self.TITLE_TEMPLATE.format(None if last_image_file is None else os.path.relpath(last_image_file)))
        self.ref_image = iview.PixbufView()
        self._menubar = self.ui_manager.get_widget('/reference_image_menubar')
        #self.buttons = self.ref_image.action_groups.create_action_button_box([
            #'zoom_in',
            #'zoom_out',
        #])
        vbox = Gtk.VBox()
        vbox.pack_start(self._menubar, expand=False, fill=True, padding=0)
        vbox.pack_start(self.ref_image, expand=True, fill=True, padding=0)
        #vbox.pack_start(self.buttons, expand=False, fill=True, padding=0)
        self.add(vbox)
        #self.set_transient_for(parent)
        self.connect("size-allocate", self._size_allocation_cb)
        self.show_all()
        if pixbuf is not None:
            self.ref_image.set_pixbuf(pixbuf)
    def _size_allocation_cb(self, widget, allocation):
        recollect.set("reference_image_viewer", "last_size", "({0.width}, {0.height})".format(allocation))
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ('reference_image_file_menu', None, _('File')),
            ('open_reference_image_file', Gtk.STOCK_OPEN, None, None,
            _('Load an image file for reference.'),
            self._open_reference_image_file_cb),
            ('close_reference_image_viewer', Gtk.STOCK_CLOSE, None, None,
            _('Close this window.'),
            self._close_reference_image_viewer_cb),
        ])
    def _open_reference_image_file_cb(self, _action):
        """
        Ask the user for the name of the file then open it.
        """
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title=_('Open Image File'),
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        last_image_file = recollect.get('reference_image_viewer', 'last_file')
        last_samples_dir = None if last_image_file is None else os.path.dirname(last_image_file)
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
            recollect.set('reference_image_viewer', 'last_file', filepath)
            self.set_title(self.TITLE_TEMPLATE.format(None if filepath is None else os.path.relpath(filepath)))
            self.ref_image.set_pixbuf(pixbuf)
        else:
            dlg.destroy()
    def _close_reference_image_viewer_cb(self, _action):
        self.get_toplevel().destroy()

class NewMixedColourDialogue(dialogue.Dialog):
    def __init__(self, number, parent=None):
        dialogue.Dialog.__init__(self, title=_("New Mixed Colour: #{:03d}").format(number),
                            parent=parent,
                            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                                     Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
                            )
        vbox = self.get_content_area()
        self.colour_description = entries.TextEntryAutoComplete(data.COLOUR_NAME_LEXICON)
        self.colour_description.connect("new-words", data.new_paint_words_cb)
        self.colour_description.connect('changed', self._description_changed_cb)
        self.set_response_sensitive(Gtk.ResponseType.ACCEPT, len(self.colour_description.get_text()) > 0)
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_("Description:")), expand=False, fill=True, padding=0)
        hbox.pack_start(self.colour_description, expand=True, fill=True, padding=0)
        vbox.pack_start(hbox, expand=False, fill=True, padding=0)
        self.colour_specifier = editor.ColourSampleMatcher(auto_match_on_paste=True)
        vbox.pack_start(self.colour_specifier, expand=True, fill=True, padding=0)
        button = Gtk.Button(_("Take Screen Sample"))
        button.connect("clicked", lambda _button: screen.take_screen_sample())
        vbox.pack_start(button, expand=False, fill=True, padding=0)
        vbox.show_all()
    def _description_changed_cb(self, widget):
        self.set_response_sensitive(Gtk.ResponseType.ACCEPT, len(self.colour_description.get_text()) > 0)

def generate_components_list_spec(view, model):
    """
    Generate the specification for a mixed colour components list
    """
    parts_col_spec = tlview.ColumnSpec(
        title =_('Parts'),
        properties={},
        sort_key_function=lambda row: row.parts,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties={'width-chars' : 8},
                    start=False
                ),
                cell_data_function_spec=None,
                attributes={'text' : model.col_index('parts')}
            ),
        ]
    )
    name_col_spec = gpaint.colour_attribute_column_spec(gpaint.TNS(_('Name'), 'name', {'expand' : True}, lambda row: row.colour.name))
    attr_cols_specs = [gpaint.colour_attribute_column_spec(tns) for tns in gpaint.COLOUR_ATTRS[1:]]
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.SINGLE,
        columns=[parts_col_spec, name_col_spec] + attr_cols_specs
    )

class ComponentsListView(PartsColourListView):
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='show_colour_details'/>
        </popup>
    </ui>
    '''
    MODEL = PartsColourListStore
    SPECIFICATION = generate_components_list_spec

    def _set_cell_connections(self):
        pass

class MixedColourInformationDialogue(dialogue.Dialog):
    """
    A dialog to display the detailed information for a mixed colour
    """

    def __init__(self, colour, target_colour, parent=None):
        dialogue.Dialog.__init__(self, title=_('Mixed Colour: {}').format(colour.name), parent=parent)
        last_size = recollect.get("mixed_colour_information", "last_size")
        if last_size:
            self.set_default_size(*last_size)
        vbox = self.get_content_area()
        vbox.pack_start(coloured.ColouredLabel(colour.name, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(coloured.ColouredLabel(colour.notes, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(coloured.ColouredLabel(_("Target"), target_colour.rgb), expand=False, fill=True, padding=0)
        thcvd = gpaint.HCVDisplay(colour, target_colour)
        vbox.pack_start(thcvd, expand=False, fill=True, padding=0)
        vbox.pack_start(Gtk.Label(colour.transparency.description()), expand=False, fill=True, padding=0)
        vbox.pack_start(Gtk.Label(colour.finish.description()), expand=False, fill=True, padding=0)
        self.cview = ComponentsListView()
        for component in colour.blobs:
            self.cview.model.append(component)
        vbox.pack_start(self.cview, expand=False, fill=True, padding=0)
        self.connect("configure-event", self._configure_event_cb)
        vbox.show_all()
    def _configure_event_cb(self, widget, allocation):
        recollect.set("mixed_colour_information", "last_size", "({0.width}, {0.height})".format(allocation))
    def unselect_all(self):
        self.cview.get_selection().unselect_all()
