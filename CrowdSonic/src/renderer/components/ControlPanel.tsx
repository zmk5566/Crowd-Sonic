import React, { useState, useEffect } from 'react';
import { APIClient } from '../services/api';
import './ControlPanel.css';

interface AudioDevice {
  id: string;
  name: string;
  is_active: boolean;
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
  currentDevice?: string;
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
  currentDevice,
}) => {
  const [urlInput, setUrlInput] = useState(baseUrl);
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [targetFps, setTargetFps] = useState(30);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);

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
        
        // Find active device
        const activeDevice = deviceList.find(d => d.is_active);
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
        setTargetFps(fps);
        console.log(`FPS changed to ${fps} for device: ${deviceToUse}`);
      } else {
        // Fallback to legacy global configuration
        await apiClient.configureStream({ target_fps: fps });
        setTargetFps(fps);
        console.log('FPS changed to:', fps);
      }
    } catch (error) {
      console.error('Failed to change FPS:', error);
    }
  };

  // Handle start device
  const handleStartDevice = async () => {
    const deviceToUse = currentDevice || selectedDevice;
    if (!deviceToUse) {
      alert('Please select a device first');
      return;
    }

    try {
      await apiClient.startDevice(deviceToUse);
      console.log(`Device started: ${deviceToUse}`);
      
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
      console.error('Failed to start device:', error);
    }
  };

  // Handle stop device
  const handleStopDevice = async () => {
    const deviceToUse = currentDevice || selectedDevice;
    if (!deviceToUse) {
      alert('Please select a device first');
      return;
    }

    try {
      await apiClient.stopDevice(deviceToUse);
      console.log(`Device stopped: ${deviceToUse}`);
      // Refresh device list to update status
      await loadDevices();
    } catch (error) {
      console.error('Failed to stop device:', error);
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
    <div className="control-panel">
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
            >
              <option value="">
                {isLoadingDevices ? 'Loading devices...' : 'Select device...'}
              </option>
              {Array.isArray(devices) && devices.map((device) => (
                <option key={device.id} value={device.id}>
                  {device.name} {device.is_active ? '(Active)' : ''}
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
              
              <button 
                onClick={handleStartDevice} 
                disabled={!selectedDevice || isLoadingDevices}
                className="start-device-button"
                title="Start selected device"
              >
                ▶️ Start
              </button>
              
              <button 
                onClick={handleStopDevice} 
                disabled={!selectedDevice || isLoadingDevices}
                className="stop-device-button"
                title="Stop selected device"
              >
                ⏹️ Stop
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="control-section">
        <h3>Playback</h3>
        
        <div className="playback-controls">
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
  );
};