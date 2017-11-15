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

use gtk;
use gtk::prelude::*;

use std::cell::RefCell;
use std::rc::Rc;
use std::str::FromStr;

use pw_gix::colour::*;
use pw_gix::colour::attributes::*;
use pw_gix::gtkx::tree_view_column::*;
use pw_gix::pwo::*;

use epaint::display::*;
use epaint::paint::*;
use epaint::characteristics::*;
use epaint::components::*;
use epaint::hue_wheel::*;
use epaint::mixed_paint::*;
use epaint::mixer::*;
use epaint::series_paint::*;
pub use epaint::series_paint::manager::*;

#[derive(Debug, PartialEq, Hash, Clone, Copy)]
pub struct ModelPaintCharacteristics {
    pub finish: Finish,
    pub transparency: Transparency,
    pub fluorescence: Fluorescence,
    pub metallic: Metallic,
}

impl CharacteristicsInterface for ModelPaintCharacteristics {
    type Entry = Rc<ModelPaintCharacteristicsEntryCore>;

    fn tv_row_len() -> usize {
        4
    }

    fn tv_columns(start_col_id: i32) -> Vec<gtk::TreeViewColumn> {
        let mut cols: Vec<gtk::TreeViewColumn> = Vec::new();
        let cfw = 30;
        cols.push(simple_text_column("Fi.", start_col_id, start_col_id, 6, 7, cfw, false));
        cols.push(simple_text_column("Tr.", start_col_id + 1, start_col_id + 1, 6, 7, cfw, false));
        cols.push(simple_text_column("Me.", start_col_id + 2, start_col_id + 2, 6, 7, cfw, false));
        cols.push(simple_text_column("Fl.", start_col_id + 3, start_col_id + 3, 6, 7, cfw, false));
        cols
    }

    fn from_floats(floats: &Vec<f64>) -> Self {
        ModelPaintCharacteristics {
            finish: Finish::from(floats[0]),
            transparency: Transparency::from(floats[1]),
            fluorescence: Fluorescence::from(floats[2]),
            metallic: Metallic::from(floats[3])
        }
    }

    fn tv_rows(&self) -> Vec<gtk::Value> {
        let mut rows: Vec<gtk::Value> = Vec::new();
        rows.push(self.finish.abbrev().to_value());
        rows.push(self.transparency.abbrev().to_value());
        rows.push(self.metallic.abbrev().to_value());
        rows.push(self.fluorescence.abbrev().to_value());
        rows
    }

    fn gui_display_widget(&self) -> gtk::Box {
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 1);
        let label = gtk::Label::new(self.finish.description());
        vbox.pack_start(&label, false, false, 1);
        let label = gtk::Label::new(self.transparency.description());
        vbox.pack_start(&label, false, false, 1);
        let label = gtk::Label::new(self.fluorescence.description());
        vbox.pack_start(&label, false, false, 1);
        let label = gtk::Label::new(self.metallic.description());
        vbox.pack_start(&label, false, false, 1);
        vbox.show_all();
        vbox
    }

    fn to_floats(&self) -> Vec<f64> {
        vec![
            self.finish.into(),
            self.transparency.into(),
            self.fluorescence.into(),
            self.metallic.into(),
        ]
    }
}

impl FromStr for ModelPaintCharacteristics {
    type Err = PaintError;

    fn from_str(string: &str) -> Result<ModelPaintCharacteristics, PaintError> {
        let finish = Finish::from_str(string)?;
        let transparency = Transparency::from_str(string)?;
        // NB: cope with older definitions that don't include
        // metallic and flourescence
        let fluorescence = match Fluorescence::from_str(string) {
            Ok(fl) => fl,
            Err(_) => Fluorescence::Nonfluorescent,
        };
        let metallic = match Metallic::from_str(string) {
            Ok(mc) => mc,
            Err(_) => Metallic::Nonmetallic,
        };
        Ok(ModelPaintCharacteristics{finish, transparency, fluorescence, metallic})
    }
}

pub struct ModelPaintCharacteristicsEntryCore {
    vbox: gtk::Box,
    finish_entry: FinishEntry,
    transparency_entry: TransparencyEntry,
    fluorescence_entry: FluorescenceEntry,
    metallic_entry: MetallicEntry,
    changed_callbacks: RefCell<Vec<Box<Fn()>>>,
}

impl ModelPaintCharacteristicsEntryCore {
    fn inform_changed(&self) {
        for callback in self.changed_callbacks.borrow().iter() {
            callback();
        }
    }
}

