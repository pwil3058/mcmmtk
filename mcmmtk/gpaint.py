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

import gtk
import gobject

from mcmmtk import options
from mcmmtk import utils
from mcmmtk import actions
from mcmmtk import tlview
from mcmmtk import gtkpwx
from mcmmtk import paint

if __name__ == '__main__':
    _ = lambda x: x
    import doctest

class MappedFloatChoice(gtkpwx.Choice):
    MFDC = None
    def __init__(self):
        choices = ['{0}\t- {1}'.format(item[0], item[1]) for item in self.MFDC.MAP]
        gtkpwx.Choice.__init__(self, choices=choices)
    def get_selection(self):
        return self.MFDC(self.MFDC.MAP[gtkpwx.Choice.get_selection(self)].abbrev)
    def set_selection(self, mapped_float):
        abbrev = str(mapped_float)
        for i, rating in enumerate(self.MFDC.MAP):
            if abbrev == rating.abbrev:
                gtkpwx.Choice.set_selection(self, i)
                return
        raise paint.MappedFloat.BadValue()

class TransparencyChoice(MappedFloatChoice):
    MFDC = paint.Transparency

class FinishChoice(MappedFloatChoice):
    MFDC = paint.Finish

class ColouredRectangle(gtk.DrawingArea):
    def __init__(self, colour, size_request=None):
        gtk.DrawingArea.__init__(self)
        if size_request is not None:
            self.set_size_request(*size_request)
        self.colour = self.new_colour(paint.RGB_WHITE) if colour is None else self.new_colour(colour)
        self.connect('expose-event', self.expose_cb)
    def expose_cb(self, _widget, _event):
        self.gc = self.window.new_gc()
        self.gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        self.gc.set_background(self.colour)
        self.window.set_background(self.colour)
        self.window.clear()
        return True
    def new_colour(self, arg):
        if isinstance(arg, paint.Colour):
            colour = gtk.gdk.Color(*arg.rgb)
        else:
            colour = gtk.gdk.Color(*arg)
        return self.get_colormap().alloc_color(colour)

class ColourSampleArea(gtk.DrawingArea, actions.CAGandUIManager):
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
        gtk.DrawingArea.__init__(self)

        self.set_size_request(200, 200)
        self._ptr_x = self._ptr_y = 100
        self._sample_images = []
        self._single_sample = single_sample
        self.default_bg_colour = self.bg_colour = self.new_colour(paint.RGB_WHITE) if default_bg is None else self.new_colour(default_bg)

        self.add_events(gtk.gdk.POINTER_MOTION_MASK|gtk.gdk.BUTTON_PRESS_MASK)
        self.connect('expose-event', self.expose_cb)
        self.connect('motion_notify_event', self._motion_notify_cb)

        actions.CAGandUIManager.__init__(self, popup='/colour_sample_popup')
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions(
            [
                ('paste_sample_image', gtk.STOCK_PASTE, None, None,
                 _('Paste an image from clipboard at this position.'), self._paste_fm_clipboard_cb),
            ])
        self.action_groups[self.AC_SAMPLES_PASTED].add_actions(
            [
                ('remove_sample_images', gtk.STOCK_REMOVE, None, None,
                 _('Remove all sample images from from the sample area.'), self._remove_sample_images_cb),
            ])
    def get_masked_condns(self):
        if len(self._sample_images) > 0:
            return actions.MaskedCondns(self.AC_SAMPLES_PASTED, self.AC_MASK)
        else:
            return actions.MaskedCondns(0, self.AC_MASK)
    def _motion_notify_cb(self, widget, event):
        if event.type == gtk.gdk.MOTION_NOTIFY:
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
        cbd = gtk.clipboard_get()
        cbd.request_image(self._image_from_clipboard_cb, (self._ptr_x, self._ptr_y))
    def _image_from_clipboard_cb(self, cbd, img, posn):
        if img is None:
            dlg = gtk.MessageDialog(
                parent=self.get_toplevel(),
                flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                buttons=gtk.BUTTONS_OK,
                message_format=_('No image data on clipboard.')
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
    def new_colour(self, arg):
        if isinstance(arg, paint.Colour):
            colour = gtk.gdk.Color(*arg.rgb)
        else:
            colour = gtk.gdk.Color(*arg)
        return self.get_colormap().alloc_color(colour)
    def set_bg_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.bg_colour = self.new_colour(colour)
        self.queue_draw()
    def expose_cb(self, _widget, _event):
        """
        Repaint the drawing area
        """
        self.gc = self.window.new_gc()
        self.gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        self.gc.set_background(self.bg_colour)
        self.window.set_background(self.bg_colour)
        self.window.clear()
        for sample in self._sample_images:
            self.window.draw_pixbuf(self.gc, sample[2], 0, 0, sample[0], sample[1])
        return True
gobject.signal_new('samples-changed', ColourSampleArea, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,))

