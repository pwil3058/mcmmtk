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

'''
Widgets the work with paint colours
'''

import collections
import math
import fractions
import sys
import cairo

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from .bab import mathx
from .bab import nmd_tuples
from .bab import options

from .epaint import paint
from .epaint import rgbh

from .gtx import actions
from .gtx import buttons
from .gtx import coloured
from .gtx import dialogue
from .gtx import gutils
from .gtx import tlview
from .gtx import recollect

options.define('colour_wheel', 'red_to_yellow_clockwise', options.Defn(bool, False, _('Direction around colour wheel from red to yellow.')))

if __name__ == '__main__':
    _ = lambda x: x
    import doctest

def _gdk_color_to_rgb(gcol):
    gcol_str = gcol.to_string()[1:]
    if len(gcol_str) == 3:
        return paint.RGB(*[int(gcol_str[i:(i+1)] * 4, 16) for i in range(3)])
    elif len(gcol_str) == 6:
        return paint.RGB(*[int(gcol_str[i*2:(i+1) * 2] * 2, 16) for i in range(3)])
    return paint.RGB(*[int(gcol_str[i*4:(i+1) * 4], 16) for i in range(3)])

class MappedFloatChoice(Gtk.ComboBoxText):
    MFDC = None
    def __init__(self):
        Gtk.ComboBoxText.__init__(self)
        for choice in ('{0}\t- {1}'.format(item[0], item[1]) for item in self.MFDC.MAP):
            self.append_text(choice)
    def get_selection(self):
        index = self.get_active()
        rating = self.MFDC.MAP[index if index >= 0 else None]
        return self.MFDC(rating.abbrev)
    def set_selection(self, mapped_float):
        abbrev = str(mapped_float)
        for index, rating in enumerate(self.MFDC.MAP):
            if abbrev == rating.abbrev:
                self.set_active(index if index is not None else -1)
                return
        raise paint.MappedFloat.BadValue()

class TransparencyChoice(MappedFloatChoice):
    MFDC = paint.Transparency

class FinishChoice(MappedFloatChoice):
    MFDC = paint.Finish

def get_colour(arg):
    if isinstance(arg, paint.Colour):
        return arg.rgb
    else:
        return arg

class ColouredRectangle(Gtk.DrawingArea):
    def __init__(self, colour, size_request=None):
        Gtk.DrawingArea.__init__(self)
        if size_request is not None:
            self.set_size_request(*size_request)
        self.colour = get_colour(paint.RGB.WHITE) if colour is None else get_colour(colour)
        self.connect("draw", self.expose_cb)
    def expose_cb(self, _widget, cairo_ctxt):
        cairo_ctxt.set_source_rgb(*self.colour)
        cairo_ctxt.paint()
        return True

class ColourSampleArea(Gtk.DrawingArea, actions.CAGandUIManager):
    """
    A coloured drawing area onto which samples can be dropped.
    """
    UI_DESCR = '''
    <ui>
        <popup name='colour_sample_popup'>
            <menuitem action='paste_sample_image'/>
            <menuitem action='remove_sample_images'/>
        </popup>
    </ui>
    '''
    AC_SAMPLES_PASTED, AC_MASK = actions.ActionCondns.new_flags_and_mask(1)
    def __init__(self, single_sample=False, default_bg=None):
        Gtk.DrawingArea.__init__(self)

        self.set_size_request(100, 100)
        self._ptr_x = self._ptr_y = 100
        self._sample_images = []
        self._single_sample = single_sample
        self.default_bg_colour = self.bg_colour = get_colour(paint.RGB.WHITE) if default_bg is None else get_colour(default_bg)

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self.expose_cb)
        self.connect('motion_notify_event', self._motion_notify_cb)

        actions.CAGandUIManager.__init__(self, popup='/colour_sample_popup')
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions(
            [
                ('paste_sample_image', Gtk.STOCK_PASTE, None, None,
                 _('Paste an image from clipboard at this position.'), self._paste_fm_clipboard_cb),
            ])
        self.action_groups[self.AC_SAMPLES_PASTED].add_actions(
            [
                ('remove_sample_images', Gtk.STOCK_REMOVE, None, None,
                 _('Remove all sample images from from the sample area.'), self._remove_sample_images_cb),
            ])
    def get_masked_condns(self):
        if len(self._sample_images) > 0:
            return actions.MaskedCondns(self.AC_SAMPLES_PASTED, self.AC_MASK)
        else:
            return actions.MaskedCondns(0, self.AC_MASK)
    def _motion_notify_cb(self, widget, event):
        if event.type == Gdk.EventType.MOTION_NOTIFY:
            self._ptr_x = event.x
            self._ptr_y = event.y
            return True
        return False
    def _remove_sample_images_cb(self, action):
        """
        Remove all samples.
        """
        self.erase_samples()
    def _paste_fm_clipboard_cb(self, _action):
        """
        Paste from the clipboard
        """
        cbd = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        # WORKAROUND: clipboard bug on Windows
        if sys.platform.startswith("win"): cbd.request_targets(lambda a, b, c: None)
        cbd.request_image(self._image_from_clipboard_cb, (self._ptr_x, self._ptr_y))
    def _image_from_clipboard_cb(self, cbd, img, posn):
        if img is None:
            dlg = dialogue.MessageDialog(
                parent=self.get_toplevel(),
                flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
                buttons=Gtk.ButtonsType.OK,
                text=_('No image data on clipboard.')
            )
            dlg.run()
            dlg.destroy()
        else:
            if self._single_sample and len(self._sample_images) == 1:
                self._sample_images[0] = (int(posn[0]), int(posn[1]), img)
            else:
                self._sample_images.append((int(posn[0]), int(posn[1]), img))
            self.queue_draw()
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_SAMPLES_PASTED, self.AC_MASK))
            self.emit('samples-changed', len(self._sample_images))
    def erase_samples(self):
        """
        Erase all samples from the drawing area
        """
        self._sample_images = []
        self.queue_draw()
        self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_MASK))
        self.emit('samples-changed', len(self._sample_images))
    def get_samples(self):
        """
        Return a list containing all samples from the drawing area
        """
        return [sample[2] for sample in self._sample_images]
    def set_bg_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.bg_colour = get_colour(colour)
        self.queue_draw()
    def expose_cb(self, _widget, cairo_ctxt):
        """
        Repaint the drawing area
        """
        cairo_ctxt.set_source_rgb(*self.bg_colour.converted_to(rgbh.RGBPN))
        cairo_ctxt.paint()
        for sample in self._sample_images:
            sfc = Gdk.cairo_surface_create_from_pixbuf(sample[2], 0, None)
            cairo_ctxt.set_source_surface(sfc, sample[0], sample[1])
            cairo_ctxt.paint()
        return True
