import React, { useRef, useEffect, useState, useCallback, ChangeEvent } from 'react';
import { APIClient, FFTFrame } from '../services/api';
import * as pako from 'pako';
import './CanvasViewport.css';

// Visualization settings for each chart
interface VisualizationSettings {
  minFreqKHz: number;
  maxFreqKHz: number;
}

// Settings panel component for frequency range - defined outside to prevent recreation
const FrequencySettingsPanel: React.FC<{
  isOpen: boolean;
  settings: VisualizationSettings;
  onSettingsChange: (settings: VisualizationSettings) => void;
  onClose: () => void;
  title: string;
}> = ({ isOpen, settings, onSettingsChange, onClose, title }) => {
  // Use a ref to track if we've initialized this panel's values
  const initializedRef = useRef(false);
  const [tempSettings, setTempSettings] = useState(() => {
    // Initialize with current settings only on first render
    return { ...settings };
  });
  const [error, setError] = useState('');
  
  // Debug: Monitor tempSettings changes
  useEffect(() => {
    console.log('🟠 TempSettings changed in', title, ':', tempSettings);
  }, [tempSettings, title]);

  // Only initialize once when panel first opens, ignore all other updates
  useEffect(() => {
    console.log('🔍 useEffect triggered for', title, '- isOpen:', isOpen, 'initialized:', initializedRef.current);
    if (isOpen && !initializedRef.current) {
      // Capture the current settings at the moment of opening
      console.log('🟢 Initializing panel settings:', settings, 'for', title);
      setTempSettings({ ...settings });
      setError('');
      initializedRef.current = true;
      console.log('✅ Panel initialized for', title, 'initialized flag now:', initializedRef.current);
    }
    // Deliberately NO dependency on settings - we want to ignore external changes
  }, [isOpen, title]);
  
  // Reset initialization flag when panel closes
  useEffect(() => {
    if (!isOpen) {
      initializedRef.current = false;
    }
  }, [isOpen]);

  // Store original settings when panel opens for cancel functionality
  const originalSettingsRef = useRef(settings);
  
  // Update original settings reference when panel opens
  useEffect(() => {
    if (isOpen && !initializedRef.current) {
      originalSettingsRef.current = { ...settings };
    }
  }, [isOpen, settings]);

  const handleMinFreqChange = (e: ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    console.log('🟡 User typing min freq:', inputValue, 'in', title);
    // Allow empty string for typing
    if (inputValue === '') {
      setTempSettings({ ...tempSettings, minFreqKHz: 0 });
      return;
    }
    
    const value = parseFloat(inputValue);
    if (!isNaN(value) && value >= 0 && value <= 200) {
      console.log('🟡 Setting min freq to:', value, 'in', title);
      setTempSettings({ ...tempSettings, minFreqKHz: value });
      if (value >= tempSettings.maxFreqKHz) {
        setError('Minimum frequency must be less than maximum frequency');
      } else {
        setError('');
      }
    }
  };

  const handleMaxFreqChange = (e: ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    console.log('🟡 User typing max freq:', inputValue, 'in', title);
    // Allow empty string for typing
    if (inputValue === '') {
      setTempSettings({ ...tempSettings, maxFreqKHz: 200 });
      return;
    }
    
    const value = parseFloat(inputValue);
    if (!isNaN(value) && value >= 0 && value <= 200) {
      console.log('🟡 Setting max freq to:', value, 'in', title);
      setTempSettings({ ...tempSettings, maxFreqKHz: value });
      if (value <= tempSettings.minFreqKHz) {
        setError('Maximum frequency must be greater than minimum frequency');
      } else {
        setError('');
      }
    }
  };

  const handleApply = () => {
    if (tempSettings.minFreqKHz < tempSettings.maxFreqKHz) {
      console.log('🟢 Applying settings:', tempSettings, 'for', title);
      onSettingsChange(tempSettings);
      initializedRef.current = false; // Allow re-initialization next time
      onClose();
    }
  };

  const handleCancel = () => {
    // Reset to the original settings that were captured when panel opened
    setTempSettings({ ...originalSettingsRef.current });
    setError('');
    initializedRef.current = false; // Allow re-initialization next time
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'absolute',
      top: '40px',
      right: '10px',
      background: 'rgba(26, 26, 46, 0.95)',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      borderRadius: '8px',
      padding: '15px',
      zIndex: 100,
      minWidth: '250px',
      backdropFilter: 'blur(8px)'
    }}>
      <h5 style={{ margin: '0 0 10px 0', color: '#fff', fontSize: '14px' }}>{title} Settings</h5>
      
      <div style={{ marginBottom: '10px' }}>
        <label style={{ display: 'block', color: '#aaa', fontSize: '12px', marginBottom: '4px' }}>
          Min Frequency (kHz)
        </label>
        <input
          type="number"
          min="0"
          max="200"
          step="10"
          value={tempSettings.minFreqKHz}
          onChange={handleMinFreqChange}
          style={{
            width: '100%',
            padding: '4px 8px',
            background: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '4px',
            color: '#fff'
          }}
        />
      </div>
      
      <div style={{ marginBottom: '10px' }}>
        <label style={{ display: 'block', color: '#aaa', fontSize: '12px', marginBottom: '4px' }}>
          Max Frequency (kHz)
        </label>
        <input
          type="number"
          min="0"
          max="200"
          step="10"
          value={tempSettings.maxFreqKHz}
          onChange={handleMaxFreqChange}
          style={{
            width: '100%',
            padding: '4px 8px',
            background: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '4px',
            color: '#fff'
          }}
        />
      </div>
      
      {error && (
        <div style={{ color: '#ff4444', fontSize: '12px', marginBottom: '10px' }}>{error}</div>
      )}
      
      <div style={{ display: 'flex', gap: '10px' }}>
        <button
          onClick={handleApply}
          disabled={!!error || tempSettings.minFreqKHz >= tempSettings.maxFreqKHz}
          style={{
            flex: 1,
            padding: '6px',
            background: error || tempSettings.minFreqKHz >= tempSettings.maxFreqKHz ? '#444' : '#00ff88',
            color: error || tempSettings.minFreqKHz >= tempSettings.maxFreqKHz ? '#888' : '#000',
            border: 'none',
            borderRadius: '4px',
            cursor: error || tempSettings.minFreqKHz >= tempSettings.maxFreqKHz ? 'not-allowed' : 'pointer'
          }}
        >
          Apply
        </button>
        <button
          onClick={handleCancel}
          style={{
            flex: 1,
            padding: '6px',
            background: 'rgba(255, 255, 255, 0.1)',
            color: '#fff',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

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
  const canvasContainerRef = useRef<HTMLDivElement>(null);

  // Performance tracking
  const [fps, setFps] = useState(0);
  const frameCount = useRef(0);
  const lastTime = useRef(Date.now());

  // Canvas dimensions
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 400 });
  
  // Visualization settings for each chart
  const [frequencySettings, setFrequencySettings] = useState<VisualizationSettings>({
    minFreqKHz: 0,
    maxFreqKHz: 200
  });
  
  const [spectrogramSettings, setSpectrogramSettings] = useState<VisualizationSettings>({
    minFreqKHz: 0,
    maxFreqKHz: 200
  });
  
  // Debug: Track when settings change
  useEffect(() => {
    console.log('🔴 FrequencySettings changed:', frequencySettings);
    console.trace('FrequencySettings change stack trace');
  }, [frequencySettings]);
  
  useEffect(() => {
    console.log('🔴 SpectrogramSettings changed:', spectrogramSettings);
    console.trace('SpectrogramSettings change stack trace');
  }, [spectrogramSettings]);
  
  // Settings panel visibility
  const [showFrequencySettings, setShowFrequencySettings] = useState(false);
  const [showSpectrogramSettings, setShowSpectrogramSettings] = useState(false);

  // Waterfall spectrogram state - using useRef to avoid re-renders
  const waterfallDataRef = useRef<number[][]>([]);
  const [waterfallHeight] = useState(200); // Number of time slices to keep
  const waterfallFreqBinsRef = useRef(0);

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
    // Use canvasContainerRef for more accurate sizing
    const canvasContainer = canvasContainerRef.current;
    if (!canvasContainer) return;
    
    const rect = canvasContainer.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(canvasContainer);
    
    // Get border values (we removed padding, but container still has border)
    const borderLeft = parseFloat(computedStyle.borderLeftWidth);
    const borderRight = parseFloat(computedStyle.borderRightWidth);
    const borderTop = parseFloat(computedStyle.borderTopWidth);
    const borderBottom = parseFloat(computedStyle.borderBottomWidth);
    
    // Canvas fills the entire container minus only the container borders
    const availableWidth = rect.width - borderLeft - borderRight;
    const availableHeight = rect.height - borderTop - borderBottom;
    
    const width = Math.max(200, Math.floor(availableWidth));
    const height = Math.max(150, Math.floor(availableHeight));
    
    // Debug logging to help diagnose canvas sizing
    console.log('Canvas sizing debug:', {
      containerRect: { width: rect.width, height: rect.height },
      borders: { top: borderTop, bottom: borderBottom, left: borderLeft, right: borderRight },
      availableSize: { width: availableWidth, height: availableHeight },
      finalCanvasSize: { width, height }
    });
    
    setCanvasSize({ width, height });
  }, []);

  useEffect(() => {
    // Initial size calculation
    const timer = setTimeout(updateCanvasSize, 100); // Allow DOM to settle
    
    let resizeObserver: ResizeObserver | null = null;
    let resizeTimeout: NodeJS.Timeout;
    
    // Use ResizeObserver for more accurate size detection
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver((entries) => {
        // Debounce resize calls to avoid excessive updates
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(updateCanvasSize, 16);
      });
      
      // Observe the container when it's available
      const observeContainer = () => {
        if (canvasContainerRef.current && resizeObserver) {
          resizeObserver.observe(canvasContainerRef.current);
        }
      };
      
      observeContainer();
    }
    
    // Fallback to window resize for older browsers or as backup
    window.addEventListener('resize', updateCanvasSize);
    
    return () => {
      clearTimeout(timer);
      clearTimeout(resizeTimeout);
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
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

    // Render spectrogram waterfall
    if (showSpectrogramRef.current && spectrogramCanvasRef.current) {
      renderSpectrogram(spectrogramCanvasRef.current, frame);
    }
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
      
      // Constants for display (use dynamic frequency settings)
      const MAX_FREQ_KHZ = frequencySettings.maxFreqKHz;
      const MIN_FREQ_KHZ = frequencySettings.minFreqKHz;
      const MIN_DB = -100;
      const MAX_DB = 0;
      const PADDING = 40;
      const PLOT_WIDTH = width - 2 * PADDING;
      const PLOT_HEIGHT = height - 2 * PADDING;
      
      // Find frequency indices to display based on settings
      const minFreqIndex = Math.max(0, Math.floor((MIN_FREQ_KHZ * 1000) / freqStep));
      const maxFreqIndex = Math.min(fftData.length, Math.floor((MAX_FREQ_KHZ * 1000) / freqStep));

      // Draw spectrum line (optimized - less points for performance)
      ctx.strokeStyle = '#00ff88';
      ctx.lineWidth = 2;
      ctx.beginPath();

      const step = Math.max(1, Math.floor((maxFreqIndex - minFreqIndex) / 800)); // Reduce points for performance
      let firstPoint = true;
      
      for (let i = minFreqIndex; i < maxFreqIndex; i += step) {
        const freq = (i * freqStep) / 1000; // Convert to kHz
        const db = fftData[i];
        
        const x = PADDING + ((freq - MIN_FREQ_KHZ) / (MAX_FREQ_KHZ - MIN_FREQ_KHZ)) * PLOT_WIDTH;
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
        if (peakFreqKHz >= MIN_FREQ_KHZ && peakFreqKHz <= MAX_FREQ_KHZ) {
          const peakX = PADDING + ((peakFreqKHz - MIN_FREQ_KHZ) / (MAX_FREQ_KHZ - MIN_FREQ_KHZ)) * PLOT_WIDTH;
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

      // Draw labels (less frequently for performance) 
      drawFrequencyLabels(ctx, width, height, MIN_FREQ_KHZ, MAX_FREQ_KHZ);
    }
  };

  // Render spectrogram waterfall
  const renderSpectrogram = (canvas: HTMLCanvasElement, frame: FFTFrame) => {
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }

    const { width, height } = canvas;
    
    // Decompress FFT data
    const fftData = decompressFFTData(frame.data_compressed);
    if (!fftData || fftData.length === 0) {
      return;
    }

    // Calculate frequency parameters
    const sampleRate = frame.sample_rate;
    const maxFreq = sampleRate / 2; // Nyquist frequency
    const freqStep = maxFreq / fftData.length;
    const MAX_FREQ_KHZ = spectrogramSettings.maxFreqKHz;
    const MIN_FREQ_KHZ = spectrogramSettings.minFreqKHz;
    const minFreqIndex = Math.max(0, Math.floor((MIN_FREQ_KHZ * 1000) / freqStep));
    const maxFreqIndex = Math.min(fftData.length, Math.floor((MAX_FREQ_KHZ * 1000) / freqStep));
    
    // Initialize or resize waterfall data if needed
    const freqBinCount = maxFreqIndex - minFreqIndex;
    if (waterfallDataRef.current.length === 0 || waterfallFreqBinsRef.current !== freqBinCount) {
      waterfallDataRef.current = Array(waterfallHeight).fill(null).map(() => 
        Array(freqBinCount).fill(-100) // Initialize with -100dB
      );
      waterfallFreqBinsRef.current = freqBinCount;
      return; // Skip this frame while initializing
    }

    // Update waterfall data: scroll up and add new data at bottom
    // Move old data up
    for (let i = 1; i < waterfallHeight; i++) {
      waterfallDataRef.current[i - 1] = waterfallDataRef.current[i];
    }
    // Add new data at the bottom (slice within the frequency range)
    waterfallDataRef.current[waterfallHeight - 1] = Array.from(fftData.slice(minFreqIndex, maxFreqIndex));

    // Constants for rendering
    const PADDING = 40;
    const PLOT_WIDTH = width - 2 * PADDING;
    const PLOT_HEIGHT = height - 2 * PADDING;
    const MIN_DB = -100;
    const MAX_DB = 0;

    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);

    // Create ImageData for efficient pixel manipulation
    const imageData = ctx.createImageData(PLOT_WIDTH, PLOT_HEIGHT);
    const pixels = imageData.data;

    // Render waterfall as pixels
    for (let y = 0; y < PLOT_HEIGHT; y++) {
      const timeIndex = Math.floor((y / PLOT_HEIGHT) * waterfallHeight);
      if (timeIndex >= 0 && timeIndex < waterfallDataRef.current.length) {
        for (let x = 0; x < PLOT_WIDTH; x++) {
          const freqIndex = Math.floor((x / PLOT_WIDTH) * freqBinCount);
          if (freqIndex >= 0 && freqIndex < waterfallDataRef.current[timeIndex].length) {
            const dbValue = waterfallDataRef.current[timeIndex][freqIndex];
            
            // Normalize dB value to 0-1 range
            const normalizedValue = Math.max(0, Math.min(1, (dbValue - MIN_DB) / (MAX_DB - MIN_DB)));
            
            // Apply viridis-like colormap
            const [r, g, b] = viridisColormap(normalizedValue);
            
            // Set pixel values
            const pixelIndex = (y * PLOT_WIDTH + x) * 4;
            pixels[pixelIndex] = r;     // Red
            pixels[pixelIndex + 1] = g; // Green
            pixels[pixelIndex + 2] = b; // Blue
            pixels[pixelIndex + 3] = 255; // Alpha
          }
        }
      }
    }

    // Draw the image data
    ctx.putImageData(imageData, PADDING, PADDING);

    // Draw frequency and time labels
    drawSpectrogramLabels(ctx, width, height, MIN_FREQ_KHZ, MAX_FREQ_KHZ);
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
  const drawFrequencyLabels = (ctx: CanvasRenderingContext2D, width: number, height: number, minFreqKHz: number, maxFreqKHz: number) => {
    const PADDING = 40;
    const PLOT_WIDTH = width - 2 * PADDING;
    const PLOT_HEIGHT = height - 2 * PADDING;
    const MIN_DB = -100;
    const MAX_DB = 0;
    
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.font = '12px Arial';
    
    // X-axis labels (frequency)
    ctx.textAlign = 'center';
    for (let i = 0; i <= 10; i++) {
      const x = PADDING + (i / 10) * PLOT_WIDTH;
      const freq = minFreqKHz + (i / 10) * (maxFreqKHz - minFreqKHz);
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

  // Draw spectrogram labels (frequency on X-axis, time on Y-axis)
  const drawSpectrogramLabels = (ctx: CanvasRenderingContext2D, width: number, height: number, minFreqKhz: number, maxFreqKhz: number) => {
    const PADDING = 40;
    const PLOT_WIDTH = width - 2 * PADDING;
    const PLOT_HEIGHT = height - 2 * PADDING;
    
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.font = '12px Arial';
    
    // X-axis labels (frequency)
    ctx.textAlign = 'center';
    for (let i = 0; i <= 10; i++) {
      const x = PADDING + (i / 10) * PLOT_WIDTH;
      const freq = minFreqKhz + (i / 10) * (maxFreqKhz - minFreqKhz);
      ctx.fillText(`${freq.toFixed(0)}k`, x, height - 10);
    }
    
    // Y-axis labels (time - newer at bottom, older at top)
    ctx.textAlign = 'right';
    ctx.fillText('New', PADDING - 10, PADDING + PLOT_HEIGHT - 5);
    ctx.fillText('Old', PADDING - 10, PADDING + 15);
  };

  // Viridis-like colormap function (simplified)
  const viridisColormap = (value: number): [number, number, number] => {
    // Clamp value to 0-1 range
    const t = Math.max(0, Math.min(1, value));
    
    // Simplified viridis approximation
    let r, g, b;
    
    if (t < 0.25) {
      const local_t = t / 0.25;
      r = Math.floor(68 + local_t * (59 - 68));
      g = Math.floor(1 + local_t * (82 - 1));
      b = Math.floor(84 + local_t * (140 - 84));
    } else if (t < 0.5) {
      const local_t = (t - 0.25) / 0.25;
      r = Math.floor(59 + local_t * (33 - 59));
      g = Math.floor(82 + local_t * (144 - 82));
      b = Math.floor(140 + local_t * (140 - 140));
    } else if (t < 0.75) {
      const local_t = (t - 0.5) / 0.25;
      r = Math.floor(33 + local_t * (94 - 33));
      g = Math.floor(144 + local_t * (201 - 144));
      b = Math.floor(140 + local_t * (98 - 140));
    } else {
      const local_t = (t - 0.75) / 0.25;
      r = Math.floor(94 + local_t * (253 - 94));
      g = Math.floor(201 + local_t * (231 - 201));
      b = Math.floor(98 + local_t * (37 - 98));
    }
    
    return [r, g, b];
  };


  // Canvas now fills the entire container, so use the full calculated height
  const displayHeight = canvasSize.height;

  // Debug: Monitor component render
  console.log('🚀 CanvasViewport render', { 
    showFrequency, 
    showSpectrogram, 
    isConnected, 
    isPlaying, 
    hasRunningDevice, 
    frequencySettings,
    spectrogramSettings 
  });

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
        <div className="canvas-container" ref={canvasContainerRef} style={{ position: 'relative' }}>
          <canvas
            ref={frequencyCanvasRef}
            width={canvasSize.width}
            height={displayHeight}
            className="visualization-canvas"
          />
          <div className="canvas-title-overlay">
            <h4>Frequency Spectrum</h4>
          </div>
          
          {/* Settings icon button */}
          <button
            onClick={() => setShowFrequencySettings(!showFrequencySettings)}
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '4px',
              padding: '6px',
              cursor: 'pointer',
              width: '30px',
              height: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10
            }}
            title="Settings"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M8 1C7.45 1 7 1.45 7 2V2.07C6.38 2.18 5.79 2.38 5.26 2.68L5.2 2.62C4.82 2.24 4.18 2.24 3.8 2.62L3.08 3.34C2.7 3.72 2.7 4.36 3.08 4.74L3.14 4.8C2.84 5.33 2.64 5.92 2.53 6.54H2.46C1.91 6.54 1.46 6.99 1.46 7.54V8.46C1.46 9.01 1.91 9.46 2.46 9.46H2.53C2.64 10.08 2.84 10.67 3.14 11.2L3.08 11.26C2.7 11.64 2.7 12.28 3.08 12.66L3.8 13.38C4.18 13.76 4.82 13.76 5.2 13.38L5.26 13.32C5.79 13.62 6.38 13.82 7 13.93V14C7 14.55 7.45 15 8 15S9 14.55 9 14V13.93C9.62 13.82 10.21 13.62 10.74 13.32L10.8 13.38C11.18 13.76 11.82 13.76 12.2 13.38L12.92 12.66C13.3 12.28 13.3 11.64 12.92 11.26L12.86 11.2C13.16 10.67 13.36 10.08 13.47 9.46H13.54C14.09 9.46 14.54 9.01 14.54 8.46V7.54C14.54 6.99 14.09 6.54 13.54 6.54H13.47C13.36 5.92 13.16 5.33 12.86 4.8L12.92 4.74C13.3 4.36 13.3 3.72 12.92 3.34L12.2 2.62C11.82 2.24 11.18 2.24 10.8 2.62L10.74 2.68C10.21 2.38 9.62 2.18 9 2.07V2C9 1.45 8.55 1 8 1ZM8 5.5C9.38 5.5 10.5 6.62 10.5 8S9.38 10.5 8 10.5S5.5 9.38 5.5 8S6.62 5.5 8 5.5Z"
                fill="white"
              />
            </svg>
          </button>
          
          {/* Settings panel */}
          <FrequencySettingsPanel
            isOpen={showFrequencySettings}
            settings={frequencySettings}
            onSettingsChange={setFrequencySettings}
            onClose={() => setShowFrequencySettings(false)}
            title="Frequency Spectrum"
          />
        </div>
      )}

      {showSpectrogram && (
        <div className="canvas-container" ref={!showFrequency ? canvasContainerRef : undefined} style={{ position: 'relative' }}>
          <canvas
            ref={spectrogramCanvasRef}
            width={canvasSize.width}
            height={displayHeight}
            className="visualization-canvas"
          />
          <div className="canvas-title-overlay">
            <h4>Spectrogram Waterfall</h4>
          </div>
          
          {/* Settings icon button */}
          <button
            onClick={() => setShowSpectrogramSettings(!showSpectrogramSettings)}
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '4px',
              padding: '6px',
              cursor: 'pointer',
              width: '30px',
              height: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10
            }}
            title="Settings"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M8 1C7.45 1 7 1.45 7 2V2.07C6.38 2.18 5.79 2.38 5.26 2.68L5.2 2.62C4.82 2.24 4.18 2.24 3.8 2.62L3.08 3.34C2.7 3.72 2.7 4.36 3.08 4.74L3.14 4.8C2.84 5.33 2.64 5.92 2.53 6.54H2.46C1.91 6.54 1.46 6.99 1.46 7.54V8.46C1.46 9.01 1.91 9.46 2.46 9.46H2.53C2.64 10.08 2.84 10.67 3.14 11.2L3.08 11.26C2.7 11.64 2.7 12.28 3.08 12.66L3.8 13.38C4.18 13.76 4.82 13.76 5.2 13.38L5.26 13.32C5.79 13.62 6.38 13.82 7 13.93V14C7 14.55 7.45 15 8 15S9 14.55 9 14V13.93C9.62 13.82 10.21 13.62 10.74 13.32L10.8 13.38C11.18 13.76 11.82 13.76 12.2 13.38L12.92 12.66C13.3 12.28 13.3 11.64 12.92 11.26L12.86 11.2C13.16 10.67 13.36 10.08 13.47 9.46H13.54C14.09 9.46 14.54 9.01 14.54 8.46V7.54C14.54 6.99 14.09 6.54 13.54 6.54H13.47C13.36 5.92 13.16 5.33 12.86 4.8L12.92 4.74C13.3 4.36 13.3 3.72 12.92 3.34L12.2 2.62C11.82 2.24 11.18 2.24 10.8 2.62L10.74 2.68C10.21 2.38 9.62 2.18 9 2.07V2C9 1.45 8.55 1 8 1ZM8 5.5C9.38 5.5 10.5 6.62 10.5 8S9.38 10.5 8 10.5S5.5 9.38 5.5 8S6.62 5.5 8 5.5Z"
                fill="white"
              />
            </svg>
          </button>
          
          {/* Settings panel */}
          <FrequencySettingsPanel
            isOpen={showSpectrogramSettings}
            settings={spectrogramSettings}
            onSettingsChange={setSpectrogramSettings}
            onClose={() => setShowSpectrogramSettings(false)}
            title="Spectrogram Waterfall"
          />
        </div>
      )}
    </div>
  );
};
