export interface Server {
  id: string;
  name: string;
  url: string;
  isDefault?: boolean; // 默认服务器不可删除
}

interface ServerStorage {
  servers: Server[];
  currentServerId: string | null;
}

const STORAGE_KEY = 'crowdsonic-servers';

// 默认服务器配置
const DEFAULT_SERVERS: Server[] = [
  {
    id: 'localhost-8380',
    name: 'Local Server',
    url: 'http://localhost:8380',
    isDefault: true
  },
  {
    id: 'local-ip-8380',
    name: 'Local IP',
    url: 'http://127.0.0.1:8380'
  }
];

class ServerStorageService {
  private getStorageData(): ServerStorage {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (data) {
        const parsed = JSON.parse(data) as ServerStorage;
        // 确保默认服务器始终存在
        const hasDefaultServer = parsed.servers.some(s => s.isDefault);
        if (!hasDefaultServer) {
          parsed.servers.unshift(DEFAULT_SERVERS[0]);
        }
        return parsed;
      }
    } catch (error) {
      console.error('Failed to load server data:', error);
    }
    
    // 返回默认配置
    return {
      servers: [...DEFAULT_SERVERS],
      currentServerId: DEFAULT_SERVERS[0].id
    };
  }

  private saveStorageData(data: ServerStorage): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      console.error('Failed to save server data:', error);
    }
  }

  // 获取所有服务器
  getServers(): Server[] {
    return this.getStorageData().servers;
  }

  // 获取当前选中的服务器ID
  getCurrentServerId(): string | null {
    return this.getStorageData().currentServerId;
  }

  // 获取当前选中的服务器
  getCurrentServer(): Server | null {
    const data = this.getStorageData();
    return data.servers.find(s => s.id === data.currentServerId) || null;
  }

  // 设置当前服务器
  setCurrentServer(serverId: string): void {
    const data = this.getStorageData();
    const server = data.servers.find(s => s.id === serverId);
    if (server) {
      data.currentServerId = serverId;
      this.saveStorageData(data);
    }
  }

  // 添加新服务器
  addServer(name: string, url: string): Server {
    const data = this.getStorageData();
    const id = `server-${Date.now()}`;
    const newServer: Server = { id, name, url };
    
    data.servers.push(newServer);
    this.saveStorageData(data);
    
    return newServer;
  }

  // 更新服务器
  updateServer(id: string, name: string, url: string): void {
    const data = this.getStorageData();
    const serverIndex = data.servers.findIndex(s => s.id === id);
    
    if (serverIndex !== -1) {
      // 不允许更新默认服务器的URL，但可以更新名称
      if (data.servers[serverIndex].isDefault) {
        data.servers[serverIndex].name = name;
      } else {
        data.servers[serverIndex].name = name;
        data.servers[serverIndex].url = url;
      }
      this.saveStorageData(data);
    }
  }

  // 删除服务器
  deleteServer(id: string): boolean {
    const data = this.getStorageData();
    const serverIndex = data.servers.findIndex(s => s.id === id);
    
    if (serverIndex === -1) return false;
    
    const server = data.servers[serverIndex];
    
    // 不允许删除默认服务器
    if (server.isDefault) {
      return false;
    }
    
    data.servers.splice(serverIndex, 1);
    
    // 如果删除的是当前服务器，切换到默认服务器
    if (data.currentServerId === id) {
      data.currentServerId = data.servers.find(s => s.isDefault)?.id || data.servers[0]?.id || null;
    }
    
    this.saveStorageData(data);
    return true;
  }

  // 根据URL查找服务器（用于兼容旧逻辑）
  getServerByUrl(url: string): Server | null {
    const servers = this.getServers();
    return servers.find(s => s.url === url) || null;
  }

  // 导入服务器（从旧系统迁移时使用）
  importServer(url: string): Server {
    let existingServer = this.getServerByUrl(url);
    if (existingServer) {
      return existingServer;
    }
    
    // 生成服务器名称
    let name = 'Custom Server';
    try {
      const urlObj = new URL(url);
      name = `${urlObj.hostname}:${urlObj.port || (urlObj.protocol === 'https:' ? '443' : '80')}`;
    } catch (error) {
      // 如果URL解析失败，使用原始URL作为名称
      name = url;
    }
    
    return this.addServer(name, url);
  }
}

export const serverStorageService = new ServerStorageService();