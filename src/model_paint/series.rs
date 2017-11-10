// Copyright 2017 Peter Williams <pwil3058@gmail.com>
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use gdk;
use gtk;
use gtk::prelude::*;

use pw_gix::colour::*;
use pw_gix::dialogue::*;
use pw_gix::gtkx::list_store::*;
use pw_gix::gtkx::notebook::*;
use pw_gix::gtkx::paned::*;
use pw_gix::gtkx::tree_view_column::*;
use pw_gix::gtkx::window::*;
use pw_gix::pwo::*;

use config::*;
use model_paint::*;

pub struct ModelPaintSeriesViewCore {
    scrolled_window: gtk::ScrolledWindow,
    list_store: gtk::ListStore,
    view: gtk::TreeView,
    menu: gtk::Menu,
    paint_info_item: gtk::MenuItem,
    add_paint_item: gtk::MenuItem,
    series: ModelPaintSeries,
    chosen_paint: RefCell<Option<ModelSeriesPaint>>,
    current_target: RefCell<Option<Colour>>,
    add_paint_callbacks: RefCell<Vec<Box<Fn(&ModelSeriesPaint)>>>,
    series_paint_dialogs: RefCell<HashMap<u32, ModelSeriesPaintDisplayDialog>>,
}

impl ModelPaintSeriesViewCore {
    fn get_series_paint_at(&self, posn: (f64, f64)) -> Option<ModelSeriesPaint> {
        let x = posn.0 as i32;
        let y = posn.1 as i32;
        if let Some(location) = self.view.get_path_at_pos(x, y) {
            if let Some(path) = location.0 {
                if let Some(iter) = self.list_store.get_iter(&path) {
                    let name: String = self.list_store.get_value(&iter, 0).get().unwrap_or_else(
                        || panic!("File: {:?} Line: {:?}", file!(), line!())
                    );
                    let paint = self.series.get_series_paint(&name).unwrap_or_else(
                        || panic!("File: {:?} Line: {:?}", file!(), line!())
                    );
                    return Some(paint)
                }
            }
        }
        None
    }

    fn inform_add_paint(&self, paint: &ModelSeriesPaint) {
        for callback in self.add_paint_callbacks.borrow().iter() {
            callback(&paint);
        }
    }

    pub fn set_target_colour(&self, ocolour: Option<&Colour>) {
        match ocolour {
            Some(colour) => {
                for dialog in self.series_paint_dialogs.borrow().values() {
                    dialog.set_current_target(Some(colour.clone()));
                };
                *self.current_target.borrow_mut() = Some(colour.clone())
            },
            None => {
                for dialog in self.series_paint_dialogs.borrow().values() {
                    dialog.set_current_target(None);
                };
                *self.current_target.borrow_mut() = None
            },
        }
    }
}

implement_pwo!(ModelPaintSeriesViewCore, scrolled_window, gtk::ScrolledWindow);

pub type ModelPaintSeriesView = Rc<ModelPaintSeriesViewCore>;

pub trait ModelPaintSeriesViewInterface {
    fn create(series: &ModelPaintSeries) -> ModelPaintSeriesView;
    fn connect_add_paint<F: 'static + Fn(&ModelSeriesPaint)>(&self, callback: F);
}

macro_rules! text_column {
    ( $name:expr, $text:expr, $bg:expr, $fg:expr, $resizable:expr, $fixed_width:expr ) => {
        {
            let col = gtk::TreeViewColumn::new();
            col.set_title($name);
            col.set_resizable($resizable);
            col.set_sort_column_id($text);
            col.set_fixed_width($fixed_width);
            let cell = gtk::CellRendererText::new();
            cell.set_property_editable(false);
            col.pack_start(&cell, true);
            col.add_attribute(&cell, "text", $text);
            col.add_attribute(&cell, "background-rgba", $bg);
            col.add_attribute(&cell, "foreground-rgba", $fg);
            col
        }
    }
}