class ColourMatchArea(gtk.DrawingArea):
    """
    A coloured drawing area for comparing two colours.
    """
    def __init__(self, target_colour=None, default_bg=None):
        gtk.DrawingArea.__init__(self)

        self.set_size_request(200, 200)
        self._ptr_x = self._ptr_y = 100
        self.default_bg_colour = self.bg_colour = self.new_colour(paint.RGB_WHITE) if default_bg is None else self.new_colour(default_bg)
        self.target_colour = self.new_colour(target_colour) if target_colour is not None else None
        self.add_events(gtk.gdk.POINTER_MOTION_MASK|gtk.gdk.BUTTON_PRESS_MASK)
        self.connect('expose-event', self.expose_cb)
    def new_colour(self, arg):
        if isinstance(arg, paint.Colour):
            colour = gtk.gdk.Color(*arg.rgb)
        else:
            colour = gtk.gdk.Color(*arg)
        return self.get_colormap().alloc_color(colour)
    def set_bg_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.bg_colour = self.new_colour(colour)
        self.queue_draw()
    def set_target_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.target_colour = self.new_colour(colour)
        self.queue_draw()
    def expose_cb(self, _widget, _event):
        """
        Repaint the drawing area
        """
        self.gc = self.window.new_gc()
        self.gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        self.gc.set_background(self.bg_colour)
        self.window.set_background(self.bg_colour)
        self.window.clear()
        if self.target_colour is not None:
            self.gc.set_foreground(self.target_colour)
            width, height = self.window.get_size()
            self.window.draw_rectangle(self.gc, True, width / 4, height / 4, width / 2, height /2)
        return True
    def clear(self):
        self.bg_colour = self.default_bg_colour
        self.target_colour = None
        self.queue_draw()


def generate_spectral_rgb_buf(hue, spread, width, height, backwards=False):
    """
    Generate a rectangular RGB buffer filled with the specified spectrum

    hue: the central hue
    spread: the total spread in radians (max. 2 * pi)
    width: the required width of the rectangle in pixels
    height: the required height of the rectangle in pixels
    backwards: whether to go clockwise from red to yellow instead of antilcockwise
    """
    row = bytearray()
    if backwards:
        start_hue_angle = hue.angle - spread / 2
        delta_hue_angle = spread / width
    else:
        start_hue_angle = hue.angle + spread / 2
        delta_hue_angle = -spread / width
    for i in range(width):
        hue = paint.Hue.from_angle(start_hue_angle + delta_hue_angle * i)
        for j in range(3):
            row.append(hue.rgb[j] >> 8)
    buf = row * height
    return buffer(buf)