GObject.signal_new('samples-changed', ColourSampleArea, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_INT,))

class ColourMatchArea(Gtk.DrawingArea):
    """
    A coloured drawing area for comparing two colours.
    """
    def __init__(self, target_colour=None, default_bg=None):
        Gtk.DrawingArea.__init__(self)

        self.set_size_request(100, 100)
        self._ptr_x = self._ptr_y = 100
        self.default_bg_colour = self.bg_colour = get_colour(paint.RGB.WHITE) if default_bg is None else get_colour(default_bg)
        self.target_colour = get_colour(target_colour) if target_colour is not None else None
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self.expose_cb)
    def set_bg_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.bg_colour = get_colour(colour)
        self.queue_draw()
    def set_target_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.target_colour = get_colour(colour)
        self.queue_draw()
    def expose_cb(self, _widget, cairo_ctxt):
        """
        Repaint the drawing area
        """
        cairo_ctxt.set_source_rgb(*self.bg_colour.converted_to(rgbh.RGBPN))
        cairo_ctxt.paint()
        if self.target_colour is not None:
            cairo_ctxt.set_source_rgb(*self.target_colour.converted_to(rgbh.RGBPN))
            width = _widget.get_allocated_width()
            height = _widget.get_allocated_height()
            cairo_ctxt.rectangle(width / 4, height / 4, width / 2, height /2)
            cairo_ctxt.fill()
        return True
    def clear(self):
        self.bg_colour = self.default_bg_colour
        self.target_colour = None
        self.queue_draw()

def get_rgb(colour):
    if isinstance(colour, Gdk.Color):
        return _gdk_color_to_rgb(colour)
    elif isinstance(colour, paint.Colour) or isinstance(colour, paint.HCV):
        return colour.rgb
    elif isinstance(colour, paint.RGB):
        return colour
    else:
        return paint.RGB(*colour)

def draw_line(cairo_ctxt, x0, y0, x1, y1):
    cairo_ctxt.move_to(x0, y0)
    cairo_ctxt.line_to(x1, y1)
    cairo_ctxt.stroke()

def draw_polygon(cairo_ctxt, polygon, filled=True):
    cairo_ctxt.move_to(*polygon[0])
    for index in range(1, len(polygon)):
        cairo_ctxt.line_to(*polygon[index])
    cairo_ctxt.close_path()
    if filled:
        cairo_ctxt.fill()
    else:
        cairo_ctxt.stroke()

def draw_circle(cairo_ctxt, cx, cy, radius, filled=False):
    cairo_ctxt.arc(cx, cy, radius, 0.0, 2 * math.pi)
    if filled:
        cairo_ctxt.fill()
    else:
        cairo_ctxt.stroke()

