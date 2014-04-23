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

import gtk

from mcmmtk import actions
from mcmmtk import icons

class Mixer(gtk.VBox, actions.CAGandUIManager):
    UI_DESCR = '''
    <ui>
    </ui>
    '''
    AC_HAVE_MIXTURE, AC_MASK = actions.ActionCondns.new_flags_and_mask(1)
    def __init__(self):
        gtk.VBox.__init__(self)
        actions.CAGandUIManager.__init__(self)
        self._last_dir = None
    def populate_action_groups(self):
        """
        Set up the actions for this component
        """
        pass
    def _quit_mixer_cb(self, _action):
        """
        Exit the program
        """
        # TODO: add checks for unsaved work in mixer before exiting
        gtk.main_quit()

class TopLevelWindow(gtk.Window):
    """
    A top level window wrapper around a palette
    """
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_title('mcmmtk: Mixer')
        self.mixer = Mixer()
        self.connect("destroy", self.mixer._quit_mixer_cb)
        self.add(self.mixer)
        self.show_all()
