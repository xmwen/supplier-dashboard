#!/bin/bash
# 采购看板每日推送脚本
# 每天7点自动执行，将最新数据推送到GitHub Pages

set -e

echo "=== 采购看板每日推送开始 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

WORKDIR="/home/hughxmwen/workspace/supplier_dashboard"
PYTHON_PATH="python3"
BUILD_SCRIPT="build.py"
GIT_REPO="https://xmwen.github.io/supplier-dashboard/"

# 进入工作目录
cd "$WORKDIR" || { echo "错误：无法进入工作目录 $WORKDIR"; exit 1; }

echo "1. 运行构建脚本..."
# 设置Python环境变量避免Unicode编码问题
export PYTHONIOENCODING=utf-8

# 执行构建脚本
if "$PYTHON_PATH" "$BUILD_SCRIPT"; then
    echo "✅ 构建成功"
    
    # 检查是否有更改
    echo "2. 检查git状态..."
    GIT_STATUS=$(git status --porcelain)
    
    if [ -z "$GIT_STATUS" ]; then
        echo "📝 没有需要提交的更改"
        echo "=== 任务完成 ==="
        exit 0
    else
        echo "📦 检测到更改，准备提交..."
        
        # 添加所有文件
        git add -A
        
        # 获取当前日期
        TODAY=$(date '+%Y-%m-%d')
        
        # 提交更改
        git commit -m "auto: daily dashboard update $TODAY"
        
        # 推送（使用SSH端口443）
        echo "3. 推送到GitHub..."
        GIT_SSH_COMMAND="ssh -o Port=443" git push origin main
        
        echo "✅ 推送成功"
        echo "=== 任务完成 ==="
        exit 0
    fi
else
    echo "❌ 构建失败，跳过git操作"
    echo "=== 任务终止 ==="
    exit 1
fi