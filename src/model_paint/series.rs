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

use gtk;
use gtk::prelude::*;

use pw_gix::colour::*;
use pw_gix::dialogue::*;
use pw_gix::gtkx::notebook::*;
use pw_gix::gtkx::paned::*;
use pw_gix::gtkx::window::*;
use pw_gix::pwo::*;

use config::*;
use model_paint::*;

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
