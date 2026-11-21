param(
    [Parameter(Mandatory=$true)][string] $InputPath,
    [Parameter(Mandatory=$true)][string] $OutputPath
)
$ErrorActionPreference = 'Stop'
python (Join-Path $PSScriptRoot 'debug_symbols.py') $InputPath $OutputPath
if ($LASTEXITCODE -ne 0) { throw 'Debug symbol export failed' }
