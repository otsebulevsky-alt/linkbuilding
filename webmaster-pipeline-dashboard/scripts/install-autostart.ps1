# Add Startup shortcut to run run-daemon.ps1 at Windows logon (current user, no admin).
# Run from repo: powershell -ExecutionPolicy Bypass -File internal/seo/linkbuilding/webmaster-pipeline-dashboard/scripts/install-autostart.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$appDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$daemon = Join-Path $appDir 'run-daemon.ps1'
if (-not (Test-Path -LiteralPath $daemon)) {
    Write-Host "ERROR: run-daemon.ps1 not found at $daemon"
    exit 1
}
$startup = [Environment]::GetFolderPath('Startup')
$lnkPath = Join-Path $startup 'WebmasterPipelineDashboard.lnk'
$w = New-Object -ComObject WScript.Shell
$sc = $w.CreateShortcut($lnkPath)
$sc.TargetPath = 'powershell.exe'
$sc.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$daemon`""
$sc.WorkingDirectory = $appDir
$sc.Description = 'Streamlit: webmaster pipeline dashboard'
$sc.Save()
Write-Host "OK: shortcut created"
Write-Host $lnkPath