def generate_graded_rgb_buf(start_colour, end_colour, width, height):
    # TODO: deprecate this function in favour of the one in pixbuf
    """
    Generate a rectangular RGB buffer whose RGB values change linearly

    start_colour: the start colour
    end_colour: the end colour
    width: the required width of the rectangle in pixels
    height: the required height of the rectangle in pixels
    """
    def get_rgb(colour):
        if isinstance(colour, gtk.gdk.Color):
            return gdk_color_to_rgb(colour)
        elif isinstance(colour, paint.Colour):
            return colour.rgb
        else:
            return colour
    start_rgb = get_rgb(start_colour)
    end_rgb = get_rgb(end_colour)
    # Use Fraction() to eliminate rounding errors causing chr() range problems
    delta_rgb = [fractions.Fraction(end_rgb[i] - start_rgb[i], width) for i in range(3)]
    row = bytearray()
    for i in range(width):
        for j in range(3):
            row.append(chr((start_rgb[j] + int(delta_rgb[j] * i)) >> 8))
    buf = row * height
    return buffer(buf)

class GenericAttrDisplay(gtk.DrawingArea):
    LABEL = None

    def __init__(self, colour=None, size=(100, 15)):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(size[0], size[1])
        self.colour = colour
        self.fg_colour = gtkpwx.best_foreground(colour)
        self.indicator_val = 0.5
        self._set_colour(colour)
        self.connect('expose-event', self.expose_cb)
        self.show()
    @staticmethod
    def indicator_top(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, 5), (-5, 0), (5, 0))]
    @staticmethod
    def indicator_bottom(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, -5), (-5, 0), (5, 0))]
    def new_colour(self, arg):
        if isinstance(arg, paint.Colour):
            colour = gtk.gdk.Color(*arg.rgb)
        else:
            colour = gtk.gdk.Color(*arg)
        return self.get_colormap().alloc_color(colour)
    def draw_indicators(self, gc):
        w, h = self.window.get_size()
        indicator_x = int(w * self.indicator_val)
        gc.set_foreground(self.fg_colour)
        gc.set_background(self.fg_colour)
        # TODO: fix bottom indicator
        self.window.draw_polygon(gc, True, self.indicator_top(indicator_x, 0))
        self.window.draw_polygon(gc, True, self.indicator_bottom(indicator_x, h - 1))
    def draw_label(self, gc):
        if self.LABEL is None:
            return
        w, h = self.window.get_size()
        layout = self.create_pango_layout(self.LABEL)
        tw, th = layout.get_pixel_size()
        x, y = ((w - tw) / 2, (h - th) / 2)
        gc.set_foreground(self.fg_colour)
        self.window.draw_layout(gc, x, y, layout, self.fg_colour)
    def expose_cb(self, _widget, _event):
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

class HueDisplay(GenericAttrDisplay):
    LABEL = _('Hue')

    def expose_cb(self, _widget, _event):
        if self.colour is None:
            self.window.set_background(gtk.gdk.Color(0, 0, 0))
            return
        gc = self.window.new_gc()
        gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        #
        if self.colour.hue.is_grey():
            self.window.set_background(self.new_colour(self.colour.hue_rgb))
            self.draw_label(gc)
            return
        #
        backwards = options.get('colour_wheel', 'red_to_yellow_clockwise')
        w, h = self.window.get_size()
        spectral_buf = generate_spectral_rgb_buf(self.colour.hue, 2 * math.pi, w, h, backwards)
        self.window.draw_rgb_image(gc, x=0, y=0, width=w, height=h,
            dith=gtk.gdk.RGB_DITHER_NONE,
            rgb_buf=spectral_buf)

        self.draw_indicators(gc)
        self.draw_label(gc)
    def _set_colour(self, colour):
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour.hue_rgb))

class ValueDisplay(GenericAttrDisplay):
    LABEL = _('Value')
    def __init__(self, colour=None, size=(100, 15)):
        GenericAttrDisplay.__init__(self, colour=colour, size=size)
        self.start_colour = paint.BLACK
        self.end_colour = paint.WHITE
    def expose_cb(self, _widget, _event):
        if self.colour is None:
            self.window.set_background(gtk.gdk.Color(0, 0, 0))
            return
        gc = self.window.new_gc()
        gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        w, h = self.window.get_size()

        graded_buf = generate_graded_rgb_buf(self.start_colour, self.end_colour, w, h)
        self.window.draw_rgb_image(gc, x=0, y=0, width=w, height=h,
            dith=gtk.gdk.RGB_DITHER_NONE,
            rgb_buf=graded_buf)

        self.draw_indicators(gc)
        self.draw_label(gc)
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour))
        self.indicator_val = colour.value

