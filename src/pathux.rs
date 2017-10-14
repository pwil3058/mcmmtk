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
use std::path::{Path, PathBuf, Component};

pub fn split_abs_path(abs_path: &Path) -> Vec<String> {
    assert!(abs_path.is_absolute());
    let mut vec: Vec<String> = Vec::new();
    for c in abs_path.components() {
        match c {
            Component::Normal(component) => {
                let oss = component.to_os_string().into_string().unwrap_or_else(
                    |err| panic!("{:?}: line {:?}: {:?}", file!(), line!(), err)
                );
                vec.push(oss);
            },
            Component::Prefix(_) => panic!("Not implemented for Windows"),
            Component::ParentDir => panic!("Illegal component"),
            _ => ()
        }
    }
    vec
}

pub fn split_rel_path(rel_path: &Path) -> Vec<String> {
    assert!(rel_path.is_relative());
    let mut vec: Vec<String> = Vec::new();
    for c in rel_path.components() {
        match c {
            Component::Normal(component) => {
                let oss = component.to_os_string().into_string().unwrap_or_else(
                    |err| panic!("{:?}: line {:?}: {:?}", file!(), line!(), err)
                );
                vec.push(oss);
            },
            Component::Prefix(_) => panic!("Not implemented for Windows"),
            Component::ParentDir => panic!("Illegal component"),
            _ => ()
        }
    }
    vec
}

pub fn first_subpath_as_string(path: &Path) -> Option<String> {
    for c in path.components() {
        match c {
            Component::RootDir => continue,
            Component::Normal(component) => {
                match component.to_os_string().into_string() {
                    Ok(oss) => return Some(oss),
                    Err(err) => panic!("{:?}: line {:?}: {:?}", file!(), line!(), err)
                };
            },
            Component::Prefix(_) => panic!("Not implemented for Windows"),
            Component::ParentDir => panic!("Illegal component"),
            _ => ()
        }
    }
    None
}

pub fn expand_home_dir(rel_path_str: &str) -> PathBuf {
    let parts = split_rel_path(&PathBuf::from(rel_path_str));
    let mut path_buf = PathBuf::new();
    if parts[0] == "~" {
        match env::home_dir() {
            Some(home_dir) => path_buf.push(home_dir),
            None => panic!("{:?}: line {:?}: badly designed OS", file!(), line!())
        }
    } else {
        panic!("Illegal input: {:?}", rel_path_str);
    };
    for part in &parts[1..] {
        path_buf.push(part);
    }
    path_buf
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_abs_path_works() {
        let parts = split_abs_path(Path::new("/home/peter/SCR"));
        assert_eq!(parts, vec!["home", "peter", "SCR"]);
    }

    #[test]
    #[should_panic]
    fn split_abs_path_panics() {
        let parts = split_abs_path(Path::new("/home/../peter/SCR"));
        assert_eq!(parts, vec!["home", "peter", "SCR"]);
    }

    #[test]
    fn first_subpath_as_string_works() {
        assert_eq!(Some("first".to_string()), first_subpath_as_string(Path::new("first/second")));
        assert_ne!(Some("second".to_string()), first_subpath_as_string(Path::new("first/second")));
        assert_eq!(Some("first".to_string()), first_subpath_as_string(Path::new("/first/second")));
    }

    #[test]
    fn test_expand_home_dir() {
        let home_dir = match env::home_dir() {
            Some(home_dir) => home_dir,
            None => panic!("{:?}: line {:?}: badly designed OS", file!(), line!())
        };
        assert_eq!(home_dir, expand_home_dir("~"));
        assert_eq!(home_dir.join("SRC/GITHUB"), expand_home_dir("~/SRC/GITHUB"));
    }
}
