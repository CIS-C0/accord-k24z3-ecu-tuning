# Find the GBR-relative stores that write given RAM addresses.
# For every "mov.l @(disp,PC),r0" + "ldc r0,gbr" (0xD0dd 0x401E), scan forward up to 0x800 bytes (stop at rts or
# another ldc gbr) for mov.b/mov.w/mov.l r0,@(disp,gbr) (0xC0dd/0xC1dd/0xC2dd) and report those whose address
# (gbr + disp*size) is one of the targets.
# With -Loads, also reports mov.b/mov.w/mov.l @(disp,gbr),r0 (0xC4dd/0xC5dd/0xC6dd) reads of the targets.
# Usage: powershell -File gbr_stores.ps1 <decrypted.bin> [-Loads] <hex> [<hex> ...]
param([string]$bin, [switch]$Loads, [Parameter(ValueFromRemainingArguments = $true)][string[]]$targets)
$rom = [IO.File]::ReadAllBytes((Resolve-Path $bin))
$BASE = 0x8000
$END = $BASE + $rom.Length
function U16([long]$a) { $o = $a - $BASE; ([int]$rom[$o] -shl 8) -bor $rom[$o + 1] }
function U32([long]$a) { ([uint32](U16 $a) -shl 16) -bor [uint32](U16 ($a + 2)) }

$want = @{}
foreach ($t in $targets) { $want[[uint32]::Parse($t.Replace('0x', ''), 'HexNumber')] = $true }

for ($pc = $BASE; $pc -lt $END - 4; $pc += 2) {
    $op = U16 $pc
    if (($op -band 0xFF00) -ne 0xD000 -or (U16 ($pc + 2)) -ne 0x401E) { continue }
    $gbr = U32 (($pc -band -4) + 4 + ($op -band 0xFF) * 4)
    for ($a = $pc + 4; $a -lt [Math]::Min($END - 2, $pc + 0x800); $a += 2) {
        $o = U16 $a
        if ($o -eq 0x401E) { break }
        $kind = $o -band 0xFF00
        $size = 0
        $what = 'store'
        if ($kind -eq 0xC000) { $size = 1 } elseif ($kind -eq 0xC100) { $size = 2 } elseif ($kind -eq 0xC200) { $size = 4 }
        elseif ($Loads -and $kind -eq 0xC400) { $size = 1; $what = 'load' }
        elseif ($Loads -and $kind -eq 0xC500) { $size = 2; $what = 'load' }
        elseif ($Loads -and $kind -eq 0xC600) { $size = 4; $what = 'load' }
        if ($size -gt 0) {
            $addr = [uint32](([int64]$gbr + ($o -band 0xFF) * $size) -band 0xFFFFFFFF)
            if ($want.ContainsKey($addr)) {
                '{0} {1:X8} (size {2}) at {3:X5}, gbr {4:X8} set at {5:X5}' -f $what, $addr, $size, $a, $gbr, $pc
            }
        }
        if ($o -eq 0x000B) { break }
    }
}
