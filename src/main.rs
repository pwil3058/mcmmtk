extern crate gtk;
extern crate gio;
extern crate lazy_static;

extern crate pw_gix;

extern crate mcmmtk;

use std::rc::Rc;

use gio::ApplicationExt;

use gtk::prelude::*;

use pw_gix::colour;
use pw_gix::colour::*;
use pw_gix::colour::attributes::*;
use pw_gix::gdkx::format_geometry;
//use pw_gix::gtkx::entry;
use pw_gix::gtkx::entry::*;
use pw_gix::pwo::*;
use pw_gix::rgb_math::rgb::*;
use pw_gix::paint::*;
use pw_gix::paint::components::*;
use pw_gix::paint::model_paint::*;
use pw_gix::paint::hue_wheel::*;
use pw_gix::paint::target::*;

use mcmmtk::recollections;

trait ColourAttributeStackInterface {
    type CASIType;
    type PackableWidgetType;

    fn create() -> Self::CASIType;
    fn pwo(&self) -> Self::PackableWidgetType;
}

struct ColourAttributeStackData {
    vbox: gtk::Box,
    hcv_cads: HueChromaValueCADS,
    rgb_entry_box: RGBHexEntryBox,
    target_rgb_entry_box: RGBHexEntryBox,
}

type ColourAttributeStack = Rc<ColourAttributeStackData>;

impl ColourAttributeStackInterface for ColourAttributeStack {
    type CASIType = ColourAttributeStack;
    type PackableWidgetType = gtk::Box;

    fn create() -> ColourAttributeStack {
        let vbox = gtk::Box::new(gtk::Orientation::Vertical, 0);
        let hcv_cads = HueChromaValueCADS::create();
        let rgb_entry_box = RGBHexEntryBox::create();
        let target_rgb_entry_box = RGBHexEntryBox::create();
        vbox.pack_start(&hcv_cads.pwo(), true, true, 0);
        vbox.pack_start(&rgb_entry_box.pwo(), false, false, 0);
        vbox.pack_start(&target_rgb_entry_box.pwo(), false, false, 0);
        let cas = Rc::new(
            ColourAttributeStackData {
                vbox,
                hcv_cads,
                rgb_entry_box,
                target_rgb_entry_box
            }
        );
        let cas_c = cas.clone();
        cas.rgb_entry_box.connect_value_changed(
            move |rgb| {
                let colour = colour::Colour::from(*rgb);
                cas_c.hcv_cads.set_colour(Some(&colour));
            }
        );
        let cas_c = cas.clone();
        cas.target_rgb_entry_box.connect_value_changed(
            move |rgb| {
                let colour = colour::Colour::from(*rgb);
                cas_c.hcv_cads.set_target_colour(Some(&colour));
            }
        );
        cas
    }

    fn pwo(&self) -> gtk::Box {
        self.vbox.clone()
    }
}

fn activate(app: &gtk::Application) {
    let window = gtk::ApplicationWindow::new(app);
    window.set_title("Modellers Colour Mixing/Matching TK");
    if let Some(geometry) = recollections().recall("main_window:geometry") {
        window.parse_geometry(&geometry);
    } else {
        window.set_default_size(200, 200);
    };
    window.connect_configure_event(
        |_, event| {
            recollections().remember("main_window:geometry", &format_geometry(event));
            false
        }
    );
    let vbox = gtk::Box::new(gtk::Orientation::Vertical, 0);
    let colour_attribute_stack = ColourAttributeStack::create();
    vbox.pack_start(&colour_attribute_stack.pwo(), true, true, 0);
    let components_box = PaintComponentsBox::<ModelPaintCharacteristics>::create_with(6, true);
    let ideal_paints = create_ideal_model_paint_series();
    vbox.pack_start(&components_box.pwo(), false, true, 0);
    let paint: ModelSeriesPaint = ideal_paints.get_series_paint("Red").unwrap();
    components_box.add_paint(&Paint::Series(paint));
    let wheel = PaintHueAttrWheel::<ModelPaintCharacteristics>::create(ScalarAttribute::Chroma);
    wheel.pwo().show_all();
    vbox.pack_start(&wheel.pwo(), true, true, 0);
    wheel.add_paint(&ideal_paints.get_paint("Red").unwrap());
    wheel.set_target_colour(Some(&Colour::from(YELLOW)));
    let target_colour = TargetColour::create(&Colour::from(CYAN), "Cyan", "a very pure colour");
    wheel.add_target_colour(&target_colour);
    let label = gtk::Label::new("GUI is under construction");
    vbox.pack_start(&label, false, true, 0);
    window.add(&vbox);
    window.show_all();
}

fn main() {
    let flags = gio::ApplicationFlags::empty();
    let app = gtk::Application::new("mcmmtk.pw.nest", flags).unwrap_or_else(
        |err| panic!("{:?}: line {:?}: {:?}", file!(), line!(), err)
    );
    app.connect_activate(activate);
    app.run(&[]);
}
