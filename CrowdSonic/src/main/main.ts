import { app, BrowserWindow, Menu } from 'electron';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';

let mainWindow: BrowserWindow;
let pythonProcess: ChildProcess | null = null;

const isDev = process.env.NODE_ENV === 'development';

// Python backend management
const startPythonBackend = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    try {
      // Path to the headless_ultrasonic directory
      const headlessPath = path.join(__dirname, '..', '..', '..', 'headless_ultrasonic');
      
      console.log('Starting Python backend from:', headlessPath);
      
      pythonProcess = spawn('python', ['-c', `
import uvicorn
from main import app
print('🎵 CrowdSonic backend starting...')
print('Server: http://localhost:8380')
uvicorn.run(app, host='0.0.0.0', port=8380, log_level='info')
`], {
        cwd: headlessPath,
        stdio: 'inherit'
      });

      pythonProcess.on('error', (error) => {
        console.error('Failed to start Python backend:', error);
        reject(error);
      });

      // Give the backend time to start
      setTimeout(() => {
        if (pythonProcess && !pythonProcess.killed) {
          console.log('Python backend started successfully');
          resolve();
        } else {
          reject(new Error('Python process failed to start'));
        }
      }, 2000);

    } catch (error) {
      console.error('Error starting Python backend:', error);
      reject(error);
    }
  });
};

const stopPythonBackend = () => {
  if (pythonProcess && !pythonProcess.killed) {
    console.log('Stopping Python backend...');
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
};

const createWindow = (): void => {
  // Create the browser window
  mainWindow = new BrowserWindow({
    height: 800,
    width: 1200,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false, // Allow cross-origin requests for API connections
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#1a1a1a',
    show: false
  });

  // Load the app
  if (isDev) {
    mainWindow.loadFile(path.join(__dirname, 'index.html'));
    // Open DevTools in development
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'index.html'));
  }

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null!;
  });
};

// Create application menu
const createMenu = () => {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: 'CrowdSonic',
      submenu: [
        { label: 'About CrowdSonic', role: 'about' },
        { type: 'separator' },
        { label: 'Hide CrowdSonic', accelerator: 'Command+H', role: 'hide' },
        { label: 'Hide Others', accelerator: 'Command+Shift+H', role: 'hideOthers' },
        { label: 'Show All', role: 'unhide' },
        { type: 'separator' },
        { label: 'Quit CrowdSonic', accelerator: 'Command+Q', role: 'quit' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { label: 'Toggle Fullscreen', accelerator: 'Ctrl+Command+F', role: 'togglefullscreen' },
        { type: 'separator' },
        { label: 'Actual Size', accelerator: 'Command+0', role: 'resetZoom' },
        { label: 'Zoom In', accelerator: 'Command+Plus', role: 'zoomIn' },
        { label: 'Zoom Out', accelerator: 'Command+-', role: 'zoomOut' }
      ]
    },
    {
      label: 'Tools',
      submenu: [
        { label: 'Toggle Developer Tools', accelerator: 'F12', role: 'toggleDevTools' }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
};

// App event handlers
app.whenReady().then(async () => {
  console.log('CrowdSonic app is ready');
  
  // Try to start Python backend, but don't fail if it's not available
  try {
    await startPythonBackend();
    console.log('Python backend started successfully');
  } catch (error: any) {
    console.warn('Could not start local Python backend:', error.message || error);
    console.log('CrowdSonic will start in remote-only mode');
  }
  
  createWindow();
  createMenu();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopPythonBackend();
});

// Handle app termination
process.on('SIGINT', () => {
  stopPythonBackend();
  app.quit();
});

process.on('SIGTERM', () => {
  stopPythonBackend();
  app.quit();
});