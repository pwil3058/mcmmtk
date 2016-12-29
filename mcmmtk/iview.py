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
A viewer for digital images
'''

import fractions
import cairo

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import GObject

from . import actions
from . import gtkpwx
from . import printer

class ZoomedPixbuf(object):
    """
    A scaled GdkPixbuf.Pixbuf and some handy methods
    """
    def __init__(self, pixbuf):
        """
        pixbuf: an instance of GdkPixbuf.Pixbuf
        """
        self.__uz_pixbuf = self.__z_pixbuf = pixbuf
        self.__zoom = fractions.Fraction(1)
    @property
    def zoomed_pixbuf(self):
        return self.__z_pixbuf
    @property
    def unzoomed_pixbuf(self):
        return self.__uz_pixbuf
    @property
    def aspect_ratio(self):
        """
        Return the aspect ratio for this Pixbuf
        """
        return fractions.Fraction(self.__uz_pixbuf.get_width(), self.__uz_pixbuf.get_height())
    @property
    def wzoom(self):
        """
        Return the zoom in factor the width dimension
        """
        return fractions.Fraction(self.__z_pixbuf.get_width(), self.__uz_pixbuf.get_width())
    @property
    def hzoom(self):
        """
        Return the zoom factor in the height dimension
        """
        return fractions.Fraction(self.__z_pixbuf.get_height(), self.__uz_pixbuf.get_height())
    @property
    def zoom(self):
        """
        Return the zoom factor
        """
        return self.__zoom
    def get_unzoomed_size(self):
        """
        Return a WH tuple with the unzoomed size of the Pixbuf
        """
        return gtkpwx.WH(self.__uz_pixbuf.get_width(), self.__uz_pixbuf.get_height())
    def get_zoomed_size(self):
        """
        Return a WH tuple with the zoomed size of the Pixbuf
        """
        return gtkpwx.WH(self.__z_pixbuf.get_width(), self.__z_pixbuf.get_height())
    def aspect_ratio_matches(self, wharg):
        """
        Does our Pixbuf's aspect ratio match the dimensions in wharg
        """
        if wharg.width < wharg.height:
            return round(wharg.height * self.aspect_ratio) == wharg.width
        else:
            return round(wharg.width / self.aspect_ratio) == wharg.height
    def set_zoom(self, zoom):
        """
        Zoom the Pixbuf by the specified amount
        """
        new_width = int(round(self.__uz_pixbuf.get_width() * zoom))
        new_height = int(round(self.__uz_pixbuf.get_height() * zoom))
        self.__z_pixbuf = self.__uz_pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
        # make sure reported zoom matches what was set so user code doesn't
        # get stuck in endless loops
        self.__zoom = zoom
    def set_zoomed_size(self, new_zsize):
        """
        Set the size of the zoomed Pixbuf to the specified sie
        """
        assert self.aspect_ratio_matches(new_zsize)
        self.__z_pixbuf = self.__uz_pixbuf.scale_simple(new_zsize.width, new_zsize.height, GdkPixbuf.InterpType.BILINEAR)
        self.__zoom = (self.hzoom + self.wzoom) / 2
    def calc_zooms_for(self, wharg):
        """
        Calculate the width and height zooms needed to match wharg
        """
        usize = self.get_unzoomed_size()
        wzoom = fractions.Fraction(wharg.width, usize.width)
        hzoom = fractions.Fraction(wharg.height, usize.height)
        return gtkpwx.WH(wzoom, hzoom)

class PixbufView(Gtk.ScrolledWindow, actions.CAGandUIManager):
    UI_DESCR = '''
        <ui>
            <popup name='pixbuf_view_popup'>
                <menuitem action='copy_to_clipboard'/>
                <menuitem action='print_pixbuf'/>
            </popup>
        </ui>
        '''
    AC_SELN_MADE, AC_SELN_MASK = actions.ActionCondns.new_flags_and_mask(1)
    AC_PIXBUF_SET, AC_PICBUF_MASK = actions.ActionCondns.new_flags_and_mask(1)
    ZOOM_FACTOR = fractions.Fraction(11, 10)
    ZOOM_IN_ADJ = (ZOOM_FACTOR - 1) / 2
    ZOOM_OUT_ADJ = (1 / ZOOM_FACTOR - 1) / 2
    def __init__(self):
        """
        A drawing area to contain a single image
        """
        Gtk.ScrolledWindow.__init__(self)
        actions.CAGandUIManager.__init__(self, popup='/pixbuf_view_popup')
        self.__pixbuf = None
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.__da = Gtk.DrawingArea()
        self.__da.connect("draw", self._expose_cb)
        self.__size_allocate_cb_id = self.connect('size-allocate', self._size_allocate_cb)
        self.add_with_viewport(self.__da)
        self.__last_alloc = None
        #
        self.add_events(Gdk.EventMask.SCROLL_MASK)
        self.connect('scroll_event', self._scroll_ecb)
        #
        self.__seln = XYSelection(self.__da)
        self.__seln.connect('status-changed', self._seln_status_change_cb)
        self.__seln.connect('motion_notify', self._seln_motion_cb)
        self.__press_cb_id = self.__da.connect('button_press_event', self._da_button_press_cb)
        self.__cb_ids = []
        self.__cb_ids.append(self.__da.connect('button_release_event', self._da_button_release_cb))
        self.__cb_ids.append(self.__da.connect('motion_notify_event', self._da_motion_notify_cb))
        self.__cb_ids.append(self.__da.connect('leave_notify_event', self._da_leave_notify_cb))
        for cb_id in self.__cb_ids:
            self.__da.handler_block(cb_id)
    def populate_action_groups(self):
        self.action_groups[self.AC_SELN_MADE].add_actions(
            [
                ('copy_to_clipboard', Gtk.STOCK_COPY, None, None,
                 _('Copy the selection to the clipboard.'),
                 self._copy_to_clipboard_acb
                ),
            ]
        )
        self.action_groups[self.AC_PIXBUF_SET].add_actions(
            [
                ('print_pixbuf', Gtk.STOCK_PRINT, None, None,
                 _('Print this image.'),
                 self._print_pixbuf_acb
                ),
                ('zoom_in', Gtk.STOCK_ZOOM_IN, None, None,
                 _('Enlarge the image.'),
                 self.zoom_in
                ),
                ('zoom_out', Gtk.STOCK_ZOOM_OUT, None, None,
                 _('Shrink the image.'),
                 self.zoom_out
                ),
            ]
        )
    @property
    def window(self):
        """
        The drawing area's window
        """
        return self.__da.window
    def _resize_da(self):
        """
        Resize the drawable area to match the zoomed pixbuf size
        """
        self.handler_block(self.__size_allocate_cb_id)
        new_size = self.__pixbuf.get_zoomed_size()
        self.__da.set_size_request(new_size.width, new_size.height)
        sizediff = self.get_allocation() - new_size
        if sizediff.width >= 0 and sizediff.height >= 0:
            self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        else:
            self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.handler_unblock(self.__size_allocate_cb_id)
    def set_pixbuf(self, pixbuf):
        """
        pixbuf: a GdkPixbuf.Pixbuf instance (to be displayed) or None.
        """
        if pixbuf is not None:
            self.__pixbuf = ZoomedPixbuf(pixbuf)
            alloc = self.get_allocation()
            sizediff = alloc - self.__pixbuf.get_unzoomed_size()
            if self.__pixbuf.aspect_ratio_matches(alloc):
                self.__pixbuf.set_zoomed_size(alloc)
                self._resize_da()
            else:
                zoom = max(self.__pixbuf.calc_zooms_for(alloc))
                self.__pixbuf.set_zoom(zoom)
                self._resize_da()
            self.__seln.clear()
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_PIXBUF_SET, self.AC_PICBUF_MASK))
        else:
            self.__pixbuf = None
            self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_PICBUF_MASK))
    def _expose_cb(self, _widget, cairo_ctxt):
        """
        Repaint the drawing area
        """
        if self.__pixbuf is not None:
            sfc = Gdk.cairo_surface_create_from_pixbuf(self.__pixbuf.zoomed_pixbuf, 0, None)
            cairo_ctxt.set_source_surface(sfc, 0, 0)
            cairo_ctxt.paint()
            if self.__seln.in_progress() or self.__seln.seln_made():
                scale = self.__pixbuf.zoom / self.__seln_zoom
                rect = self.__seln.get_scaled_rectangle(scale)
                if self.__seln.seln_made():
                    cairo_ctxt.set_dash([])
                else:
                    cairo_ctxt.set_dash([3])
                cairo_ctxt.rectangle(*rect)
                cairo_ctxt.set_source_rgb(0, 0, 0)
                cairo_ctxt.set_operator(cairo.OPERATOR_XOR)
                cairo_ctxt.stroke()
        return True
    def _size_allocate_cb(self, _widget, _event):
        """
        Handle a resize incident
        """
        alloc = self.get_allocation()
        if self.__last_alloc is None:
            self.__zin_adj = (alloc.width * self.ZOOM_IN_ADJ, alloc.height * self.ZOOM_IN_ADJ)
            self.__zout_adj = (alloc.width * self.ZOOM_OUT_ADJ, alloc.height * self.ZOOM_OUT_ADJ)
            self.__last_alloc = gtkpwx.WH(alloc.width, alloc.height)
            return
        elif alloc == self.__last_alloc:
            return
        self.__zin_adj = (alloc.width * self.ZOOM_IN_ADJ, alloc.height * self.ZOOM_IN_ADJ)
        self.__zout_adj = (alloc.width * self.ZOOM_OUT_ADJ, alloc.height * self.ZOOM_OUT_ADJ)
        delta_alloc = alloc - self.__last_alloc
        self.__last_alloc = gtkpwx.WH(alloc.width, alloc.height)
        if self.__pixbuf is None:
            return False
        zoomed_sizediff = alloc - self.__pixbuf.get_zoomed_size()
        if self.__pixbuf.aspect_ratio_matches(alloc) and abs(zoomed_sizediff.width) < 10:
            # right ratio and approximately the right size
            self.__pixbuf.set_zoomed_size(alloc)
            self._resize_da()
        elif delta_alloc.width >= 0 and delta_alloc.height >= 0:
            # We're getting bigger
            if zoomed_sizediff.width > 10 or zoomed_sizediff.height > 10:
                zoom = max(self.__pixbuf.calc_zooms_for(alloc))
                self.__pixbuf.set_zoom(zoom)
                self._resize_da()
            elif zoomed_sizediff.width < 0 or zoomed_sizediff.height < 0:
                self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            else:
                self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        elif delta_alloc.width <= 0 and delta_alloc.height <= 0:
            # We're getting smaller
            if zoomed_sizediff.width > 10 or zoomed_sizediff.height > 10:
                zoom = max(self.__pixbuf.calc_zooms_for(alloc))
                self.__pixbuf.set_zoom(zoom)
                self._resize_da()
            elif zoomed_sizediff.width < -10 and zoomed_sizediff.height < -10:
                if zoomed_sizediff.width > -30 or zoomed_sizediff.height > -30:
                    zoom = max(self.__pixbuf.calc_zooms_for(alloc))
                    self.__pixbuf.set_zoom(zoom)
                    self._resize_da()
            elif zoomed_sizediff.width < 0 or zoomed_sizediff.height < 0:
                self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            else:
                self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
    def _seln_status_change_cb(self, _widget, seln_made):
        """
        Record the "zoom" value at the time of status change so that
        it can be used to determine if the "zoom" has changed at draw
        time and if so scale the selection accordingly.
        """
        if self.__pixbuf is not None:
            self.__seln_zoom = self.__pixbuf.zoom
        else:
            self.__seln_zoom = None
        self.action_groups.update_condns(actions.MaskedCondns(self.AC_SELN_MADE if seln_made else 0, self.AC_SELN_MASK))
        self.__da.queue_draw()
    def _seln_motion_cb(self, _widget):
        """
        Trigger repaint to show updated selection rectangle
        """
        self.__da.queue_draw()
    # TODO: make 'zoom in' smoother
    def zoom_in(self, _action=None):
        if self.__pixbuf is not None:
            current_zoom = self.__pixbuf.zoom
            self.__pixbuf.set_zoom(current_zoom * self.ZOOM_FACTOR)
            self._resize_da()
            for dim, adj in enumerate([self.get_hadjustment(), self.get_vadjustment()]):
                new_val = adj.get_value() * self.ZOOM_FACTOR + self.__zin_adj[dim]
                adj.set_value(new_val)
    # TODO: make 'zoom out' smoother
    def zoom_out(self, _action=None):
        if self.__pixbuf is not None:
            current_zoom = self.__pixbuf.zoom
            min_zoom = max(self.__pixbuf.calc_zooms_for(self.__last_alloc))
            if current_zoom <= min_zoom:
                Gdk.beep()
            else:
                self.__pixbuf.set_zoom(max(current_zoom / self.ZOOM_FACTOR, min_zoom))
                self._resize_da()
                for dim, adj in enumerate([self.get_hadjustment(), self.get_vadjustment()]):
                    new_val = adj.get_value() / self.ZOOM_FACTOR + self.__zout_adj[dim]
                    adj.set_value(max(0, new_val))
    def _scroll_ecb(self, _widget, event):
        """
        Manage use of the scroll wheel for zooming and scrolling
        """
        if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.DOWN:
                self.zoom_in()
                return True
            elif event.direction == Gdk.ScrollDirection.UP:
                self.zoom_out()
                return True
        elif event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self.emit('scroll-child', Gtk.SCROLL_STEP_FORWARD, True)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.emit('scroll-child', Gtk.SCROLL_STEP_BACKWARD, True)
            return True
    # Careful not to override CAGandUIManager method
    def _da_button_press_cb(self, widget, event):
        if event.button == 1 and event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            self.__last_xy = gtkpwx.XY(event.x, event.y)
            for cb_id in self.__cb_ids:
                widget.handler_unblock(cb_id)
            return True
    def _da_motion_notify_cb(self, widget, event):
        this_xy = gtkpwx.XY(event.x, event.y)
        delta_xy = this_xy - self.__last_xy
        size = self.__last_alloc
        self.__last_xy = this_xy
        for dim, adj in enumerate([self.get_hadjustment(), self.get_vadjustment()]):
            new_val = adj.get_value() - delta_xy[dim]
            adj.set_value(min(max(new_val, 0), adj.upper - adj.page_size))
        widget.queue_draw()
        return True
    def _da_button_release_cb(self, widget, event):
        if event.button != 1:
            return
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        return True
    def _da_leave_notify_cb(self, widget, event):
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        return True
    def _copy_to_clipboard_acb(self, _action):
        """
        Copy the selection to the system clipboard
        """
        scale = self.__pixbuf.zoom / self.__seln_zoom
        rect = self.__seln.get_scaled_rectangle(scale)
        pixbuf = self.__pixbuf.zoomed_pixbuf.new_subpixbuf(*rect)
        cbd = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cbd.set_image(pixbuf)
    def _print_pixbuf_acb(self, _action):
        """
        Print this pixbuf
        """
        printer.print_pixbuf(self.__pixbuf.unzoomed_pixbuf)

class XYSelection(GObject.GObject):
    """
    A generic XY selection widget
    """
    def __init__(self, source):
        """
        source: the widget on which the selection is to be made
        """
        GObject.GObject.__init__(self)
        self.__source = source
        self.__seln_made = False
        self.__start_xy = self.__end_xy = None
        source.add_events(Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.__press_cb_id = source.connect('button_press_event', self._button_press_cb)
        self.__cb_ids = []
        self.__cb_ids.append(source.connect('button_release_event', self._button_release_cb))
        self.__cb_ids.append(source.connect('motion_notify_event', self._motion_notify_cb))
        self.__cb_ids.append(source.connect('leave_notify_event', self._leave_notify_cb))
        for cb_id in self.__cb_ids:
            source.handler_block(cb_id)
    def in_progress(self):
        return self.__start_xy is not None and not self.__seln_made
    def seln_made(self):
        return self.__seln_made
    @property
    def start_xy(self):
        return self.__start_xy
    @property
    def end_xy(self):
        return self.__end_xy
    def get_scaled_rectangle(self, scale=1.0):
        """
        Return a gtkpwx.RECT with integer values suitable for drawable
        and pixbuf method arguments
        """
        if self.__start_xy is None:
            # TODO: change this to raising an Exception
            return None
        start = self.__start_xy * scale
        end = self.__end_xy * scale
        delta = end - start
        # event x/y are reals so we need to conert to int
        rint = lambda v : int(round(v))
        # width and height have to be positive
        if delta.x >= 0:
            xx = rint(start.x)
            ww = rint(delta.x)
        else:
            xx = rint(end.x)
            ww = rint(-delta.x)
        if delta.y >= 0:
            yy = rint(start.y)
            hh = rint(delta.y)
        else:
            yy = rint(end.y)
            hh = rint(-delta.y)
        return gtkpwx.RECT(x=xx, y=yy, width=ww, height=hh)
    def _clear(self):
        self.__seln_made = False
        self.__start_xy = self.__end_xy = None
        self.emit('status-changed', False)
    def clear(self):
        if self.in_progress():
            raise Exception('clear while selection in progress')
        self._clear()
    def _button_press_cb(self, widget, event):
        """
        Start the selection
        """
        if event.button == 1 and event.get_state() & Gdk.ModifierType.CONTROL_MASK == 0:
            self.__start_xy = self.__end_xy = gtkpwx.XY(event.x, event.y)
            self.__seln_made = False
            for cb_id in self.__cb_ids:
                widget.handler_unblock(cb_id)
            self.emit('status-changed', False)
            return True
        elif event.button == 2:
            if self.in_progress():
                for cb_id in self.__cb_ids:
                    widget.handler_block(cb_id)
                self._clear()
            elif self.__seln_made:
                self.clear()
            return True
    def _motion_notify_cb(self, widget, event):
        """
        Record the position and pass on the "motion-notify" signal
        """
        self.__end_xy = gtkpwx.XY(event.x, event.y)
        self.emit('motion-notify')
        return True
    def _leave_notify_cb(self, widget, event):
        """
        Start the selection
        """
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        self._clear()
        return True
    def _button_release_cb(self, widget, event):
        """
        Start the selection
        """
        if event.button != 1 or not self.in_progress():
            return
        self.__end_xy = gtkpwx.XY(event.x, event.y)
        self.__seln_made = True
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        self.emit('status-changed', True)
        return True
GObject.type_register(XYSelection)
GObject.signal_new('status-changed', XYSelection, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_BOOLEAN,))
GObject.signal_new('motion-notify', XYSelection, GObject.SignalFlags.RUN_LAST, None, ())
