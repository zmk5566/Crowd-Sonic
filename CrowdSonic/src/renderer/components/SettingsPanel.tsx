import React, { useState } from 'react';
import './SettingsPanel.css';

interface SettingsPanelProps {
  showFrequency: boolean;
  showSpectrogram: boolean;
  targetFps: number;
  isConnected: boolean;
  isPlaying: boolean;
  onFrequencyToggle: (show: boolean) => void;
  onSpectrogramToggle: (show: boolean) => void;
  onFpsChange: (fps: number) => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  showFrequency,
  showSpectrogram,
  targetFps,
  isConnected,
  isPlaying,
  onFrequencyToggle,
  onSpectrogramToggle,
  onFpsChange,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className={`settings-panel ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Toggle Button - always visible on the left side */}
      <button 
        className="toggle-button"
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? "Expand Settings" : "Collapse Settings"}
      >
        <svg 
          width="16" 
          height="16" 
          viewBox="0 0 16 16" 
          fill="none"
          style={{ transform: isCollapsed ? "rotate(-90deg)" : "rotate(90deg)" }}
        >
          <path 
            d="M4 6L8 10L12 6"
            stroke="currentColor" 
            strokeWidth="1.5" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {/* Collapsible Content */}
      <div className="panel-content">
        {/* Display Options */}
        <div className="panel-section">
          <div className="section-title">Display</div>
        <div className="display-options">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showFrequency}
              onChange={(e) => onFrequencyToggle(e.target.checked)}
            />
            <span>Spectrum</span>
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

      {/* Settings */}
      <div className="panel-section">
        <div className="section-title">Settings</div>
        
        {isConnected && (
          <div className="settings-controls">
            <div className="setting-item">
              <label htmlFor="fps-slider">FPS: {targetFps}</label>
              <input
                id="fps-slider"
                type="range"
                min="5"
                max="60"
                step="5"
                value={targetFps}
                onChange={(e) => onFpsChange(parseInt(e.target.value))}
                disabled={isPlaying}
              />
              <div className="fps-presets">
                {[15, 30, 60].map(fps => (
                  <button
                    key={fps}
                    onClick={() => onFpsChange(fps)}
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
        </div>
      </div>
    </div>
  );
};