# Remove Startup shortcut created by install-autostart.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$startup = [Environment]::GetFolderPath('Startup')
$lnkPath = Join-Path $startup 'WebmasterPipelineDashboard.lnk'
if (Test-Path -LiteralPath $lnkPath) {
    Remove-Item -LiteralPath $lnkPath -Force
    Write-Host "OK: removed"
} else {
    Write-Host "SKIP: shortcut not found"
}
