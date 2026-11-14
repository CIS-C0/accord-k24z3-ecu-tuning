# 2011 Accord coupe ECU project: PRIORITY RULES (apply in every chat and every branch of this project)

The car: 2011 Honda Accord EX coupe 2.4 K24Z3 5MT, VIN XXXXXXXXXXXXXXXXX, ECU 37805-R42-A240 (SH7058 1Mb, Keihin),
adapter GODIAG J2534. Working flash tool: FlashToolTest_v2 (source in src\HondaReflashTool-main).
READ FIRST in any new session: docs\KNOWLEDGE.md (all verified facts, addresses, protocol, tools, car state),
TODO.md (tasks), docs\CHECKLIST_FLASH_DAY.md (car day procedure). Update KNOWLEDGE.md whenever something new is proven.

## 1. Confidence score on everything
Every answer, step, check or change states TWO confidence scores (0-100 %) and why: "it works" and "it won't
damage/break anything". Never round a guess up.
Say clearly what is verified (with the evidence) and what is assumed.

## 2. Nothing is flashed until it is 100 % right and test proven
If any doubt is left, we do not flash. Checklist, ALL items, every time:

File
- FirmwareValidator OK: rwd header, rwd file checksum, start 0x8000 / size 0xF8000, CAN address 0x10,
  exactly one part number inside, supported by the file, ECUS_KEYS.txt entry present
- internal checksum: firmware area 0x8000-0xFFFFF byte sum = 0 mod 256 (verified on A240 + A220;
  the HondaReflashTool mod-255 algorithm is WRONG for this ECU)
- diff vs stock = only the intended bytes (+ the checksum byte at 0x8400), each one explained
- file SHA256 recorded, files kept read-only (stock, work, flash folders)

Change
- understood in Ghidra: what reads the bytes, what they control, no other code using them
- stock vs modified behavior emulated on the real ECU code (Ghidra EmulatorHelper), results compared and explained

Tool
- every code change fully reviewed for bugs (reread the whole diff, every path, every error case)
- self test passing: FlashToolTest.exe --selftest <stock.gz> <stock.bin> <custom.rwd> <custom.bin> <log>
- deployed exe hash = built exe hash, checked BEFORE anything else (a deploy can fail silently if the app is open)

Car
- Connect ECU: VIN and calibration ID read and matching
- DTCs read in all modules before and after
- battery: stable (not dropping) for 3 minutes with the ignition ON, >= 11.5 V minimum (tool refuses below),
  charged the day before; headlights OFF (not AUTO), HVAC/radio off, head unit shut down, engine OFF and cold
- laptop on AC power; no other program using the adapter (HDS closed)
- dry run on the car (FLASH_DRYRUN.txt) before the real flash
- recovery ready: verified stock .rwd.gz, recovery path known (Recovery flash prompt, unplug/replug adapter)

## 3. Lessons from the 2026-10-24 incident (ECU erased, recovered the same day)
- The GODIAG ISO15765 channel HANGS on any multi-frame request (8+ bytes). Only single-frame requests had been
  tested before the real flash, so the problem showed up only after the erase. Always test every message type
  (single and multi-frame, both directions) on the real car BEFORE an erase. Fix in use: software ISO-TP over a
  raw CAN channel (FlashEngine); its CAN filter needs the CAN_29BIT_ID flag.
- A test that seemed to prove multi-frame worked was a 7-byte (single-frame) message: check that a test really
  tests what it claims.
- A destructive step (removing the dry-run file) was chained after a deploy that failed: never chain a step
  after one that can fail; check each result first.
- A key byte-order bug was caught only by comparing with the real car logs: always test against real recorded data.
- Pin 12 programming voltage is not used (not needed, FLASH_PIN12.txt to enable).
- The adapter also hangs the same way AFTER a long raw CAN session: Connect ECU then gets no answer -> unplug/replug
  the USB. And Connect ECU gets no answer when the key is OFF: check the key before blaming the adapter.
- DarkMessageBox hid the Yes/No buttons when the text was long; flash dialogs now use the standard Windows MessageBox
  with No as the default button.

## 2026-10-25: flash #1 (speed limiter 240 km/h) succeeded. Current build: FlashToolTest_v2 (standard dialogs).
## 2026-10-30: flash #2 (v2_tipin_fuelcut = v1 + tip-in x2 + decel cut delay 40) succeeded. Car now runs v2.
## 2026-10-30 19:44: flash #3 (v3_fuelcut20 = v2 + decel cut delay 20, table + gear change floor) succeeded.
## 2026-11-01 16:32: flash #4 (v5_maf115 = v3 + MAF transfer table x1.15 for the 7 cm Amazon intake) succeeded.
## 2026-11-01 17:31: flash #5 (v6_maf_taper = v3 + MAF table x1.15 up to A/D 376, tapering to x1.08 from 488) succeeded.
## Car now runs v6. Fallback file: flash\v5_maf115.rwd. Stock intake refitted: flash\v3_fuelcut20.rwd.
Old intermediate builds moved to _archive_old_builds (do not use).

## 4. Working rules
- Run commands in the user's terminal (run_in_terminal) when possible; .ps1 scripts are blocked there by policy.
- Read the source of any tool function before asking the user to use it.
- Short answers, one step at a time during work on the car.
