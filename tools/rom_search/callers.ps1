# List the callers of given function addresses: "bsr" (0xBddd) to it, and "mov.l @(disp,PC),Rn" loading a pool
# word equal to it (jsr @Rn, or a function pointer). Pool words that no mov.l loads are listed too (pointer tables).
# The caller function start is guessed as the instruction after the previous rts + delay slot.
# Usage: powershell -File callers.ps1 <decrypted.bin> <hex> [<hex> ...]
param([string]$bin, [Parameter(ValueFromRemainingArguments = $true)][string[]]$funcs)
$rom = [IO.File]::ReadAllBytes((Resolve-Path $bin))
$BASE = 0x8000
$END = $BASE + $rom.Length
function U16([long]$a) { $o = $a - $BASE; ([int]$rom[$o] -shl 8) -bor $rom[$o + 1] }
function U32([long]$a) { ([uint32](U16 $a) -shl 16) -bor [uint32](U16 ($a + 2)) }
function StartOf([long]$pc) {
    $s = $pc
    while ($s -gt $BASE + 2 -and (U16 ($s - 2)) -ne 0x000B -and $pc - $s -lt 0x2000) { $s -= 2 }
    $s + 2
}

foreach ($f in $funcs) {
    $t = [long]::Parse($f.Replace('0x', ''), 'HexNumber')
    '=== callers of {0:X5}' -f $t
    for ($pc = $BASE; $pc -lt $END - 2; $pc += 2) {
        $op = U16 $pc
        if (($op -band 0xF000) -eq 0xB000) {
            $d = $op -band 0xFFF; if ($d -ge 0x800) { $d -= 0x1000 }
            if ($pc + 4 + 2 * $d -eq $t) { '  bsr at {0:X5} (caller start ~{1:X5})' -f $pc, (StartOf $pc) }
        }
    }
    for ($p = $BASE; $p -le $END - 4; $p += 4) {
        if ((U32 $p) -ne $t) { continue }
        $loaded = $false
        for ($pc = [Math]::Max($BASE, $p - 1020); $pc -lt $p; $pc += 2) {
            $op = U16 $pc
            if (($op -band 0xF000) -eq 0xD000 -and (($pc -band -4) + 4 + ($op -band 0xFF) * 4) -eq $p) {
                '  pool {0:X5} loaded at {1:X5} (caller start ~{2:X5})' -f $p, $pc, (StartOf $pc)
                $loaded = $true
            }
        }
        if (-not $loaded) { '  pool {0:X5} not loaded by mov.l (pointer table?)' -f $p }
    }
}
