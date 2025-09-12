import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Example API methods - we'll expand this as needed
  platform: process.platform,
  version: process.versions.electron,
  
  // Future: Add methods for communicating with main process
  // openDevTools: () => ipcRenderer.invoke('open-dev-tools'),
  // minimizeApp: () => ipcRenderer.invoke('minimize-app'),
  // maximizeApp: () => ipcRenderer.invoke('maximize-app'),
  // closeApp: () => ipcRenderer.invoke('close-app'),
});

// Types for the exposed API
declare global {
  interface Window {
    electronAPI: {
      platform: string;
      version: string;
    };
  }
}