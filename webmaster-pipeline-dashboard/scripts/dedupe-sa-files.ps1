$ErrorActionPreference = 'Stop'
$dir = Join-Path (Split-Path $PSScriptRoot -Parent) '.streamlit'
$a = Join-Path $dir 'gcp-service-account.json'
$b = Join-Path $dir 'service_account.json.json'
$c = Join-Path $dir 'service_account.json'
if ((Test-Path $a) -and (Test-Path $b)) {
    $ha = (Get-FileHash -LiteralPath $a).Hash
    $hb = (Get-FileHash -LiteralPath $b).Hash
    Write-Output "gcp vs service_account.json.json SAME=$($ha -eq $hb)"
}
if ((Test-Path $a) -and (Test-Path $c)) {
    $hc = (Get-FileHash -LiteralPath $c).Hash
    $ha = (Get-FileHash -LiteralPath $a).Hash
    Write-Output "gcp vs service_account.json SAME=$($ha -eq $hc)"
}
