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
use std::rc::Rc;

use gtk;
use gtk::prelude::*;

use pw_gix::colour::*;
use pw_gix::gtkx::notebook::*;
use pw_gix::pwo::*;

use config::*;
use model_paint::*;

pub struct PaintSelectorCore {
    vbox: gtk::Box,
    hue_value_wheel: ModelPaintHueAttrWheel,
    hue_greyness_wheel: ModelPaintHueAttrWheel,
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
                add_paint_callbacks: RefCell::new(Vec::new()),
            }
        );
        let hbox = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        let series_name = format!("Series Name: {}", series.series_id().series_name());
        hbox.pack_start(&gtk::Label::new(Some(series_name.as_str())), true, true, 0);
        let series_name = format!("Manufacturer: {}", series.series_id().manufacturer());
        hbox.pack_start(&gtk::Label::new(Some(series_name.as_str())), true, true, 0);
        paint_selector.vbox.pack_start(&hbox, false, false, 0);

        let notebook = gtk::Notebook::new();
        notebook.append_page(&paint_selector.hue_value_wheel.pwo(), Some(&gtk::Label::new("Hue/Value Wheel")));
        notebook.append_page(&paint_selector.hue_greyness_wheel.pwo(), Some(&gtk::Label::new("Hue/Greyness Wheel")));
        let af = gtk::AspectFrame::new(None, 0.5, 0.5, 0.95, false);
        af.add(&notebook);
        let hbox = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        hbox.pack_start(&af, true, true, 0);
        hbox.pack_start(&gtk::Label::new("PAINT LIST GOES HERE") , true, true, 0);
        paint_selector.vbox.pack_start(&hbox, true, true, 0);

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

        paint_selector
    }

    fn connect_add_paint<F: 'static + Fn(&ModelSeriesPaint)>(&self, callback: F) {
        self.add_paint_callbacks.borrow_mut().push(Box::new(callback))
    }

    fn set_target_colour(&self, ocolour: Option<&Colour>) {
        self.hue_value_wheel.set_target_colour(ocolour);
        self.hue_greyness_wheel.set_target_colour(ocolour);
    }
}

pub struct SeriesPaintManagerCore {
    pub notebook: gtk::Notebook,
}

pub type SeriesPaintManager = Rc<SeriesPaintManagerCore>;

pub trait SeriesPaintManagerInterface {
    fn create() -> SeriesPaintManager;
}

impl SeriesPaintManagerInterface for SeriesPaintManager {
    fn create() -> SeriesPaintManager {
        let notebook = gtk:: Notebook::new();
        let spm = Rc::new(
            SeriesPaintManagerCore{notebook}
        );
        let series_file_paths = get_series_file_paths();
        for series_file_path in series_file_paths.iter() {
            if let Ok(series) = ModelPaintSeries::from_file(&series_file_path) {
                let paint_selector = PaintSelector::create(&series);
                let l_text = format!("{}\n{}", series.series_id().series_name(), series.series_id().manufacturer());
                let tt_text = "Remove this Paint Series from the tool kit";
                let label = TabRemoveLabel::create(Some(l_text.as_str()), Some(&tt_text));
                let spm_c = spm.clone();
                let ps_c = paint_selector.pwo().clone();
                label.connect_remove_page(
                    move || {
                        let page_num = spm_c.notebook.page_num(&ps_c);
                        spm_c.notebook.remove_page(page_num);
                    }
                );
                spm.notebook.append_page(&paint_selector.pwo(), Some(&label.pwo()));
            } else {

            }
        }

        spm
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {

    }
}