impl ModelPaintSeriesViewInterface for ModelPaintSeriesView {
    fn create(series: &ModelPaintSeries) -> ModelPaintSeriesView {
        let spec = [
            gtk::Type::String,          // 0 Name
            gtk::Type::String,          // 1 Notes
            gtk::Type::String,          // 2 Greyness
            gtk::Type::String,          // 3 Value
            gdk::RGBA::static_type(),   // 8 4 Colour
            gdk::RGBA::static_type(),   // 9 5 FG for Colour
            gdk::RGBA::static_type(),   // 10 6 Monochrome Colour
            gdk::RGBA::static_type(),   // 11 7 FG for Monochrome Colour
            gdk::RGBA::static_type(),   // 12 8 Hue Colour
            f64::static_type(),         // 13 9 Hue angle (radians)
            gtk::Type::String,          // 4 10 Finish
            gtk::Type::String,          // 5 11 Transparency
            gtk::Type::String,          // 6 12 Metallic
            gtk::Type::String,          // 7 13 Fluorescence
        ];
        let len = 14;
        let list_store = gtk::ListStore::new(&spec[0..len]);
        for paint in series.get_series_paints().iter() {
            let rgba: gdk::RGBA = paint.colour().rgb().into();
            let frgba: gdk::RGBA = paint.colour().rgb().best_foreground_rgb().into();
            let mrgba: gdk::RGBA = paint.colour().monotone_rgb().into();
            let mfrgba: gdk::RGBA = paint.colour().monotone_rgb().best_foreground_rgb().into();
            let hrgba: gdk::RGBA = paint.colour().max_chroma_rgb().into();
            let row = vec![
                paint.name().to_value(),
                paint.notes().to_value(),
                format!("{:5.4}", paint.colour().greyness()).to_value(),
                format!("{:5.4}", paint.colour().value()).to_value(),
                rgba.to_value(),
                frgba.to_value(),
                mrgba.to_value(),
                mfrgba.to_value(),
                hrgba.to_value(),
                paint.colour().hue().angle().radians().to_value(),
                paint.characteristics().finish.abbrev().to_value(),
                paint.characteristics().transparency.abbrev().to_value(),
                paint.characteristics().metallic.abbrev().to_value(),
                paint.characteristics().fluorescence.abbrev().to_value(),
            ];
            list_store.append_row(&row);
        }
        let view = gtk::TreeView::new_with_model(&list_store.clone());
        view.set_headers_visible(true);
        view.get_selection().set_mode(gtk::SelectionMode::None);

        let menu = gtk::Menu::new();
        let paint_info_item = gtk::MenuItem::new_with_label("Information");
        menu.append(&paint_info_item.clone());
        let add_paint_item = gtk::MenuItem::new_with_label("Add to Mixer");
        add_paint_item.set_visible(false);
        menu.append(&add_paint_item.clone());
        menu.show_all();

        let mspl = Rc::new(
            ModelPaintSeriesViewCore {
                scrolled_window: gtk::ScrolledWindow::new(None, None),
                list_store: list_store,
                menu: menu,
                paint_info_item: paint_info_item.clone(),
                add_paint_item: add_paint_item.clone(),
                series: series.clone(),
                view: view,
                chosen_paint: RefCell::new(None),
                current_target: RefCell::new(None),
                add_paint_callbacks: RefCell::new(Vec::new()),
                series_paint_dialogs: RefCell::new(HashMap::new()),
            }
        );

        mspl.view.append_column(&simple_text_column("Name", 0, 0, 4, 5, -1, true));
        mspl.view.append_column(&text_column!("Notes", 1, 4, 5, true, -1));

        let col = gtk::TreeViewColumn::new();
        col.set_title("Hue");
        col.set_sort_column_id(9);
        col.set_fixed_width(40);
        let cell = gtk::CellRendererText::new();
        cell.set_property_editable(false);
        col.pack_start(&cell, true);
        col.add_attribute(&cell, "background-rgba", 8);
        mspl.view.append_column(&simple_text_column("Hue", -1, 9, 8, -1, 50, true));

        let fw = 60;
        mspl.view.append_column(&text_column!("Grey", 2, 4, 5, false,fw));
        mspl.view.append_column(&text_column!("Value", 3, 6, 7, false,fw));
        let cfw = 30;
        mspl.view.append_column(&text_column!("Fi.", 10, 4, 5, false, cfw));
        mspl.view.append_column(&text_column!("Tr.", 11, 4, 5, false, cfw));
        mspl.view.append_column(&text_column!("Me.", 12, 4, 5, false, cfw));
        mspl.view.append_column(&text_column!("Fl.", 13, 4, 5, false, cfw));

        mspl.view.show_all();

        mspl.scrolled_window.add(&mspl.view.clone());
        mspl.scrolled_window.show_all();

        let mspl_c = mspl.clone();
        mspl.view.connect_button_press_event(
            move |_, event| {
                if event.get_event_type() == gdk::EventType::ButtonPress {
                    if event.get_button() == 3 {
                        let o_paint = mspl_c.get_series_paint_at(event.get_position());
                        mspl_c.paint_info_item.set_sensitive(o_paint.is_some());
                        mspl_c.add_paint_item.set_sensitive(o_paint.is_some());
                        let have_listeners = mspl_c.add_paint_callbacks.borrow().len() > 0;
                        mspl_c.add_paint_item.set_visible(have_listeners);
                        *mspl_c.chosen_paint.borrow_mut() = o_paint;
                        mspl_c.menu.popup_at_pointer(None);
                        return Inhibit(true)
                    }
                }
                Inhibit(false)
             }
        );

        let mspl_c = mspl.clone();
        add_paint_item.connect_activate(
            move |_| {
                if let Some(ref paint) = *mspl_c.chosen_paint.borrow() {
                    mspl_c.inform_add_paint(paint);
                } else {
                    panic!("File: {:?} Line: {:?} SHOULDN'T GET HERE", file!(), line!())
                }
            }
        );

        let mspl_c = mspl.clone();
        paint_info_item.clone().connect_activate(
            move |_| {
                if let Some(ref paint) = *mspl_c.chosen_paint.borrow() {
                    let target = if let Some(ref colour) = *mspl_c.current_target.borrow() {
                        Some(colour.clone())
                    } else {
                        None
                    };
                    let have_listeners = mspl_c.add_paint_callbacks.borrow().len() > 0;
                    let buttons = if have_listeners {
                        let mspl_c_c = mspl_c.clone();
                        let paint_c = paint.clone();
                        let spec = SeriesPaintDisplayButtonSpec {
                            label: "Add".to_string(),
                            tooltip_text: "Add this paint to the paint mixing area.".to_string(),
                            callback:  Box::new(move || mspl_c_c.inform_add_paint(&paint_c))
                        };
                        vec![spec]
                    } else {
                        vec![]
                    };
                    let dialog = ModelSeriesPaintDisplayDialog::create(
                        &paint,
                        target,
                        None,
                        buttons
                    );
                    let mspl_c_c = mspl_c.clone();
                    dialog.connect_destroy(
                        move |id| { mspl_c_c.series_paint_dialogs.borrow_mut().remove(&id); }
                    );
                    mspl_c.series_paint_dialogs.borrow_mut().insert(dialog.id_no(), dialog.clone());
                    dialog.show();
                }
            }
        );

        mspl
    }

