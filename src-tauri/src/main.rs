#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use tauri::{Manager};

fn send_shutdown_signal() {
    let client = reqwest::blocking::Client::new();
    let result = client.get("http://127.0.0.1:5000/shutdown").send();

    if let Err(e) = result {
        eprintln!("Failed to send shutdown request: {}", e);
    }
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start Flask server
            Command::new("bin/app.exe")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("Failed to launch backend");

            let app_handle = app.handle();

            tauri::async_runtime::spawn(async move {
                let client = reqwest::Client::new();
                let mut retries = 0;

                while retries < 20 {
                    if client.get("http://127.0.0.1:5000").send().await.is_ok() {
                        break;
                    }
                    retries += 1;
                    tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                }

                let splash = app_handle.get_window("splashscreen").unwrap();
                let main = app_handle.get_window("main").unwrap();
                splash.close().unwrap();
                main.show().unwrap();
            });

            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                if event.window().label() == "main" {
                    send_shutdown_signal();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