class ChromaDisplay(ValueDisplay):
    LABEL = _('Chroma')
    def __init__(self, colour=None, size=(100, 15)):
        ValueDisplay.__init__(self, colour=colour, size=size)
        if colour is not None:
            self._set_colour(colour)
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.start_colour = self.colour.hcv.chroma_side()
        self.end_colour = colour.hue_rgb
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(self.start_colour))
        self.indicator_val = colour.chroma

class HCVDisplay(gtk.VBox):
    def __init__(self, colour=paint.WHITE, size=(256, 120), stype = gtk.SHADOW_ETCHED_IN):
        gtk.VBox.__init__(self)
        #
        w, h = size
        self.hue = HueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.hue, stype), expand=False)
        self.value = ValueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.value, stype), expand=False)
        self.chroma = ChromaDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.chroma, stype), expand=False)
        self.show()
    def set_colour(self, new_colour):
        self.chroma.set_colour(new_colour)
        self.hue.set_colour(new_colour)
        self.value.set_colour(new_colour)

# Targetted attribute displays

class GenericTargetedAttrDisplay(gtk.DrawingArea):
    LABEL = None

    def __init__(self, colour=None, size=(100, 15)):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(size[0], size[1])
        self.colour = colour
        self.fg_colour = gtkpwx.best_foreground(colour)
        self.indicator_val = 0.5
        self.target_colour = colour
        self.target_val = None
        self.target_fg_colour = gtkpwx.best_foreground(colour)
        self._set_target_colour(colour)
        self._set_colour(colour)
        self.connect('expose-event', self.expose_cb)
        self.show()
    @staticmethod
    def indicator_top(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, 5), (-5, 0), (5, 0))]
    @staticmethod
    def indicator_bottom(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, -5), (-5, 0), (5, 0))]
    def new_colour(self, arg):
        if isinstance(arg, paint.Colour):
            colour = gtk.gdk.Color(*arg.rgb)
        else:
            colour = gtk.gdk.Color(*arg)
        return self.get_colormap().alloc_color(colour)
    def draw_indicators(self, gc):
        if self.indicator_val is None:
            return
        w, h = self.window.get_size()
        indicator_x = int(w * self.indicator_val)
        gc.set_foreground(self.fg_colour)
        gc.set_background(self.fg_colour)
        # TODO: fix bottom indicator
        self.window.draw_polygon(gc, True, self.indicator_top(indicator_x, 0))
        self.window.draw_polygon(gc, True, self.indicator_bottom(indicator_x, h - 1))
    def draw_label(self, gc):
        if self.LABEL is None:
            return
        w, h = self.window.get_size()
        layout = self.create_pango_layout(self.LABEL)
        tw, th = layout.get_pixel_size()
        x, y = ((w - tw) / 2, (h - th) / 2)
        gc.set_foreground(self.fg_colour)
        self.window.draw_layout(gc, x, y, layout, self.fg_colour)
    def draw_target(self, gc):
        if self.target_val is None:
            return
        w, h = self.window.get_size()
        target_x = int(w * self.target_val)
        gc.set_foreground(self.target_fg_colour)
        gc.set_background(self.target_fg_colour)
        self.window.draw_line(gc, target_x, 0, target_x, int(h))
    def expose_cb(self, _widget, _event):
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
    def _set_target_colour(self, colour):
        """
        Set values that only change when the colour changes.
        Such as the location of the indicators.
        """
        pass
    def set_target_colour(self, colour):
        self.target_colour = colour
        self._set_target_colour(colour)
        self.queue_draw()

