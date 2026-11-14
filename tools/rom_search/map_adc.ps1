# Map the A/D driver table (ROM 0xE120..0xE220) to the RAM variables the raw-copy functions store into.
# For each pool word pointing into the table: find the "mov.l @(disp,PC),Rn" loading it, then scan the next
# 12 instructions for another mov.l whose pool value is a RAM address (0xFFFFxxxx) and report it, with the
# shift count (shlr2/shlr: 10-bit result taken from the left aligned A/D register).
# Usage: powershell -File map_adc.ps1 <decrypted.bin>
param([string]$bin)
$rom = [IO.File]::ReadAllBytes((Resolve-Path $bin))
$BASE = 0x8000
$END = $BASE + $rom.Length
function U16([long]$a) { $o = $a - $BASE; ([int]$rom[$o] -shl 8) -bor $rom[$o + 1] }
function U32([long]$a) { ([uint32](U16 $a) -shl 16) -bor [uint32](U16 ($a + 2)) }
function PoolTarget([long]$pc, [int]$op) { ($pc -band -4) + 4 + ($op -band 0xFF) * 4 }

for ($pc = $BASE; $pc -lt $END - 2; $pc += 2) {
    $op = U16 $pc
    if (($op -band 0xF000) -ne 0xD000) { continue }
    $t = PoolTarget $pc $op
    if ($t + 4 -gt $END) { continue }
    $entry = U32 $t
    if ($entry -lt 0xE120 -or $entry -ge 0xE220) { continue }
    $adreg = U32 $entry
    $dests = @()
    $shifts = 0
    for ($k = 1; $k -le 12; $k++) {
        $a = $pc + 2 * $k
        $o = U16 $a
        if (($o -band 0xF000) -eq 0xD000) {
            $v = U32 (PoolTarget $a $o)
            if ($v -ge [uint32]4294901760) { $dests += ('{0:X8}' -f $v) }
        }
        if (($o -band 0xF0FF) -eq 0x4009) { $shifts += 2 } elseif (($o -band 0xF0FF) -eq 0x4001) { $shifts += 1 }
        if ($o -eq 0x000B) {
            # rts: count its delay slot, then stop
            if (((U16 ($a + 2)) -band 0xF0FF) -eq 0x4009) { $shifts += 2 }
            break
        }
    }
    'code {0:X5} entry {1:X5} -> AD reg {2:X8}  >>{3}  RAM {4}' -f $pc, $entry, $adreg, $shifts, ($dests -join ' ')
}
