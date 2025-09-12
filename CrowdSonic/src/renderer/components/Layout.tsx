import React from 'react';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="layout">
      <div className="layout-header">
        <div className="app-title">
          <span className="app-logo">🎵</span>
          <span className="app-name">CrowdSonic</span>
          <span className="app-subtitle">Professional Ultrasonic Visualizer</span>
        </div>
      </div>
      
      <div className="layout-body">
        {children}
      </div>
    </div>
  );
};