    fn connect_add_paint<F: 'static + Fn(&ModelSeriesPaint)>(&self, callback: F) {
        self.add_paint_callbacks.borrow_mut().push(Box::new(callback))
    }
}

pub struct PaintSelectorCore {
    vbox: gtk::Box,
    hue_value_wheel: ModelPaintHueAttrWheel,
    hue_greyness_wheel: ModelPaintHueAttrWheel,
    paint_list: ModelPaintSeriesView,
    add_paint_callbacks: RefCell<Vec<Box<Fn(&ModelSeriesPaint)>>>,
}

implement_pwo!(PaintSelectorCore, vbox, gtk::Box);

pub type PaintSelector = Rc<PaintSelectorCore>;

pub trait PaintSelectorInterface {
    fn create(series: &ModelPaintSeries) -> PaintSelector;
    fn connect_add_paint<F: 'static + Fn(&ModelSeriesPaint)>(&self, callback: F);
    fn set_target_colour(&self, ocolour: Option<&Colour>);
}

impl PaintSelectorCore {
    fn inform_add_paint(&self, paint: &ModelSeriesPaint) {
        for callback in self.add_paint_callbacks.borrow().iter() {
            callback(&paint);
        }
    }
}

impl PaintSelectorInterface for PaintSelector {
    fn create(series: &ModelPaintSeries) -> PaintSelector {
        let paint_selector = Rc::new(
            PaintSelectorCore {
                vbox: gtk::Box::new(gtk::Orientation::Vertical, 0),
                hue_value_wheel: ModelPaintHueAttrWheel::create(ScalarAttribute::Value),
                hue_greyness_wheel: ModelPaintHueAttrWheel::create(ScalarAttribute::Greyness),
                paint_list: ModelPaintSeriesView::create(series),
                add_paint_callbacks: RefCell::new(Vec::new()),
            }
        );
        let hbox = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        let series_name = format!("Series Name: {}", series.series_id().series_name());
        hbox.pack_start(&gtk::Label::new(Some(series_name.as_str())), true, true, 0);
        let series_name = format!("Manufacturer: {}", series.series_id().manufacturer());
        hbox.pack_start(&gtk::Label::new(Some(series_name.as_str())), true, true, 0);

        let notebook = gtk::Notebook::new();
        notebook.append_page(&paint_selector.hue_value_wheel.pwo(), Some(&gtk::Label::new("Hue/Value Wheel")));
        notebook.append_page(&paint_selector.hue_greyness_wheel.pwo(), Some(&gtk::Label::new("Hue/Greyness Wheel")));
        let hpaned = gtk::Paned::new(gtk::Orientation::Horizontal);
        hpaned.pack1(&notebook, true, true);
        hpaned.pack2(&paint_selector.paint_list.pwo() , true, true);
        hpaned.set_position_from_recollections("model_paint_selector", 200);
        paint_selector.vbox.pack_start(&hpaned, true, true, 0);

        for paint in series.get_paints().iter() {
            paint_selector.hue_value_wheel.add_paint(&paint);
            paint_selector.hue_greyness_wheel.add_paint(&paint);
        }

        let paint_selector_c = paint_selector.clone();
        paint_selector.hue_value_wheel.connect_add_paint(
            move |paint| paint_selector_c.inform_add_paint(paint)
        );
        let paint_selector_c = paint_selector.clone();
        paint_selector.hue_greyness_wheel.connect_add_paint(
            move |paint| paint_selector_c.inform_add_paint(paint)
        );
        let paint_selector_c = paint_selector.clone();
        paint_selector.paint_list.connect_add_paint(
            move |paint| paint_selector_c.inform_add_paint(paint)
        );

        paint_selector
    }

