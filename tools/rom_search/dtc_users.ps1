# Find the code that loads given 16-bit DTC numbers with "mov.w @(disp,PC),Rn" (0x9ndd, target = pc + 4 + disp*2),
# then list the RAM addresses (0xFFFFxxxx) loaded with mov.l from the function around it (previous rts to next rts).
# Usage: powershell -File dtc_users.ps1 <decrypted.bin> <hexDTC> [<hexDTC> ...]
param([string]$bin, [Parameter(ValueFromRemainingArguments = $true)][string[]]$codes)
$rom = [IO.File]::ReadAllBytes((Resolve-Path $bin))
$BASE = 0x8000
$END = $BASE + $rom.Length
function U16([long]$a) { $o = $a - $BASE; ([int]$rom[$o] -shl 8) -bor $rom[$o + 1] }
function U32([long]$a) { ([uint32](U16 $a) -shl 16) -bor [uint32](U16 ($a + 2)) }

$wanted = @{}
foreach ($c in $codes) { $wanted[[int]::Parse($c.Replace('0x', ''), 'HexNumber')] = $true }

for ($pc = $BASE; $pc -lt $END - 2; $pc += 2) {
    $op = U16 $pc
    if (($op -band 0xF000) -ne 0x9000) { continue }
    $t = $pc + 4 + ($op -band 0xFF) * 2
    if ($t + 2 -gt $END) { continue }
    $code = U16 $t
    if (-not $wanted.ContainsKey($code)) { continue }
    $start = $pc; while ($start -gt $BASE -and (U16 ($start - 2)) -ne 0x000B -and $pc - $start -lt 0x1000) { $start -= 2 }
    $start += 2  # skip the rts delay slot
    $stop = $pc; while ($stop -lt $END - 2 -and (U16 $stop) -ne 0x000B -and $stop - $pc -lt 0x1000) { $stop += 2 }
    $ram = @{}
    for ($a = $start; $a -lt $stop; $a += 2) {
        $o = U16 $a
        if (($o -band 0xF000) -ne 0xD000) { continue }
        $v = U32 (($a -band -4) + 4 + ($o -band 0xFF) * 4)
        if ($v -ge [uint32]4294901760) { $ram['{0:X8}' -f $v] = $true }
    }
    'P{0:X4} loaded at {1:X5} (func ~{2:X5}-{3:X5}) RAM: {4}' -f $code, $pc, $start, $stop, (($ram.Keys | Sort-Object) -join ' ')
}
