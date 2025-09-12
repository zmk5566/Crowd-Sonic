import React, { useState, useEffect } from 'react';
import { Server, serverStorageService } from '../services/serverStorage';
import './ServerManager.css';

interface ServerManagerProps {
  isOpen: boolean;
  onClose: () => void;
  onServerChange?: (serverId: string) => void;
}

export const ServerManager: React.FC<ServerManagerProps> = ({
  isOpen,
  onClose,
  onServerChange
}) => {
  const [servers, setServers] = useState<Server[]>([]);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [formData, setFormData] = useState({ name: '', url: '' });
  const [errors, setErrors] = useState({ name: '', url: '' });

  // 加载服务器列表
  useEffect(() => {
    if (isOpen) {
      loadServers();
    }
  }, [isOpen]);

  const loadServers = () => {
    const serverList = serverStorageService.getServers();
    setServers(serverList);
  };

  const validateForm = (): boolean => {
    const newErrors = { name: '', url: '' };
    let isValid = true;

    if (!formData.name.trim()) {
      newErrors.name = '服务器名称不能为空';
      isValid = false;
    }

    if (!formData.url.trim()) {
      newErrors.url = '服务器URL不能为空';
      isValid = false;
    } else {
      try {
        new URL(formData.url);
      } catch {
        newErrors.url = '请输入有效的URL格式';
        isValid = false;
      }
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleSave = () => {
    if (!validateForm()) return;

    try {
      if (isAddingNew) {
        const newServer = serverStorageService.addServer(formData.name.trim(), formData.url.trim());
        console.log('Added new server:', newServer);
      } else if (editingServer) {
        serverStorageService.updateServer(editingServer.id, formData.name.trim(), formData.url.trim());
        console.log('Updated server:', editingServer.id);
      }

      loadServers();
      resetForm();
    } catch (error) {
      console.error('Failed to save server:', error);
    }
  };

  const handleDelete = (server: Server) => {
    if (server.isDefault) {
      alert('默认服务器无法删除');
      return;
    }

    if (confirm(`确定要删除服务器 "${server.name}" 吗？`)) {
      const success = serverStorageService.deleteServer(server.id);
      if (success) {
        loadServers();
        console.log('Deleted server:', server.id);
      } else {
        alert('删除服务器失败');
      }
    }
  };

  const handleEdit = (server: Server) => {
    setEditingServer(server);
    setIsAddingNew(false);
    setFormData({ name: server.name, url: server.url });
    setErrors({ name: '', url: '' });
  };

  const handleAddNew = () => {
    setEditingServer(null);
    setIsAddingNew(true);
    setFormData({ name: '', url: 'http://' });
    setErrors({ name: '', url: '' });
  };

  const resetForm = () => {
    setEditingServer(null);
    setIsAddingNew(false);
    setFormData({ name: '', url: '' });
    setErrors({ name: '', url: '' });
  };

  const handleServerSelect = (server: Server) => {
    serverStorageService.setCurrentServer(server.id);
    if (onServerChange) {
      onServerChange(server.id);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="server-manager-overlay" onClick={onClose}>
      <div className="server-manager-modal" onClick={(e) => e.stopPropagation()}>
        <div className="server-manager-header">
          <h3>服务器管理</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="server-manager-content">
          {/* 服务器列表 */}
          <div className="server-list-section">
            <div className="section-header">
              <h4>服务器列表</h4>
              <button className="add-server-button" onClick={handleAddNew}>
                + 添加服务器
              </button>
            </div>

            <div className="server-list">
              {servers.map((server) => (
                <div key={server.id} className="server-item">
                  <div className="server-info">
                    <div className="server-name">
                      {server.name}
                      {server.isDefault && <span className="default-badge">默认</span>}
                    </div>
                    <div className="server-url">{server.url}</div>
                  </div>
                  
                  <div className="server-actions">
                    <button 
                      className="select-button"
                      onClick={() => handleServerSelect(server)}
                    >
                      选择
                    </button>
                    <button 
                      className="edit-button"
                      onClick={() => handleEdit(server)}
                    >
                      编辑
                    </button>
                    {!server.isDefault && (
                      <button 
                        className="delete-button"
                        onClick={() => handleDelete(server)}
                      >
                        删除
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 编辑表单 */}
          {(isAddingNew || editingServer) && (
            <div className="edit-form-section">
              <h4>{isAddingNew ? '添加新服务器' : '编辑服务器'}</h4>
              
              <div className="form-group">
                <label>服务器名称:</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如：本地服务器"
                />
                {errors.name && <span className="error-text">{errors.name}</span>}
              </div>

              <div className="form-group">
                <label>服务器URL:</label>
                <input
                  type="text"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder="例如：http://192.168.1.100:8380"
                  disabled={editingServer?.isDefault}
                />
                {errors.url && <span className="error-text">{errors.url}</span>}
                {editingServer?.isDefault && (
                  <span className="info-text">默认服务器的URL无法修改</span>
                )}
              </div>

              <div className="form-actions">
                <button className="save-button" onClick={handleSave}>
                  {isAddingNew ? '添加' : '保存'}
                </button>
                <button className="cancel-button" onClick={resetForm}>
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};