impl CharacteristicsEntryInterface<ModelPaintCharacteristics> for Rc<ModelPaintCharacteristicsEntryCore> {
    fn create() -> Self {
        let cei = Rc::new(
            ModelPaintCharacteristicsEntryCore {
                vbox: gtk::Box::new(gtk::Orientation::Vertical, 0),
                finish_entry: FinishEntry::create(),
                transparency_entry: TransparencyEntry::create(),
                fluorescence_entry: FluorescenceEntry::create(),
                metallic_entry: MetallicEntry::create(),
                changed_callbacks: RefCell::new(Vec::new()),
            }
        );
        let cei_c = cei.clone();
        cei.finish_entry.combo_box_text().connect_changed(
            move |_| cei_c.inform_changed()
        );
        let cei_c = cei.clone();
        cei.transparency_entry.combo_box_text().connect_changed(
            move |_| cei_c.inform_changed()
        );
        let cei_c = cei.clone();
        cei.fluorescence_entry.combo_box_text().connect_changed(
            move |_| cei_c.inform_changed()
        );
        let cei_c = cei.clone();
        cei.metallic_entry.combo_box_text().connect_changed(
            move |_| cei_c.inform_changed()
        );
        cei.vbox.pack_start(&cei.finish_entry.combo_box_text(), false, false, 0);
        cei.vbox.pack_start(&cei.transparency_entry.combo_box_text(), false, false, 0);
        cei.vbox.pack_start(&cei.fluorescence_entry.combo_box_text(), false, false, 0);
        cei.vbox.pack_start(&cei.metallic_entry.combo_box_text(), false, false, 0);
        cei.vbox.show_all();
        cei
    }

    fn pwo(&self) -> gtk::Box {
        self.vbox.clone()
    }

    fn get_characteristics(&self) -> Option<ModelPaintCharacteristics> {
        let finish = if let Some(value) = self.finish_entry.get_value() {
            value
        } else {
            return None
        };
        let transparency = if let Some(value) = self.transparency_entry.get_value() {
            value
        } else {
            return None
        };
        let fluorescence = if let Some(value) = self.fluorescence_entry.get_value() {
            value
        } else {
            return None
        };
        let metallic = if let Some(value) = self.metallic_entry.get_value() {
            value
        } else {
            return None
        };
        Some(ModelPaintCharacteristics {finish, transparency, fluorescence, metallic})
    }

    fn set_characteristics(&self, o_characteristics: Option<&ModelPaintCharacteristics>) {
        if let Some(characteristics) = o_characteristics {
            self.finish_entry.set_value(Some(characteristics.finish));
            self.transparency_entry.set_value(Some(characteristics.transparency));
            self.fluorescence_entry.set_value(Some(characteristics.fluorescence));
            self.metallic_entry.set_value(Some(characteristics.metallic));

        } else {
            self.finish_entry.set_value(None);
            self.transparency_entry.set_value(None);
            self.fluorescence_entry.set_value(None);
            self.metallic_entry.set_value(None);
        }
    }

    fn connect_changed<F: 'static + Fn()>(&self, callback: F) {
        self.changed_callbacks.borrow_mut().push(Box::new(callback))
    }
}

pub struct ModelPaintAttributes {
    vbox: gtk::Box,
    hue_cad: HueCAD,
    greyness_cad: GreynessCAD,
    value_cad: ValueCAD,
}

impl ColourAttributesInterface for ModelPaintAttributes {
    fn pwo(&self) -> gtk::Box {
        self.vbox.clone()
    }

    fn create() -> Rc<ModelPaintAttributes> {
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 1);
        let hue_cad = HueCAD::create();
        let greyness_cad = GreynessCAD::create();
        let value_cad = ValueCAD::create();
        vbox.pack_start(&hue_cad.pwo(), true, true, 0);
        vbox.pack_start(&greyness_cad.pwo(), true, true, 0);
        vbox.pack_start(&value_cad.pwo(), true, true, 0);
        Rc::new(
            ModelPaintAttributes {
                vbox,
                hue_cad,
                greyness_cad,
                value_cad,
            }
        )
    }

    fn tv_columns() -> Vec<gtk::TreeViewColumn> {
        let fw = 60;
        vec![
            simple_text_column("Hue", -1, 13, 10, -1, 50, true),
            simple_text_column("Grey", 3, 3, 6, 7, fw, false),
            simple_text_column("Value", 4, 4, 8, 9, fw, false),
        ]
    }

    fn scalar_attributes() -> Vec<ScalarAttribute> {
        vec![ScalarAttribute::Value, ScalarAttribute::Greyness]
    }


    fn set_colour(&self, colour: Option<&Colour>) {
        self.hue_cad.set_colour(colour);
        self.greyness_cad.set_colour(colour);
        self.value_cad.set_colour(colour);
    }

    fn set_target_colour(&self, target_colour: Option<&Colour>) {
        self.hue_cad.set_target_colour(target_colour);
        self.greyness_cad.set_target_colour(target_colour);
        self.value_cad.set_target_colour(target_colour);
    }
}

