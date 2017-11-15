extern crate gtk;
extern crate gio;
extern crate lazy_static;

extern crate epaint;
extern crate pw_gix;

extern crate mcmmtk;

use std::path::*;
use std::rc::Rc;

use gio::ApplicationExt;

use gtk::prelude::*;

use pw_gix::colour;
use pw_gix::colour::*;
use pw_gix::colour::attributes::*;
use pw_gix::gtkx::entry::*;
use pw_gix::gtkx::window::*;
use pw_gix::pwo::*;
use pw_gix::recollections;
use pw_gix::rgb_math::rgb::*;

use epaint::mixer::*;
use epaint::paint::{CharacteristicsInterface, CharacteristicsEntryInterface};
use epaint::target::*;
use epaint::characteristics::*;

//use mcmmtk::recollections;
use mcmmtk::config;
use mcmmtk::model_paint::*;
//use mcmmtk::model_paint::series::*;

fn activate(app: &gtk::Application) {
    let window = gtk::ApplicationWindow::new(app);
    window.set_title("Modellers Colour Mixing/Matching TK");
    window.set_geometry_from_recollections("main_window", (200, 200));
    let vbox = gtk::Box::new(gtk::Orientation::Vertical, 0);
    let ideal_paints = create_ideal_model_paint_series();
    let paint: ModelSeriesPaint = ideal_paints.get_series_paint("Red").unwrap();
    let target_colour = TargetColour::create(&Colour::from(CYAN), "Cyan", "a very pure colour");
    let current_target = Colour::from((YELLOW + GREEN + WHITE) / 3);
    let mixer = ModelPaintMixer::create();
    mixer.set_target_colour(Some(&current_target));
    vbox.pack_start(&mixer.pwo(), true, true, 0);
    let data_path = config::get_paint_series_files_data_path();
    let psm = ModelPaintSeriesManager::create(&data_path);
    psm.set_target_colour(Some(&current_target));
    vbox.pack_start(&psm.button(), false, false, 0);
    let mixer_c = mixer.clone();
    psm.connect_add_paint(
        move |paint| mixer_c.add_series_paint(paint)
    );
    let ce = <ModelPaintCharacteristics as CharacteristicsInterface>::Entry::create();
    vbox.pack_start(&ce.pwo(), false, true, 0);
    ce.connect_changed(|| println!("characteristics changed"));
    let label = gtk::Label::new("GUI is under construction");
    vbox.pack_start(&label, false, true, 0);
    window.add(&vbox);
    window.show_all();
}

fn main() {
    recollections::init(&config::get_gui_config_dir_path().join("recollections"));
    let flags = gio::ApplicationFlags::empty();
    let app = gtk::Application::new("mcmmtk.pw.nest", flags).unwrap_or_else(
        |err| panic!("{:?}: line {:?}: {:?}", file!(), line!(), err)
    );
    app.connect_activate(activate);
    app.run(&[]);
}
