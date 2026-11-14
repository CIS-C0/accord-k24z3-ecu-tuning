#Deploy the checked build to FlashToolTest_v2 (copy of the last working folder), dry run ON
$Root = "C:\Users\<user>\Desktop\2011_accord_coupe"
$Dest = Join-Path $Root "FlashToolTest_v2"
if (Test-Path $Dest) { Write-Host "FlashToolTest_v2 already exists, not overwritten"; exit 1 }
Copy-Item (Join-Path $Root "FlashToolTest_raw3") $Dest -Recurse
Copy-Item (Join-Path $Root "src\build\FlashToolTest.exe"), (Join-Path $Root "src\build\FlashToolTest.pdb") $Dest -Force
Remove-Item (Join-Path $Dest "J2534_debug.log") -ErrorAction SilentlyContinue
Set-Content -Path (Join-Path $Dest "FLASH_DRYRUN.txt") -Value "Delete this file to allow a real flash." -Encoding ascii
$Built = (Get-FileHash (Join-Path $Root "src\build\FlashToolTest.exe")).Hash
$Deployed = (Get-FileHash (Join-Path $Dest "FlashToolTest.exe")).Hash
Write-Host "exe hash: $Deployed"
Write-Host ("hash match: " + ($Built -eq $Deployed))
Write-Host ("dry run file present: " + (Test-Path (Join-Path $Dest "FLASH_DRYRUN.txt")))
Write-Host ("pin 12 file present: " + (Test-Path (Join-Path $Dest "FLASH_PIN12.txt")))
foreach ($f in "ECUS_KEYS.txt", "BootLoaderSumBytesList.txt", "J2534-Sharp.dll", "DarkUI.dll") { Write-Host ("$f present: " + (Test-Path (Join-Path $Dest $f))) }
