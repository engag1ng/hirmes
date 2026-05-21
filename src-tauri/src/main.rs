#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use std::{fs, path::PathBuf};
use tauri::Manager;
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

fn send_shutdown_signal() {
    let client = reqwest::blocking::Client::new();
    let result = client.get("http://127.0.0.1:5000/shutdown").send();

    if let Err(e) = result {
        eprintln!("Failed to send shutdown request: {}", e);
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            None,
        ))
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(|app| {
            let app_dir: PathBuf = app.path().app_data_dir()?;
            let flag_file = app_dir.join("autostart_enabled");

            if !flag_file.exists() {
                let autostart = app.autolaunch();
                autostart.enable().expect("Failed to enable autostart");

                fs::create_dir_all(&app_dir)?;
                fs::write(&flag_file, "enabled")?;
                println!("Autostart enabled (first run)");
            }

            Command::new(format!("bin/app{}", std::env::consts::EXE_SUFFIX))
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("Failed to launch backend");

            let app_handle = app.handle().clone();

            {
                let app_handle = app_handle.clone();
                app.handle().global_shortcut().on_shortcut("Ctrl+Shift+Space", move |_app, _shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let is_visible = window.is_visible().unwrap_or(false);
                            if is_visible {
                                window.hide().unwrap();
                            } else {
                                window.show().unwrap();
                                window.set_focus().unwrap();
                            }
                        }
                    }
                })?;
            }

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

                let splash = app_handle.get_webview_window("splashscreen").unwrap();
                let main = app_handle.get_webview_window("main").unwrap();
                splash.close().unwrap();
                main.show().unwrap();
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if window.label() == "main" {
                    send_shutdown_signal();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
