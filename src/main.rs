extern crate gdk_pixbuf;
extern crate gtk;
extern crate gio;
extern crate lazy_static;

extern crate epaint;
extern crate pw_gix;

extern crate mcmmtk;

use gio::ApplicationExt;

use gtk::prelude::*;

use pw_gix::colour::*;
use pw_gix::gdk_pixbufx::iview::*;
use pw_gix::gtkx::window::*;
use pw_gix::recollections;
use pw_gix::rgb_math::rgb::*;

use epaint::mixed_paint::mixer::*;

use mcmmtk::config;
use mcmmtk::model_paint::*;

fn activate(app: &gtk::Application) {
    let window = gtk::ApplicationWindow::new(app);
    window.set_title("Modellers Colour Mixing/Matching TK");
    window.set_geometry_from_recollections("main_window", (200, 200));
    let stack = gtk::Stack::new();
    let data_path = config::get_paint_series_files_data_path();
    let mixer = ModelPaintMixer::create(&data_path);
    stack.add_titled(&mixer.pwo(), "paint_mixer", "Paint Mixer");
    let vbox = gtk::Box::new(gtk::Orientation::Vertical, 0);
    let mspe = ModelSeriesPaintEntry::create();
    vbox.pack_start(&mspe.pwo(), false, true, 0);
    stack.add_titled(&vbox, "series_paint_editor", "Series Paint Editor/Creator");
    let iview = PixbufView::create();
    stack.add_titled(&iview.pwo(), "sample_viewer", "Sample Viewer");
    let stack_switcher = gtk::StackSwitcher::new();
    stack_switcher.set_stack(Some(&stack));
    let vbox = gtk::Box::new(gtk::Orientation::Vertical, 0);
    vbox.pack_start(&stack_switcher, false, false, 0);
    vbox.pack_start(&stack.clone(), true, true, 0);
    window.add(&vbox);
    window.show_all();
    match gdk_pixbuf::Pixbuf::new_from_file("mcmmtk.png") {
        Ok(pixbuf) => iview.set_pixbuf(Some(&pixbuf)),
        Err(err) => println!("{:?}", err)
    };
    stack.set_visible_child(&mixer.pwo());
}

fn main() {
    //Command::new("gnome-screenshot").arg("-ca").spawn();
    recollections::init(&config::get_gui_config_dir_path().join("recollections"));
    let flags = gio::ApplicationFlags::empty();
    let app = gtk::Application::new("mcmmtk.pw.nest", flags).unwrap_or_else(
        |err| panic!("{:?}: line {:?}: {:?}", file!(), line!(), err)
    );
    app.connect_activate(activate);
    app.run(&[]);
}
