import React, { useState, useEffect } from 'react';
import { APIClient } from '../services/api';
import './ControlPanel.css';

interface AudioDevice {
  id: string;
  name: string;
  status: string;  // "available", "running", "stopped"
  instance_state: string | null;  // null, "running", "stopped"
  is_default: boolean;
}

interface ControlPanelProps {
  isConnected: boolean;
  isPlaying: boolean;
  baseUrl: string;
  showFrequency: boolean;
  showSpectrogram: boolean;
  apiClient: APIClient;
  onPlay: () => void;
  onBaseUrlChange: (url: string) => void;
  onFrequencyToggle: (show: boolean) => void;
  onSpectrogramToggle: (show: boolean) => void;
  onTestConnection: () => void;
  onDeviceChange?: (deviceId: string) => void;
  onFpsChange?: (fps: number) => void;
  currentDevice?: string;
  targetFps?: number;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  isConnected,
  isPlaying,
  baseUrl,
  showFrequency,
  showSpectrogram,
  apiClient,
  onPlay,
  onBaseUrlChange,
  onFrequencyToggle,
  onSpectrogramToggle,
  onTestConnection,
  onDeviceChange,
  onFpsChange,
  currentDevice,
  targetFps = 30,
}) => {
  const [urlInput, setUrlInput] = useState(baseUrl);
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Load available audio devices
  const loadDevices = async () => {
    if (!isConnected) return;
    
    setIsLoadingDevices(true);
    try {
      const deviceList = await apiClient.getDevices();
      console.log('Device list response:', deviceList);
      
      // Ensure deviceList is an array
      if (Array.isArray(deviceList)) {
        setDevices(deviceList);
        
        // Find active device (status === "running")
        const activeDevice = deviceList.find(d => d.status === "running");
        if (activeDevice) {
          setSelectedDevice(activeDevice.id);
        }
      } else {
        console.error('Device list is not an array:', deviceList);
        setDevices([]);
      }
    } catch (error) {
      console.error('Failed to load devices:', error);
      setDevices([]);
    } finally {
      setIsLoadingDevices(false);
    }
  };

  // Handle device change
  const handleDeviceChange = async (deviceId: string) => {
    try {
      await apiClient.setDevice(deviceId);
      setSelectedDevice(deviceId);
      
      // Notify parent component about device change
      if (onDeviceChange) {
        onDeviceChange(deviceId);
      }
      
      console.log('Device changed to:', deviceId);
    } catch (error) {
      console.error('Failed to change device:', error);
    }
  };

  // Handle FPS change for specific device
  const handleFpsChange = async (fps: number) => {
    try {
      const deviceToUse = currentDevice || selectedDevice;
      
      if (deviceToUse) {
        // Configure FPS for specific device
        await apiClient.configureDeviceStream(deviceToUse, { target_fps: fps });
        console.log(`FPS changed to ${fps} for device: ${deviceToUse}`);
      } else {
        // Fallback to legacy global configuration
        await apiClient.configureStream({ target_fps: fps });
        console.log('FPS changed to:', fps);
      }
      
      // Update App's FPS state
      if (onFpsChange) {
        onFpsChange(fps);
      }
    } catch (error) {
      console.error('Failed to change FPS:', error);
    }
  };

  // Handle enable device
  const handleStartDevice = async () => {
    const deviceToUse = currentDevice || selectedDevice;
    if (!deviceToUse) {
      alert('Please select a device first');
      return;
    }

    try {
      await apiClient.startDevice(deviceToUse);
      console.log(`Device enabled: ${deviceToUse}`);
      
      // Notify parent component about device change (set as current device)
      if (onDeviceChange) {
        onDeviceChange(deviceToUse);
      }
      
      // Wait a moment and check device status
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      try {
        const status = await apiClient.getDeviceStatus(deviceToUse);
        console.log(`Device ${deviceToUse} status:`, status);
      } catch (statusError) {
        console.error('Failed to get device status:', statusError);
      }
      
      // Refresh device list to update status
      await loadDevices();
    } catch (error) {
      console.error('Failed to enable device:', error);
    }
  };

  // Handle disable device
  const handleStopDevice = async () => {
    const deviceToUse = currentDevice || selectedDevice;
    if (!deviceToUse) {
      alert('Please select a device first');
      return;
    }

    try {
      await apiClient.stopDevice(deviceToUse);
      console.log(`Device disabled: ${deviceToUse}`);
      // Refresh device list to update status
      await loadDevices();
    } catch (error) {
      console.error('Failed to disable device:', error);
    }
  };

  // Load devices when connected
  useEffect(() => {
    if (isConnected) {
      loadDevices();
    } else {
      setDevices([]);
      setSelectedDevice('');
    }
  }, [isConnected]);

  const handleUrlSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onBaseUrlChange(urlInput);
  };

  return (
    <div className={`control-panel ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Collapse Toggle Button */}
      <button 
        className="collapse-toggle" 
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? "Expand Control Panel" : "Collapse Control Panel"}
      >
        {isCollapsed ? '▼' : '▲'}
      </button>

      {/* Control Panel Content */}
      <div className={`control-content ${isCollapsed ? 'hidden' : ''}`}>
        <div className="control-section">
          <h3>Connection</h3>
          
          <div className="connection-status">
            <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></div>
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>

          <form onSubmit={handleUrlSubmit} className="url-form">
            <label htmlFor="base-url">Backend URL:</label>
            <input
              id="base-url"
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="http://localhost:8380"
            />
            <div className="url-form-buttons">
              <button type="submit">Connect</button>
              <button type="button" onClick={onTestConnection}>Test</button>
            </div>
          </form>
        </div>

      {/* Audio Device Selection */}
      {isConnected && (
        <div className="control-section">
          <h3>Audio Device</h3>
          
          <div className="device-selection">
            <select
              value={selectedDevice}
              onChange={(e) => handleDeviceChange(e.target.value)}
              disabled={isLoadingDevices || isPlaying}
              title={isPlaying ? "Cannot change device during visualization stream" : "Select audio device"}
            >
              <option value="">
                {isLoadingDevices ? 'Loading devices...' : 'Select device...'}
              </option>
              {Array.isArray(devices) && devices.map((device) => (
                <option key={device.id} value={device.id}>
                  {device.name} {device.status === "running" ? '(Running)' : device.status === "stopped" ? '(Stopped)' : '(Available)'}
                </option>
              ))}
            </select>
            
            <div className="device-buttons">
              <button 
                onClick={loadDevices} 
                disabled={isLoadingDevices}
                className="refresh-button"
              >
                🔄 Refresh
              </button>
              
              {(() => {
                const selectedDeviceObj = devices.find(d => d.id === selectedDevice);
                const isDeviceActive = selectedDeviceObj?.status === "running";
                
                return (
                  <>
                    <button 
                      onClick={handleStartDevice} 
                      disabled={!selectedDevice || isLoadingDevices || isDeviceActive || isPlaying}
                      className="start-device-button"
                      title={
                        isPlaying ? "Cannot enable device during visualization stream" :
                        isDeviceActive ? "Device already enabled" : 
                        "Enable selected device"
                      }
                    >
                      ✅ Enable
                    </button>
                    
                    <button 
                      onClick={handleStopDevice} 
                      disabled={!selectedDevice || isLoadingDevices || !isDeviceActive || isPlaying}
                      className="stop-device-button"
                      title={
                        isPlaying ? "Cannot disable device during visualization stream" :
                        !isDeviceActive ? "Device already disabled" : 
                        "Disable selected device"
                      }
                    >
                      ❌ Disable
                    </button>
                  </>
                );
              })()}
            </div>
          </div>
        </div>
      )}

      <div className="control-section">
        <h3>Visualization Stream</h3>
        
        <div className="stream-controls">
          <button
            className={`play-button ${isPlaying ? 'playing' : ''}`}
            onClick={onPlay}
            disabled={!isConnected}
          >
            <div className={`status-indicator ${isPlaying ? 'playing' : ''}`}></div>
            {isPlaying ? 'Stop' : 'Start'}
          </button>
        </div>
      </div>

      <div className="control-section">
        <h3>Display</h3>
        
        <div className="display-options">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showFrequency}
              onChange={(e) => onFrequencyToggle(e.target.checked)}
            />
            <span>Frequency Spectrum</span>
          </label>
          
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showSpectrogram}
              onChange={(e) => onSpectrogramToggle(e.target.checked)}
            />
            <span>Spectrogram</span>
          </label>
        </div>
      </div>

      <div className="control-section">
        <h3>Settings</h3>
        
        {isConnected && (
          <div className="settings-controls">
            <div className="setting-item">
              <label htmlFor="fps-slider">Target FPS: {targetFps}</label>
              <input
                id="fps-slider"
                type="range"
                min="5"
                max="60"
                step="5"
                value={targetFps}
                onChange={(e) => handleFpsChange(parseInt(e.target.value))}
                disabled={isPlaying}
              />
              <div className="fps-presets">
                {[15, 30, 60].map(fps => (
                  <button
                    key={fps}
                    onClick={() => handleFpsChange(fps)}
                    disabled={isPlaying}
                    className={targetFps === fps ? 'active' : ''}
                  >
                    {fps}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        
        <div className="settings-info">
          <p>Platform: {window.electronAPI?.platform || 'Unknown'}</p>
          <p>Version: {window.electronAPI?.version || 'Unknown'}</p>
        </div>
      </div>
      </div>
    </div>
  );
};