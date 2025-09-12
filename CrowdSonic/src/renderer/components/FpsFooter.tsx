import React from 'react';
import './FpsFooter.css';

interface FpsFooterProps {
  targetFps: number;
  isConnected: boolean;
  isPlaying: boolean;
  onFpsChange: (fps: number) => void;
}

export const FpsFooter: React.FC<FpsFooterProps> = ({
  targetFps,
  isConnected,
  isPlaying,
  onFpsChange,
}) => {
  if (!isConnected) return null;

  return (
    <div className="fps-footer">
      <div className="fps-controls">
        <span className="fps-label">FPS: {targetFps}</span>
        
        <input
          type="range"
          min="5"
          max="60"
          step="5"
          value={targetFps}
          onChange={(e) => onFpsChange(parseInt(e.target.value))}
          disabled={isPlaying}
          className="fps-slider"
        />
        
        <div className="fps-presets">
          {[15, 30, 60].map(fps => (
            <button
              key={fps}
              onClick={() => onFpsChange(fps)}
              disabled={isPlaying}
              className={`fps-preset ${targetFps === fps ? 'active' : ''}`}
            >
              {fps}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};