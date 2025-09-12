import React, { useRef, useEffect, useState, useCallback } from 'react';
import { APIClient, FFTFrame } from '../services/api';
import * as pako from 'pako';
import './CanvasViewport.css';

interface CanvasViewportProps {
  apiClient: APIClient;
  isConnected: boolean;
  isPlaying: boolean;
  showFrequency: boolean;
  showSpectrogram: boolean;
  currentDevice?: string;
  hasRunningDevice: boolean;
  onStatusUpdate: (status: {
    fps: number;
    peakFreq: number;
    peakAmplitude: number;
    dataRate: number;
  }) => void;
}

export const CanvasViewport: React.FC<CanvasViewportProps> = ({
  apiClient,
  isConnected,
  isPlaying,
  showFrequency,
  showSpectrogram,
  currentDevice,
  hasRunningDevice,
  onStatusUpdate,
}) => {
  const frequencyCanvasRef = useRef<HTMLCanvasElement>(null);
  const spectrogramCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Performance tracking
  const [fps, setFps] = useState(0);
  const frameCount = useRef(0);
  const lastTime = useRef(Date.now());

  // Canvas dimensions
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 400 });

  // Decompress FFT data from compressed base64 format
  const decompressFFTData = useCallback((compressedData: string): Float32Array | null => {
    try {
      // Decode base64
      const binaryString = atob(compressedData);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Decompress with pako
      const decompressed = pako.inflate(bytes);
      
      // Convert to Float32Array (same as Python's np.float32)
      return new Float32Array(decompressed.buffer);
    } catch (error) {
      console.error('FFT data decompression failed:', error);
      return null;
    }
  }, []);

  // Update canvas size on container resize
  const updateCanvasSize = useCallback(() => {
    if (!containerRef.current) return;
    
    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    const width = Math.floor(rect.width - 32); // Account for padding
    const height = Math.floor(rect.height - 32);
    
    setCanvasSize({ width, height });
  }, []);

  useEffect(() => {
    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);
    
    return () => {
      window.removeEventListener('resize', updateCanvasSize);
    };
  }, [updateCanvasSize]);

  // Use refs to avoid dependency changes
  const onStatusUpdateRef = useRef(onStatusUpdate);
  const showFrequencyRef = useRef(showFrequency);
  const showSpectrogramRef = useRef(showSpectrogram);
  
  // Update refs when props change
  useEffect(() => {
    onStatusUpdateRef.current = onStatusUpdate;
    showFrequencyRef.current = showFrequency;
    showSpectrogramRef.current = showSpectrogram;
  }, [onStatusUpdate, showFrequency, showSpectrogram]);

  // Handle incoming FFT data - no dependencies to avoid reconnection
  const handleFFTData = useCallback((frame: FFTFrame) => {
    frameCount.current++;
    
    // Calculate FPS
    const now = Date.now();
    if (now - lastTime.current >= 1000) {
      const currentFps = frameCount.current;
      setFps(currentFps);
      frameCount.current = 0;
      lastTime.current = now;
      
      // Debug: Log backend FPS vs our FPS
      console.log(`Frontend FPS: ${currentFps}, Backend FPS: ${frame.fps?.toFixed(1) || 'N/A'}`);
      
      // Update status using current FPS
      onStatusUpdateRef.current({
        fps: currentFps,
        peakFreq: frame.peak_frequency_hz || 0,
        peakAmplitude: frame.peak_magnitude_db || 0,
        dataRate: frame.data_size_bytes || 0
      });
    }

    // Render frequency spectrum (only when visible)
    if (showFrequencyRef.current && frequencyCanvasRef.current) {
      renderFrequencySpectrum(frequencyCanvasRef.current, frame);
    }

    // Skip spectrogram rendering for now to improve performance
    // if (showSpectrogramRef.current && spectrogramCanvasRef.current) {
    //   renderSpectrogram(spectrogramCanvasRef.current, frame);
    // }
  }, []); // Empty dependency array!

  // Connect/disconnect from data stream
  useEffect(() => {
    if (isConnected && isPlaying) {
      if (currentDevice) {
        console.log(`Connecting to device stream for device: ${currentDevice}`);
        apiClient.connectToDeviceStream(
          currentDevice,
          handleFFTData,
          (error) => {
            console.error('Device stream error:', error);
          }
        );
      } else {
        console.log('Connecting to general data stream...');
        apiClient.connectToStream(
          handleFFTData,
          (error) => {
            console.error('Stream error:', error);
          }
        );
      }
    } else {
      console.log('Disconnecting from data stream...');
      apiClient.disconnectFromStream();
    }

    return () => {
      apiClient.disconnectFromStream();
    };
  }, [isConnected, isPlaying, currentDevice, apiClient]);

  // Render frequency spectrum (optimized)
  const renderFrequencySpectrum = (canvas: HTMLCanvasElement, frame: FFTFrame) => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    
    // Clear canvas  
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, width, height);

    // Draw grid (less frequently for performance)
    drawGrid(ctx, width, height);

    // Decompress and draw spectrum data
    const fftData = decompressFFTData(frame.data_compressed);
    if (fftData && fftData.length > 0) {
      // Calculate frequency bins based on sample rate and FFT size
      const sampleRate = frame.sample_rate;
      const maxFreq = sampleRate / 2; // Nyquist frequency
      const freqStep = maxFreq / fftData.length;
      
      // Constants for display (similar to original headless_ultrasonic)
      const MAX_FREQ_KHZ = 100;
      const MIN_DB = -100;
      const MAX_DB = 0;
      const PADDING = 40;
      const PLOT_WIDTH = width - 2 * PADDING;
      const PLOT_HEIGHT = height - 2 * PADDING;
      
      // Find max frequency index to display (up to 100kHz)
      const maxFreqIndex = Math.min(fftData.length, Math.floor((MAX_FREQ_KHZ * 1000) / freqStep));

      // Draw spectrum line (optimized - less points for performance)
      ctx.strokeStyle = '#00ff88';
      ctx.lineWidth = 2;
      ctx.beginPath();

      const step = Math.max(1, Math.floor(maxFreqIndex / 800)); // Reduce points for performance
      let firstPoint = true;
      
      for (let i = 0; i < maxFreqIndex; i += step) {
        const freq = (i * freqStep) / 1000; // Convert to kHz
        const db = fftData[i];
        
        const x = PADDING + (freq / MAX_FREQ_KHZ) * PLOT_WIDTH;
        // Normalize dB value and flip Y axis
        const normalizedDb = Math.max(0, Math.min(1, (db - MIN_DB) / (MAX_DB - MIN_DB)));
        const y = PADDING + (1 - normalizedDb) * PLOT_HEIGHT;
        
        if (firstPoint) {
          ctx.moveTo(x, y);
          firstPoint = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      // Skip fill area for performance
      // Draw only peak frequency indicator
      if (frame.peak_frequency_hz > 0) {
        const peakFreqKHz = frame.peak_frequency_hz / 1000;
        if (peakFreqKHz <= MAX_FREQ_KHZ) {
          const peakX = PADDING + (peakFreqKHz / MAX_FREQ_KHZ) * PLOT_WIDTH;
          ctx.strokeStyle = '#ff4444';
          ctx.lineWidth = 1;
          ctx.setLineDash([5, 5]);
          ctx.beginPath();
          ctx.moveTo(peakX, PADDING);
          ctx.lineTo(peakX, PADDING + PLOT_HEIGHT);
          ctx.stroke();
          ctx.setLineDash([]);
          
          // Peak frequency label (less frequent updates)
          ctx.fillStyle = '#ffffff';
          ctx.font = '12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText(`${peakFreqKHz.toFixed(1)}kHz`, peakX, PADDING - 10);
        }
      }
    }

    // Draw labels (less frequently for performance) 
    drawFrequencyLabels(ctx, width, height);
  };

  // Render spectrogram (placeholder)
  const renderSpectrogram = (canvas: HTMLCanvasElement, frame: FFTFrame) => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    
    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);

    // Draw placeholder text
    ctx.fillStyle = '#666666';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Spectrogram View', width / 2, height / 2);
    ctx.fillText('(Coming Soon)', width / 2, height / 2 + 24);
  };

  // Draw grid helper (professional style)
  const drawGrid = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    const PADDING = 40;
    const PLOT_WIDTH = width - 2 * PADDING;
    const PLOT_HEIGHT = height - 2 * PADDING;
    
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    
    // Vertical grid lines (frequency)
    for (let i = 0; i <= 10; i++) {
      const x = PADDING + (i / 10) * PLOT_WIDTH;
      ctx.beginPath();
      ctx.moveTo(x, PADDING);
      ctx.lineTo(x, PADDING + PLOT_HEIGHT);
      ctx.stroke();
    }
    
    // Horizontal grid lines (amplitude)
    for (let i = 0; i <= 10; i++) {
      const y = PADDING + (i / 10) * PLOT_HEIGHT;
      ctx.beginPath();
      ctx.moveTo(PADDING, y);
      ctx.lineTo(PADDING + PLOT_WIDTH, y);
      ctx.stroke();
    }
  };

  // Draw frequency and amplitude labels
  const drawFrequencyLabels = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    const PADDING = 40;
    const PLOT_WIDTH = width - 2 * PADDING;
    const PLOT_HEIGHT = height - 2 * PADDING;
    const MAX_FREQ_KHZ = 100;
    const MIN_DB = -100;
    const MAX_DB = 0;
    
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.font = '12px Arial';
    
    // X-axis labels (frequency)
    ctx.textAlign = 'center';
    for (let i = 0; i <= 10; i++) {
      const x = PADDING + (i / 10) * PLOT_WIDTH;
      const freq = (i / 10) * MAX_FREQ_KHZ;
      ctx.fillText(`${freq.toFixed(0)}k`, x, height - 10);
    }
    
    // Y-axis labels (amplitude in dB)
    ctx.textAlign = 'right';
    for (let i = 0; i <= 10; i++) {
      const y = PADDING + (i / 10) * PLOT_HEIGHT;
      const db = MAX_DB - (i / 10) * (MAX_DB - MIN_DB);
      ctx.fillText(`${db.toFixed(0)}dB`, PADDING - 10, y + 4);
    }
  };

  const getDisplayHeight = () => {
    const totalViews = (showFrequency ? 1 : 0) + (showSpectrogram ? 1 : 0);
    if (totalViews === 0) return 0;
    return Math.floor((canvasSize.height - 16) / totalViews);
  };

  const displayHeight = getDisplayHeight();

  return (
    <div className="canvas-viewport" ref={containerRef}>
      {!isConnected && (
        <div className="viewport-overlay">
          <div className="overlay-message">
            <h3>Not Connected</h3>
            <p>Please connect to a backend server to view data</p>
          </div>
        </div>
      )}

      {isConnected && !isPlaying && !hasRunningDevice && (
        <div className="viewport-overlay">
          <div className="overlay-message">
            <h3>Device Not Ready</h3>
            <p>Please enable the device to get ready for streaming</p>
          </div>
        </div>
      )}

      {isConnected && !isPlaying && hasRunningDevice && (
        <div className="viewport-overlay">
          <div className="overlay-message">
            <h3>Ready</h3>
            <p>Click to begin visualization</p>
          </div>
        </div>
      )}

      {showFrequency && (
        <div className="canvas-container">
          <h4>Frequency Spectrum</h4>
          <canvas
            ref={frequencyCanvasRef}
            width={canvasSize.width}
            height={displayHeight}
            className="visualization-canvas"
          />
        </div>
      )}

      {showSpectrogram && (
        <div className="canvas-container">
          <h4>Spectrogram</h4>
          <canvas
            ref={spectrogramCanvasRef}
            width={canvasSize.width}
            height={displayHeight}
            className="visualization-canvas"
          />
        </div>
      )}
    </div>
  );
};