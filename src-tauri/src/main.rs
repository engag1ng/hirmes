// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use std::env;
use std::path::PathBuf;

fn main() {
    hirmes_lib::run();

    let mut exe_path = std::env::current_exe().expect("Failed to get current exe path");
    exe_path.pop();
    exe_path.push("bin");
    exe_path.push("app.exe");
    Command::new(exe_path)
        .stdout(Stdio::null())
        .spawn()
        .expect("Failed to start Flask App");

    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
