@echo off
rem Kills every HDS 3.105 (C:\GenRad) and i-HDS (C:\i-HDS) program still running, so the GODIAG adapter is free.
rem Only processes started from those two folders; the Windows services TDSNetSetup and iqsext are left alone.
powershell -NoProfile -Command "$p = Get-Process | Where-Object { ($_.Path -like 'C:\GenRad\*' -or $_.Path -like 'C:\i-HDS\*') -and $_.ProcessName -notin 'TDSNetSetup','iqsext' }; if ($p) { $p | ForEach-Object { 'kill ' + $_.ProcessName + ' (' + $_.Id + ')' }; $p | Stop-Process -Force } else { 'no HDS process running' }"
pause
