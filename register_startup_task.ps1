# ==============================================================================
# PowerShell Script to register Omnex Multi-Agent Background Daemon on Windows Logon
# Requires NO Administrator rights (uses User Startup folder with hidden window)
# Run: powershell -ExecutionPolicy Bypass -File register_startup_task.ps1
# ==============================================================================

$WorkingDir = $PSScriptRoot
$PythonExe = (Get-Command python.exe).Source
$ScriptPath = Join-Path $WorkingDir "daily_pipeline_cron.py"
$StartupFolder = [System.Environment]::GetFolderPath('Startup')
$VbsPath = Join-Path $StartupFolder "OmnexAgentDaemon.vbs"

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Registering Omnex Background Autonomous Agent Task..." -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# Create silent VBScript launcher in Windows User Startup Folder
# WindowStyle 0 = Completely Hidden Background Process (no console popup)
$q = [char]34
$line1 = "Set WshShell = CreateObject(" + $q + "WScript.Shell" + $q + ")"
$line2 = "WshShell.CurrentDirectory = " + $q + $WorkingDir + $q
$line3 = "cmd = " + $q + $PythonExe + $q + " & " + $q + " " + $q + " & " + $q + $ScriptPath + $q + " & " + $q + " --daemon" + $q
$line4 = "WshShell.Run cmd, 0, False"

$lines = @($line1, $line2, $line3, $line4)
Set-Content -Path $VbsPath -Value $lines -Encoding ASCII

Write-Host "`n[SUCCESS] Omnex Autonomous Agent registered successfully!" -ForegroundColor Green
Write-Host "Location: $VbsPath" -ForegroundColor DarkGray
Write-Host "Status:   Zero-permission background startup configured." -ForegroundColor Yellow
Write-Host "`nThe agent will now start automatically in the background whenever you log into Windows." -ForegroundColor Green
Write-Host "It will silently generate the 5:00 PM Master Excel rollups and watch Downloads for new transcripts." -ForegroundColor Green

# Launch it now for the current session
Write-Host "`nStarting daemon for current session..." -ForegroundColor Cyan
Start-Process "wscript.exe" -ArgumentList "`"$VbsPath`""
Write-Host "[OK] Daemon is now running silently in the background!" -ForegroundColor Green
