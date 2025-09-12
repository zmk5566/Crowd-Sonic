import React, { useState, useEffect } from 'react';
import { APIClient } from '../services/api';
import { ServerManager } from './ServerManager';
import { serverStorageService } from '../services/serverStorage';
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
  onDeviceStatusChange?: (hasRunning: boolean) => void;
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
  onDeviceStatusChange,
  currentDevice,
  targetFps = 30,
}) => {
  const [urlInput, setUrlInput] = useState(baseUrl);
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [showServerManager, setShowServerManager] = useState(false);
  const [availableServers, setAvailableServers] = useState(serverStorageService.getServers());

  // Load available servers when component mounts
  useEffect(() => {
    setAvailableServers(serverStorageService.getServers());
  }, []);

  // Update URL input when baseUrl changes (e.g., from server selection)
  useEffect(() => {
    setUrlInput(baseUrl);
  }, [baseUrl]);

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
        
        // Check if any device is running and notify parent
        const hasRunning = deviceList.some(d => d.status === "running");
        if (onDeviceStatusChange) {
          onDeviceStatusChange(hasRunning);
        }
        
        // Find active device (status === "running")
        const activeDevice = deviceList.find(d => d.status === "running");
        if (activeDevice) {
          setSelectedDevice(activeDevice.id);
        }
      } else {
        console.error('Device list is not an array:', deviceList);
        setDevices([]);
        if (onDeviceStatusChange) {
          onDeviceStatusChange(false);
        }
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

  // Load devices when connected or apiClient changes
  useEffect(() => {
    if (isConnected) {
      loadDevices();
    } else {
      setDevices([]);
      setSelectedDevice('');
    }
  }, [isConnected, apiClient]); // Add apiClient as dependency


  // Handle server manager
  const handleOpenServerManager = () => {
    setShowServerManager(true);
  };

  const handleCloseServerManager = () => {
    setShowServerManager(false);
    // Refresh server list when manager closes
    setAvailableServers(serverStorageService.getServers());
  };

  const handleServerChange = (serverId: string) => {
    const server = availableServers.find(s => s.id === serverId);
    if (server) {
      setUrlInput(server.url);
      onBaseUrlChange(server.url);
      // Refresh server list to reflect the change
      setAvailableServers(serverStorageService.getServers());
    }
    setShowServerManager(false);
  };

  const getConnectionDisplayText = () => {
    if (!isConnected) return 'Disconnected';
    
    // Try to find the server name from storage
    const server = serverStorageService.getServerByUrl(baseUrl);
    if (server) {
      return server.name;
    }
    
    // Fallback to old logic - just show server identifier without "Connected"
    if (baseUrl.includes('localhost')) {
      return 'Local Server';
    } else if (baseUrl.includes('127.0.0.1')) {
      return 'Local IP';
    }
    
    // For other URLs, try to extract hostname
    try {
      const url = new URL(baseUrl);
      return url.hostname + (url.port ? `:${url.port}` : '');
    } catch {
      return 'Remote Server';
    }
  };

  return (
    <div className="control-panel">
      {/* Control Panel Content */}
      <div className="control-content">
        <div className="control-section">
          <div className="connection-section">
            <div className="connection-status">
              <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></div>
              <span className="connection-text">{getConnectionDisplayText()}</span>
            </div>
            <button 
              className="manage-servers-button"
              onClick={handleOpenServerManager}
              title="管理服务器"
            >
              ⚙️ 编辑
            </button>
          </div>
        </div>

      {/* Audio Device Selection */}
      {isConnected && (
        <div className="control-section">
          <div className="device-selection-compact">
            <select
              value={selectedDevice}
              onChange={(e) => handleDeviceChange(e.target.value)}
              disabled={isLoadingDevices || isPlaying}
              title={isPlaying ? "Cannot change device during visualization stream" : "Select audio device"}
              className="device-select"
            >
              <option value="">
                {isLoadingDevices ? 'Loading...' : `Device (${devices.length})`}
              </option>
              {Array.isArray(devices) && devices.map((device) => (
                <option key={device.id} value={device.id}>
                  {device.name} {device.status === "running" ? '(Running)' : device.status === "stopped" ? '(Stopped)' : '(Available)'}
                </option>
              ))}
            </select>
            
            <button 
              onClick={loadDevices} 
              disabled={isLoadingDevices}
              className="refresh-button-compact"
              title="Refresh devices"
            >
              🔄
            </button>
            
            {(() => {
              const selectedDeviceObj = devices.find(d => d.id === selectedDevice);
              const isDeviceActive = selectedDeviceObj?.status === "running";
              
              return (
                <>
                  <button 
                    onClick={handleStartDevice} 
                    disabled={!selectedDevice || isLoadingDevices || isDeviceActive || isPlaying}
                    className="start-device-button-compact"
                    title={
                      isPlaying ? "Cannot enable device during visualization stream" :
                      isDeviceActive ? "Device already enabled" : 
                      "Enable selected device"
                    }
                  >
                    ✅
                  </button>
                  
                  <button 
                    onClick={handleStopDevice} 
                    disabled={!selectedDevice || isLoadingDevices || !isDeviceActive || isPlaying}
                    className="stop-device-button-compact"
                    title={
                      isPlaying ? "Cannot disable device during visualization stream" :
                      !isDeviceActive ? "Device already disabled" : 
                      "Disable selected device"
                    }
                  >
                    ❌
                  </button>
                </>
              );
            })()}
          </div>
        </div>
      )}

      <div className="control-section">
        <button
          className={`stream-button ${isPlaying ? 'streaming' : ''}`}
          onClick={onPlay}
          disabled={!isConnected || !devices.some(d => d.status === "running")}
        >
          {isPlaying ? 'Stop Streaming' : 'Start Streaming'}
        </button>
      </div>

      </div>
      
      {/* Server Manager Modal */}
      <ServerManager
        isOpen={showServerManager}
        onClose={handleCloseServerManager}
        onServerChange={handleServerChange}
      />
    </div>
  );
};