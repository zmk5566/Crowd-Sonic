/**
 * API Client for CrowdSonic
 * Handles communication with the Python FastAPI backend
 */

export interface FFTFrame {
  timestamp: number;
  sequence_id: number;
  sample_rate: number;
  fft_size: number;
  data_compressed: string;
  compression_method: string;
  data_size_bytes: number;
  original_size_bytes: number;
  peak_frequency_hz: number;
  peak_magnitude_db: number;
  spl_db: number;
  fps: number;
}

export interface SystemStatus {
  is_running: boolean;
  fps: number;
  frame_count: number;
  error_count: number;
  device_info: any;
}

export class APIClient {
  private baseUrl: string;
  private eventSource: EventSource | null = null;

  constructor(baseUrl: string = 'http://localhost:8380') {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
  }

  /**
   * Test connection to the backend
   */
  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/system/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      return response.ok;
    } catch (error) {
      console.error('Connection test failed:', error);
      return false;
    }
  }

  /**
   * Start audio capture (legacy - now uses system-wide stop/start)
   */
  async start(): Promise<void> {
    // Legacy API - just call stop all for now
    const response = await fetch(`${this.baseUrl}/api/system/stop-all`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to start capture: ${response.statusText}`);
    }
  }

  /**
   * Stop audio capture (legacy - now uses system-wide stop)
   */
  async stop(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/system/stop-all`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to stop capture: ${response.statusText}`);
    }
  }

  /**
   * Start specific device
   */
  async startDevice(deviceId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/devices/${deviceId}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to start device: ${response.statusText}`);
    }
  }

  /**
   * Stop specific device
   */
  async stopDevice(deviceId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/devices/${deviceId}/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to stop device: ${response.statusText}`);
    }
  }

  /**
   * Get system status
   */
  async getStatus(): Promise<SystemStatus> {
    const response = await fetch(`${this.baseUrl}/api/status`);
    
    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Connect to the real-time data stream (legacy - uses general stream)
   */
  connectToStream(onData: (frame: FFTFrame) => void, onError?: (error: Event) => void): void {
    // Close existing connection
    this.disconnectFromStream();

    try {
      this.eventSource = new EventSource(`${this.baseUrl}/api/stream`);

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Skip connection/heartbeat messages, only process FFT frames
          if (data.type === 'connected' || data.type === 'heartbeat') {
            return;
          }
          
          // Check if this looks like an FFT frame (has required properties)
          if (data.data_compressed && typeof data.peak_frequency_hz === 'number') {
            const frame: FFTFrame = data;
            onData(frame);
          }
        } catch (error) {
          console.error('Failed to parse stream data:', error, 'Raw data:', event.data);
        }
      };

      this.eventSource.onerror = (error) => {
        console.error('Stream connection error:', error);
        if (onError) {
          onError(error);
        }
      };

      this.eventSource.onopen = () => {
        console.log('Stream connection opened');
      };

    } catch (error) {
      console.error('Failed to connect to stream:', error);
      if (onError) {
        onError(error as Event);
      }
    }
  }

  /**
   * Connect to device-specific real-time data stream
   */
  connectToDeviceStream(deviceId: string, onData: (frame: FFTFrame) => void, onError?: (error: Event) => void): void {
    // Close existing connection
    this.disconnectFromStream();

    try {
      this.eventSource = new EventSource(`${this.baseUrl}/api/devices/${deviceId}/stream`);

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Skip connection/heartbeat messages, only process FFT frames
          if (data.type === 'connected' || data.type === 'heartbeat') {
            return;
          }
          
          // Check if this looks like an FFT frame (has required properties)
          if (data.data_compressed && typeof data.peak_frequency_hz === 'number') {
            const frame: FFTFrame = data;
            onData(frame);
          }
        } catch (error) {
          console.error('Failed to parse device stream data:', error, 'Raw data:', event.data);
        }
      };

      this.eventSource.onerror = (error) => {
        console.error('Device stream connection error:', error);
        if (onError) {
          onError(error);
        }
      };

      this.eventSource.onopen = () => {
        console.log(`Device stream connection opened for device: ${deviceId}`);
      };

    } catch (error) {
      console.error('Failed to connect to device stream:', error);
      if (onError) {
        onError(error as Event);
      }
    }
  }

  /**
   * Disconnect from the data stream
   */
  disconnectFromStream(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      console.log('Stream connection closed');
    }
  }

  /**
   * Update base URL for remote connections
   */
  updateBaseUrl(newBaseUrl: string): void {
    this.baseUrl = newBaseUrl.replace(/\/$/, '');
    // If there's an active stream, reconnect with new URL
    if (this.eventSource) {
      this.disconnectFromStream();
    }
  }

  /**
   * Get available devices
   */
  async getDevices(): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/api/system/devices`);
    
    if (!response.ok) {
      throw new Error(`Failed to get devices: ${response.statusText}`);
    }

    const data = await response.json();
    return data.devices || []; // Extract devices array from response
  }

  /**
   * Set active device - just start the selected device without stopping others
   * This is for cloud service where multiple devices can run simultaneously
   */
  async setDevice(deviceId: string): Promise<void> {
    try {
      // Just start the specific device - don't stop others (cloud service)
      const startResponse = await fetch(`${this.baseUrl}/api/devices/${deviceId}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!startResponse.ok) {
        throw new Error(`Failed to start device: ${startResponse.statusText}`);
      }
      
      console.log(`Device ${deviceId} started successfully`);
    } catch (error) {
      throw new Error(`Failed to set device: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Configure stream settings (legacy - disable adaptive FPS, etc.)
   */
  async configureStream(options: {
    enable_adaptive_fps?: boolean;
    enable_smart_skip?: boolean;
    target_fps?: number;
  }): Promise<void> {
    // Update filter settings
    if (typeof options.enable_adaptive_fps !== 'undefined' || 
        typeof options.enable_smart_skip !== 'undefined') {
      const filterResponse = await fetch(`${this.baseUrl}/api/config/filter`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          enable_adaptive_fps: options.enable_adaptive_fps ?? true,
          enable_smart_skip: options.enable_smart_skip ?? false,
        }),
      });

      if (!filterResponse.ok) {
        throw new Error(`Failed to configure filter: ${filterResponse.statusText}`);
      }
    }

    // Update FPS if specified
    if (options.target_fps) {
      const fpsResponse = await fetch(`${this.baseUrl}/api/config/fps`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_fps: options.target_fps,
        }),
      });

      if (!fpsResponse.ok) {
        throw new Error(`Failed to configure FPS: ${fpsResponse.statusText}`);
      }
    }
  }

  /**
   * Configure device-specific stream settings
   */
  async configureDeviceStream(deviceId: string, options: {
    enable_adaptive_fps?: boolean;
    enable_smart_skip?: boolean;
    target_fps?: number;
  }): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/devices/${deviceId}/config/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        enable_adaptive_fps: options.enable_adaptive_fps ?? false,
        enable_smart_skip: options.enable_smart_skip ?? false,
        target_fps: options.target_fps ?? 30,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to configure device stream: ${response.statusText}`);
    }
  }

  /**
   * Get device status
   */
  async getDeviceStatus(deviceId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/devices/${deviceId}/status`);
    
    if (!response.ok) {
      throw new Error(`Failed to get device status: ${response.statusText}`);
    }
    
    return await response.json();
  }
}