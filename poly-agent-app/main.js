const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let agentProcess = null;
let agentEnabled = false;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'PolyAgent - Autonomous Polymarket Trading',
    backgroundColor: '#1a1a2e',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    icon: path.join(__dirname, 'renderer/icon.png')
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'));

  // Create menu bar (matches your diagram)
  const template = [
    { label: 'File', submenu: [
      { role: 'quit' }
    ]},
    { label: 'Edit', submenu: [
      { role: 'undo' },
      { role: 'redo' },
      { type: 'separator' },
      { role: 'cut' },
      { role: 'copy' },
      { role: 'paste' }
    ]},
    { label: 'Options', submenu: [
      { 
        label: agentEnabled ? 'Disable Agent' : 'Enable Agent',
        click: () => toggleAgent()
      },
      { type: 'separator' },
      { label: 'Settings...', accelerator: 'CmdOrCtrl+,', click: () => showSettings() }
    ]},
    { label: 'Tools', submenu: [
      { label: 'Scan Markets', accelerator: 'CmdOrCtrl+S', click: () => sendToAgent('scan') },
      { label: 'Check Positions', accelerator: 'CmdOrCtrl+P', click: () => sendToAgent('positions') }
    ]},
    { label: 'Window', submenu: [
      { role: 'minimize' },
      { role: 'zoom' },
      { type: 'separator' },
      { role: 'togglefullscreen' }
    ]},
    { label: 'Help', submenu: [
      { label: 'About PolyAgent', click: () => showAbout() }
    ]}
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function toggleAgent() {
  if (agentEnabled) {
    stopAgent();
  } else {
    startAgent();
  }
}

function startAgent() {
  agentEnabled = true;
  
  // Spawn Python agent as background process
  const pythonPath = 'python'; // or 'python3' on some systems
  
  try {
    agentProcess = spawn(pythonPath, [path.join(__dirname, 'agent/main.py')], {
      cwd: path.join(__dirname, 'agent'),
      stdio: ['pipe', 'pipe', 'pipe']
    });

    agentProcess.stdout.on('data', (data) => {
      const msg = data.toString().trim();
      if (msg && mainWindow) {
        mainWindow.webContents.send('agent-message', { type: 'output', text: msg });
      }
    });

    agentProcess.stderr.on('data', (data) => {
      const msg = data.toString().trim();
      if (msg && mainWindow) {
        mainWindow.webContents.send('agent-message', { type: 'error', text: msg });
      }
    });

    agentProcess.on('close', (code) => {
      agentEnabled = false;
      if (mainWindow) {
        mainWindow.webContents.send('agent-status', { enabled: false, code });
      }
    });

    if (mainWindow) {
      mainWindow.webContents.send('agent-status', { enabled: true });
    }
  } catch (err) {
    if (mainWindow) {
      mainWindow.webContents.send('agent-message', { 
        type: 'error', 
        text: `Failed to start agent: ${err.message}. Make sure Python is installed.` 
      });
    }
  }
}

function stopAgent() {
  agentEnabled = false;
  if (agentProcess) {
    try { agentProcess.kill('SIGTERM'); } catch(e) {}
    agentProcess = null;
  }
  if (mainWindow) {
    mainWindow.webContents.send('agent-status', { enabled: false });
  }
}

function sendToAgent(message) {
  if (!agentEnabled || !agentProcess) return;
  
  // Send message to Python agent via stdin
  const msg = JSON.stringify({ type: 'command', payload: message }) + '\n';
  try {
    agentProcess.stdin.write(msg);
  } catch(e) {}
}

function showSettings() {
  if (mainWindow) {
    mainWindow.webContents.send('show-settings');
  }
}

function showAbout() {
  const aboutWin = new BrowserWindow({
    width: 400, height: 250,
    parent: mainWindow, modal: true,
    title: 'About PolyAgent'
  });
  aboutWin.loadFile(path.join(__dirname, 'renderer/about.html'));
}

// IPC handlers for frontend ↔ main process communication
ipcMain.on('agent-toggle', (event, enabled) => {
  if (enabled && !agentEnabled) startAgent();
  else if (!enabled && agentEnabled) stopAgent();
});

ipcMain.on('agent-message', (event, msg) => {
  // Forward messages from frontend to agent
  sendToAgent(msg);
});

ipcMain.on('get-agent-status', (event) => {
  event.reply('agent-status-reply', { enabled: agentEnabled });
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (agentEnabled) stopAgent(); // Clean shutdown
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
