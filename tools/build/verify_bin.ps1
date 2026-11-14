param(
    [string]$Stock = "C:\Users\<user>\Desktop\2011_accord_coupe\stock\37805-R42-A240-M1.0x8000.bin",
    [Parameter(Mandatory = $true)][string]$Edited,
    [Parameter(Mandatory = $true)][int]$ExpectedSpeedLimit
)
# Independent check of an edited R42-A240 firmware .bin (no bootloader, ROM address = file offset + 0x8000).
# Allowed differences vs stock: Speedlimiter word at ROM 0xB2C2 and the checksum byte at ROM 0x8400.
$s = [IO.File]::ReadAllBytes($Stock)
$e = [IO.File]::ReadAllBytes($Edited)
$ok = $true
if ($s.Length -ne $e.Length) { "FAIL length: stock $($s.Length) edited $($e.Length)"; exit 1 }

$allowed = @((0xB2C2 - 0x8000), (0xB2C3 - 0x8000), (0x8400 - 0x8000))
$diffs = @()
for ($i = 0; $i -lt $s.Length; $i++) { if ($s[$i] -ne $e[$i]) { $diffs += $i } }
foreach ($d in $diffs) {
    $tag = if ($allowed -contains $d) { "allowed" } else { $ok = $false; "UNEXPECTED" }
    "diff at ROM 0x{0:X5}: {1:X2} -> {2:X2}  ({3})" -f ($d + 0x8000), $s[$d], $e[$d], $tag
}
if ($diffs.Count -eq 0) { "no differences vs stock" }

$o = 0xB2C2 - 0x8000
$v = $e[$o] * 256 + $e[$o + 1]
if ($v -ge 32768) { $v -= 65536 }
"Speedlimiter @0xB2C2 = $v (expected $ExpectedSpeedLimit)"
if ($v -ne $ExpectedSpeedLimit) { $ok = $false }

# Checksum, same algorithm as the tool: negative byte sum with +255 wrap, then add the bootloader sum
$cl = 0x8400 - 0x8000
$sum = 0
for ($i = 0; $i -lt $e.Length; $i++) { if ($i -ne $cl) { $sum -= $e[$i]; if ($sum -lt 0) { $sum += 255 } } }
$expectedChk = 0xB1 + $sum
if ($expectedChk -ge 256) { $expectedChk -= 255 }
"checksum @0x8400 = 0x{0:X2}, expected 0x{1:X2} (bootloader sum 0xB1)" -f $e[$cl], $expectedChk
if ($e[$cl] -ne $expectedChk) { $ok = $false }

if ($ok) { "RESULT: OK" } else { "RESULT: FAIL" }
