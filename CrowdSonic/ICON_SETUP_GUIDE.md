# CrowdSonic Icon Setup Guide

## 问题描述
Electron应用在macOS上编译后，图标在Dock和Finder中显示为空白或默认图标，而不是自定义的应用图标。

## 解决方案

### 1. 图标尺寸要求
- **推荐尺寸**: 512x512像素（而非1024x1024）
- **格式**: PNG格式，背景透明
- **位置**: `build/icon.png`

### 2. package.json配置
```json
{
  "build": {
    "mac": {
      "icon": "build/icons/mac/icon.icns",
      "extendInfo": {
        "CFBundleIconName": "icon",
        "CFBundleIconFile": "icon.icns"
      }
    }
  }
}
```

### 3. 生成图标脚本
```json
{
  "scripts": {
    "icon": "electron-icon-maker --input=build/icon.png --output=build"
  }
}
```

## 构建流程

1. **准备图标文件**
   ```bash
   # 如果图标尺寸过大，调整为512x512
   sips -z 512 512 build/icon.png --out build/icon_512.png
   mv build/icon_512.png build/icon.png
   ```

2. **生成多格式图标**
   ```bash
   npm run icon
   ```
   这会生成：
   - `build/icons/mac/icon.icns` (macOS)
   - `build/icons/win/icon.ico` (Windows)
   - `build/icons/png/` 各种尺寸的PNG文件

3. **编译应用**
   ```bash
   npm run build
   npm run dist
   ```

## macOS缓存清理

如果图标仍不显示，清理系统缓存：

```bash
# 清理图标服务缓存
sudo rm -rf /Library/Caches/com.apple.iconservices.store

# 清理Dock和图标服务缓存
sudo find /private/var/folders/ \( -name com.apple.dock.iconcache -or -name com.apple.iconservices \) -exec rm -rf {} \;

# 重启相关服务
killall Dock && killall Finder

# 强制刷新Applications目录
sudo touch /Applications/*
```

## 验证图标正确性

检查生成的Info.plist是否包含正确的图标配置：
```xml
<key>CFBundleIconFile</key>
<string>icon.icns</string>
<key>CFBundleIconName</key>
<string>icon</string>
```

## 依赖包

确保安装了以下开发依赖：
```bash
npm install --save-dev electron-icon-maker electron-builder
```

## 故障排除

1. **图标仍为空白**: 重启电脑进行完整的缓存清理
2. **图标模糊**: 确保原始PNG图片清晰且为512x512像素
3. **构建失败**: 检查`build/icon.png`文件是否存在且可访问

## 关键要点

- ✅ 使用512x512像素的PNG源文件
- ✅ 配置`extendInfo`明确指定图标文件名
- ✅ 清理macOS图标缓存
- ✅ 将图标文件放在正确的目录结构中

---
*最后更新: 2025-09-13*