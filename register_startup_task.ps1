# ==============================================================================
# PowerShell Script to register Omnex Multi-Agent Background Daemon on Windows Logon
# Run in PowerShell as Administrator: powershell -ExecutionPolicy Bypass -File register_startup_task.ps1
# ==============================================================================

$TaskName = "OmnexAgentDaemon"
$WorkingDir = $PSScriptRoot
$PythonExe = (Get-Command python.exe).Source
$ScriptPath = Join-Path $WorkingDir "daily_pipeline_cron.py"

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Registering Omnex Background Autonomous Agent Task..." -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# Define Action
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`" --daemon" -WorkingDirectory $WorkingDir

# Define Trigger (At Logon)
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Define Settings (Run in background, restart if failed)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Register or update task
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs Omnex RAG Agent Background Daemon and 5:00 PM Excel Cron"

Write-Host "`n[SUCCESS] Task '$TaskName' registered successfully!" -ForegroundColor Green
Write-Host "The agent will now start automatically in the background whenever you log into Windows." -ForegroundColor Yellow
Write-Host "It will automatically generate the 5:00 PM Excel rollups and watch the Downloads folder for new transcripts." -ForegroundColor Green
