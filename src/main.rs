extern crate gtk;
extern crate gio;

extern crate pw_gix;

extern crate mcmmtk;

use gio::ApplicationExt;

use gtk::prelude::*;

use pw_gix::gdkx::format_geometry;
use pw_gix::colour;
use pw_gix::rgb_math::rgb::*;

use mcmmtk::recollections;

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
    let value_indicator = colour::attributes::ValueCAD::new();
    value_indicator.set_colour(Some(colour::Colour::from(BLUE)));
    value_indicator.set_target_colour(Some(colour::Colour::from(YELLOW)));
    //let snapshot_selector = g_snapshot::SnapshotSelector::new();
    vbox.pack_start(&value_indicator.drawing_area, true, true, 0);
    let label = gtk::Label::new("GUI is under construction");
    vbox.pack_start(&label, true, true, 0);
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