pub type ModelSeriesPaint = SeriesPaint<ModelPaintCharacteristics>;
pub type ModelSeriesPaintSpec = SeriesPaintSpec<ModelPaintCharacteristics>;
pub type ModelMixedPaint = MixedPaint<ModelPaintCharacteristics>;
pub type ModelPaint = Paint<ModelPaintCharacteristics>;
pub type ModelPaintDisplayDialog = PaintDisplayDialog<ModelPaintAttributes, ModelPaintCharacteristics>;
pub type ModelPaintSeries = PaintSeries<ModelPaintCharacteristics>;
pub type ModelPaintComponentsBox = PaintComponentsBox<ModelPaintCharacteristics>;
pub type ModelPaintMixer = PaintMixer<ModelPaintAttributes, ModelPaintCharacteristics>;
pub type ModelPaintHueAttrWheel = PaintHueAttrWheel<ModelPaintAttributes, ModelPaintCharacteristics>;
pub type ModelPaintSeriesView = PaintSeriesView<ModelPaintAttributes, ModelPaintCharacteristics>;
pub type ModelPaintSeriesManager = SeriesPaintManager<ModelPaintAttributes, ModelPaintCharacteristics>;

const IDEAL_PAINT_STR: &str =
"Manufacturer: Imaginary
Series: Ideal Paint Colours Series
ModelPaint(name=\"Black\", rgb=RGB16(red=0x0, green=0x0, blue=0x0), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")
ModelPaint(name=\"Blue\", rgb=RGB16(red=0x0, green=0x0, blue=0xFFFF), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")
ModelPaint(name=\"Cyan\", rgb=RGB16(red=0x0, green=0xFFFF, blue=0xFFFF), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")
ModelPaint(name=\"Green\", rgb=RGB16(red=0x0, green=0xFFFF, blue=0x0), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")
ModelPaint(name=\"Magenta\", rgb=RGB16(red=0xFFFF, green=0x0, blue=0xFFFF), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")
ModelPaint(name=\"Red\", rgb=RGB16(red=0xFFFF, green=0x0, blue=0x0), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")
ModelPaint(name=\"White\", rgb=RGB16(red=0xFFFF, green=0xFFFF, blue=0xFFFF), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")
ModelPaint(name=\"Yellow\", rgb=RGB16(red=0xFFFF, green=0xFFFF, blue=0x0), transparency=\"O\", finish=\"G\", metallic=\"NM\", fluorescence=\"NF\", notes=\"\")";

pub fn create_ideal_model_paint_series() -> ModelPaintSeries {
    ModelPaintSeries::from_str(IDEAL_PAINT_STR).unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;
    use pw_gix::rgb_math::rgb::*;
    use pw_gix::colour::*;

const OBSOLETE_PAINT_STR: &str =
"Manufacturer: Tamiya
Series: Flat Acrylic (Peter Williams Digital Samples #3)
NamedColour(name=\"XF 1: Flat Black *\", rgb=RGB(0x2D00, 0x2B00, 0x3000), transparency=\"O\", finish=\"F\")
NamedColour(name=\"XF 2: Flat White *\", rgb=RGB(0xFE00, 0xFE00, 0xFE00), transparency=\"O\", finish=\"F\")
NamedColour(name=\"XF 3: Flat Yellow *\", rgb=RGB(0xF800, 0xCD00, 0x2900), transparency=\"O\", finish=\"F\")
NamedColour(name=\"XF 4: Yellow Green *\", rgb=RGB(0xAA00, 0xAE00, 0x4000), transparency=\"O\", finish=\"F\")
";

    #[test]
    fn paint_model_paint() {
        let test_str = r#"ModelPaint(name="71.001 White", rgb=RGB16(red=0xF800, green=0xFA00, blue=0xF600), transparency="O", finish="F", metallic="NM", fluorescence="NF", notes="FS37925 RAL9016 RLM21")"#.to_string();
        assert!(SERIES_PAINT_RE.is_match(&test_str));
        if let Ok(spec) = ModelSeriesPaintSpec::from_str(&test_str) {
            assert_eq!(spec.name, "71.001 White");
            assert_eq!(spec.characteristics.finish, Finish::Flat);
            assert_eq!(spec.characteristics.transparency, Transparency::Opaque);
            assert_eq!(spec.characteristics.fluorescence, Fluorescence::Nonfluorescent);
            assert_eq!(spec.characteristics.metallic, Metallic::Nonmetallic);
            assert_eq!(spec.notes, "FS37925 RAL9016 RLM21");
            let rgb16 = RGB16::from(spec.rgb);
            assert_eq!(rgb16.red, u16::from_str_radix("F800", 16).unwrap());
            assert_eq!(rgb16.green, u16::from_str_radix("FA00", 16).unwrap());
            assert_eq!(rgb16.blue, u16::from_str_radix("F600", 16).unwrap());
        } else {
            panic!("File: {:?} Line: {:?}", file!(), line!())
        }
    }

    #[test]
    fn paint_model_paint_obsolete() {
        let test_str = r#"NamedColour(name="XF 2: Flat White *", rgb=RGB16(0xF800, 0xFA00, 0xF600), transparency="O", finish="F")"#.to_string();
        assert!(SERIES_PAINT_RE.is_match(&test_str));
        if let Ok(spec) = ModelSeriesPaintSpec::from_str(&test_str) {
            assert_eq!(spec.name, "XF 2: Flat White *");
            assert_eq!(spec.characteristics.finish, Finish::Flat);
            assert_eq!(spec.characteristics.transparency, Transparency::Opaque);
            assert_eq!(spec.characteristics.fluorescence, Fluorescence::Nonfluorescent);
            assert_eq!(spec.characteristics.metallic, Metallic::Nonmetallic);
            assert_eq!(spec.notes, "");
            let rgb16 = RGB16::from(spec.rgb);
            assert_eq!(rgb16.red, u16::from_str_radix("F800", 16).unwrap());
            assert_eq!(rgb16.green, u16::from_str_radix("FA00", 16).unwrap());
            assert_eq!(rgb16.blue, u16::from_str_radix("F600", 16).unwrap());
        } else {
            panic!("File: {:?} Line: {:?}", file!(), line!())
        }
    }

    #[test]
    fn paint_model_paint_ideal_series() {
        if let Ok(series) = ModelPaintSeries::from_str(IDEAL_PAINT_STR) {
            for pair in [
                ("Red", RED),
                ("Green", GREEN),
                ("Blue", BLUE),
                ("Cyan", CYAN),
                ("Magenta", MAGENTA),
                ("Yellow", YELLOW),
                ("Black", BLACK),
                ("White", WHITE)
            ].iter()
            {
                assert_eq!(series.get_series_paint(pair.0).unwrap().colour().rgb(), pair.1);
            }
        } else {
            panic!("File: {:?} Line: {:?}", file!(), line!())
        }
        let series = create_ideal_model_paint_series();
        for pair in [
            ("Red", RED),
            ("Green", GREEN),
            ("Blue", BLUE),
            ("Cyan", CYAN),
            ("Magenta", MAGENTA),
            ("Yellow", YELLOW),
            ("Black", BLACK),
            ("White", WHITE)
        ].iter()
        {
            assert_eq!(series.get_series_paint(pair.0).unwrap().colour().rgb(), pair.1);
            assert_eq!(series.get_paint(pair.0).unwrap().colour().rgb(), pair.1);
        }
    }

    #[test]
    fn paint_model_paint_obsolete_series() {
        match ModelPaintSeries::from_str(OBSOLETE_PAINT_STR) {
            Ok(series) => {
                for pair in [
                    ("XF 1: Flat Black *", RGB16::from_str("RGB(0x2D00, 0x2B00, 0x3000)").unwrap()),
                    ("XF 2: Flat White *", RGB16::from_str("RGB(0xFE00, 0xFE00, 0xFE00)").unwrap()),
                    ("XF 3: Flat Yellow *", RGB16::from_str("RGB(0xF800, 0xCD00, 0x2900)").unwrap()),
                    ("XF 4: Yellow Green *", RGB16::from_str("RGB(0xAA00, 0xAE00, 0x4000)").unwrap()),
                ].iter()
                {
                    assert_eq!(series.get_series_paint(pair.0).unwrap().colour().rgb(), RGB::from(pair.1));
                }
            },
            Err(err) => panic!("File: {:?} Line: {:?} {:?}", file!(), line!(), err),
        }
    }

    #[test]
    fn paint_model_paint_contributions_box() {
        if !gtk::is_initialized() {
            if let Err(err) = gtk::init() {
                panic!("File: {:?} Line: {:?}: {:?}", file!(), line!(), err)
            };
        }

        let components_box = ModelPaintComponentsBox::create_with(6, true);
        let series = create_ideal_model_paint_series();
        for pair in [
            ("Red", RED),
            ("Green", GREEN),
            ("Blue", BLUE),
            ("Cyan", CYAN),
            ("Magenta", MAGENTA),
            ("Yellow", YELLOW),
            ("Black", BLACK),
            ("White", WHITE)
        ].iter()
        {
            assert_eq!(series.get_series_paint(pair.0).unwrap().colour().rgb(), pair.1);
            assert_eq!(series.get_paint(pair.0).unwrap().colour().rgb(), pair.1);
            let paint = series.get_paint(pair.0).unwrap();
            assert_eq!(paint.colour().rgb(), pair.1);
            components_box.add_paint(&paint);
        }
    }
}
