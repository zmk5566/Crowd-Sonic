# CrowdSonic 核心更新指南

本指南记录了如何正确更新和集成编译后的 headless_ultrasonic 核心组件，以及避免常见的缓存问题。

## 🚨 重要警告：编译缓存陷阱

### 问题描述
在开发过程中发现，即使修复了源代码并重新编译，CrowdSonic 仍然可能使用**旧的编译缓存版本**，导致：
- 代码修复不生效
- 运行时错误持续存在
- 调试困惑（以为代码没修好）

### 根本原因
1. **PyInstaller编译缓存**：编译过程可能使用了旧的源文件缓存
2. **文件复制缓存**：CrowdSonic/resources 目录中的版本没有及时更新
3. **进程缓存**：旧的后端进程可能仍在运行

## 📋 正确的核心更新流程

### 1. 修改源代码
```bash
cd headless_ultrasonic
# 修改源文件...
vim api/device_control.py
```

### 2. 完全清理环境
```bash
# 停止所有相关进程
pkill -f "headless_ultrasonic"
pkill -f "Electron"
lsof -ti:8380 | xargs kill -9 2>/dev/null || true

# 清理PyInstaller缓存
rm -rf dist/ build/ *.spec
rm -rf /var/folders/*/T/MEI* /tmp/MEI* 2>/dev/null || true
```

### 3. 重新编译
```bash
cd headless_ultrasonic
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate audio-sync
./build.sh
```

### 4. 验证编译结果
```bash
# 检查编译时间戳
ls -la dist/headless_ultrasonic/

# 验证修复内容（以config_loader为例）
grep -r "config_loader" dist/headless_ultrasonic/_internal/api/device_control.py
```

### 5. 更新CrowdSonic中的版本
```bash
cd ../CrowdSonic

# ⚠️ 关键步骤：完全删除旧版本
rm -rf resources/headless_ultrasonic

# 复制新编译版本
cp -r ../headless_ultrasonic/dist/headless_ultrasonic resources/
```

### 6. 验证更新成功
```bash
# 检查CrowdSonic中版本的时间戳
ls -la resources/headless_ultrasonic/

# 验证修复内容
grep -r "config_loader" resources/headless_ultrasonic/_internal/api/device_control.py
```

### 7. 重新构建并测试
```bash
npm run build
npm start
```

## 🔍 问题排查检查清单

当遇到"修复后仍有问题"时，按以下顺序检查：

### A. 源文件检查
```bash
# 确认源文件确实已修改
cd headless_ultrasonic
grep -n "config_loader" api/device_control.py
```

### B. 编译版本检查
```bash
# 检查编译版本时间戳
ls -la dist/headless_ultrasonic/
# 应该是最近的时间

# 检查编译版本内容
grep -r "config_loader" dist/headless_ultrasonic/_internal/api/device_control.py
# 应该包含修复内容
```

### C. CrowdSonic版本检查
```bash
cd ../CrowdSonic
# 检查CrowdSonic中版本时间戳
ls -la resources/headless_ultrasonic/
# 应该与编译版本时间戳一致

# 检查CrowdSonic中版本内容
grep -r "config_loader" resources/headless_ultrasonic/_internal/api/device_control.py
# 应该包含修复内容
```

### D. 运行时检查
```bash
# 确认没有旧进程
ps aux | grep -E "(electron|headless_ultrasonic)" | grep -v grep

# 确认端口未被占用
lsof -i:8380
```

## 📝 实际案例记录

### 问题场景
修复了 `api/device_control.py` 中的 `from config import Config` → `from config_loader import Config`，但运行时仍报错：
```
No module named 'config'
```

### 调试发现
1. 源文件已正确修改
2. 重新编译了（`./build.sh` 成功）
3. 但CrowdSonic中的版本时间戳仍是旧的：
   - 旧版本：22:05
   - 新版本：22:36
4. 检查文件内容发现旧版本仍包含 `from config import Config`

### 解决方案
使用完全删除+重新复制的方式更新：
```bash
rm -rf resources/headless_ultrasonic
cp -r ../headless_ultrasonic/dist/headless_ultrasonic resources/
```

## 🛠️ 自动化脚本建议

创建一个自动更新脚本 `update_core.sh`：

```bash
#!/bin/bash
set -e

echo "🔄 开始核心更新流程..."

# 1. 清理环境
echo "1. 清理环境..."
pkill -f "headless_ultrasonic" 2>/dev/null || true
pkill -f "Electron" 2>/dev/null || true
lsof -ti:8380 | xargs kill -9 2>/dev/null || true

# 2. 重新编译
echo "2. 重新编译..."
cd headless_ultrasonic
rm -rf dist/ build/ *.spec
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate audio-sync
./build.sh

# 3. 更新CrowdSonic
echo "3. 更新CrowdSonic..."
cd ../CrowdSonic
rm -rf resources/headless_ultrasonic
cp -r ../headless_ultrasonic/dist/headless_ultrasonic resources/

# 4. 验证
echo "4. 验证更新..."
TIMESTAMP=$(ls -la resources/headless_ultrasonic/ | grep _internal | awk '{print $6, $7, $8}')
echo "✅ 新版本时间戳: $TIMESTAMP"

echo "🎉 核心更新完成！"
echo "💡 现在可以运行: npm run build && npm start"
```

## 🎯 关键要点总结

1. **永远完全删除旧版本**：不要依赖文件覆盖
2. **验证时间戳**：确保版本确实是最新的
3. **验证内容**：grep检查关键修复是否真的存在
4. **清理进程**：避免端口冲突和缓存问题
5. **系统性检查**：从源文件→编译版本→CrowdSonic版本→运行时，逐步验证

## 🔗 相关文件路径

- 源文件：`headless_ultrasonic/api/device_control.py`
- 编译版本：`headless_ultrasonic/dist/headless_ultrasonic/_internal/api/device_control.py`  
- CrowdSonic版本：`CrowdSonic/resources/headless_ultrasonic/_internal/api/device_control.py`
- 构建脚本：`headless_ultrasonic/build.sh`
- Electron主进程：`CrowdSonic/src/main/main.ts`

---

📅 **创建时间**：2025-09-12 22:36  
🐛 **触发原因**：config模块导入错误修复后仍然报错  
✅ **解决状态**：已解决，核心更新流程已建立  