class TargetedHueDisplay(GenericTargetedAttrDisplay):
    LABEL = _('Hue')

    def expose_cb(self, _widget, _event):
        if self.colour is None and self.target_val is None:
            self.window.set_background(gtk.gdk.Color(0, 0, 0))
            return
        gc = self.window.new_gc()
        gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        #
        if self.target_val is None:
            if self.indicator_val is None:
                self.window.set_background(self.new_colour(self.colour.hue_rgb))
                self.draw_label(gc)
                return
            else:
                centre_hue = self.colour.hue
        else:
            centre_hue = self.target_colour.hue
        #
        backwards = options.get('colour_wheel', 'red_to_yellow_clockwise')
        w, h = self.window.get_size()
        spectral_buf = generate_spectral_rgb_buf(centre_hue, 2 * math.pi, w, h, backwards)
        self.window.draw_rgb_image(gc, x=0, y=0, width=w, height=h,
            dith=gtk.gdk.RGB_DITHER_NONE,
            rgb_buf=spectral_buf)

        self.draw_target(gc)
        self.draw_indicators(gc)
        self.draw_label(gc)
    def _set_colour(self, colour):
        if colour is None:
            self.indicator_val = None
        elif colour.hue.is_grey():
            self.indicator_val = None
        else:
            self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour.hue_rgb))
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
            self.target_fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour.hue_rgb))
            self.target_val = 0.5
            if self.indicator_val is not None:
                offset = 0.5 * (self.colour.hue - colour.hue) / math.pi
                if options.get('colour_wheel', 'red_to_yellow_clockwise'):
                    self.indicator_val = 0.5 + offset
                else:
                    self.indicator_val = 0.5 - offset

class TargetedValueDisplay(GenericTargetedAttrDisplay):
    LABEL = _('Value')
    def __init__(self, colour=None, size=(100, 15)):
        GenericTargetedAttrDisplay.__init__(self, colour=colour, size=size)
        self.start_colour = paint.BLACK
        self.end_colour = paint.WHITE
    def expose_cb(self, _widget, _event):
        if self.colour is None:
            self.window.set_background(gtk.gdk.Color(0, 0, 0))
            return
        gc = self.window.new_gc()
        gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        w, h = self.window.get_size()

        graded_buf = generate_graded_rgb_buf(self.start_colour, self.end_colour, w, h)
        self.window.draw_rgb_image(gc, x=0, y=0, width=w, height=h,
            dith=gtk.gdk.RGB_DITHER_NONE,
            rgb_buf=graded_buf)

        self.draw_indicators(gc)
        self.draw_label(gc)
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour))
        self.indicator_val = colour.value

class TargetedChromaDisplay(TargetedValueDisplay):
    LABEL = _('Chroma')
    def __init__(self, colour=None, size=(100, 15)):
        TargetedValueDisplay.__init__(self, colour=colour, size=size)
        if colour is not None:
            self._set_colour(colour)
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.start_colour = self.colour.hcv.chroma_side()
        self.end_colour = colour.hue_rgb
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(self.start_colour))
        self.indicator_val = colour.chroma

class TargetedHCVDisplay(gtk.VBox):
    def __init__(self, colour=paint.WHITE, size=(256, 120), stype = gtk.SHADOW_ETCHED_IN):
        gtk.VBox.__init__(self)
        #
        w, h = size
        self.hue = TargetedHueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.hue, stype), expand=False)
        self.value = TargetedValueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.value, stype), expand=False)
        self.chroma = TargetedChromaDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.chroma, stype), expand=False)
        self.show()
    def set_colour(self, new_colour):
        self.chroma.set_colour(new_colour)
        self.hue.set_colour(new_colour)
        self.value.set_colour(new_colour)
    def set_target_colour(self, new_target_colour):
        self.chroma.set_target_colour(new_target_colour)
        self.hue.set_target_colour(new_target_colour)
        self.value.set_target_colour(new_target_colour)

class HueWheelNotebook(gtk.Notebook):
    def __init__(self):
        gtk.Notebook.__init__(self)
        self.hue_chroma_wheel = HueChromaWheel(nrings=5)
        self.hue_value_wheel = HueValueWheel()
        self.append_page(self.hue_value_wheel, gtk.Label(_('Hue/Value Wheel')))
        self.append_page(self.hue_chroma_wheel, gtk.Label(_('Hue/Chroma Wheel')))
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

