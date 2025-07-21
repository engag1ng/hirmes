#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use std::{thread, time};
use std::net::TcpStream;

fn wait_for_flask_ready() {
    let max_retries = 20;
    let wait_time = time::Duration::from_millis(200);

    for _ in 0..max_retries {
        if TcpStream::connect("127.0.0.1:5000").is_ok() {
            return;
        }
        thread::sleep(wait_time);
    }

    panic!("Flask backend failed to start on port 5000");
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
        .setup(|_app| {
            Command::new("bin/app.exe")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("Failed to launch backend");

            wait_for_flask_ready();

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                // This triggers BEFORE the window closes
                send_shutdown_signal();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}