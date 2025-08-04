#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use tauri::{Window, AppHandle};

// Command to be called from the frontend after it finishes loading
#[tauri::command]
async fn close_splashscreen(window: Window) {
    window
        .get_window("splashscreen")
        .expect("no window labeled 'splashscreen' found")
        .close()
        .unwrap();

    window
        .get_window("main")
        .expect("no window labeled 'main' found")
        .show()
        .unwrap();
}

fn send_shutdown_signal() {
    let client = reqwest::blocking::Client::new();
    let result = client
        .post("http://127.0.0.1:5000/shutdown")
        .send();

    match result {
        Ok(response) => {
            println!("Shutdown request sent: {}", response.status());
        }
        Err(e) => {
            eprintln!("Failed to send shutdown request: {}", e);
        }
    }
}

fn main() {
    tauri::Builder::default()
        .invokeHandler(tauri::generate_handler![close_splashscreen])
        .setup(|app| {
            Command::new("bin/app.exe")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("Failed to launch backend");

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                send_shutdown_signal();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}