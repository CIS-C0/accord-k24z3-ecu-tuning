# Car day checklist: flash #5 (v6_maf_taper = v3 + MAF table x1.15 up to A/D 376, tapering to x1.08 from A/D 488)
(Flash #1 2026-10-25 v1, #2 2026-10-30 v2, #3 2026-10-30 v3, #4 2026-11-01 v5_maf115 (car runs v5), same list.)

Rule: every gate must be GREEN. One red gate = stop, no flash. Confidence is stated at each gate.
v6 (like v5) is ONLY for the current Amazon short ram intake (7 cm tube). If the stock intake is put back, flash v3.

PREP STATUS 2026-11-01 (at home, nothing flashed): v6 built from v3 (src\build_v6.py, built twice, same hashes),
independent check OK (rwd decodes to bin, file checksum, header, byte sum 0 mod 256, 1 part number), diff vs stock =
the 110 bytes of D1, diff vs v5 = 68 MAF data bytes only (points 26-62); emulation EmuMaf v6 = v5 up to A/D 376,
stock x1.08 from A/D 488, no stop, no overflow (src\emu_v6_raw.txt); self test with v6 51/52 (only the expected v1
2-byte check; docs\logs\2026-11-01_v6_selftest), exe deployed = built E2DFC687..., files read-only,
flash\v6_maf_taper.rwd = work copy. On the car day, redo A2 + A3 + A5 (one command, below).

## Part A: at home, before going to the car
- [ ] A1 Laptop charged, charger with you (laptop on AC power during the flash).
- [ ] A2 FIRST: tool `FlashToolTest_v2\FlashToolTest.exe` hash = `src\build\FlashToolTest.exe` = E2DFC687...
      (2026-10-30 progress bar fix; previous 97AB3006 kept in _archive_old_builds\FlashToolTest_v2_97AB3006)
- [ ] A3 `FlashToolTest_v2\FLASH_DRYRUN.txt` present (dry run ON until gate D4), `FLASH_PIN12.txt` absent.
- [ ] A4 Self test: with the v6 files 51/52, the ONLY fail allowed is "v1 differs from stock by 2 bytes" (v6 has 110).
      Log of 2026-11-01 in docs\logs\2026-11-01_v6_selftest.
- [ ] A5 Files present and hashes unchanged: `flash\v6_maf_taper.rwd` 49724F5D..., `stock\37805-R42-A240-M1.RWD.gz`
      6E4CACCB... (the stock file is the recovery file), `flash\v5_maf115.rwd` 804C3B6E... (fallback to v5).
      A2 + A3 + A5 in one command (PowerShell terminal, in the project folder):
      `Get-FileHash FlashToolTest_v2\FlashToolTest.exe,src\build\FlashToolTest.exe,flash\v6_maf_taper.rwd,flash\v5_maf115.rwd,stock\37805-R42-A240-M1.RWD.gz | Format-Table Hash,Path; Test-Path FlashToolTest_v2\FLASH_DRYRUN.txt; Test-Path FlashToolTest_v2\FLASH_PIN12.txt`
      Expected: E2DFC687 x2, 49724F5D, 804C3B6E, 6E4CACCB, True, False.
- [ ] A6 Head unit shutdown method ready (ADB commands tested, or the plug/fuse known).
- [ ] A7 Car NOT driven to the flash place right before (engine must be cold, B2).

## Part B: car state (engine OFF)
- [ ] B1 Battery charged overnight. Charger connected and FORCED to 10 A mode (flash #1: 12.56-12.61 V that way;
      on the maintainer alone only ~11.9 V with the ignition ON, too close to the 11.8 V gate).
- [ ] B2 Engine cold (radiator fan must not start). Headlights switch OFF (not AUTO), HVAC, blower, radio off, doors closed.
- [ ] B3 Head unit shut down / disconnected.
- [ ] B4 HDS: codes read in ALL modules (screenshot). Clear ABS/SRS/PGM-FI codes, ignition OFF 10 s / ON, lights out.
      Close HDS completely (it holds the adapter).
- [ ] B5 Brake fluid level OK (ABS 65-11).

GATE B: all green? If 65-11 comes back or a light stays on: find why first (not a flash blocker by itself, but note it).

## Part C: connection (ignition ON, engine OFF)
- [ ] C1 Open FlashToolTest_v2, select GODIAG - J2534 and SH7058-1MB | Manual (0x10).
- [ ] C2 Title shows the battery voltage. Watch it 3 minutes: STABLE (not dropping) and >= 11.8 V.
- [ ] C3 Connect ECU: VIN XXXXXXXXXXXXXXXXX, Calibration ID 37805-R42-A240.
- [ ] C4 J2534 Command `22,F1,90,F1,81,F1,8C,F1,87` (multi-frame request over raw CAN): answered, adapter still OK.

GATE C: voltage stable >= 11.8 V, VIN + cal ID right, multi-frame OK.

## Part D: dry run, then the flash
- [ ] D1 Flash Firmware -> `flash\v6_maf_taper.rwd`. The file check must show: OK, part number 37805-R42-A240,
      internal checksum OK (0x28, sum 0 mod 256), file checksum 0x06A752C9, differences with stock: 110 bytes at
      0x08400, 0x0B13F, 0x0B141, 0x0B2C3, 0x13BFB, 0x13BFD, 0x13BFF, 0x13C01, 0x13C03, 0x13C05, 0x13C07, 0x13C09,
      0x13C0B, 0x13C0D, 0x13C0F, 0x13C11, 0x13C13-0x13C15, 0x13C17, 0x13C19-0x13C1D, 0x13C1F-0x13C21, 0x13C23-0x13C25,
      0x13C27-0x13C29, 0x13C2B-0x13C2D, 0x13C2F-0x13C35, 0x13C37-0x13C4C, 0x13C4E-0x13C6F, 0x1419D, 0x1419F,
      0x141A1-0x141A3, 0x15AC3, 0x15AC5, 0x15AC7, 0x15AC9, 0x15ACB (same list as the 2026-11-01 v6 self test).
- [ ] D2 Dialog says DRY RUN. Yes -> result "DRY RUN: unlock OK". Read flash_logs\flash_<date>.log: seed/key OK,
      battery logged.
- [ ] D3 Voltage still stable >= 11.8 V.
- [ ] D4 Remove `FLASH_DRYRUN.txt` (check it is gone, check the exe hash again).
- [ ] D5 Flash Firmware -> `flash\v6_maf_taper.rwd`, same file check, dialog says THE ECU WILL BE ERASED. Yes.
- [ ] D6 Touch nothing until the final message (~3 minutes). The log shows a battery reading every 50 blocks.

## Part E: after
- Success: ignition OFF 10 s, ON, start. Connect ECU (cal ID A240). HDS: codes in all modules, clear them.
- Failure after erase: ignition stays ON. Unplug/replug the adapter if "adapter not available". Flash
  `stock\37805-R42-A240-M1.RWD.gz` (answer Yes to "Recovery flash"). Proven on 2026-10-24.
- Failure before erase: the ECU did not change. Read the log, find why, no retry until understood.
- Put FLASH_DRYRUN.txt back after the flash.
- If v6 runs badly (rough idle, hesitation, check engine light, WOT lambda leaner than cmd 0.848): flash
  `flash\v5_maf115.rwd` back (same list). Stock intake refitted: `flash\v3_fuelcut20.rwd`.

## Part E6: how we know v6 worked
Same drive as E5 (warm, HDS Snapshot every ~2.5 min: idle, cruise MAP 30-45 / 45-70, 2-3 WOT pulls in 3rd
4000-6000 rpm). Copy the .dat files to docs\logs\<date>_v6\, decode, then `compare_sessions.py <v6 raw>` and
`maf_corr.py work\v6_maf_taper.bin <v6 raw>` (factor vs the v6 table, expected ~1.00 per point; maf_corr.py applies
LT in open loop too, so for WOT read lambda vs cmd directly). Expected: idle / light load same as v5 (0.96-1.02);
MAP 45-70 and >= 70 total ST x LT 0.96-1.04 (v5 0.91-0.94); WOT measured lambda ~0.81-0.83 (v5 0.76-0.78, cmd 0.848),
NEVER leaner than 0.848; WOT ignition ~1 deg more than v5; no DTC.

## Part E5: how we know v5 worked
1. Right after the flash: idle warm, HDS PGM-FI Data List: note LT (KLAFAVE) and ST. If LT stayed ~1.05-1.09 the
   mixture is a bit rich until it relearns (safe side); LAMBDA should still read ~1.00 in closed loop.
2. Drive 20-30 min warm, same HDS Snapshot drive as 2026-11-01 (idle, cruise 30-45 / 45-70 kPa, a few WOT pulls
   in 3rd 4000-6000 rpm only when warm). Copy the .dat files to docs\logs\<date>_v5\.
3. Decode, then `py -I src\hds_snapshot\compare_sessions.py <raw dir>` and `py -I src\hds_snapshot\maf_corr.py
   work\v5_maf115.bin <raw dir>`. Expected: total correction ST x LT ~0.95-1.05 in every load bin (was 1.15-1.21);
   WOT measured lambda close to cmd 0.848 (was 0.899-0.935); no DTC (P0101/P0171 family).
4. If the correction stays > 1.05 or < 0.95 in one zone: a second, smaller per-zone table change (new build).

## Part E4: how we know v3 worked
Same road test protocol as E3 below (warm, HDS Snapshot, lift-offs in 2nd/3rd at 2500-3400 rpm, clutch OUT, no pedal
for 2 s; a few above 4200 rpm; a few right after an upshift; stopped blips). Copy the .dat files to
docs\logs\<date>_v3\. Expected: FCDEC ~0.55-0.75 s moving below 4000 rpm (v2 0.74-1.03, median 0.81), ~0.5-0.6 s
above 4000 rpm (v2 0.69-0.77), right after a shift the same as without a shift, stopped unchanged 0.35 s.
`mapsettle.py v2\all.csv:40 v3\all.csv:20:20`: MAP settle still ~0.4 s, "FCDEC - settle" ~0.2 s (v2 0.41).
Then `tickfit2.py baseline\all.csv:80 v2\all.csv:40 v3\all.csv:20:20` (3 tick counts settle crank vs time).
Feel: shorter rev hang on lift-off; tip-in unchanged (same as v2).

## Part E3: how we know v2 worked (done 2026-10-30, kept as the protocol)
Road test protocol (same as the 2026-10-25 baseline so the numbers compare; legal speeds only, a passenger handles
the laptop or stop safely to save):
1. Engine WARM (ECT 84-90 C, after the idle relearn / fan). Laptop on, HDS PGM-FI Data List running.
2. Snapshot (F8): Manual trigger, Record Time 3 Min, trigger slider fully RIGHT (saves the 3 min BEFORE the click).
   Click the camera every ~2.5 min so the windows overlap (each save has a ~2.5 s gap).
3. Stopped, neutral (2-3 times): blip to ~3000-3500 rpm and release (FCDEC check stopped, was 0.35 s).
4. Tip-ins in 1st/2nd at 5-30 km/h, 1000-2000 rpm, light pedal 25-40 % (the big lags were here: up to 1.5 s);
   and a few big ones 65-100 % at 25-50 km/h. Hold the pedal still ~2 s each time.
5. Lift-offs in 2nd/3rd at 2500-3400 rpm (25-50 km/h): pedal from > 15 % to 0, clutch OUT, wait 2 s without touching
   the pedal (no pedal back before the cut). About 10. Was FCDEC 1.2-1.4 s, expected 0.73-0.92 s.
6. A few lift-offs above 4200 rpm in 2nd (unchanged control, was 0.75-0.85 s) and in 4th (already 40).
7. Note any jerk on tip-in (1st/2nd) or harsh lift-off. Save the last snapshot.
8. Copy C:\Teradyne\HDS\Stored Files\Automotive\Snapshot\*.dat of the day to docs\logs\<date>_v2\ (Claude decodes
   them with src\hds_snapshot snap.py -> merge.py -> ana2.py / tickfit.py and compares with the baseline).
- Same HDS Snapshot drive as the 2026-10-25 baseline (warm, lift-offs in gear 2-3 at 2500-3400 rpm, tip-ins at
  5-30 km/h). Expected: FCDEC 0.73-0.92 s after lift-off moving below 4000 rpm (was 1.1-1.4 s), unchanged above
  4000 rpm and in 4th/5th (already 40), pedal lag shorter (was 0.23 s median). Decode with the same scripts
  (src\hds_snapshot), then `py -I src\hds_snapshot\tickfit.py <all.csv>`: the new delays also tell whether the
  timer ticks on time or on crank (open point, KNOWLEDGE "Confidence research").
- Expected feel: sharper pedal in 1st/2nd, rev hang shorter on slow lift-offs; quick shifts barely change (the
  overrun throttle opening is NOT changed: Honda oil consumption fix, bulletin 11-049). 0-50 km/h ~0.05 s (model).

## Part E2: how we know v1 worked (no dyno, no public road test)
1. Bytes in the ECU (~97 %): all 496 blocks acknowledged with their counter, 71 01 FF 01 positive, and the car
   starts and runs normally (the ECU checks the checksum at boot), so it runs exactly the v1 image (which contains 240).
2. Direct read-back (optional, harmless read, ~30 % the ECU supports it): service 23 (read memory by address) at ROM
   0xB2C2, expected 00 F0 (240). If refused, nothing happens.
3. Behavior (~85 %): proven by emulation of the real ECU code (stock cuts above 200, v1 above 240). Not proven: km/h
   units, a possible second limiter.
4. 100 % only above 200 km/h on a closed track or a dyno, never on public roads.

## Part F: road test (later)
- Tires speed rating checked (V = 240 km/h).
- Lean condition (+15-20 % trims) not fixed: no long full throttle.
- Expected: no cut at 200 km/h. Note where/if any limit appears (a second limiter is possible).
