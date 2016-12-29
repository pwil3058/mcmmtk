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
Provide some higher level access to PyGTK printing mechanisms
'''

# TODO: find out more about PyGTK printing and make this better

import os
import math
import fractions

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import PangoCairo

from . import options

MM_PER_PT = 25.4 / 72

_USER_SETTINGS_FILE = os.path.join(options.get_user_config_dir(), 'printer.cfg')

SETTINGS = Gtk.PrintSettings()

if os.path.exists(_USER_SETTINGS_FILE) and os.path.getsize(_USER_SETTINGS_FILE):
    if not SETTINGS.load_file(_USER_SETTINGS_FILE):
        SETTINGS.to_file(_USER_SETTINGS_FILE)
else:
    SETTINGS.to_file(_USER_SETTINGS_FILE)

def print_text(text, parent=None):
    '''
    Print a plain text
    '''
    prop = Gtk.PrintOperation()

    prop.set_print_settings(SETTINGS)
    prop.set_unit(Gtk.UNIT_MM)

    data = {'text' : text}

    prop.connect( "begin-print", begin_print_text, data)
    prop.connect("draw-page", draw_page_text, data)

    res = prop.run(Gtk.PrintOperationAction.PRINT_DIALOG, parent)

    if res == Gtk.PrintOperationResult.ERROR:
        emsg = prop.get_error()
        error_dialog = Gtk.MessageDialog(parent,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.CLOSE,
            "Error printing: {}\n".format(emsg))
        error_dialog.connect("response", lambda w,id: w.destroy())
        error_dialog.show()
    elif res == Gtk.PrintOperationResult.APPLY:
        settings = prop.get_print_settings()
        if settings.to_file(_USER_SETTINGS_FILE):
            SETTINGS.load_file(_USER_SETTINGS_FILE)

def begin_print_text(operation, context, data):
    """
    Process the "begin-print" signal
    """
    layout = context.create_pango_layout()
    layout.set_width(int(context.get_width() * Pango.SCALE))
    layout.set_text(data['text'])
    _twidth, theight = layout.get_pixel_size()
    data['layout'] = layout
    lheight = float(theight) / layout.get_line_count()
    pheight = context.get_height()
    lpp = int(pheight / lheight)
    data['lines_per_page'] = lpp
    operation.set_n_pages(int(math.ceil(float(layout.get_line_count()) / lpp)))

def draw_page_text(operation, context, page_num, data):
    """
    Process the "draw-page" signal
    """
    cc = context.get_cairo_context()

    layout = data['layout']

    start_line = page_num * data['lines_per_page']
    if page_num + 1 != operation.props.n_pages:
        end_line = start_line + data['lines_per_page']
    else:
        end_line = None

    layout.set_text(''.join(data['text'].splitlines(True)[start_line:end_line]))

    cc.move_to(0, 0)
    cc.show_layout(layout)

def print_markup_chunks(chunks, parent=None):
    """
    Print a series of marked up chunks with no page breaks within a
    chunk unless the chunk itself is too big for one page.
    """
    prop = Gtk.PrintOperation()
    #
    prop.set_print_settings(SETTINGS)
    prop.set_unit(Gtk.Unit.MM)
    #
    data = {'chunks' : chunks}
    #
    prop.connect( "begin-print", begin_print_markup_chunks, data)
    prop.connect("draw-page", draw_page_markup_chunks, data)
    #
    res = prop.run(Gtk.PrintOperationAction.PRINT_DIALOG, parent)
    #
    if res == Gtk.PrintOperationResult.ERROR:
        emsg = prop.get_error()
        error_dialog = Gtk.MessageDialog(parent,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.CLOSE,
            "Error printing: {}\n".format(emsg))
        error_dialog.connect("response", lambda w,id: w.destroy())
        error_dialog.show()
    elif res == Gtk.PrintOperationResult.APPLY:
        settings = prop.get_print_settings()
        if settings.to_file(_USER_SETTINGS_FILE):
            SETTINGS.load_file(_USER_SETTINGS_FILE)

def begin_print_markup_chunks(operation, context, data):
    """
    Allocate the chunks to pages ready for printing.
    """
    pheight = context.get_height()
    spwidth = int(context.get_width() * Pango.SCALE)
    pages = []
    page = []
    total_height = 0
    for chunk in data['chunks']:
        layout = context.create_pango_layout()
        layout.set_width(spwidth)
        layout.set_markup(chunk)
        _twidth, theight = layout.get_pixel_size()
        if total_height + theight < pheight:
            page.append(layout)
            total_height += theight
        elif theight < pheight:
            pages.append(page)
            page = [layout]
            total_height = theight
        else:
            # TODO: handle the case where a marked up chunk is too big for one page
            pass
    if page:
        pages.append(page)
    data['pages'] = pages
    operation.set_n_pages(len(pages))

def draw_page_markup_chunks(operation, context, page_num, data):
    """
    Process the "draw-page" signal
    """
    y = 0
    for layout in data['pages'][page_num]:
        cc = context.get_cairo_context()
        cc.move_to(0, y)
        PangoCairo.show_layout(cc, layout)
        _w, h = layout.get_pixel_size()
        y += h

def print_pixbuf(pixbuf, parent=None):
    """
    Print a single pixbuf on one page.
    """
    prop = Gtk.PrintOperation()
    #
    prop.set_print_settings(SETTINGS)
    prop.set_unit(Gtk.UNIT_MM)
    #
    data = {'pixbuf' : pixbuf}
    #
    prop.connect( "begin-print", begin_print_pixbuf, data)
    prop.connect("draw-page", draw_page_pixbuf, data)
    #
    res = prop.run(Gtk.PrintOperationAction.PRINT_DIALOG, parent)
    #
    if res == Gtk.PrintOperationResult.ERROR:
        emsg = prop.get_error()
        error_dialog = Gtk.MessageDialog(parent,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.CLOSE,
            "Error printing: {}\n".format(emsg))
        error_dialog.connect("response", lambda w,id: w.destroy())
        error_dialog.show()
    elif res == Gtk.PrintOperationResult.APPLY:
        settings = prop.get_print_settings()
        if settings.to_file(_USER_SETTINGS_FILE):
            SETTINGS.load_file(_USER_SETTINGS_FILE)

def begin_print_pixbuf(operation, context, data):
    """
    Scale the  pixbuf to fit the page.
    """
    pheight = data['pixbuf'].get_height()
    pwidth = data['pixbuf'].get_width()
    psu = context.get_page_setup()
    if pwidth > pheight:
        data['pixbuf'] = data['pixbuf'].rotate_simple(Gdk.PIXBUF_ROTATE_CLOCKWISE)
        pheight = data['pixbuf'].get_height()
        pwidth = data['pixbuf'].get_width()
    cheight = fractions.Fraction.from_float(context.get_height())
    cwidth = fractions.Fraction.from_float(context.get_width())
    hscale = fractions.Fraction(cheight, pheight)
    wscale = fractions.Fraction(cwidth, pwidth)
    if hscale < wscale:
        new_width = int(round(pwidth * hscale))
        new_height = int(round(pheight * hscale))
    else:
        new_width = int(round(pwidth * wscale))
        new_height = int(round(pheight * wscale))
    data['pixbuf'] = data['pixbuf'].scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
    operation.set_n_pages(1)

def draw_page_pixbuf(operation, context, page_num, data):
    """
    Process the "draw-page" signal
    """
    cc = context.get_cairo_context()
    cc.set_source_pixbuf(data['pixbuf'], 0, 0)
    cc.paint()
