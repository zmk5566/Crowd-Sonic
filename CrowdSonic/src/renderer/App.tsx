import React, { useState, useEffect, useMemo } from 'react';
import { Layout } from './components/Layout';
import { ControlPanel } from './components/ControlPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { CanvasViewport } from './components/CanvasViewport';
import { StatusBar } from './components/StatusBar';
import { APIClient } from './services/api';
import { serverStorageService } from './services/serverStorage';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [baseUrl, setBaseUrl] = useState(() => {
    // Initialize baseUrl from storage or default
    const currentServer = serverStorageService.getCurrentServer();
    return currentServer?.url || 'http://localhost:8380';
  });
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentDevice, setCurrentDevice] = useState<string>('');
  const [targetFps, setTargetFps] = useState(30); // Track user's FPS setting
  
  // View state
  const [showFrequency, setShowFrequency] = useState(true);
  const [showSpectrogram, setShowSpectrogram] = useState(true);

  // Status data
  const [statusData, setStatusData] = useState({
    fps: 0,
    peakFreq: 0,
    peakAmplitude: 0,
    dataRate: 0
  });

  // Use useMemo to prevent APIClient from being recreated on every render
  const apiClient = useMemo(() => new APIClient(baseUrl), [baseUrl]);

  useEffect(() => {
    // Test connection on startup
    testConnection();
  }, []);

  const testConnection = async () => {
    try {
      const isHealthy = await apiClient.testConnection();
      setIsConnected(isHealthy);
    } catch (error) {
      console.error('Connection test failed:', error);
      setIsConnected(false);
    }
  };

  const handlePlay = async () => {
    try {
      if (isPlaying) {
        // Stop visualization stream - just disconnect from stream, don't stop the device
        console.log('Stopping visualization stream (device remains running)');
      } else {
        // Configure optimal stream settings for current device
        if (currentDevice) {
          await apiClient.configureDeviceStream(currentDevice, {
            enable_adaptive_fps: false,  // Disable adaptive FPS
            enable_smart_skip: false,    // Disable smart skip
            target_fps: targetFps        // Use user's FPS setting
          });
          console.log(`Stream configured with ${targetFps} FPS`);
        }
        // Note: Don't call start() here - device should already be started by the Start button
        // Just set playing state to trigger stream connection
      }
      setIsPlaying(!isPlaying);
    } catch (error) {
      console.error('Failed to toggle playbook:', error);
    }
  };

  const handleBaseUrlChange = (newUrl: string) => {
    setBaseUrl(newUrl);
    
    // Import server if it doesn't exist in storage
    const existingServer = serverStorageService.getServerByUrl(newUrl);
    if (!existingServer) {
      const importedServer = serverStorageService.importServer(newUrl);
      console.log('Imported new server:', importedServer);
    }
    
    // Set as current server if it exists
    const server = serverStorageService.getServerByUrl(newUrl);
    if (server) {
      serverStorageService.setCurrentServer(server.id);
    }
    
    // Re-test connection with new URL
    testConnection();
  };

  const handleDeviceChange = (deviceId: string) => {
    setCurrentDevice(deviceId);
    console.log('App: Current device changed to:', deviceId);
  };

  const handleFpsChange = (fps: number) => {
    setTargetFps(fps);
    console.log('App: Target FPS changed to:', fps);
  };

  return (
    <Layout>
      {/* Control Panel - Now horizontal at top */}
      <ControlPanel
        isConnected={isConnected}
        isPlaying={isPlaying}
        baseUrl={baseUrl}
        showFrequency={showFrequency}
        showSpectrogram={showSpectrogram}
        apiClient={apiClient}
        onPlay={handlePlay}
        onBaseUrlChange={handleBaseUrlChange}
        onTestConnection={testConnection}
        onDeviceChange={handleDeviceChange}
        onFpsChange={handleFpsChange}
        currentDevice={currentDevice}
        targetFps={targetFps}
      />

      {/* Main Content Area */}
      <div className="main-content">
        {/* Main Visualization Area */}
        <CanvasViewport
          apiClient={apiClient}
          isConnected={isConnected}
          isPlaying={isPlaying}
          showFrequency={showFrequency}
          showSpectrogram={showSpectrogram}
          onStatusUpdate={setStatusData}
          currentDevice={currentDevice}
        />
      </div>

      {/* Footer Status Bar */}
      <StatusBar
        isConnected={isConnected}
        fps={statusData.fps}
        peakFreq={statusData.peakFreq}
        peakAmplitude={statusData.peakAmplitude}
        dataRate={statusData.dataRate}
      />

      {/* Settings Panel - Fixed position bottom right */}
      <SettingsPanel
        showFrequency={showFrequency}
        showSpectrogram={showSpectrogram}
        targetFps={targetFps}
        isConnected={isConnected}
        isPlaying={isPlaying}
        onFrequencyToggle={setShowFrequency}
        onSpectrogramToggle={setShowSpectrogram}
        onFpsChange={handleFpsChange}
      />
    </Layout>
  );
};

export default App;