    fn connect_add_paint<F: 'static + Fn(&ModelSeriesPaint)>(&self, callback: F) {
        self.add_paint_callbacks.borrow_mut().push(Box::new(callback))
    }

    fn set_target_colour(&self, ocolour: Option<&Colour>) {
        self.hue_value_wheel.set_target_colour(ocolour);
        self.hue_greyness_wheel.set_target_colour(ocolour);
        self.paint_list.set_target_colour(ocolour);
    }
}

pub struct SeriesPaintManagerCore {
    window: gtk::Window,
    notebook: gtk::Notebook,
    add_paint_callbacks: RefCell<Vec<Box<Fn(&ModelSeriesPaint)>>>,
    paint_selectors: RefCell<HashMap<PaintSeriesIdentity, PaintSelector>>,
}

impl SeriesPaintManagerCore {
    fn inform_add_paint(&self, paint: &ModelSeriesPaint) {
        for callback in self.add_paint_callbacks.borrow().iter() {
            callback(&paint);
        }
    }

    fn remove_paint_series(&self, ps_id: &PaintSeriesIdentity) {
        let mut selectors = self.paint_selectors.borrow_mut();
        if let Some(selector) = selectors.remove(ps_id) {
            let page_num = self.notebook.page_num(&selector.pwo());
            self.notebook.remove_page(page_num);
        } else {
            panic!("File: {:?} Line: {:?}", file!(), line!())
        }
    }

