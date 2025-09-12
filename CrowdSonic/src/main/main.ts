import { app, BrowserWindow, Menu } from 'electron';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';

let mainWindow: BrowserWindow;
let pythonProcess: ChildProcess | null = null;

const isDev = process.env.NODE_ENV === 'development';

// Compiled backend management
const startCompiledBackend = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    try {
      // Path to the compiled headless_ultrasonic executable
      const backendPath = path.join(__dirname, '..', 'resources', 'headless_ultrasonic', 'headless_ultrasonic');
      const workingDir = path.dirname(backendPath);
      
      console.log('Starting compiled backend from:', backendPath);
      console.log('Working directory:', workingDir);
      
      // Track resolution state to avoid multiple resolve/reject calls
      let resolved = false;
      
      pythonProcess = spawn(backendPath, [], {
        cwd: workingDir,
        stdio: ['ignore', 'pipe', 'pipe']
      });

      pythonProcess.stdout?.on('data', (data) => {
        const output = data.toString();
        console.log('Backend:', output.trim());
        
        // Check if server has started successfully
        if (output.includes('Uvicorn running on')) {
          console.log('✅ Compiled backend started successfully');
          if (!resolved) {
            resolved = true;
            resolve();
          }
        }
      });

      pythonProcess.stderr?.on('data', (data) => {
        const output = data.toString();
        console.error('Backend Error:', output.trim());
      });

      pythonProcess.on('error', (error) => {
        console.error('Failed to start compiled backend:', error);
        if (!resolved) {
          resolved = true;
          reject(error);
        }
      });

      pythonProcess.on('exit', (code) => {
        console.log(`Backend process exited with code ${code}`);
        if (!resolved && code !== 0) {
          resolved = true;
          reject(new Error(`Backend process failed with exit code ${code}`));
        }
      });

      // Give the backend time to start
      setTimeout(() => {
        if (!resolved) {
          resolved = true;
          if (pythonProcess && !pythonProcess.killed) {
            console.log('✅ Backend startup timeout, but process is running');
            resolve();
          } else {
            reject(new Error('Backend process failed to start within timeout'));
          }
        }
      }, 5000); // Increased timeout for compiled version

    } catch (error) {
      console.error('Error starting compiled backend:', error);
      reject(error);
    }
  });
};

const stopCompiledBackend = () => {
  if (pythonProcess && !pythonProcess.killed) {
    console.log('Stopping compiled backend...');
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
  
  // Try to start compiled backend, but don't fail if it's not available
  try {
    await startCompiledBackend();
    console.log('✅ Compiled backend started successfully');
  } catch (error: any) {
    console.warn('Could not start compiled backend:', error.message || error);
    console.log('CrowdSonic will start in remote-only mode');
  }
  
  createWindow();
  createMenu();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopCompiledBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopCompiledBackend();
});

// Handle app termination
process.on('SIGINT', () => {
  stopCompiledBackend();
  app.quit();
});

process.on('SIGTERM', () => {
  stopCompiledBackend();
  app.quit();
});