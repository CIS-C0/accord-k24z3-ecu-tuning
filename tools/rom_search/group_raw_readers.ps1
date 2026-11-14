# For a list of RAM variables: find every "mov.l @(disp,PC),Rn" that loads their address, guess the function
# start (previous rts + delay slot, nop padding skipped) and list the functions that load two or more of them.
# Usage: powershell -File group_raw_readers.ps1 <decrypted.bin> <hex> [<hex> ...]
param([string]$bin, [Parameter(ValueFromRemainingArguments = $true)][string[]]$vars)
$rom = [IO.File]::ReadAllBytes((Resolve-Path $bin))
$BASE = 0x8000
$END = $BASE + $rom.Length
function U16([long]$a) { $o = $a - $BASE; ([int]$rom[$o] -shl 8) -bor $rom[$o + 1] }
function U32([long]$a) { ([uint32](U16 $a) -shl 16) -bor [uint32](U16 ($a + 2)) }

$wanted = @{}
foreach ($v in $vars) { $wanted[[uint32]::Parse($v.Replace('0x', ''), 'HexNumber')] = $true }

# pool address -> value, only for wanted values
$pools = @{}
for ($p = $BASE; $p -le $END - 4; $p += 4) { $v = U32 $p; if ($wanted.ContainsKey($v)) { $pools[$p] = $v } }

$byFunc = @{}
for ($pc = $BASE; $pc -lt $END - 2; $pc += 2) {
    $op = U16 $pc
    if (($op -band 0xF000) -ne 0xD000) { continue }
    $t = ($pc -band -4) + 4 + ($op -band 0xFF) * 4
    if (-not $pools.ContainsKey($t)) { continue }
    $start = $null
    for ($a = $pc - 2; $a -gt [Math]::Max($BASE, $pc - 0x2000); $a -= 2) {
        if ((U16 $a) -eq 0x000B) { $start = $a + 4; while ((U16 $start) -eq 0x0009) { $start += 2 }; break }
    }
    $key = if ($start) { '{0:X5}' -f $start } else { '?' }
    if (-not $byFunc.ContainsKey($key)) { $byFunc[$key] = @{} }
    $byFunc[$key]['{0:X8}' -f $pools[$t]] += @('{0:X5}' -f $pc)
}

foreach ($k in ($byFunc.Keys | Sort-Object)) {
    if ($byFunc[$k].Count -lt 2) { continue }
    $parts = $byFunc[$k].Keys | Sort-Object | ForEach-Object { '{0}@{1}' -f $_, ($byFunc[$k][$_] -join ',') }
    'func {0}: {1}' -f $k, ($parts -join '  ')
}
