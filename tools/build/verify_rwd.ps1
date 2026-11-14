param(
    [string]$StockRwd = "C:\Users\<user>\Desktop\2011_accord_coupe\stock\37805-R42-A240-M1.RWD.gz",
    [string]$StockBin = "C:\Users\<user>\Desktop\2011_accord_coupe\stock\37805-R42-A240-M1.0x8000.bin",
    [Parameter(Mandatory = $true)][string]$NewRwd,
    [Parameter(Mandatory = $true)][string]$NewBin
)
# Independent check of a .rwd made by HondaReflashTool, without using its code:
# the byte cipher is learned from the stock .rwd/.bin pair, then used to decode the new .rwd.
Add-Type -AssemblyName System.IO.Compression
$ok = $true

Write-Host "[1/6] Loading files..."
$in = [IO.File]::OpenRead($StockRwd)
$gz = New-Object IO.Compression.GZipStream($in, [IO.Compression.CompressionMode]::Decompress)
$ms = New-Object IO.MemoryStream
$gz.CopyTo($ms)
$in.Close()
$S = $ms.ToArray()
$R = [IO.File]::ReadAllBytes($NewRwd)
$SB = [IO.File]::ReadAllBytes($StockBin)
$VB = [IO.File]::ReadAllBytes($NewBin)
$hdr = $S.Length - $SB.Length - 4
Write-Host ("      stock rwd {0} bytes, new rwd {1} bytes, header {2} bytes" -f $S.Length, $R.Length, $hdr)
if ($R.Length -ne $S.Length -or $VB.Length -ne $SB.Length) { Write-Host "FAIL: lengths differ"; $ok = $false }

Write-Host "[2/6] Comparing headers..."
$hdrDiff = 0
for ($i = 0; $i -lt $hdr; $i++) { if ($R[$i] -ne $S[$i]) { $hdrDiff++ } }
Write-Host "      header differences: $hdrDiff"
if ($hdrDiff) { $ok = $false }

Write-Host "[3/6] Learning cipher table from the stock pair..."
$map = New-Object 'int[]' 256
for ($k = 0; $k -lt 256; $k++) { $map[$k] = -1 }
$conflict = 0
for ($i = 0; $i -lt $SB.Length; $i++) {
    $e = $S[$hdr + $i]
    $d = $SB[$i]
    if ($map[$e] -eq -1) { $map[$e] = $d } elseif ($map[$e] -ne $d) { $conflict++ }
    if (($i % 200000) -eq 0) { Write-Host ("      {0}%" -f [int]($i * 100 / $SB.Length)) }
}
$known = @($map | Where-Object { $_ -ge 0 }).Count
$distinct = @($map | Where-Object { $_ -ge 0 } | Sort-Object -Unique).Count
Write-Host "      table: $known entries, $distinct distinct outputs, $conflict conflicts"
if ($conflict -or $known -ne $distinct) { $ok = $false }

Write-Host "[4/6] Decoding new rwd and comparing to new bin..."
$mism = 0
$unk = 0
for ($i = 0; $i -lt $VB.Length; $i++) {
    $d = $map[$R[$hdr + $i]]
    if ($d -lt 0) { $unk++ } elseif ($d -ne $VB[$i]) { $mism++ }
    if (($i % 200000) -eq 0) { Write-Host ("      {0}%" -f [int]($i * 100 / $VB.Length)) }
}
Write-Host "      mismatches: $mism, unknown bytes: $unk"
if ($mism -or $unk) { $ok = $false }

Write-Host "[5/6] Checking rwd file checksum..."
[uint64]$sum = 0
for ($i = 0; $i -lt $R.Length - 4; $i++) { $sum += $R[$i] }
$sum = $sum % 4294967296
$n = $R.Length
$stored = [uint32]$R[$n - 1] * 16777216 + [uint32]$R[$n - 2] * 65536 + [uint32]$R[$n - 3] * 256 + $R[$n - 4]
Write-Host ("      computed 0x{0:X8}, stored (little-endian) 0x{1:X8}" -f $sum, $stored)
if ($sum -ne $stored) { $ok = $false }

Write-Host "[6/6] Differences vs stock rwd..."
for ($i = 0; $i -lt $R.Length; $i++) {
    if ($R[$i] -ne $S[$i]) {
        if ($i -ge $hdr -and $i -lt $n - 4) { Write-Host ("      ROM 0x{0:X5}" -f ($i - $hdr + 0x8000)) }
        else { Write-Host ("      rwd file offset 0x{0:X} (file checksum)" -f $i) }
    }
}

if ($ok) { Write-Host "RESULT: OK" -ForegroundColor Green } else { Write-Host "RESULT: FAIL" -ForegroundColor Red }