class ColourWheel(gtk.DrawingArea):
    def __init__(self, nrings=9):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(400, 400)
        self.scale = 1.0
        self.zoom = 1.0
        self.one = 100 * self.scale
        self.size = 3
        self.scaled_size = self.size * self.scale
        self.cx = 0.0
        self.cy = 0.0
        self.paint_colours = {}
        self.mixed_colours = {}
        self.target_colours = {}
        self.crosshair = None
        self.nrings = nrings
        self.connect('expose-event', self.expose_cb)
        self.set_has_tooltip(True)
        self.connect('query-tooltip', self.query_tooltip_cb)
        self.add_events(gtk.gdk.SCROLL_MASK)
        self.connect('scroll-event', self.scroll_event_cb)
        self.show()
    def polar_to_cartesian(self, radius, angle):
        if options.get('colour_wheel', 'red_to_yellow_clockwise'):
            x = -radius * math.cos(angle)
        else:
            x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        return (int(self.cx + x), int(self.cy - y))
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
        # TODO: move location of tootip as mouse moves
        colour, rng = self.get_colour_nearest_to_xy(x, y)
        tooltip.set_text(colour.name if colour is not None else '')
        return True
    def scroll_event_cb(self, _widget, event):
        if event.device.source == gtk.gdk.SOURCE_MOUSE:
            new_zoom = self.zoom + 0.025 * (-1 if event.direction == gtk.gdk.SCROLL_UP else 1)
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
    def new_colour(self, rgb):
        colour = gtk.gdk.Color(*rgb)
        return self.get_colormap().alloc_color(colour)
    def draw_circle(self, cx, cy, radius, filled=False):
        cx -= radius
        cy -= radius
        diam = int(2 * radius)
        self.window.draw_arc(self.gc, filled, int(cx), int(cy), diam, diam, 0, 360 * 64)
    def expose_cb(self, _widget, _event):
        self.gc = self.window.new_gc()
        self.gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        #
        spacer = 10
        scaledmax = 110.0
        #
        self.gc.set_background(self.new_colour(paint.RGB_WHITE / 2))
        #
        dw, dh = self.window.get_size()
        self.cx = dw / 2
        self.cy = dh / 2
        #
        # calculate a scale factor to use for drawing the graph based
        # on the minimum available width or height
        mindim = min(self.cx, dh / 2)
        self.scale = mindim / scaledmax
        self.one = self.scale * 100
        self.scaled_size = self.size * self.scale
        #
        # Draw the graticule
        self.gc.set_foreground(self.new_colour(paint.RGB_WHITE * 3 / 4))
        for radius in [100 * (i + 1) * self.scale / self.nrings for i in range(self.nrings)]:
            self.draw_circle(self.cx, self.cy, int(round(radius * self.zoom)))
        #
        self.gc.line_width = 2
        for angle in [utils.PI_60 * i for i in range(6)]:
            hue = paint.Hue.from_angle(angle)
            self.gc.set_foreground(self.new_colour(hue.rgb))
            self.window.draw_line(self.gc, self.cx, self.cy, *self.polar_to_cartesian(self.one * self.zoom, angle))
        for target_colour in self.target_colours.values():
            target_colour.draw()
        for paint_colour in self.paint_colours.values():
            paint_colour.draw()
        for mix in self.mixed_colours.values():
            mix.draw()
        if self.crosshair is not None:
            self.crosshair.draw()
        return True
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
            self.colour_angle = self.colour.hue.angle if not self.colour.hue.is_grey() else utils.Angle(math.pi / 2)
            self.fg_colour = self.parent.new_colour(self.colour.rgb)
            self.value_colour = self.parent.new_colour(paint.BLACK)
            self.chroma_colour = self.parent.new_colour(self.colour.hcv.chroma_side())
            self.choose_radius_attribute()
        def range_from(self, x, y):
            dx = x - self.x
            dy = y - self.y
            return math.sqrt(dx * dx + dy * dy)
    class ColourSquare(ColourShape):
        polypoints = ((-1, 1), (-1, -1), (1, -1), (1, 1))
        def draw(self):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            square = tuple(tuple(pp[i] * self.parent.scaled_size for i in range(2)) for pp in self.polypoints)
            square_pts = [tuple((int(self.x + pt[0]), int(self.y +  pt[1]))) for pt in square]
            # draw the middle
            self.parent.gc.set_foreground(self.fg_colour)
            self.parent.window.draw_polygon(self.parent.gc, filled=True, points=square_pts)
            self.parent.gc.set_foreground(self.chroma_colour)
            self.parent.window.draw_polygon(self.parent.gc, filled=False, points=square_pts)
    class ColourDiamond(ColourSquare):
        polypoints = ((1.5, 0), (0, -1.5), (-1.5, 0), (0, 1.5))
    class ColourCircle(ColourShape):
        def draw(self):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            self.parent.gc.set_foreground(self.fg_colour)
            self.parent.draw_circle(self.x, self.y, radius=self.parent.scaled_size, filled=True)
            self.parent.gc.set_foreground(self.chroma_colour)
            self.parent.draw_circle(self.x, self.y, radius=self.parent.scaled_size, filled=False)
    class ColourCrossHair(ColourShape):
        def draw(self):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            self.parent.gc.set_foreground(self.fg_colour)
            radius = self.parent.scaled_size
            halflen = radius * 2
            self.parent.draw_circle(self.x, self.y, radius=radius, filled=False)
            self.parent.window.draw_line(self.parent.gc, int(self.x - halflen), int(self.y), int(self.x + halflen), int(self.y))
            self.parent.window.draw_line(self.parent.gc, int(self.x), int(self.y - halflen), int(self.x), int(self.y + halflen))

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
    Row = collections.namedtuple('Row', ['colour'])
    types = Row(colour=object)
    def append_colour(self, colour):
        self.append(self.Row(colour))
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
gobject.signal_new('colour-removed', ColourListStore, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))

