# Decode 1D table descriptors (12 bytes: count byte, 3 format bytes, axis pointer, data pointer; used by the
# lookup helper 0x8CD8) and print axis and data as signed 16-bit values.
# Usage: powershell -File dump_tables.ps1 <decrypted.bin> <hexDescriptor> [<hexDescriptor> ...]
param([string]$bin, [Parameter(ValueFromRemainingArguments = $true)][string[]]$descs)
$rom = [IO.File]::ReadAllBytes((Resolve-Path $bin))
$BASE = 0x8000
function U8([long]$a) { [int]$rom[$a - $BASE] }
function S16([long]$a) { $v = (U8 $a) * 256 + (U8 ($a + 1)); if ($v -ge 0x8000) { $v - 0x10000 } else { $v } }
function U32([long]$a) { ([uint32](U8 $a) -shl 24) -bor ([uint32](U8 ($a + 1)) -shl 16) -bor ([uint32](U8 ($a + 2)) -shl 8) -bor [uint32](U8 ($a + 3)) }

foreach ($d in $descs) {
    $a = [long]::Parse($d.Replace('0x', ''), 'HexNumber')
    $n = U8 $a
    $fmt = '{0:X2}{1:X2}{2:X2}' -f (U8 ($a + 1)), (U8 ($a + 2)), (U8 ($a + 3))
    $axis = U32 ($a + 4)
    $data = U32 ($a + 8)
    if ($n -lt 1 -or $n -gt 32 -or $axis -lt $BASE -or $data -lt $BASE -or $axis -ge 0x100000 -or $data -ge 0x100000) {
        '{0:X5}: not a 1D descriptor ({1:X2} {2} {3:X8} {4:X8})' -f $a, $n, $fmt, $axis, $data
        continue
    }
    $ax = (0..($n - 1) | ForEach-Object { S16 ($axis + 2 * $_) }) -join ' '
    $da = (0..($n - 1) | ForEach-Object { S16 ($data + 2 * $_) }) -join ' '
    '{0:X5}: n={1} fmt={2} axis@{3:X5} [{4}] data@{5:X5} [{6}]' -f $a, $n, $fmt, $axis, $ax, $data, $da
}
