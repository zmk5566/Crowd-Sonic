#!/bin/bash
# CrowdSonic 核心更新脚本
# 用于正确更新编译后的headless_ultrasonic核心组件

set -e  # 出错时停止执行

echo "🔄 开始CrowdSonic核心更新流程..."
echo ""

# 检查是否在正确的目录
if [ ! -d "headless_ultrasonic" ] || [ ! -d "CrowdSonic" ]; then
    echo "❌ 错误：请在包含headless_ultrasonic和CrowdSonic目录的父目录下运行此脚本"
    echo "当前目录：$(pwd)"
    echo "应该在：Simple-UAC-Visualizer目录"
    exit 1
fi

# 1. 清理环境
echo "1️⃣ 清理运行环境..."
echo "   停止所有相关进程..."
pkill -f "headless_ultrasonic" 2>/dev/null || true
pkill -f "Electron" 2>/dev/null || true
echo "   清理端口占用..."
lsof -ti:8380 | xargs kill -9 2>/dev/null || true
echo "   清理PyInstaller缓存..."
rm -rf /var/folders/*/T/MEI* /tmp/MEI* 2>/dev/null || true
echo "   ✅ 环境清理完成"
echo ""

# 2. 重新编译headless_ultrasonic
echo "2️⃣ 重新编译headless_ultrasonic..."
cd headless_ultrasonic

# 清理旧的编译文件
echo "   清理旧的编译文件..."
rm -rf dist/ build/ *.spec 2>/dev/null || true

# 激活conda环境
echo "   激活conda环境..."
if ! source /opt/anaconda3/etc/profile.d/conda.sh; then
    echo "❌ 无法加载conda，请确认conda已正确安装"
    exit 1
fi

if ! conda activate audio-sync; then
    echo "❌ 无法激活audio-sync环境，请确认环境已创建"
    echo "创建环境：conda create -n audio-sync python=3.11 -y"
    exit 1
fi

# 编译
echo "   执行编译..."
if ! ./build.sh; then
    echo "❌ 编译失败，请检查错误信息"
    exit 1
fi

echo "   ✅ 编译完成"
echo ""

# 3. 验证编译结果
echo "3️⃣ 验证编译结果..."
if [ ! -f "dist/headless_ultrasonic/headless_ultrasonic" ]; then
    echo "❌ 编译产物不存在"
    exit 1
fi

COMPILE_TIME=$(ls -la dist/headless_ultrasonic/ | grep _internal | awk '{print $6, $7, $8}')
echo "   编译时间戳：$COMPILE_TIME"
echo "   ✅ 编译结果验证通过"
echo ""

# 4. 更新CrowdSonic中的版本
echo "4️⃣ 更新CrowdSonic核心..."
cd ../CrowdSonic

# 检查旧版本时间戳（如果存在）
if [ -d "resources/headless_ultrasonic" ]; then
    OLD_TIME=$(ls -la resources/headless_ultrasonic/ | grep _internal | awk '{print $6, $7, $8}' 2>/dev/null || echo "无法获取")
    echo "   旧版本时间戳：$OLD_TIME"
fi

# 完全删除旧版本
echo "   删除旧版本..."
rm -rf resources/headless_ultrasonic

# 创建resources目录（如果不存在）
mkdir -p resources

# 复制新版本
echo "   复制新编译版本..."
cp -r ../headless_ultrasonic/dist/headless_ultrasonic resources/

# 验证更新
NEW_TIME=$(ls -la resources/headless_ultrasonic/ | grep _internal | awk '{print $6, $7, $8}')
echo "   新版本时间戳：$NEW_TIME"

if [ "$COMPILE_TIME" = "$NEW_TIME" ]; then
    echo "   ✅ 版本更新验证通过"
else
    echo "   ⚠️ 警告：时间戳不匹配，可能存在问题"
fi
echo ""

# 5. 内容验证（可选）
echo "5️⃣ 验证关键修复..."
if grep -q "config_loader" resources/headless_ultrasonic/_internal/api/device_control.py 2>/dev/null; then
    echo "   ✅ 发现config_loader导入（修复已生效）"
else
    echo "   ⚠️ 未发现config_loader导入，可能需要检查"
fi

# 检查是否有旧的config导入
if grep -q "from config import" resources/headless_ultrasonic/_internal/api/device_control.py 2>/dev/null; then
    echo "   ⚠️ 警告：仍然发现旧的config导入"
else
    echo "   ✅ 未发现旧的config导入"
fi
echo ""

# 6. 重新构建CrowdSonic
echo "6️⃣ 重新构建CrowdSonic..."
if npm run build; then
    echo "   ✅ CrowdSonic构建成功"
else
    echo "   ❌ CrowdSonic构建失败"
    exit 1
fi
echo ""

echo "🎉 核心更新流程完成！"
echo ""
echo "📋 更新摘要："
echo "   编译版本时间戳：$COMPILE_TIME"
echo "   CrowdSonic版本时间戳：$NEW_TIME"
echo ""
echo "🚀 接下来可以运行："
echo "   npm start"
echo ""
echo "🔍 如果遇到问题，请检查："
echo "   1. 进程是否完全停止：ps aux | grep -E '(electron|headless_ultrasonic)'"
echo "   2. 端口是否被占用：lsof -i:8380"
echo "   3. 查看详细指南：cat CORE_UPDATE_GUIDE.md"