def paint_cell_data_func(column, cell, model, model_iter, attribute):
    colour = model.get_value_named(model_iter, 'colour')
    if attribute == 'name':
        cell.set_property('text', colour.name)
        cell.set_property('background', gtk.gdk.Color(*colour.rgb))
        cell.set_property('foreground', gtkpwx.best_foreground(colour.rgb))
    elif attribute == 'value':
        cell.set_property('text', str(round(colour.value, 2)))
        cell.set_property('background', gtk.gdk.Color(*colour.value_rgb()))
        cell.set_property('foreground', gtkpwx.best_foreground(colour.value_rgb()))
    elif attribute == 'hue':
        cell.set_property('background', gtk.gdk.Color(*colour.hue_rgb))
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
                    cell_renderer=gtk.CellRendererText,
                    expand=None,
                    start=False
                ),
                properties=None,
                cell_data_function_spec=tlview.CellDataFunctionSpec(
                    function=paint_cell_data_func,
                    user_data=tns.attr
                ),
                attributes={}
            ),
        ],
    )

COLOUR_ATTRS = [
    TNS(_('Colour Name'), 'name', {'resizable' : True}, lambda row: row.colour.name),
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
        selection_mode=gtk.SELECTION_MULTIPLE,
        columns=colour_attribute_column_specs(model)
    )

class ColourListView(tlview.View, actions.CAGandUIManager):
    Model = ColourListStore
    specification = generate_colour_list_spec(ColourListStore)
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
                ('remove_selected_colours', gtk.STOCK_REMOVE, None, None,
                 _('Remove the selected colours from the list.'), self._remove_selection_cb),
            ]
        )
    def _remove_selection_cb(self, _action):
        """
        Delete the currently selected colours
        """
        self.model.remove_colours(self.get_selected_colours())
    def get_selected_colours(self):
        """
        Return the currently selected colours as a list.
        """
        return [row.colour for row in tlview.NamedTreeModel.get_selected_rows(self.get_selection())]

if __name__ == '__main__':
    doctest.testmod()
