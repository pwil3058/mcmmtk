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

use std::env;
use std::fs::File;
use std::io::{Read, Write};
use std::path::PathBuf;

use pathux;

const DEFAULT_CONFIG_DIR_PATH: &str = "~/.config/mcmmtk/ng";

const DCDP_OVERRIDE_ENVAR: &str = "MCMMTK_CONFIG_DIR";

pub fn abs_default_config_dir_path() -> PathBuf {
    pathux::expand_home_dir(DEFAULT_CONFIG_DIR_PATH)
}

fn get_config_dir_path() -> PathBuf {
    match env::var(DCDP_OVERRIDE_ENVAR) {
        Ok(dir_path) => if dir_path.len() == 0 {
            abs_default_config_dir_path()
        } else if dir_path.starts_with("~") {
            pathux::expand_home_dir(&dir_path)
        } else {
            PathBuf::from(dir_path)
        },
        Err(_) => abs_default_config_dir_path()
    }
}

pub fn get_gui_config_dir_path() -> PathBuf {
    get_config_dir_path().join("rs_gui")
}

// SERIES PAINT DATA FILES
pub fn get_paint_series_files_data_path() -> PathBuf {
    get_config_dir_path().join("paint_series_files")
}

pub fn get_series_file_paths() -> Vec<PathBuf> {
    let mut vpb = Vec::new();
    let file_path = get_config_dir_path().join("paint_series_files");
    if !file_path.exists() {
        return vpb
    };
    let mut file = File::open(&file_path).unwrap_or_else(
        |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
    );
    let mut string = String::new();
    file.read_to_string(&mut string).unwrap_or_else(
        |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
    );
    for line in string.lines() {
        vpb.push(PathBuf::from(line));
    }

    vpb
}

pub fn set_series_file_paths(file_paths: &Vec<PathBuf>) {
    let file_path = get_config_dir_path().join("paint_series_files");
    let mut file = File::create(&file_path).unwrap_or_else(
        |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
    );
    for file_path in file_paths.iter() {
        if let Some(file_path_str) = file_path.to_str() {
            write!(file, "{}\n", file_path_str).unwrap_or_else(
                |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
            );
        } else  {
            panic!("File: {:?} Line: {:?}", file!(), line!())
        };
    }
}

// PAINT STANDARD DATA FILES
pub fn get_paint_standards_files_data_path() -> PathBuf {
    get_config_dir_path().join("paint_standards_files")
}

pub fn get_standards_file_paths() -> Vec<PathBuf> {
    let mut vpb = Vec::new();
    let file_path = get_config_dir_path().join("paint_standards_files");
    if !file_path.exists() {
        return vpb
    };
    let mut file = File::open(&file_path).unwrap_or_else(
        |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
    );
    let mut string = String::new();
    file.read_to_string(&mut string).unwrap_or_else(
        |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
    );
    for line in string.lines() {
        vpb.push(PathBuf::from(line));
    }

    vpb
}

pub fn set_standards_file_paths(file_paths: &Vec<PathBuf>) {
    let file_path = get_config_dir_path().join("paint_standards_files");
    let mut file = File::create(&file_path).unwrap_or_else(
        |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
    );
    for file_path in file_paths.iter() {
        if let Some(file_path_str) = file_path.to_str() {
            write!(file, "{}\n", file_path_str).unwrap_or_else(
                |err| panic!("File: {:?} Line: {:?} : {:?}", file!(), line!(), err)
            );
        } else  {
            panic!("File: {:?} Line: {:?}", file!(), line!())
        };
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_config_dir_works() {
        let new_path = "./TEST/config";
        env::set_var(DCDP_OVERRIDE_ENVAR, new_path);
        assert_eq!(get_config_dir_path(), PathBuf::from(new_path));
        assert_eq!(get_gui_config_dir_path(), PathBuf::from(new_path).join("rs_gui"));
        env::set_var(DCDP_OVERRIDE_ENVAR, "");
        assert_eq!(get_config_dir_path(), abs_default_config_dir_path());
        assert_eq!(get_gui_config_dir_path(), abs_default_config_dir_path().join("rs_gui"));
    }
}
