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
Provide generic enhancements to Tree and List View widgets primarily to create
them from templates and allow easier access to named contents.
"""

import collections

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk

class _NamedTreeModelMixin:
    # TODO: trim and improve _NamedTreeModelMixin
    ROW = None # this is a namedtuple type
    TYPES = None # this is an instance of ROW defining column types
    @classmethod
    def col_index(cls, label):
        return cls.ROW._fields.index(label)
    @classmethod
    def col_indices(cls, labels):
        return [cls.ROW._fields.index(label) for label in labels]
    @staticmethod
    def get_selected_rows(selection):
        """
        Return the list of ROW() tuples associated with a list of paths.
        selection: a Gtk.TreeSelection specifying the model and the
        rows to be retrieved
        """
        model, paths = selection.get_selected_rows()
        return [model.ROW(*model[p]) for p in paths]
    @staticmethod
    def get_selected_row(selection):
        model, model_iter = selection.get_selected()
        return model.ROW(*model[tree_iter])
    def get_row(self, model_iter):
        return self.ROW(*self[model_iter])
    def get_named(self, model_iter, *labels):
        return self.get(model_iter, *self.col_indices(labels))
    def get_value_named(self, model_iter, label):
        return self.get_value(model_iter, self.col_index(label))
    def set_value_named(self, model_iter, label, value):
        self.set_value(model_iter, self.col_index(label), value)
    def set_named(self, model_iter, *label_values):
        col_values = []
        for index in len(label_values):
            if (index % 2) == 0:
                col_values.append(self.col_index(label_values[index]))
            else:
                col_values.append(label_values[index])
        self.set(model_iter, *col_values)
    def named(self):
        # Iterate over rows as instances of type ROW()
        model_iter = self.get_iter_first()
        while model_iter is not None:
            yield self.get_row(model_iter)
            model_iter = self.iter_next(model_iter)
        return
    def find_named(self, select_func):
        model_iter = self.get_iter_first()
        while model_iter:
            if select_func(self.get_row(model_iter)):
                return model_iter
            else:
                model_iter = self.iter_next(model_iter)
        return None

class NamedListStore(Gtk.ListStore, _NamedTreeModelMixin):
    __g_type_name__ = "NamedListStore"
    def __init__(self):
        Gtk.ListStore.__init__(*[self] + list(self.TYPES))
    def append_contents(self, rows):
        for row in rows:
            self.append(row)
    def set_contents(self, rows):
        self.clear()
        for row in rows:
            self.append(row)

class NamedTreeStore(Gtk.TreeStore, _NamedTreeModelMixin):
    __g_type_name__ = "NamedTreeStore"
    def __init__(self):
        Gtk.TreeStore.__init__(*[self] + list(self.TYPES))

# Utility functions
def delete_selection(seln):
    model, paths = seln.get_selected_rows()
    model_iters = [model.get_iter(path) for path in paths]
    for model_iter in model_iters:
        model.remove(model_iter)

def insert_before_selection(seln, row):
    model, paths = seln.get_selected_rows()
    if not paths:
        return
    model_iter = model.insert_before(model.get_iter(paths[0]), row)
    return (model, model_iter)

def insert_after_selection(seln, row):
    model, paths = seln.get_selected_rows()
    if not paths:
        return
    model_iter = model.insert_after(model.get_iter(paths[-1]), row)
    return (model, model_iter)

# come in handy classes
class CellRendererSpin(Gtk.CellRendererSpin):
    __g_type_name__ = "CellRendererSpin"
    """
    A modified version that propagates the SpinButton's "value-changed"
    signal.  Makes the behaviour more like a SpinButton.
    """
    def __init__(self, *args, **kwargs):
        """
        Add an "editing-started" callback to setup connection to SpinButton
        """
        Gtk.CellRendererSpin.__init__(self, *args, **kwargs)
        self.connect("editing-started", CellRendererSpin._editing_started_cb)
    @staticmethod
    def _editing_started_cb(cell, spinbutton, path):
        """
        Connect to the spinbutton's "value-changed" signal
        """
        spinbutton.connect("value-changed", CellRendererSpin._spinbutton_value_changed_cb, cell, path)
    @staticmethod
    def _spinbutton_value_changed_cb(spinbutton, cell, path):
        """
        Propagate "value-changed" signal to get things moving
        """
        cell.emit("value-changed", path, spinbutton)
GObject.signal_new("value-changed", CellRendererSpin, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT,))

# Views
class ViewSpec:
    __slots__ = ("properties", "selection_mode", "columns")
    def __init__(self, properties=None, selection_mode=None, columns=None):
        self.properties = properties if properties is not None else dict()
        self.selection_mode = selection_mode
        self.columns = columns if columns is not None else list()

class ColumnSpec:
    __slots__ = ("title", "properties", "cells", "sort_key_function")
    def __init__(self, title, properties=None, cells=None, sort_key_function=None):
        self.title = title
        self.properties = properties if properties is not None else dict()
        self.cells = cells if cells is not None else list()
        self.sort_key_function = sort_key_function

def simple_column(lbl, *cells):
    return ColumnSpec(
        title=lbl,
        properties={"expand": False, "resizable" : True},
        cells=cells,
    )

class CellRendererSpec:
    __slots__ = ("cell_renderer", "properties", "expand", "start", "signal_handlers")
    def __init__(self, cell_renderer, properties=None, expand=None, start=False, signal_handlers=None):
        self.cell_renderer = cell_renderer
        self.properties = properties if properties else {}
        self.signal_handlers = signal_handlers if signal_handlers else {}
        self.expand = expand
        self.start = start

class CellDataFunctionSpec:
    __slots__ = ("function", "user_data")
    def __init__(self, function, user_data=None):
        self.function = function
        self.user_data = user_data

class CellSpec:
    __slots__ = ("cell_renderer_spec", "cell_data_function_spec", "attributes")
    def __init__(self, cell_renderer_spec, cell_data_function_spec=None, attributes=None):
        self.cell_renderer_spec = cell_renderer_spec
        self.cell_data_function_spec = cell_data_function_spec
        self.attributes = attributes if attributes is not None else dict()

def stock_icon_cell(model, fld, xalign=0.5):
    return CellSpec(
        cell_renderer_spec=CellRendererSpec(
            cell_renderer=Gtk.CellRendererPixbuf,
            expand=False,
            start=True,
            properties={"xalign": xalign},
        ),
        cell_data_function_spec=None,
        attributes = {"stock_id" : model.col_index("icon")}
    )

def _text_cell(model, fld, editable, xalign=0.5):
    return CellSpec(
        cell_renderer_spec=CellRendererSpec(
            cell_renderer=Gtk.CellRendererText,
            expand=False,
            start=True,
            properties={"editable" : editable, "xalign": xalign},
        ),
        cell_data_function_spec=None,
        attributes = {"text" : model.col_index(fld)}
    )

def fixed_text_cell(model, fld, xalign=0.5):
    return _text_cell(model, fld, False, xalign)

def editable_text_cell(model, fld, xalign=0.5):
    return _text_cell(model, fld, True, xalign)

def _toggle_cell(model, fld, activatable, toggle_cb=None, xalign=0.5):
    return CellSpec(
        cell_renderer_spec=CellRendererSpec(
            cell_renderer=Gtk.CellRendererToggle,
            expand=False,
            start=True,
            properties={"activatable" : activatable},
            signal_handlers={"toggled" : toggle_cb} if toggle_cb else None
        ),
        cell_data_function_spec=None,
        attributes = {"active" : model.col_index(fld)}
    )

def fixed_toggle_cell(model, fld, xalign=0.5):
    return _toggle_cell(model, fld, False, None, xalign)

def activatable_toggle_cell(model, fld, toggle_cb, xalign=0.5):
    return _togg;e_cell(model, fld, True, toggle_cb, xalign)

def _transformer(treeviewcolumn, cell, model, iter, func_and_index):
    func, index = func_and_index
    pyobj = model.get_value(iter, index)
    cell.set_property("text", func(pyobj))
    return

def _stock_id_transformer(treeviewcolumn, cell, model, iter, func_and_index):
    func, index = func_and_index
    pyobj = model.get_value(iter, index)
    cell.set_property("stock_id", func(pyobj))
    return

def transform_data_cell(model, fld, transform_func, xalign=0.5):
    return CellSpec(
        cell_renderer_spec=CellRendererSpec(
            cell_renderer=Gtk.CellRendererText,
            expand=False,
            start=True,
            properties={"editable" : False, "xalign": xalign},
        ),
        cell_data_function_spec=CellDataFunctionSpec(_transformer, (transform_func, model.col_index(fld))),
        attributes = {}
    )

def transform_pixbuf_stock_id_cell(model, fld, transform_func, xalign=0.5):
    return CellSpec(
        cell_renderer_spec=CellRendererSpec(
            cell_renderer=Gtk.CellRendererPixbuf,
            expand=False,
            start=True,
            properties={"xalign": xalign},
        ),
        cell_data_function_spec=CellDataFunctionSpec(_stock_id_transformer, (transform_func, model.col_index(fld))),
        attributes = {}
    )

def mark_up_cell(model, fld):
    return CellSpec(
        cell_renderer_spec=CellRendererSpec(
            cell_renderer=Gtk.CellRendererText,
            expand=False,
            start=True,
            properties={"editable" : False},
        ),
        cell_data_function_spec=None,
        attributes = {"markup" : model.col_index(fld)}
    )

def handle_control_c_key_press_cb(widget, event):
    if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
        if event.keyval in [Gdk.keyval_from_name(ch) for ch in "cC"]:
            widget.handle_control_c_key_press_cb()
            return True
    return False

class View(Gtk.TreeView):
    __g_type_name__ = "View"
    # TODO: bust View() up into a number of "mix ins" for more flexibility
    MODEL = None
    SPECIFICATION = None
    def __init__(self, model=None, size_req=None):
        if model is None:
            model = self.MODEL()
        else:
            assert isinstance(model, self.MODEL) or isinstance(model.get_model(), self.MODEL)
        Gtk.TreeView.__init__(self, model)
        if size_req:
            self.set_size_request(size_req[0], size_req[1])
        spec = self.SPECIFICATION if isinstance(self.SPECIFICATION, ViewSpec) else self.SPECIFICATION(model)
        for prop_name, prop_val in spec.properties.items():
            self.set_property(prop_name, prop_val)
        if spec.selection_mode is not None:
            self.get_selection().set_mode(spec.selection_mode)
        for col_d in spec.columns:
            self._view_add_column(col_d)
        self.connect("button_press_event", self._handle_clear_selection_cb)
        self.connect("key_press_event", self._handle_clear_selection_cb)
        self.connect("key_press_event", handle_control_c_key_press_cb)
        self._connect_model_changed_cbs()
        self._modified_cbs = []
    def _connect_model_changed_cbs(self):
        """
        Set up the call back for changes to the store so that the
        "sorted" indicator can be turned off if the model changes in
        any way.
        """
        model = self.get_model()
        sig_names = ["row-changed", "row-deleted", "row-has-child-toggled",
            "row-inserted", "rows-reordered"]
        self._change_cb_ids = [model.connect(sig_name, self._model_changed_cb) for sig_name in sig_names]
        self.last_sort_column = None
        self.sort_order = Gtk.SortType.ASCENDING
    @staticmethod
    def _create_cell(column, cell_renderer_spec):
        cell = cell_renderer_spec.cell_renderer()
        if cell_renderer_spec.expand is not None:
            if cell_renderer_spec.start:
                column.pack_start(cell, expand=cell_renderer_spec.expand)
            else:
                column.pack_end(cell, expand=cell_renderer_spec.expand)
        else:
            if cell_renderer_spec.start:
                column.pack_start(cell, expand=True)
            else:
                column.pack_end(cell, expand=True)
        for prop_name, value in cell_renderer_spec.properties.items():
            cell.set_property(prop_name, value)
        for signal_name, signal_handler in cell_renderer_spec.signal_handlers.items():
            cell.connect(signal_name, signal_handler)
        return cell
    def handle_control_c_key_press_cb(self):
        pass
    def _view_add_column(self, col_d):
        col = Gtk.TreeViewColumn(col_d.title)
        self.append_column(col)
        for prop_name, prop_val in col_d.properties.items():
            col.set_property(prop_name, prop_val)
        for cell_d in col_d.cells:
            self._view_add_cell(col, cell_d)
        if col_d.sort_key_function is not None:
            col.connect("clicked", self._column_clicked_cb, lambda x: col_d.sort_key_function(x[1]))
            col.set_clickable(True)
    def _view_add_cell(self, col, cell_d):
        cell = self._create_cell(col, cell_d.cell_renderer_spec)
        if cell_d.cell_data_function_spec is not None:
            col.set_cell_data_func(cell, cell_d.cell_data_function_spec.function, cell_d.cell_data_function_spec.user_data)
        for attr_name, attr_index in cell_d.attributes.items():
            col.add_attribute(cell, attr_name, attr_index)
            if attr_name == "text":
                cell.connect("edited", self._cell_text_edited_cb, attr_index)
            elif attr_name == "active":
                cell.connect("toggled", self._cell_toggled_cb, attr_index)
    @property
    def model(self):
        return self.get_model()
    @model.setter
    def model(self, new_model):
        self.set_model(new_model)
    def set_model(self, model):
        assert model is None or isinstance(model, self.MODEL) or isinstance(model.get_model(), self.MODEL)
        old_model = self.get_model()
        for sig_cb_id in self._change_cb_ids:
            old_model.disconnect(sig_cb_id)
        Gtk.TreeView.set_model(self, model)
        if model is not None:
            self._connect_model_changed_cbs()
    def _notify_modification(self):
        for cbk, data in self._modified_cbs:
            if data is None:
                cbk()
            else:
                cbk(data)
    def register_modification_callback(self, cbk, data=None):
        self._modified_cbs.append([cbk, data])
    def _handle_clear_selection_cb(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 2:
                self.get_selection().unselect_all()
                return True
        elif event.type == Gdk.EventType.KEY_PRESS:
            if event.keyval == Gdk.keyval_from_name("Escape"):
                self.get_selection().unselect_all()
                return True
        return False
    def _cell_text_edited_cb(self, cell, path, new_text, index):
        # TODO: need to do type cast on ALL tree editable cells
        if isinstance(cell, Gtk.CellRendererSpin):
            self.get_model()[path][index] = self.get_model().TYPES[index](new_text)
        else:
            self.get_model()[path][index] = new_text
        self._notify_modification()
    def _cell_toggled_cb(self, cell, path, index):
        # TODO: test CellRendererToggle
        # should it be model[path][index] = not model[path][index]
        self.model[path][index] = cell.get_active()
        self._notify_modification()
    def _model_changed_cb(self, *_args, **_kwargs):
        """
        The model has changed and if the column involved is the
        current sort column the may no longer be sorted so we
        need to turn off the sort indicators.
        """
        # TODO: be more fine grained turning off sort indication
        if self.last_sort_column is not None:
            self.last_sort_column.set_sort_indicator(False)
            self.last_sort_column = None
    def _column_clicked_cb(self, column, sort_key_function):
        """Sort the rows based on the given column"""
        # Heavily based on the FAQ example
        assert column.get_tree_view() == self
        if self.last_sort_column is not None:
            self.last_sort_column.set_sort_indicator(False)
        #
        if self.last_sort_column == column:
           if self.sort_order == Gtk.SortType.ASCENDING:
              self.sort_order = Gtk.SortType.DESCENDING
           else:
              self.sort_order = Gtk.SortType.ASCENDING
        else:
           self.sort_order   = Gtk.SortType.ASCENDING
           self.last_sort_column = column
        model = self.get_model()
        if len(model) == 0:
            return
        erows = list(enumerate(model.named()))
        erows.sort(key=sort_key_function)
        if self.sort_order == Gtk.SortType.DESCENDING:
            erows.reverse()
        # Turn off reorder callback while we do the reordering
        model.handler_block(self._change_cb_ids[-1])
        model.reorder([r[0] for r in erows])
        model.handler_unblock(self._change_cb_ids[-1])
        column.set_sort_indicator(True)
        column.set_sort_order(self.sort_order)

class ListView(View):
    __g_type_name__ = "ListView"
    MODEL = NamedListStore

class TreeView(View):
    __g_type_name__ = "TreeView"
    MODEL = NamedTreeStore
