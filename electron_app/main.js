const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let flaskProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    webPreferences: {
      contextIsolation: true,
    }
  });

  mainWindow.loadURL('http://localhost:5000');
}

function startFlask() {
  const python = process.platform === 'win32'
    ? path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe')
    : path.join(__dirname, '..', '.venv', 'bin', 'python');

  flaskProcess = spawn(python, [path.join(__dirname, '..', 'start.py')]);

  flaskProcess.stdout.on('data', (data) => console.log(`[flask] ${data}`));
  flaskProcess.stderr.on('data', (data) => console.error(`[flask error] ${data}`));
}

app.whenReady().then(() => {
  startFlask();
  setTimeout(createWindow, 1000);
});

app.on('window-all-closed', () => {
  if (flaskProcess) flaskProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});
