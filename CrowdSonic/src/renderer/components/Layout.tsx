import React from 'react';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="layout">
      <div className="layout-header">
        {/* Empty draggable area for window movement */}
      </div>
      
      <div className="layout-body">
        {children}
      </div>
    </div>
  );
};