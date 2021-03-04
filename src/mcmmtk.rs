// Copyright 2020 Peter Williams <pwil3058@gmail.com> <pwil3058@bigpond.net.au>

use std::{process::Command, rc::Rc};

use pw_gix::{
    gdk_pixbufx::viewer::PixbufViewBuilder,
    gtk::{self, prelude::*},
    gtkx::window::RememberGeometry,
    sample,
    wrapper::*,
};

use apaint_gtk::{
    characteristics::CharacteristicType,
    colour::ScalarAttribute,
    factory::{BasicPaintFactory, BasicPaintFactoryBuilder},
    mixer::targeted::{TargetedPaintMixer, TargetedPaintMixerBuilder},
};

use crate::config;

#[derive(PWO, Wrapper)]
pub struct ModellersColourMixerMatcherTK {
    vbox: gtk::Box,
    mixer: Rc<TargetedPaintMixer>,
    factory: Rc<BasicPaintFactory>,
}

impl ModellersColourMixerMatcherTK {
    pub fn new() -> Rc<Self> {
        let attributes = vec![
            ScalarAttribute::Value,
            ScalarAttribute::Greyness,
            ScalarAttribute::Chroma,
        ];
        let characteristics = vec![
            CharacteristicType::Finish,
            CharacteristicType::Transparency,
            CharacteristicType::Fluorescence,
            CharacteristicType::Metallicness,
        ];
        let mixer = TargetedPaintMixerBuilder::new()
            .attributes(&attributes)
            .characteristics(&characteristics)
            .config_dir_path(&config::config_dir_path())
            .build();
        let factory = BasicPaintFactoryBuilder::new()
            .attributes(&attributes)
            .characteristics(&characteristics)
            .build();
        let mcmmtk = Rc::new(Self {
            vbox: gtk::Box::new(gtk::Orientation::Vertical, 0),
            mixer,
            factory,
        });
        let hbox = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        mcmmtk.vbox.pack_start(&hbox, false, false, 0);

        let stack = gtk::StackBuilder::new().build();
        stack.add_titled(&mcmmtk.mixer.pwo(), "mixer", "Mixer");
        stack.add_titled(
            &mcmmtk.factory.pwo(),
            "factory",
            "Paint/Standard Editor/Factory",
        );
        mcmmtk.vbox.pack_start(&stack, true, true, 0);
        let stack_switcher = gtk::StackSwitcherBuilder::new()
            .tooltip_text("Select mode.")
            .stack(&stack)
            .build();
        hbox.pack_start(&stack_switcher, true, true, 0);

        let seperator = gtk::SeparatorBuilder::new().build();
        hbox.pack_start(&seperator, false, false, 0);

        let button = gtk::Button::with_label("PDF Viewer");
        hbox.pack_start(&button, false, false, 0);
        let mcmmtk_c = Rc::clone(&mcmmtk);
        button.connect_clicked(move |_| mcmmtk_c.launch_pdf_viewer());

        let button = gtk::Button::with_label("Image Viewer");
        hbox.pack_start(&button, false, false, 0);
        button.connect_clicked(move |_| launch_image_viewer());

        if sample::screen_sampling_available() {
            let btn = gtk::Button::with_label("Take Sample");
            btn.set_tooltip_text(Some("Take a sample of a portion of the screen"));
            let mcmmtk_c = Rc::clone(&mcmmtk);
            btn.connect_clicked(move |_| {
                if let Err(err) = sample::take_screen_sample() {
                    mcmmtk_c.report_error("Failure", &err);
                }
            });
            hbox.pack_start(&btn, false, false, 0);
        }

        mcmmtk.vbox.show_all();

        mcmmtk
    }

    pub fn ok_to_quit(&self) -> bool {
        let buttons = [
            ("Cancel", gtk::ResponseType::Cancel),
            ("Continue Discarding Changes", gtk::ResponseType::Other(1)),
        ];
        let question = if self.mixer.needs_saving() {
            if self.factory.needs_saving() {
                Some("Mixer and Paint/Standards Editor/Factory have unsaved changes!")
            } else {
                Some("Mixer has unsaved changes!")
            }
        } else if self.factory.needs_saving() {
            Some("Paint/Standards Editor/Factory has unsaved changes!")
        } else {
            None
        };
        if let Some(question) = question {
            if self.ask_question(question, None, &buttons) == gtk::ResponseType::Cancel {
                return false;
            }
        }
        true
    }

    fn launch_pdf_viewer(&self) {
        // TODO: make pdf viewer configurable
        let viewer = "xreader";
        if let Err(err) = Command::new(viewer).spawn() {
            let msg = format!("Error running \"{}\"", viewer);
            self.report_error(&msg, &err);
        }
    }
}

fn launch_image_viewer() {
    let window = gtk::Window::new(gtk::WindowType::Toplevel);
    window.set_geometry_from_recollections("mcmmtk_gtk::image_viewer", (200, 200));
    window.set_destroy_with_parent(true);
    window.set_title("mcmmtk_gtk: Image Viewer");

    let view = PixbufViewBuilder::new().load_last_image(true).build();
    window.add(&view.pwo());
    window.show_all();

    window.present();
}
