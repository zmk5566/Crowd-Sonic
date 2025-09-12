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
  const [showUrlInput, setShowUrlInput] = useState(false);

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
    setShowUrlInput(false); // Hide URL input after submit
  };

  const handleConnectionClick = () => {
    setShowUrlInput(!showUrlInput);
  };

  const handleQuickConnect = (url: string) => {
    setUrlInput(url);
    onBaseUrlChange(url);
    setShowUrlInput(false);
  };

  const getConnectionDisplayText = () => {
    if (!isConnected) return 'Disconnected';
    if (baseUrl.includes('localhost') || baseUrl.includes('127.0.0.1')) {
      return 'Localserver Connected';
    }
    return 'Remote Connected';
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
          <div className="connection-dropdown">
            <button 
              className={`connection-button ${isConnected ? 'connected' : 'disconnected'}`}
              onClick={handleConnectionClick}
            >
              <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></div>
              <span>{getConnectionDisplayText()}</span>
              <span className="dropdown-arrow">{showUrlInput ? '▲' : '▼'}</span>
            </button>
            
            {showUrlInput && (
              <div className="connection-menu">
                <button 
                  className="quick-connect-button"
                  onClick={() => handleQuickConnect('http://localhost:8380')}
                >
                  Local Server (localhost:8380)
                </button>
                <button 
                  className="quick-connect-button"
                  onClick={() => handleQuickConnect('http://127.0.0.1:8380')}
                >
                  Local IP (127.0.0.1:8380)
                </button>
                <div className="custom-url-section">
                  <form onSubmit={handleUrlSubmit} className="url-form compact">
                    <input
                      id="base-url"
                      type="url"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      placeholder="Custom URL"
                    />
                    <button type="submit">Connect</button>
                  </form>
                </div>
              </div>
            )}
          </div>
        </div>

      {/* Audio Device Selection */}
      {isConnected && (
        <div className="control-section">
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
        <button
          className={`stream-button ${isPlaying ? 'streaming' : ''}`}
          onClick={onPlay}
          disabled={!isConnected}
        >
          {isPlaying ? 'Streaming' : 'Stream'}
        </button>
      </div>

      </div>
    </div>
  );
};