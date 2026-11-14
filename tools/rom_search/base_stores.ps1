# Find stores to a RAM address made through a base register: a "mov.l/mov.w @(disp,PC),Rn" loads a base B within
# 0x7F bytes below the target, then (up to 60 instructions later, "add #imm,Rn" followed) a store reaches the target:
# mov.b/w R0,@(disp,Rn) (80nd/81nd), mov.l Rm,@(disp,Rn) (1nmd), mov.b/w/l Rm,@Rn (2nm0/1/2).
# Approximate: stops following Rn when another instruction writes Rn, ignores branches.
# Usage: powershell -File base_stores.ps1 <decrypted.bin> <hex> [<hex> ...]
param([string]$bin, [Parameter(ValueFromRemainingArguments = $true)][string[]]$targets)
$rom = [IO.File]::ReadAllBytes((Resolve-Path $bin))
$BASE = 0x8000
$END = $BASE + $rom.Length
function U16([long]$a) { $o = $a - $BASE; ([int]$rom[$o] -shl 8) -bor $rom[$o + 1] }
function U32([long]$a) { ([uint32](U16 $a) -shl 16) -bor [uint32](U16 ($a + 2)) }

foreach ($t in $targets) {
    $tgt = [uint32]::Parse($t.Replace('0x', ''), 'HexNumber')
    '=== stores to {0:X8}' -f $tgt
    for ($pc = $BASE; $pc -lt $END - 2; $pc += 2) {
        $op = U16 $pc
        $v = $null
        if (($op -band 0xF000) -eq 0x9000) {
            $p = $pc + 4 + ($op -band 0xFF) * 2
            if ($p -lt $END - 1) { $w = U16 $p; if ($w -ge 0x8000) { $v = [uint32]([long]4294901760 + $w) } }
        } elseif (($op -band 0xF000) -eq 0xD000) {
            $p = ($pc -band -4) + 4 + ($op -band 0xFF) * 4
            if ($p -lt $END - 3) { $v = U32 $p }
        }
        if ($null -eq $v -or $v -gt $tgt -or $tgt - $v -gt 0x7F) { continue }
        $n = ($op -shr 8) -band 0xF
        $b = [long]$v
        for ($q = $pc + 2; $q -lt [Math]::Min($END - 2, $pc + 122); $q += 2) {
            $o = U16 $q
            $hi = $o -shr 12
            $sz = 0; $addr = -1
            if (($o -band 0xFF00) -eq 0x8000 -and (($o -shr 4) -band 0xF) -eq $n) { $sz = 1; $addr = $b + ($o -band 0xF) }
            elseif (($o -band 0xFF00) -eq 0x8100 -and (($o -shr 4) -band 0xF) -eq $n) { $sz = 2; $addr = $b + ($o -band 0xF) * 2 }
            elseif ($hi -eq 1 -and (($o -shr 8) -band 0xF) -eq $n) { $sz = 4; $addr = $b + ($o -band 0xF) * 4 }
            elseif ($hi -eq 2 -and (($o -shr 8) -band 0xF) -eq $n -and ($o -band 0xF) -le 2) { $sz = 1 -shl ($o -band 0xF); $addr = $b }
            if ($addr -ge 0 -and $tgt -ge $addr -and $tgt -lt $addr + $sz) {
                '  store {0:X4} at {1:X5} (base {2:X8} loaded at {3:X5})' -f $o, $q, $v, $pc
            }
            if ($hi -eq 7 -and (($o -shr 8) -band 0xF) -eq $n) { $d = $o -band 0xFF; if ($d -ge 0x80) { $d -= 0x100 }; $b += $d; continue }
            # other writes to Rn end the trace
            if (($hi -in 6, 0xE, 0xD, 9) -and (($o -shr 8) -band 0xF) -eq $n) { break }
            if ($o -eq 0x000B) { break }
        }
    }
}