    pub fn set_target_colour(&self, ocolour: Option<&Colour>) {
        for selector in self.paint_selectors.borrow().values() {
            selector.set_target_colour(ocolour);
        }
    }
}

pub type SeriesPaintManager = Rc<SeriesPaintManagerCore>;

pub trait SeriesPaintManagerInterface {
    fn create() -> SeriesPaintManager;
    fn connect_add_paint<F: 'static + Fn(&ModelSeriesPaint)>(&self, callback: F);
    fn add_paint_series(&self, series: &ModelPaintSeries);
    fn button(&self) -> gtk::Button;
}

impl SeriesPaintManagerInterface for SeriesPaintManager {
    fn create() -> SeriesPaintManager {
        let window = gtk::Window::new(gtk::WindowType::Toplevel);
        window.set_geometry_from_recollections("series_paint_manager", (600, 200));
        window.set_destroy_with_parent(true);
        window.set_title("mcmmtk: Series Paint Manager");
        window.connect_delete_event(
            move |w,_| {w.hide_on_delete(); gtk::Inhibit(true)}
        );
        let notebook = gtk:: Notebook::new();
        notebook.set_scrollable(true);
        notebook.popup_enable();
        window.add(&notebook.clone());
        let add_paint_callbacks: RefCell<Vec<Box<Fn(&ModelSeriesPaint)>>> = RefCell::new(Vec::new());
        let paint_selectors: RefCell<HashMap<PaintSeriesIdentity, PaintSelector>> = RefCell::new(HashMap::new());
        let spm = Rc::new(
            SeriesPaintManagerCore{window, notebook, add_paint_callbacks,  paint_selectors}
        );
        let series_file_paths = get_series_file_paths();
        for series_file_path in series_file_paths.iter() {
            if let Ok(series) = ModelPaintSeries::from_file(&series_file_path) {
                spm.add_paint_series(&series);
            } else {
                let expln = format!("Error parsing \"{:?}\"\n", series_file_path);
                let msg = "Malformed Paint Series Text";
                warn_user(Some(&spm.window), msg, Some(expln.as_str()));
            }
        };
        spm.notebook.show_all();

        spm
    }

    fn connect_add_paint<F: 'static + Fn(&ModelSeriesPaint)>(&self, callback: F) {
        self.add_paint_callbacks.borrow_mut().push(Box::new(callback))
    }

    fn add_paint_series(&self, series: &ModelPaintSeries) {
        let mut selectors = self.paint_selectors.borrow_mut();
        if selectors.contains_key(&series.series_id()) {
            let expln = format!("{} ({}): already included in the tool box.\nSkipped.", series.series_id().series_name(), series.series_id().manufacturer());
            inform_user(Some(&self.window), "Duplicate Paint Series", Some(expln.as_str()));
            return;
        }
        let paint_selector = PaintSelector::create(&series);
        selectors.insert(series.series_id(), paint_selector.clone());
        let spm_c = self.clone();
        paint_selector.connect_add_paint(
            move |paint| spm_c.inform_add_paint(paint)
        );
        let l_text = format!("{}\n{}", series.series_id().series_name(), series.series_id().manufacturer());
        let tt_text = format!("Remove {} ({}) from the tool kit", series.series_id().series_name(), series.series_id().manufacturer());
        let label = TabRemoveLabel::create(Some(l_text.as_str()), Some(&tt_text.as_str()));
        let l_text = format!("{} ({})", series.series_id().series_name(), series.series_id().manufacturer());
        let menu_label = gtk::Label::new(Some(l_text.as_str()));
        let spm_c = self.clone();
        let ps_id = series.series_id();
        label.connect_remove_page(
            move || spm_c.remove_paint_series(&ps_id)
        );
        self.notebook.append_page_menu(&paint_selector.pwo(), Some(&label.pwo()), Some(&menu_label));
    }

    fn button(&self) -> gtk::Button {
        let button = gtk::Button::new_with_label("Series Paint Manager");
        let spm_c = self.clone();
        button.connect_clicked(
            move |_| spm_c.window.present()
        );
        button
    }
}

#[cfg(test)]
mod tests {
    //use super::*;

    #[test]
    fn it_works() {

    }
}
