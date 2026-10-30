$rootDir = "C:\Users\ayush\Desktop\devsquad-main"

# 1. Kill any existing processes holding port 8000 or 3000
Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.OwningProcess -gt 0) {
        Write-Host "Stopping process holding port: $($_.OwningProcess)"
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 1

# 2. Launch FastAPI backend
Write-Host "Starting FastAPI backend on port 8000..."
$backendProcess = Start-Process `
    -FilePath "$rootDir\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory "$rootDir\backend" `
    -RedirectStandardOutput "$rootDir\backend_stdout.log" `
    -RedirectStandardError "$rootDir\backend_stderr.log" `
    -PassThru

Write-Host "Backend started with PID $($backendProcess.Id)"

# 3. Launch Next.js frontend
Write-Host "Starting Next.js frontend on port 3000..."
$frontendProcess = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm", "run", "dev" `
    -WorkingDirectory "$rootDir\frontend" `
    -RedirectStandardOutput "$rootDir\frontend_stdout.log" `
    -RedirectStandardError "$rootDir\frontend_stderr.log" `
    -PassThru

Write-Host "Frontend started with PID $($frontendProcess.Id)"

# 4. Wait for both servers to initialize
Start-Sleep -Seconds 5

# 5. Check health
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get -TimeoutSec 3
    Write-Host "Backend is UP! Health status: $($health.status)"
} catch {
    Write-Host "Backend check failed: $_"
}

try {
    $front = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -UseBasicParsing -TimeoutSec 3
    Write-Host "Frontend is UP! Status: $($front.StatusCode)"
} catch {
    Write-Host "Frontend check failed: $_"
}
