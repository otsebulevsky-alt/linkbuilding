# Streamlit: restart on exit so the dashboard stays available (stop: close window or Task Manager).
# Strings: English only (workspace PowerShell rules).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot
Write-Host "Webmaster pipeline dashboard daemon. Stop: close this window or End Task."

$preferred = 8503
$port = $preferred
try {
    $inUse = Get-NetTCPConnection -LocalPort $preferred -State Listen -ErrorAction SilentlyContinue
} catch {
    $inUse = $null
}
if ($inUse) {
    Write-Host "Port $preferred in use, using 8504..."
    $port = 8504
}
Write-Host "Open: http://127.0.0.1:$port"

while ($true) {
    try {
        & py -m streamlit run app.py --server.port $port --server.address 127.0.0.1
    } catch {
        Write-Host "Streamlit error, restarting in 5s..."
    }
    Start-Sleep -Seconds 5
}
