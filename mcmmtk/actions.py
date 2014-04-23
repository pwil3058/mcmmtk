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
Conditionally enabled GTK action groups
'''

import collections

import gtk
import gobject

def create_flag_generator():
    """
    Create a new flag generator
    """
    next_flag_num = 0
    while True:
        yield 2 ** next_flag_num
        next_flag_num += 1

class MaskedCondns(collections.namedtuple('MaskedCondns', ['condns', 'mask'])):
    __slots__ = ()

    def __or__(self, other):
        return MaskedCondns(self.condns | other.condns, self.mask | other.mask)

class ActionCondns(object):
    _flag_generator = create_flag_generator()

    @staticmethod
    def new_flags_and_mask(count):
        """
        Return "count" new condition flags and their mask as a tuple
        """
        flags = [ActionCondns._flag_generator.next() for _i in range(count)]
        mask = sum(flags)
        return tuple(flags + [mask])

AC_DONT_CARE = 0
AC_SELN_NONE, \
AC_SELN_MADE, \
AC_SELN_UNIQUE, \
AC_SELN_PAIR, \
AC_SELN_MASK = ActionCondns.new_flags_and_mask(4)

def get_masked_seln_conditions(seln):
    if seln is None:
        return MaskedCondns(AC_DONT_CARE, AC_SELN_MASK)
    selsz = seln.count_selected_rows()
    if selsz == 0:
        return MaskedCondns(AC_SELN_NONE, AC_SELN_MASK)
    elif selsz == 1:
        return MaskedCondns(AC_SELN_MADE + AC_SELN_UNIQUE, AC_SELN_MASK)
    elif selsz == 2:
        return MaskedCondns(AC_SELN_MADE + AC_SELN_PAIR, AC_SELN_MASK)
    else:
        return MaskedCondns(AC_SELN_MADE, AC_SELN_MASK)

class ActionButton(gtk.Button):
    def __init__(self, action, use_underline=True):
        label = action.get_property("label")
        stock_id = action.get_property("stock-id")
        if label is not None:
            # Empty (NB not None) label means use image only
            gtk.Button.__init__(self, use_underline=use_underline)
            if stock_id is not None:
                image = gtk.Image()
                image.set_from_stock(stock_id, gtk.ICON_SIZE_BUTTON)
                self.set_image(image)
            if label:
                self.set_label(label)
        else:
            gtk.Button.__init__(self, stock=stock_id, label=label, use_underline=use_underline)
        self.set_tooltip_text(action.get_property("tooltip"))
        action.connect_proxy(self)

class ActionButtonList:
    def __init__(self, action_group_list, action_name_list=None, use_underline=True):
        self.list = []
        self.dict = {}
        if action_name_list:
            for a_name in action_name_list:
                for a_group in action_group_list:
                    action = a_group.get_action(a_name)
                    if action:
                        button = ActionButton(action, use_underline)
                        self.list.append(button)
                        self.dict[a_name] = button
                        break
        else:
            for a_group in action_group_list:
                for action in a_group.list_actions():
                    button = ActionButton(action, use_underline)
                    self.list.append(button)
                    self.dict[action.get_name()] = button

class ActionHButtonBox(gtk.HBox):
    def __init__(self, action_group_list, action_name_list=None,
                 use_underline=True, expand=True, fill=True, padding=0):
        gtk.HBox.__init__(self)
        self.button_list = ActionButtonList(action_group_list, action_name_list, use_underline)
        for button in self.button_list.list:
            self.pack_start(button, expand, fill, padding)
        return self

class ConditionalActionGroups(object):
    class UnknownAction(Exception): pass
    def __init__(self, name, ui_mgrs=None, selection=None):
        self.groups = dict()
        self.current_condns = 0
        self.ui_mgrs = [] if ui_mgrs is None else ui_mgrs[:]
        self.name = name
        self.set_selection(selection)
    def _group_name(self, condns):
        return '{0}:{1:x}'.format(self.name, condns)
    def _seln_condns_change_cb(self, seln):
        self.update_condns(get_masked_seln_conditions(seln))
    def set_selection(self, seln):
        if seln is None:
            return None
        self.update_condns(get_masked_seln_conditions(seln))
        return seln.connect('changed', self._seln_condns_change_cb)
    def __getitem__(self, condns):
        if condns not in self.groups:
            self.groups[condns] = gtk.ActionGroup(self._group_name(condns))
            self.groups[condns].set_sensitive((condns & self.current_condns) == condns)
            for ui_mgr in self.ui_mgrs:
                ui_mgr.insert_action_group(self.groups[condns], -1)
        return self.groups[condns]
    def copy_action(self, new_condns, action_name):
        action = self.get_action(action_name)
        if not action:
            raise self.UnknownAction(action)
        self[new_condns].add_action(action)
    def move_action(self, new_condns, action_name):
        for agrp in self.groups.values():
            action = agrp.get_action(action_name)
            if not action:
                raise self.UnknownAction(action)
            agrp.remove_action(action)
            self[new_condns].add_action(action)
    def update_condns(self, changed_condns):
        """
        Update the current condition state
        changed_condns: is a MaskedCondns instance
        """
        condns = changed_condns.condns | (self.current_condns & ~changed_condns.mask)
        for key_condns, group in self.groups.items():
            if changed_condns.mask & key_condns:
                group.set_sensitive((key_condns & condns) == key_condns)
        self.current_condns = condns
    def set_visibility_for_condns(self, condns, visible):
        self.groups[condns].set_visible(visible)
    def add_ui_mgr(self, ui_mgr):
        self.ui_mgrs.append(ui_mgr)
        for agrp in self.groups.values():
            ui_mgr.insert_action_group(agrp, -1)
    def get_action(self, action_name):
        for agrp in self.groups.values():
            action = agrp.get_action(action_name)
            if action:
                return action
        return None
    def connect_activate(self, action_name, callback, *user_data):
        """
        Connect the callback to the "activate" signal of the named action
        """
        return self.get_action(action_name).connect('activate', callback, *user_data)
    def __str__(self):
        string = 'ConditionalActionGroups({0})\n'.format(self.name)
        for condns, group in self.groups.items():
            name = group.get_name()
            member_names = '['
            for member_name in [action.get_name() for action in group.list_actions()]:
                member_names += '{0}, '.format(member_name)
            member_names += ']'
            string += '\tGroup({0:x},{1}): {2}\n'.format(condns, name, member_names)
        return string
    def create_action_button(self, action_name, use_underline=True):
        action = self.get_action(action_name)
        return ActionButton(action, use_underline=use_underline)
    def create_action_button_box(self, action_name_list, use_underline=True,
                                 horizontal=True,
                                 expand=True, fill=True, padding=0):
        if horizontal:
            box = gtk.HBox()
        else:
            box = gtk.VBox()
        for action_name in action_name_list:
            button = self.create_action_button(action_name, use_underline)
            box.pack_start(button, expand, fill, padding)
        return box

CLASS_INDEP_AGS = ConditionalActionGroups('class_indep')

class UIManager(gtk.UIManager):
    # TODO: check to see if this workaround is still necessary
    def __init__(self):
        gtk.UIManager.__init__(self)
        self.connect('connect-proxy', self._ui_manager_connect_proxy)
    @staticmethod
    def _ui_manager_connect_proxy(_ui_mgr, action, widget):
        tooltip = action.get_property('tooltip')
        if isinstance(widget, gtk.MenuItem) and tooltip:
            widget.set_tooltip_text(tooltip)

class CAGandUIManager(gobject.GObject):
    '''This is a "mix in" class and needs to be merged with a gtk.Window() descendant'''
    UI_DESCR = '''<ui></ui>'''
    def __init__(self, selection=None, popup=None):
        gobject.GObject.__init__(self)
        self.ui_manager = UIManager()
        CLASS_INDEP_AGS.add_ui_mgr(self.ui_manager)
        name = '{0}:{1:x}'.format(self.__class__.__name__, self.__hash__())
        self.action_groups = ConditionalActionGroups(name, ui_mgrs=[self.ui_manager], selection=selection)
        self.populate_action_groups()
        self.ui_manager.add_ui_from_string(self.UI_DESCR)
        self._popup_cb_id = self._popup = None
        self.set_popup(popup)
    def populate_action_groups(self):
        assert False, 'should be derived in subclass'
    @staticmethod
    def _button_press_cb(widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 3 and widget._popup:
                menu = widget.ui_manager.get_widget(widget._popup)
                menu.popup(None, None, None, event.button, event.time)
                return True
        return False
    def set_popup(self, popup):
        if self._popup_cb_id is None:
            self._popup_cb_id = self.connect('button_press_event', self._button_press_cb)
            if popup is None:
                self.enable_popup(False)
        elif self._popup is None and popup is not None:
            self.enable_popup(True)
        elif popup is None:
            self.enable_popup(False)
        self._popup = popup
    def enable_popup(self, enable):
        if self._popup_cb_id is not None:
            if enable:
                self.handler_unblock(self._popup_cb_id)
            else:
                self.handler_block(self._popup_cb_id)
    def set_visibility_for_condns(self, condns, visible):
        self.action_groups.set_visibility_for_condns(condns, visible)
