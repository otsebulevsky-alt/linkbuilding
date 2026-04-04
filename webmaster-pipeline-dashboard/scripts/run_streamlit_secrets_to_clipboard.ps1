# Build Streamlit Cloud Secrets TOML and copy to clipboard (Windows).
# Usage (from webmaster-pipeline-dashboard): powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_streamlit_secrets_to_clipboard.ps1

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root
& python (Join-Path $here "build_streamlit_cloud_secrets_toml.py") --clipboard
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Next: share.streamlit.io -> app -> Settings -> Secrets -> Ctrl+V -> Save -> Reboot app."
