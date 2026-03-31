$ErrorActionPreference = 'SilentlyContinue'
$roots = @(
    (Join-Path $env:USERPROFILE 'Downloads'),
    (Join-Path $env:USERPROFILE 'Desktop'),
    (Join-Path $env:USERPROFILE 'Documents')
)
foreach ($root in $roots) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    Get-ChildItem -LiteralPath $root -Filter '*.json' -File -Recurse -Depth 6 | ForEach-Object {
        Write-Output $_.FullName
    }
}
