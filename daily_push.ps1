# 采购看板每日推送脚本（PowerShell版本）
# 每天7点自动执行，将最新数据推送到GitHub Pages

Write-Host "=== 采购看板每日推送开始 ===" -ForegroundColor Cyan
Write-Host "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan

$WORKDIR = "D:\workbuddy\supplier_dashboard"
$PYTHON_PATH = "C:\Users\chens\AppData\Local\Programs\Python\Python312\python.exe"
$BUILD_SCRIPT = "build.py"

# 进入工作目录
Set-Location $WORKDIR
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：无法进入工作目录 $WORKDIR" -ForegroundColor Red
    exit 1
}

Write-Host "1. 运行构建脚本..." -ForegroundColor Yellow

# 设置Python环境变量避免Unicode编码问题
$env:PYTHONIOENCODING = "utf-8"

# 执行构建脚本
& $PYTHON_PATH $BUILD_SCRIPT
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 构建成功" -ForegroundColor Green
    
    # 检查是否有更改
    Write-Host "2. 检查git状态..." -ForegroundColor Yellow
    $gitStatus = & git status --porcelain 2>$null
    
    if ([string]::IsNullOrWhiteSpace($gitStatus)) {
        Write-Host "📝 没有需要提交的更改" -ForegroundColor Blue
        Write-Host "=== 任务完成 ===" -ForegroundColor Cyan
        exit 0
    } else {
        Write-Host "📦 检测到更改，准备提交..." -ForegroundColor Yellow
        
        # 添加所有文件
        & git add -A
        
        # 获取当前日期
        $today = Get-Date -Format "yyyy-MM-dd"
        
        # 提交更改
        & git commit -m "auto: daily dashboard update $today"
        
        # 推送（使用SSH端口443）
        Write-Host "3. 推送到GitHub..." -ForegroundColor Yellow
        $env:GIT_SSH_COMMAND = "ssh -o Port=443"
        & git push origin main
        Remove-Item Env:GIT_SSH_COMMAND
        
        Write-Host "✅ 推送成功" -ForegroundColor Green
        Write-Host "=== 任务完成 ===" -ForegroundColor Cyan
        exit 0
    }
} else {
    Write-Host "❌ 构建失败，跳过git操作" -ForegroundColor Red
    Write-Host "=== 任务终止 ===" -ForegroundColor Cyan
    exit 1
}