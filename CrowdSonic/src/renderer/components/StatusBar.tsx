import React from 'react';
import './StatusBar.css';

interface StatusBarProps {
  isConnected: boolean;
  fps: number;
  peakFreq: number;
  peakAmplitude: number;
  dataRate: number;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  isConnected,
  fps,
  peakFreq,
  peakAmplitude,
  dataRate,
}) => {
  const formatFrequency = (freq: number): string => {
    if (freq >= 1000) {
      return `${(freq / 1000).toFixed(1)}kHz`;
    }
    return `${freq.toFixed(0)}Hz`;
  };

  const formatAmplitude = (amp: number): string => {
    return `${amp.toFixed(2)}dB`;
  };

  const formatDataRate = (rate: number): string => {
    if (rate >= 1000) {
      return `${(rate / 1000).toFixed(1)}k samples/s`;
    }
    return `${rate} samples/s`;
  };

  return (
    <div className="status-bar">
      <div className="status-section">
        <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></div>
        <span className="status-text">
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <div className="status-divider"></div>

      <div className="status-section">
        <span className="status-label">FPS:</span>
        <span className={`status-value ${fps > 0 ? 'active' : ''}`}>
          {fps}
        </span>
      </div>

      <div className="status-divider"></div>

      <div className="status-section">
        <span className="status-label">Peak:</span>
        <span className={`status-value ${peakFreq > 0 ? 'active' : ''}`}>
          {formatFrequency(peakFreq)}
        </span>
      </div>

      <div className="status-divider"></div>

      <div className="status-section">
        <span className="status-label">Level:</span>
        <span className={`status-value ${peakAmplitude > 0 ? 'active' : ''}`}>
          {formatAmplitude(peakAmplitude)}
        </span>
      </div>

      <div className="status-divider"></div>

      <div className="status-section">
        <span className="status-label">Rate:</span>
        <span className={`status-value ${dataRate > 0 ? 'active' : ''}`}>
          {formatDataRate(dataRate)}
        </span>
      </div>

      <div className="status-spacer"></div>

      <div className="status-section">
        <span className="status-text version">
          CrowdSonic v1.0.0
        </span>
      </div>
    </div>
  );
};