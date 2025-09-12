import React, { useState, useEffect, useMemo } from 'react';
import { Layout } from './components/Layout';
import { ControlPanel } from './components/ControlPanel';
import { CanvasViewport } from './components/CanvasViewport';
import { StatusBar } from './components/StatusBar';
import { APIClient } from './services/api';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [baseUrl, setBaseUrl] = useState('http://localhost:8380');
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
      {/* Control Panel */}
      <ControlPanel
        isConnected={isConnected}
        isPlaying={isPlaying}
        baseUrl={baseUrl}
        showFrequency={showFrequency}
        showSpectrogram={showSpectrogram}
        apiClient={apiClient}
        onPlay={handlePlay}
        onBaseUrlChange={handleBaseUrlChange}
        onFrequencyToggle={setShowFrequency}
        onSpectrogramToggle={setShowSpectrogram}
        onTestConnection={testConnection}
        onDeviceChange={handleDeviceChange}
        onFpsChange={handleFpsChange}
        currentDevice={currentDevice}
        targetFps={targetFps}
      />

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

      {/* Status Bar */}
      <StatusBar
        isConnected={isConnected}
        fps={statusData.fps}
        peakFreq={statusData.peakFreq}
        peakAmplitude={statusData.peakAmplitude}
        dataRate={statusData.dataRate}
      />
    </Layout>
  );
};

export default App;