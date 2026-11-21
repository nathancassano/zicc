$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$romPath = Join-Path $workspace 'build/link_smoke.sfc'
$romBytes = [IO.File]::ReadAllBytes($romPath)
function Require([bool] $condition, [string] $message) {
    if (-not $condition) { throw $message }
}
function Word([byte[]] $bytes, [int] $offset) {
    return [int]$bytes[$offset] -bor ([int]$bytes[$offset + 1] -shl 8)
}
Require ($romBytes.Length -eq 32768) 'ROM length is not exactly 32 KiB'
$fields = @(0x30, 0, 5, 0, 0, 0, 0)
for ($i = 0; $i -lt $fields.Count; ++$i) {
    Require ($romBytes[0x7FD5 + $i] -eq $fields[$i]) "Wrong metadata byte $i"
}
$checksum = Word $romBytes 0x7FDE
$complement = Word $romBytes 0x7FDC
$sum = 0
foreach ($byte in $romBytes) { $sum = ($sum + $byte) -band 0xFFFF }
Require ($sum -eq $checksum) 'Checksum does not match final ROM bytes'
Require (($checksum -bxor $complement) -eq 0xFFFF) 'Invalid checksum complement'
$unusedTarget = Word $romBytes 0x7FE0
Require ($unusedTarget -ge 0x8000) 'Unused vector target is outside ROM'
Require ($romBytes[$unusedTarget -band 0x7FFF] -eq 0x40) 'Unused target is not RTI'
for ($i = 0x7FE0; $i -lt 0x8000; $i += 2) {
    if ($i -eq 0x7FEA -or $i -eq 0x7FFC) { continue }
    Require ((Word $romBytes $i) -eq $unusedTarget) 'Unused vectors do not share RTI'
}
$reset = Word $romBytes 0x7FFC
$nmi = Word $romBytes 0x7FEA
Require ($reset -ge 0x8000 -and $romBytes[$reset -band 0x7FFF] -eq 0x78) 'Reset fixture does not start with SEI'
Require ($nmi -ge 0x8000 -and $romBytes[$nmi -band 0x7FFF] -eq 0x5C) 'Native NMI fixture does not enter its bank-$80 veneer'

$tool = Join-Path $workspace 'build/romtool.exe'
$logs = if ($env:ZICC_LOGS_DIR) { $env:ZICC_LOGS_DIR } else { Join-Path (Get-Location).Path 'logs' }
$output = Join-Path $logs 'rom-check'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$testTitle = Join-Path $output 'test-title.txt'
$testOutput = Join-Path $output 'test-header.sfc'
[IO.File]::WriteAllText($testTitle, '123456789012345678901', [Text.Encoding]::ASCII)
& $tool $romPath $testOutput $testTitle
Require ($LASTEXITCODE -eq 0) '21-character title rejected'
$testBytes = [IO.File]::ReadAllBytes($testOutput)
Require ([Text.Encoding]::ASCII.GetString($testBytes, 0x7FC0, 21) -ceq '123456789012345678901') '21-byte title changed or terminated'
[IO.File]::WriteAllText($testTitle, 'CALC', [Text.Encoding]::ASCII)
& $tool $romPath $testOutput $testTitle
Require ($LASTEXITCODE -eq 0) 'Short title rejected'
$testBytes = [IO.File]::ReadAllBytes($testOutput)
Require ([Text.Encoding]::ASCII.GetString($testBytes, 0x7FC0, 21) -ceq 'CALC                 ') 'Short title not space padded'
$secondOutput = Join-Path $output 'test-header-again.sfc'
& $tool $testOutput $secondOutput $testTitle
Require ($LASTEXITCODE -eq 0) 'Second finalization failed'
$secondBytes = [IO.File]::ReadAllBytes($secondOutput)
Require ($testBytes.Length -eq $secondBytes.Length) 'Second finalization changed ROM length'
for ($i = 0; $i -lt $testBytes.Length; ++$i) {
    Require ($testBytes[$i] -eq $secondBytes[$i]) 'Finalization is not idempotent'
}
[IO.File]::WriteAllText($testTitle, '1234567890123456789012', [Text.Encoding]::ASCII)
$ErrorActionPreference = 'Continue'
& $tool $romPath $testOutput $testTitle 2>$null
$ErrorActionPreference = 'Stop'
Require ($LASTEXITCODE -ne 0) 'Overlong title accepted'
$shortRom = Join-Path $output 'test-short.raw'
[IO.File]::WriteAllBytes($shortRom, [byte[]]@(0, 1))
[IO.File]::WriteAllText($testTitle, 'CALC', [Text.Encoding]::ASCII)
$ErrorActionPreference = 'Continue'
& $tool $shortRom $testOutput $testTitle 2>$null
$ErrorActionPreference = 'Stop'
Require ($LASTEXITCODE -ne 0) 'Wrong-sized ROM accepted'
Write-Output 'ROM layout, metadata, vectors, checksum, title boundaries, and rejection checks passed.'
