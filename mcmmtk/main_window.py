### Copyright (C) 2005-2016 Peter Williams <pwil3058@gmail.com>
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

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GdkPixbuf

from .bab.decorators import singleton

from .gtx import actions
from . import icons
from .gtx import dialogue
from .gtx import recollect

from .epaint import gpaint
from .epaint import pedit
from .epaint import pmix
from .epaint import pseries
from .epaint import vpaint
from .epaint import standards

APP_ICON_PIXBUF = GdkPixbuf.Pixbuf.new_from_file(icons.APP_ICON_FILE)

class ModelPaintMixer(pmix.PaintMixer):
    PAINT = vpaint.ModelPaint
    MATCHED_PAINT_LIST_VIEW = pmix.MatchedModelPaintListView
    PAINT_SERIES_MANAGER = pseries.ModelPaintSeriesManager
    PAINT_STANDARDS_MANAGER = standards.PaintStandardsManager
    MIXED_PAINT_INFORMATION_DIALOGUE = pmix.MixedModelPaintInformationDialogue
    MIXTURE = pmix.ModelMixture
    MIXED_PAINT = pmix.MixedModelPaint
    UI_DESCR = """
    <ui>
        <menubar name="mixer_menubar">
            <menu action="mixer_file_menu">
                <menuitem action="print_mixer"/>
            </menu>
            <menu action="mixer_series_manager_menu">
                <menuitem action="mixer_load_paint_series"/>
            </menu>
            <menu action="mixer_standards_manager_menu">
                <menuitem action="mixer_load_paint_standard"/>
            </menu>
            <menu action="reference_resource_menu">
                <menuitem action="open_reference_image_viewer"/>
            </menu>
        </menubar>
    </ui>
    """

class ModelPaintListNotebook(gpaint.PaintListNotebook):
    class PAINT_LIST_VIEW(gpaint.ModelPaintListView):
        UI_DESCR = '''
            <ui>
                <popup name='paint_list_popup'>
                    <menuitem action='edit_selected_paint'/>
                    <menuitem action='remove_selected_paints'/>
                </popup>
            </ui>
            '''
        def populate_action_groups(self):
            """
            Populate action groups ready for UI initialization.
            """
            self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
                [
                    ('edit_selected_paint', Gtk.STOCK_EDIT, None, None,
                     _('Load the selected paint into the paint editor.'), ),
                ]
            )

class ModelPaintEditor(pedit.PaintEditor):
    PAINT = vpaint.ModelPaint
    RESET_CHARACTERISTICS = False

class ModelPaintSeriesEditor(Gtk.VBox):
    class Editor(pseries.PaintSeriesEditor):
        PAINT_EDITOR = ModelPaintEditor
        PAINT_LIST_NOTEBOOK = ModelPaintListNotebook
        UI_DESCR = """
        <ui>
          <menubar name="paint_series_editor_menubar">
            <menu action="paint_collection_editor_file_menu">
              <menuitem action="new_paint_collection"/>
              <menuitem action="open_paint_collection_file"/>
              <menuitem action="save_paint_collection_to_file"/>
              <menuitem action="save_paint_collection_as_file"/>
            </menu>
            <menu action="paint_collection_editor_samples_menu">
              <menuitem action="take_screen_sample"/>
              <menuitem action="open_sample_viewer"/>
            </menu>
          </menubar>
        </ui>
        """
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.editor = self.Editor(pack_current_file_box=False)
        self.editor.action_groups.get_action('close_colour_editor').set_visible(False)
        self.editor.set_file_path(None)
        self._menubar = self.editor.ui_manager.get_widget('/paint_series_editor_menubar')
        hbox = Gtk.HBox()
        hbox.pack_start(self._menubar, expand=False, fill=True, padding=0)
        hbox.pack_start(Gtk.VSeparator(), expand=False, fill=True, padding=0)
        hbox.pack_start(Gtk.Label("  "), expand=False, fill=True, padding=0)
        hbox.pack_start(self.editor.current_file_box, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        self.pack_start(self.editor, expand=True, fill=True, padding=0)

class ModelPaintStandardEditor(Gtk.VBox):
    class Editor(standards.PaintStandardEditor):
        PAINT_EDITOR = ModelPaintEditor
        PAINT_LIST_NOTEBOOK = ModelPaintListNotebook
        UI_DESCR = """
        <ui>
          <menubar name="paint_standards_editor_menubar">
            <menu action="paint_collection_editor_file_menu">
              <menuitem action="new_paint_collection"/>
              <menuitem action="open_paint_collection_file"/>
              <menuitem action="save_paint_collection_to_file"/>
              <menuitem action="save_paint_collection_as_file"/>
            </menu>
            <menu action="paint_collection_editor_samples_menu">
              <menuitem action="take_screen_sample"/>
              <menuitem action="open_sample_viewer"/>
            </menu>
          </menubar>
        </ui>
        """
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.editor = self.Editor(pack_current_file_box=False)
        self.editor.action_groups.get_action('close_colour_editor').set_visible(False)
        self.editor.set_file_path(None)
        self._menubar = self.editor.ui_manager.get_widget('/paint_standards_editor_menubar')
        hbox = Gtk.HBox()
        hbox.pack_start(self._menubar, expand=False, fill=True, padding=0)
        hbox.pack_start(Gtk.VSeparator(), expand=False, fill=True, padding=0)
        hbox.pack_start(Gtk.Label("  "), expand=False, fill=True, padding=0)
        hbox.pack_start(self.editor.current_file_box, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        self.pack_start(self.editor, expand=True, fill=True, padding=0)

@singleton
class MainWindow(dialogue.MainWindow, actions.CAGandUIManager):
    __g_type_name__ = "MainWindow"
    UI_DESCR = """
    <ui>
        <menubar name="mcmmtk_left_menubar">
            <menu action="mcmmtk_main_window_file_menu">
              <menuitem action="mcmmtk_main_window_quit"/>
            </menu>
        </menubar>
    </ui>
    """
    recollect.define("mcmmtk_main_window", "last_geometry", recollect.Defn(str, ""))
    def __init__(self):
        dialogue.MainWindow.__init__(self)
        self.parse_geometry(recollect.get("mcmmtk_main_window", "last_geometry"))
        actions.CAGandUIManager.__init__(self)
        self.set_default_icon(APP_ICON_PIXBUF)
        self.set_icon(APP_ICON_PIXBUF)
        self.connect("delete_event", Gtk.main_quit)
        vbox = Gtk.VBox()
        lmenu_bar = self.ui_manager.get_widget('/mcmmtk_left_menubar')
        vbox.pack_start(lmenu_bar, expand=False, fill=True, padding=0)
        stack = Gtk.Stack()
        stack.add_titled(ModelPaintMixer(), "paint_mixer", _("Paint Mixer"))
        stack.add_titled(ModelPaintSeriesEditor(), "paint_series_editor", _("Paint Series Editor"))
        stack.add_titled(ModelPaintStandardEditor(), "paint_standards_editor", _("Paint Standards Editor"))
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        vbox.pack_start(stack_switcher, expand=False, fill=True, padding=0)
        vbox.pack_start(stack, expand=True, fill=True, padding=0)
        self.add(vbox)
        self.show_all()
        self.connect("configure-event", self._configure_event_cb)
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions(
            [
                ("mcmmtk_main_window_file_menu", None, _("File"), ),
                ("mcmmtk_main_window_quit", Gtk.STOCK_QUIT, _("Quit"), None,
                 _("Close the application."),
                 lambda _action: Gtk.main_quit()
                ),
            ])
    def _configure_event_cb(self, widget, event):
        recollect.set("mcmmtk_main_window", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))
