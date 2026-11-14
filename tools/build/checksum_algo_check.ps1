param([string[]]$Files = @(
    "C:\Users\<user>\Desktop\2011_accord_coupe\stock\37805-R42-A240-M1.RWD.gz",
    "C:\Users\<user>\Desktop\2011_accord_coupe\stock\37805-R42-A220-M1.rwd.gz"))
# Which checksum algorithm does the R42 ECU use for the byte at ROM 0x8400?
# The firmware files miss the bootloader (ROM 0x0000-0x7FFF). For each algorithm we compute the bootloader
# contribution that makes each file's checksum byte valid. Two calibrations of the same family should share the
# same bootloader, so the right algorithm gives the SAME bootloader value for every file.
Add-Type -AssemblyName System.IO.Compression

function Read-Rwd([string]$Path) {
    $raw = [IO.File]::ReadAllBytes($Path)
    if ($raw[0] -eq 0x1F -and $raw[1] -eq 0x8B) {
        $in = New-Object IO.MemoryStream(, $raw)
        $gz = New-Object IO.Compression.GZipStream($in, [IO.Compression.CompressionMode]::Decompress)
        $ms = New-Object IO.MemoryStream
        $gz.CopyTo($ms)
        $raw = $ms.ToArray()
    }
    # header: 5A 0D 0A then 6 groups (count, count x (len, bytes)), then start, size (BE)
    $idx = 3
    $groups = @()
    for ($h = 0; $h -lt 6; $h++) {
        $count = $raw[$idx]; $idx++
        $g = New-Object System.Collections.Generic.List[byte]
        for ($c = 0; $c -lt $count; $c++) { $len = $raw[$idx]; $idx++; for ($k = 0; $k -lt $len; $k++) { $g.Add($raw[$idx + $k]) }; $idx += $len }
        $groups += , $g.ToArray()
    }
    $start = ([uint32]$raw[$idx] -shl 24) -bor ([uint32]$raw[$idx+1] -shl 16) -bor ([uint32]$raw[$idx+2] -shl 8) -bor $raw[$idx+3]
    $idx += 8
    $keys = $groups[5]
    $n = $raw.Length - 4 - $idx
    $fw = New-Object byte[] $n
    for ($i = 0; $i -lt $n; $i++) {
        $e = $raw[$idx + $i]
        $fw[$i] = [byte]((((($e -bxor $keys[2]) + $keys[1]) - $keys[0]) % 256 + 256) % 256)
    }
    return @{ Start = $start; Fw = $fw }
}

$results = @()
foreach ($f in $Files) {
    $r = Read-Rwd $f
    $fw = $r.Fw
    $loc = 0x8400 - $r.Start
    $chk = $fw[$loc]
    # A) HondaReflashTool: negative sum with +255 wrap (end around), excluding the checksum byte
    $s = 0
    for ($i = 0; $i -lt $fw.Length; $i++) { if ($i -ne $loc) { $s -= $fw[$i]; if ($s -lt 0) { $s += 255 } } }
    $bootA = $chk - $s; if ($bootA -lt 0) { $bootA += 255 }
    # B) rwd-xray: two's complement, sum of everything (bootloader + firmware incl. checksum) = 0 mod 256
    $sum = 0
    for ($i = 0; $i -lt $fw.Length; $i++) { $sum += $fw[$i] }
    $bootB = (256 - ($sum % 256)) % 256
    # C) plain sum mod 256 equals the checksum byte (checksum = sum of all other bytes)
    $sumEx = ($sum - $chk) % 256
    $bootC = (($chk - $sumEx) % 256 + 256) % 256
    $name = [IO.Path]::GetFileName($f)
    "{0}: start 0x{1:X} chk@0x8400=0x{2:X2} | A (tool, mod255) boot=0x{3:X2} | B (rwd-xray, -sum mod256) boot=0x{4:X2} | C (sum mod256) boot=0x{5:X2}" -f $name, $r.Start, $chk, $bootA, $bootB, $bootC
    $results += @{ A = $bootA; B = $bootB; C = $bootC }
}
""
"BootLoaderSumBytesList.txt says R42-A210..A240 = 177 (0xB1)"
foreach ($k in "A", "B", "C") {
    $vals = @($results | ForEach-Object { $_[$k] })
    $same = (@($vals | Sort-Object -Unique).Count -eq 1)
    "{0}: values {1} -> {2}" -f $k, (($vals | ForEach-Object { '0x{0:X2}' -f $_ }) -join ', '), $(if ($same) { "SAME for all files" } else { "different" })
}
