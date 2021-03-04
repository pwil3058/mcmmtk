// Copyright 2020 Peter Williams <pwil3058@gmail.com> <pwil3058@bigpond.net.au>

use std::{
    env,
    path::{Path, PathBuf},
};

use pw_pathux::expand_home_dir_or_mine;

const DEFAULT_CONFIG_DIR_PATH: &str = "~/.config/mcmmtk_gtk";

const DCDP_OVERRIDE_ENVAR: &str = "MCMMTK_GTK_CONFIG_DIR";

fn abs_default_config_dir_path() -> PathBuf {
    expand_home_dir_or_mine(&Path::new(DEFAULT_CONFIG_DIR_PATH))
}

pub fn config_dir_path() -> PathBuf {
    match env::var(DCDP_OVERRIDE_ENVAR) {
        Ok(dir_path) => {
            if dir_path.is_empty() {
                abs_default_config_dir_path()
            } else if dir_path.starts_with('~') {
                expand_home_dir_or_mine(&Path::new(&dir_path))
            } else {
                dir_path.into()
            }
        }
        Err(_) => abs_default_config_dir_path(),
    }
}

pub fn gui_config_dir_path() -> PathBuf {
    config_dir_path().join("gui")
}

pub fn recollection_file_path() -> PathBuf {
    gui_config_dir_path().join("recollections")
}
