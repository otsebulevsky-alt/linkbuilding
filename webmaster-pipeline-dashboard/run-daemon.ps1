# Streamlit: restart on exit so the dashboard stays available (stop: close window or Task Manager).
# Strings: English only (workspace PowerShell rules).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot
Write-Host "Webmaster pipeline dashboard daemon. Stop: close this window or End Task."
Write-Host "Open: http://localhost:8503"
while ($true) {
    try {
        & py -m streamlit run app.py
    } catch {
        Write-Host "Streamlit error, restarting in 5s..."
    }
    Start-Sleep -Seconds 5
}
