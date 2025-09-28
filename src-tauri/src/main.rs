#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use std::{fs, path::PathBuf};
use tauri::{Manager, GlobalShortcutManager};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};

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
        .setup(|app| {
            let app_dir: PathBuf = app.path_resolver().app_data_dir().unwrap();
            let flag_file = app_dir.join("autostart_enabled");

            if !flag_file.exists() {
                let autostart = app.autolaunch();
                autostart.enable().expect("Failed to enable autostart");

                fs::create_dir_all(&app_dir)?;
                fs::write(&flag_file, "enabled")?;
                println!("Autostart enabled (first run)");
            }

            // Start Flask server
            Command::new("bin/app.exe")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("Failed to launch backend");

            let app_handle = app.handle();

	    {
                let app_handle = app_handle.clone();
                let mut gsm = app.global_shortcut_manager();

                gsm.register("Ctrl+Shift+Space", move || {
                    if let Some(window) = app_handle.get_window("main") {
                        let is_visible = window.is_visible().unwrap_or(false);
                        if is_visible {
                            window.hide().unwrap();
                        } else {
                            window.show().unwrap();
                            window.set_focus().unwrap();
                        }
                    }
                }).expect("failed to register global shortcut");
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