class GenericAttrDisplay(Gtk.DrawingArea):
    LABEL = None

    def __init__(self, colour=None, target_colour=None, size=(100, 15)):
        Gtk.DrawingArea.__init__(self)
        self.set_size_request(size[0], size[1])
        self.colour = colour
        self.target_fg_colour = self.fg_colour = colour.best_foreground()
        self.indicator_val = 0.5
        # Set these to none so _set_colour() won't crash
        self.target_colour = None
        self.target_val = None
        self._set_colour(colour)
        # OK now set the target colour
        self.target_colour = target_colour
        self._set_target_colour(target_colour)
        self.connect("draw", self.expose_cb)
        self.show()
    @staticmethod
    def indicator_top(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, 5), (-5, 0), (5, 0))]
    @staticmethod
    def indicator_bottom(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, -5), (-5, 0), (5, 0))]
    def draw_indicators(self, cairo_ctxt):
        if self.indicator_val is None:
            return
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        indicator_x = int(width * self.indicator_val)
        cairo_ctxt.set_source_rgb(*self.fg_colour)
        draw_polygon(cairo_ctxt, self.indicator_top(indicator_x, 0), True)
        draw_polygon(cairo_ctxt, self.indicator_bottom(indicator_x, height - 1), True)
    def draw_label(self, cairo_ctxt):
        if self.LABEL is None:
            return
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        cairo_ctxt.set_font_size(15)
        tw, th = cairo_ctxt.text_extents(self.LABEL)[2:4]
        x = (width - tw + 0.5) / 2
        y = (height + th - 0.5) / 2
        cairo_ctxt.move_to(x, y)
        cairo_ctxt.set_source_rgb(*self.fg_colour)
        cairo_ctxt.show_text(self.LABEL)
    def expose_cb(self, _widget, _cr):
        pass
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes.
        Such as the location of the indicators.
        """
        pass
    def set_colour(self, colour):
        self.colour = colour
        self._set_colour(colour)
        self.queue_draw()
    def draw_target(self, cairo_ctxt):
        if self.target_val is None:
            return
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        target_x = int(w * self.target_val)
        cairo_ctxt.set_source_rgb(*self.target_fg_colour)
        draw_line(cairo_ctxt, target_x, 0, target_x, int(h))
    def _set_target_colour(self, colour):
        """
        Set values that only change when the target colour changes.
        """
        pass
    def set_target_colour(self, colour):
        self.target_colour = colour
        self._set_target_colour(colour)
        self.queue_draw()

class HueDisplay(GenericAttrDisplay):
    LABEL = _('Hue')

    def expose_cb(self, widget, cairo_ctxt):
        if self.colour is None and self.target_val is None:
            cairo_ctxt.set_source_rgb(0, 0, 0)
            cairo_ctxt.paint()
            return
        #
        if self.target_val is None:
            if self.indicator_val is None:
                cairo_ctxt.set_source_rgb(*self.colour.hue_rgb)
                self.draw_label(cairo_ctxt)
                return
            else:
                centre_hue = self.colour.hue
        else:
            centre_hue = self.target_colour.hue
        #
        backwards = options.get('colour_wheel', 'red_to_yellow_clockwise')
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        spread = 2 * math.pi
        if backwards:
            start_hue_angle = self.colour.hue.angle - spread / 2
            delta_hue_angle = spread / width
        else:
            start_hue_angle = self.colour.hue.angle + spread / 2
            delta_hue_angle = -spread / width
        linear_gradient = cairo.LinearGradient(0, 0, width, height)
        for i in range(width):
            hue = paint.Hue.from_angle(start_hue_angle + delta_hue_angle * i)
            linear_gradient.add_color_stop_rgb(float(i) / width, *hue.rgb_converted_to(rgbh.RGBPN))
        cairo_ctxt.rectangle(0, 0, width, height)
        cairo_ctxt.set_source(linear_gradient)
        cairo_ctxt.fill()

        self.draw_target(cairo_ctxt)
        self.draw_indicators(cairo_ctxt)
        self.draw_label(cairo_ctxt)
    def _set_colour(self, colour):
        if colour is None:
            self.indicator_val = None
        elif colour.hue.is_grey():
            self.indicator_val = None
        else:
            self.fg_colour = colour.hue_rgb.best_foreground()
            if self.target_val is None:
                self.indicator_val = 0.5
            elif options.get('colour_wheel', 'red_to_yellow_clockwise'):
                self.indicator_val = 0.5 + 0.5 * (colour.hue - self.target_colour.hue) / math.pi
            else:
                self.indicator_val = 0.5 - 0.5 * (colour.hue - self.target_colour.hue) / math.pi
    def _set_target_colour(self, colour):
        if colour is None:
            self.target_val = None
        elif colour.hue.is_grey():
            self.target_val = None
        else:
            self.target_fg_colour = colour.hue_rgb.best_foreground()
            self.target_val = 0.5
            if self.indicator_val is not None:
                offset = 0.5 * (self.colour.hue - colour.hue) / math.pi
                if options.get('colour_wheel', 'red_to_yellow_clockwise'):
                    self.indicator_val = 0.5 + offset
                else:
                    self.indicator_val = 0.5 - offset

class ValueDisplay(GenericAttrDisplay):
    LABEL = _('Value')

    def __init__(self, colour=None, target_colour=None, size=(100, 15)):
        self.start_colour = paint.BLACK
        self.end_colour = paint.WHITE
        GenericAttrDisplay.__init__(self, colour=colour, target_colour=target_colour, size=size)
    def expose_cb(self, widget, cairo_ctxt):
        if self.colour is None and self.target_colour is None:
            cairo_ctxt.set_source_rgb(0, 0, 0)
            cairo_ctxt.paint()
            return
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        linear_gradient = cairo.LinearGradient(0, 0, width, height)
        linear_gradient.add_color_stop_rgb(0.0, *self.start_colour)
        linear_gradient.add_color_stop_rgb(1.0, *self.end_colour)
        cairo_ctxt.rectangle(0, 0, width, height)
        cairo_ctxt.set_source(linear_gradient)
        cairo_ctxt.fill()

        self.draw_target(cairo_ctxt)
        self.draw_indicators(cairo_ctxt)
        self.draw_label(cairo_ctxt)
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        if colour is None:
            self.indicator_val = None
        else:
            self.fg_colour = colour.best_foreground()
            self.indicator_val = colour.value
    def _set_target_colour(self, colour):
        """
        Set values that only change when the target colour changes
        """
        if colour is None:
            self.target_val = None
        else:
            self.target_fg_colour = colour.best_foreground()
            self.target_val = colour.value

class ChromaDisplay(ValueDisplay):
    LABEL = _('Chroma')

    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        if colour is None:
            self.indicator_val = None
            if self.target_colour is None:
                self.start_colour = start.end_colour = paint.WHITE
                self.fg_colour = self.target_fg_colour = paint.BLACK
        else:
            if self.target_colour is None:
                self.start_colour = self.colour.hcv.chroma_side()
                self.end_colour = colour.hue_rgb
            self.fg_colour = self.start_colour.best_foreground()
            self.indicator_val = colour.chroma
    def _set_target_colour(self, colour):
        """
        Set values that only change when the target colour changes
        """
        if colour is None:
            self.target_val = None
            if self.colour is None:
                self.start_colour = start.end_colour = paint.WHITE
                self.fg_colour = self.target_fg_colour = paint.BLACK
            else:
                self._set_colour(self.colour)
        else:
            self.start_colour = colour.hcv.zero_chroma_rgb()
            self.end_colour = colour.hue_rgb
            self.target_fg_colour = self.start_colour.best_foreground()
            self.target_val = colour.chroma


class HCVDisplay(Gtk.VBox):
    def __init__(self, colour=paint.WHITE, target_colour=None, size=(256, 120), stype = Gtk.ShadowType.ETCHED_IN):
        Gtk.VBox.__init__(self)
        #
        w, h = size
        self.hue = HueDisplay(colour=colour, target_colour=target_colour, size=(w, h / 4))
        self.pack_start(gutils.wrap_in_frame(self.hue, stype), expand=False, fill=True, padding=0)
        self.value = ValueDisplay(colour=colour, target_colour=target_colour, size=(w, h / 4))
        self.pack_start(gutils.wrap_in_frame(self.value, stype), expand=False, fill=True, padding=0)
        self.chroma = ChromaDisplay(colour=colour, target_colour=target_colour, size=(w, h / 4))
        self.pack_start(gutils.wrap_in_frame(self.chroma, stype), expand=False, fill=True, padding=0)
        self.show()
    def set_colour(self, new_colour):
        self.chroma.set_colour(new_colour)
        self.hue.set_colour(new_colour)
        self.value.set_colour(new_colour)
    def set_target_colour(self, new_target_colour):
        self.chroma.set_target_colour(new_target_colour)
        self.hue.set_target_colour(new_target_colour)
        self.value.set_target_colour(new_target_colour)

class HueWheelNotebook(Gtk.Notebook):
    def __init__(self, popup='/colour_wheel_I_popup'):
        Gtk.Notebook.__init__(self)
        self.hue_chroma_wheel = HueChromaWheel(nrings=5, popup=popup)
        self.hue_value_wheel = HueValueWheel(popup=popup)
        self.append_page(self.hue_value_wheel, Gtk.Label(label=_('Hue/Value Wheel')))
        self.append_page(self.hue_chroma_wheel, Gtk.Label(label=_('Hue/Chroma Wheel')))
    def set_wheels_colour_info_acb(self, callback):
        self.hue_chroma_wheel.set_colour_info_acb(callback)
        self.hue_value_wheel.set_colour_info_acb(callback)
    def set_wheels_add_colour_acb(self, callback):
        self.hue_chroma_wheel.set_add_colour_acb(callback)
        self.hue_value_wheel.set_add_colour_acb(callback)
    def add_colour(self, new_colour):
        self.hue_chroma_wheel.add_colour(new_colour)
        self.hue_value_wheel.add_colour(new_colour)
    def del_colour(self, colour):
        self.hue_chroma_wheel.del_colour(colour)
        self.hue_value_wheel.del_colour(colour)
    def add_target_colour(self, name, target_colour):
        self.hue_chroma_wheel.add_target_colour(name, target_colour)
        self.hue_value_wheel.add_target_colour(name, target_colour)
    def del_target_colour(self, name):
        self.hue_chroma_wheel.del_target_colour(name)
        self.hue_value_wheel.del_target_colour(name)
    def set_crosshair(self, target_colour):
        self.hue_chroma_wheel.set_crosshair(target_colour)
        self.hue_value_wheel.set_crosshair(target_colour)
    def unset_crosshair(self):
        self.hue_chroma_wheel.unset_crosshair()
        self.hue_value_wheel.unset_crosshair()

class ColourWheel(Gtk.DrawingArea, actions.CAGandUIManager):
    UI_DESCR = '''
        <ui>
            <popup name='colour_wheel_I_popup'>
                <menuitem action='colour_info'/>
            </popup>
            <popup name='colour_wheel_AI_popup'>
                <menuitem action='add_colour'/>
                <menuitem action='colour_info'/>
            </popup>
        </ui>
        '''
    AC_HAVE_POPUP_COLOUR, _DUMMY = actions.ActionCondns.new_flags_and_mask(1)
    def __init__(self, nrings=9, popup='/colour_wheel_I_popup'):
        Gtk.DrawingArea.__init__(self)
        actions.CAGandUIManager.__init__(self, popup=popup)
        self.__popup_colour = None
        self.BLACK = get_colour([0, 0, 0])
        self.set_size_request(400, 400)
        self.scale = 1.0
        self.zoom = 1.0
        self.one = 100 * self.scale
        self.size = 3
        self.scaled_size = self.size * self.scale
        self.centre = nmd_tuples.XY(0, 0)
        self.offset = nmd_tuples.XY(0, 0)
        self.__last_xy = nmd_tuples.XY(0, 0)
        self.paint_colours = {}
        self.mixed_colours = {}
        self.target_colours = {}
        self.crosshair = None
        self.nrings = nrings
        self.connect("draw", self.expose_cb)
        self.set_has_tooltip(True)
        self.connect('query-tooltip', self.query_tooltip_cb)
        self.add_events(Gdk.EventMask.SCROLL_MASK|Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('scroll-event', self.scroll_event_cb)
        self.__press_cb_id = self.connect('button_press_event', self._button_press_cb)
        self.__cb_ids = []
        self.__cb_ids.append(self.connect('button_release_event', self._button_release_cb))
        self.__cb_ids.append(self.connect('motion_notify_event', self._motion_notify_cb))
        self.__cb_ids.append(self.connect('leave_notify_event', self._leave_notify_cb))
        for cb_id in self.__cb_ids:
            self.handler_block(cb_id)
        self.show()
    @property
    def popup_colour(self):
        return self.__popup_colour
    def populate_action_groups(self):
        self.action_groups[self.AC_HAVE_POPUP_COLOUR].add_actions([
            ('colour_info', Gtk.STOCK_INFO, None, None,
             _('Detailed information for this colour.'),
            ),
            ('add_colour', Gtk.STOCK_ADD, None, None,
             _('Add this colour to the mixer.'),
            ),
        ])
        self.__ci_acbid = self.action_groups.connect_activate('colour_info', self._show_colour_details_acb)
        self.__ac_acbid = None
    def _show_colour_details_acb(self, _action):
        PaintColourInformationDialogue(self.__popup_colour).show()
    def do_popup_preliminaries(self, event):
        colour, rng = self.get_colour_nearest_to_xy(event.x, event.y)
        if colour is not None and rng <= self.scaled_size:
            self.__popup_colour = colour
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_POPUP_COLOUR, self.AC_HAVE_POPUP_COLOUR))
        else:
            self.__popup_colour = None
            self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_HAVE_POPUP_COLOUR))
    def set_colour_info_acb(self, callback):
        self.action_groups.disconnect_action('colour_info', self.__ci_acbid)
        self.__ci_acbid = self.action_groups.connect_activate('colour_info', callback, self)
    def set_add_colour_acb(self, callback):
        if self.__ac_acbid is not None:
            self.action_groups.disconnect_action('add_colour', self.__ac_acbid)
        self.__ac_acbid = self.action_groups.connect_activate('add_colour', callback, self)
    def polar_to_cartesian(self, radius, angle):
        if options.get('colour_wheel', 'red_to_yellow_clockwise'):
            x = -radius * math.cos(angle)
        else:
            x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        return (int(self.centre.x + x), int(self.centre.y - y))
    def get_colour_nearest_to_xy(self, x, y):
        smallest = 0xFF
        nearest = None
        for colour_set in [self.paint_colours.values(), self.mixed_colours.values(), self.target_colours.values()]:
            for colour in colour_set:
                rng = colour.range_from(x, y)
                if rng < smallest:
                    smallest = rng
                    nearest = colour.colour
        return (nearest, smallest)
    def get_colour_at_xy(self, x, y):
        colour, rng = self.get_colour_nearest_to_xy(x, y)
        return colour if rng < self.scaled_size else None
    def query_tooltip_cb(self, widget, x, y, keyboard_mode, tooltip):
        colour, rng = self.get_colour_nearest_to_xy(x, y)
        if colour is not None and rng <= self.scaled_size:
            tooltip.set_text(colour.name)
            return True
        else:
            tooltip.set_text("")
            return False
    def scroll_event_cb(self, _widget, event):
        # TODO: investigate strange zoom behaviour in colour wheel
        if event.device.get_source() == Gdk.InputSource.MOUSE:
            new_zoom = self.zoom + 0.025 * (-1 if event.direction == Gdk.ScrollDirection.UP else 1)
            if new_zoom > 1.0 and new_zoom < 5.0:
                self.zoom = new_zoom
                self.queue_draw()
            return True
        return False
    def add_colour(self, new_colour):
        if isinstance(new_colour, paint.MixedColour):
            self.mixed_colours[new_colour] = self.ColourCircle(self, new_colour)
        else:
            self.paint_colours[new_colour] = self.ColourSquare(self, new_colour)
        # The data has changed so do a redraw
        self.queue_draw()
    def del_colour(self, colour):
        if isinstance(colour, paint.MixedColour):
            self.mixed_colours.pop(colour)
        else:
            self.paint_colours.pop(colour)
        # The data has changed so do a redraw
        self.queue_draw()
    def add_target_colour(self, name, target_colour):
        dname = _("{0}: Target").format(name)
        self.target_colours[name] = self.ColourDiamond(self, paint.NamedColour(dname, target_colour))
        # The data has changed so do a redraw
        self.queue_draw()
    def del_target_colour(self, name):
        self.target_colours.pop(name)
        # The data has changed so do a redraw
        self.queue_draw()
    def set_crosshair(self, colour):
        self.crosshair = self.ColourCrossHair(self, colour)
        # The data has changed so do a redraw
        self.queue_draw()
    def unset_crosshair(self):
        self.crosshair = None
        # The data has changed so do a redraw
        self.queue_draw()
    def expose_cb(self, widget, cairo_ctxt):
        #
        spacer = 10
        scaledmax = 110.0
        #
        bg_colour = (paint.RGB.WHITE / 2).converted_to(rgbh.RGBPN)
        cairo_ctxt.set_source_rgb(*bg_colour)
        cairo_ctxt.paint()
        #
        dw = widget.get_allocated_width()
        dh = widget.get_allocated_height()
        self.centre = nmd_tuples.XY(dw / 2, dh / 2) + self.offset
        #
        # calculate a scale factor to use for drawing the graph based
        # on the minimum available width or height
        mindim = min(self.centre.x, dh / 2)
        self.scale = mindim / scaledmax
        self.one = self.scale * 100
        self.scaled_size = self.size * self.scale
        #
        # Draw the graticule
        ring_colour = (paint.RGB.WHITE * 3 / 4).converted_to(rgbh.RGBPN)
        cairo_ctxt.set_source_rgb(*ring_colour)
        for radius in [100 * (i + 1) * self.scale / self.nrings for i in range(self.nrings)]:
            draw_circle(cairo_ctxt, self.centre.x, self.centre.y, int(round(radius * self.zoom)))
        #
        cairo_ctxt.set_line_width(2)
        for angle in [mathx.PI_60 * i for i in range(6)]:
            hue = paint.Hue.from_angle(angle)
            cairo_ctxt.set_source_rgb(*hue.rgb_converted_to(rgbh.RGBPN))
            cairo_ctxt.move_to(self.centre.x, self.centre.y)
            cairo_ctxt.line_to(*self.polar_to_cartesian(self.one * self.zoom, angle))
            cairo_ctxt.stroke()
        for target_colour in self.target_colours.values():
            target_colour.draw(cairo_ctxt)
        for paint_colour in self.paint_colours.values():
            paint_colour.draw(cairo_ctxt)
        for mix in self.mixed_colours.values():
            mix.draw(cairo_ctxt)
        if self.crosshair is not None:
            self.crosshair.draw(cairo_ctxt)
        return True
    # Allow graticule to be moved using mouse (left button depressed)
    # Careful not to override CAGandUIManager method
    def _button_press_cb(self, widget, event):
        if event.button == 1:
            self.__last_xy = nmd_tuples.XY(int(event.x), int(event.y))
            for cb_id in self.__cb_ids:
                widget.handler_unblock(cb_id)
            return True
        return actions.CAGandUIManager._button_press_cb(widget, event)
    def _motion_notify_cb(self, widget, event):
        this_xy = nmd_tuples.XY(int(event.x), int(event.y))
        delta_xy = this_xy - self.__last_xy
        self.__last_xy = this_xy
        # TODO: limit offset values
        self.offset += delta_xy
        widget.queue_draw()
        return True
    def _button_release_cb(self, widget, event):
        if event.button != 1:
            return False
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        return True
    def _leave_notify_cb(self, widget, event):
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        return False
    class ColourShape(object):
        def __init__(self, parent, colour):
            self.parent = parent
            self.colour = colour
            self.x = 0
            self.y = 0
            self.pen_width = 2
            self.predraw_setup()
        def predraw_setup(self):
            """
            Set up colour values ready for drawing
            """
            self.colour_angle = self.colour.hue.angle if not self.colour.hue.is_grey() else mathx.Angle(math.pi / 2)
            self.fg_colour = self.colour.rgb #self.parent.new_colour(self.colour.rgb)
            self.value_colour = paint.BLACK #self.parent.new_colour(paint.BLACK)
            self.chroma_colour = self.colour.hcv.chroma_side() #self.parent.new_colour(self.colour.hcv.chroma_side())
            self.choose_radius_attribute()
        def range_from(self, x, y):
            dx = x - self.x
            dy = y - self.y
            return math.sqrt(dx * dx + dy * dy)
    class ColourSquare(ColourShape):
        polypoints = ((-1, 1), (-1, -1), (1, -1), (1, 1))
        def draw(self, cairo_ctxt):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            square = tuple(tuple(pp[i] * self.parent.scaled_size for i in range(2)) for pp in self.polypoints)
            square_pts = [tuple((int(self.x + pt[0]), int(self.y +  pt[1]))) for pt in square]
            # draw the middle
            cairo_ctxt.set_source_rgb(*self.fg_colour.converted_to(rgbh.RGBPN))
            draw_polygon(cairo_ctxt, square_pts, filled=True)
            cairo_ctxt.set_source_rgb(*self.chroma_colour)
            draw_polygon(cairo_ctxt, square_pts, filled=False)
    class ColourDiamond(ColourSquare):
        polypoints = ((1.5, 0), (0, -1.5), (-1.5, 0), (0, 1.5))
    class ColourCircle(ColourShape):
        def draw(self, cairo_ctxt):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            cairo_ctxt.set_source_rgb(*self.fg_colour.converted_to(rgbh.RGBPN))
            draw_circle(cairo_ctxt, self.x, self.y, radius=self.parent.scaled_size, filled=True)
            cairo_ctxt.set_source_rgb(*self.chroma_colour)
            draw_circle(cairo_ctxt, self.x, self.y, radius=self.parent.scaled_size, filled=False)
    class ColourCrossHair(ColourShape):
        def draw(self, cairo_ctxt):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            radius = self.parent.scaled_size
            halflen = radius * 2
            cairo_ctxt.set_source_rgb(*self.fg_colour.converted_to(rgbh.RGBPN))
            draw_circle(cairo_ctxt, self.x, self.y, radius=radius, filled=True)
            cairo_ctxt.set_source_rgb(*self.parent.BLACK)
            draw_circle(cairo_ctxt, self.x, self.y, radius=radius, filled=False)
            draw_line(cairo_ctxt, int(self.x - halflen), int(self.y), int(self.x + halflen), int(self.y))
            draw_line(cairo_ctxt, int(self.x), int(self.y - halflen), int(self.x), int(self.y + halflen))

class HueChromaWheel(ColourWheel):
    class ColourSquare(ColourWheel.ColourSquare):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma
    class ColourCircle(ColourWheel.ColourCircle):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma
    class ColourDiamond(ColourWheel.ColourDiamond):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma
    class ColourCrossHair(ColourWheel.ColourCrossHair):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma

class HueValueWheel(ColourWheel):
    class ColourSquare(ColourWheel.ColourSquare):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value
    class ColourCircle(ColourWheel.ColourCircle):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value
    class ColourDiamond(ColourWheel.ColourDiamond):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value
    class ColourCrossHair(ColourWheel.ColourCrossHair):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value

class ColourListStore(tlview.NamedListStore):
    ROW = collections.namedtuple('ROW', ['colour'])
    TYPES = ROW(colour=object)
    def append_colour(self, colour):
        self.append(self.ROW(colour))
    def remove_colour(self, colour):
        model_iter = self.find_named(lambda x: x.colour == colour)
        if model_iter is None:
            raise LookupError()
        # return the iter in case the client is interested
        self.emit('colour-removed', colour)
        return self.remove(model_iter)
    def remove_colours(self, colours):
        for colour in colours:
            self.remove_colour(colour)
    def get_colours(self):
        return [row.colour for row in self.named()]
    def get_colour_with_name(self, colour_name):
        """
        Return the colour with the specified name or None if not present
        """
        for row in self.named():
            if row.colour.name == colour_name:
                return row.colour
        return None
GObject.signal_new('colour-removed', ColourListStore, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

def paint_cell_data_func(column, cell, model, model_iter, attribute):
    colour = model.get_value_named(model_iter, 'colour')
    if attribute == 'name':
        cell.set_property('text', colour.name)
        cell.set_property('background-gdk', colour.to_gdk_color())
        cell.set_property('foreground-gdk', colour.best_foreground_gdk_color())
    elif attribute == 'value':
        cell.set_property('text', str(float(round(colour.value, 2))))
        cell.set_property('background-gdk', colour.value_rgb().to_gdk_color())
        cell.set_property('foreground-gdk', colour.value_rgb().best_foreground_gdk_color())
    elif attribute == 'hue':
        cell.set_property('background-gdk', colour.hue_rgb.to_gdk_color())
    elif attribute == 'finish':
        cell.set_property('text', str(colour.finish))
    elif attribute == 'transparency':
        cell.set_property('text', str(colour.transparency))

TNS = collections.namedtuple('TNS', ['title', 'attr', 'properties', 'sort_key_function'])

def colour_attribute_column_spec(tns):
    return tlview.ColumnSpec(
        title=tns.title,
        properties=tns.properties,
        sort_key_function=tns.sort_key_function,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties=None,
                    start=False
                ),
                cell_data_function_spec=tlview.CellDataFunctionSpec(
                    function=paint_cell_data_func,
                    user_data=tns.attr
                ),
                attributes={}
            ),
        ],
    )

COLOUR_ATTRS = [
    TNS(_('Colour Name'), 'name', {'resizable' : True, 'expand' : True}, lambda row: row.colour.name),
    TNS(_('Value'), 'value', {}, lambda row: row.colour.value),
    TNS(_('Hue'), 'hue', {}, lambda row: row.colour.hue),
    TNS(_('T.'), 'transparency', {}, lambda row: row.colour.transparency),
    TNS(_('F.'), 'finish', {}, lambda row: row.colour.finish),
]

def colour_attribute_column_specs(model):
    """
    Generate the column specitications for colour attributes
    """
    return [colour_attribute_column_spec(tns) for tns in COLOUR_ATTRS]

def generate_colour_list_spec(model):
    """
    Generate the specification for a paint colour list
    """
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.MULTIPLE,
        columns=colour_attribute_column_specs(model)
    )

class ColourListView(tlview.View, actions.CAGandUIManager, dialogue.AskerMixin):
    MODEL = ColourListStore
    SPECIFICATION = generate_colour_list_spec(ColourListStore)
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='remove_selected_colours'/>
        </popup>
    </ui>
    '''
    def __init__(self, *args, **kwargs):
        tlview.View.__init__(self, *args, **kwargs)
        actions.CAGandUIManager.__init__(self, selection=self.get_selection(), popup='/colour_list_popup')
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_SELN_MADE].add_actions(
            [
                ('remove_selected_colours', Gtk.STOCK_REMOVE, None, None,
                 _('Remove the selected colours from the list.'), self._remove_selection_cb),
            ]
        )
    def _remove_selection_cb(self, _action):
        """
        Delete the currently selected colours
        """
        colours = self.get_selected_colours()
        if len(colours) == 0:
            return
        msg = _("The following colours are about to be deleted:\n")
        for colour in colours:
            msg += "\t{0}\n".format(colour.name)
        msg += _("and will not be recoverable. OK?")
        if self.ask_ok_cancel(msg):
            self.model.remove_colours(colours)
    def get_selected_colours(self):
        """
        Return the currently selected colours as a list.
        """
        return [row.colour for row in self.MODEL.get_selected_rows(self.get_selection())]

class RGBEntryBox(Gtk.HBox):
    def __init__(self, initial_colour=paint.BLACK):
        Gtk.HBox.__init__(self)
        self.red = buttons.HexSpinButton(0xFFFF, coloured.ColouredLabel(_("Red"), paint.RED))
        self.red.connect("value-changed", self._spinners_changed_cb)
        self.pack_start(self.red, expand=True, fill=True, padding=0)
        self.green = buttons.HexSpinButton(0xFFFF, coloured.ColouredLabel(_("Green"), paint.GREEN))
        self.green.connect("value-changed", self._spinners_changed_cb)
        self.pack_start(self.green, expand=True, fill=True, padding=0)
        self.blue = buttons.HexSpinButton(0xFFFF, coloured.ColouredLabel(_("Blue"), paint.BLUE))
        self.blue.connect("value-changed", self._spinners_changed_cb)
        self.pack_start(self.blue, expand=True, fill=True, padding=0)
        self.set_colour(initial_colour)
    def set_colour(self, colour):
        rgb = get_rgb(colour)
        self.red.set_value(rgb.red)
        self.green.set_value(rgb.green)
        self.blue.set_value(rgb.blue)
    def get_colour(self):
        return paint.RGB(self.red.get_value(), self.green.get_value(), self.blue.get_value())
    def _spinners_changed_cb(self, spinner, was_tabbed):
        self.emit("colour-changed")
        if was_tabbed:
            if spinner is self.red:
                self.green.entry.grab_focus()
            elif spinner is self.green:
                self.blue.entry.grab_focus()
            elif spinner is self.blue:
                self.red.entry.grab_focus()
GObject.signal_new("colour-changed", RGBEntryBox, GObject.SignalFlags.RUN_LAST, None, ())

class PaintColourInformationDialogue(dialogue.Dialog):
    """
    A dialog to display the detailed information for a paint colour
    """
    def __init__(self, colour, parent=None):
        dialogue.Dialog.__init__(self, title=_('Paint Colour: {}').format(colour.name), parent=parent)
        last_size = recollect.get("paint_colour_information", "last_size")
        if last_size:
            self.set_default_size(*eval(last_size))
        vbox = self.get_content_area()
        vbox.pack_start(coloured.ColouredLabel(colour.name, colour), expand=False, fill=True, padding=0)
        if isinstance(colour, paint.PaintColour):
            vbox.pack_start(coloured.ColouredLabel(colour.series.series_id.name, colour), expand=False, fill=True, padding=0)
            vbox.pack_start(coloured.ColouredLabel(colour.series.series_id.maker, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(HCVDisplay(colour=colour), expand=False, fill=True, padding=0)
        if isinstance(colour, paint.PaintColour):
            vbox.pack_start(Gtk.Label(colour.transparency.description()), expand=False, fill=True, padding=0)
            vbox.pack_start(Gtk.Label(colour.finish.description()), expand=False, fill=True, padding=0)
        self.connect("configure-event", self._configure_event_cb)
        vbox.show_all()
    def _configure_event_cb(self, widget, allocation):
        recollect.set("paint_colour_information", "last_size", "({0.width}, {0.height})".format(allocation))

if __name__ == '__main__':
    doctest.testmod()
