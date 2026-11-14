# 2011 Accord coupe: to do

## RULE FOR EVERY FLASH (most important)
Nothing is flashed until it is right with 100% confidence and test proven:
- every change understood in Ghidra (what reads it, what it controls), nothing assumed
- stock vs modified behavior emulated on the real ECU code, results compared and explained
- file checked by the validator (checksums, part number, diff vs stock = only the intended bytes)
- flash tool self test passing, then a dry run on the car (unlock only)
- if any doubt is left, we do not flash

## Flash #1: speed limiter 240 km/h -- DONE (2026-10-25)
- [x] Flashed flash\v1_speedlimiter.rwd with FlashToolTest_v2: 496/496 blocks, 71 01 FF 01, car runs normally,
      PGM-FI no DTC, SRS 56-31 cleared, ABS 61-11/65-11 history only (pre-existing). Battery 12.56-12.61 V on the
      charger forced to 10 A. Full story in docs/KNOWLEDGE.md.
- [ ] Road test on a closed track or dyno (public road not possible): confirm no cut at 200 km/h. Tires V-rated,
      no long full throttle while the lean condition is not fixed.

## Flash #2: tip-in ramp x2 (A2) + decel fuel cut delay 80 -> 40 (C) -- FLASHED 2026-10-30, SUCCESS
- [x] Flashed flash\v2_tipin_fuelcut.rwd: 496/496, 71 01 FF 01, no PGM-FI DTC, no MIL (KNOWLEDGE.md)
- [x] Built flash\v2_tipin_fuelcut.rwd (src\build_v2.py), verify_rwd OK, emulated on the built file, self test
      51/52 (only the hard-coded v1 diff check, expected), SHA256 in KNOWLEDGE.md, read-only (2026-10-25)
- [x] Home prep re-checked 2026-10-25 (hashes, read-only, exe, dry-run file, checksum, diff, self test 51/52):
      PREP STATUS in CHECKLIST_FLASH_DAY.md
- [x] Car day: docs\CHECKLIST_FLASH_DAY.md with flash\v2_tipin_fuelcut.rwd (dry run first) -- 2026-10-30
- [x] After: same HDS Snapshot tests as the baseline, compare pedal lag and FCDEC delay (2026-10-30: FCDEC median
      1.27 -> 0.87 s, tip-in lag median 0.23 -> 0.11 s; KNOWLEDGE "Flash #2 FLASHED")
- [x] Slow tip-ins at 5-10 km/h ~1000 rpm "lag up to ~1.1 s": checked sample by sample, not a delay (2-stage pedal,
      target rising with rpm, MAP already 83-88 kPa, clutch). Nothing to change (KNOWLEDGE, 2026-10-30)
- [ ] Later: "two knocks" on tip-in / lift-off = driveline shuffle (~4-5 Hz): check engine mounts, then look at
      Honda's anti-jerk (tip-in IG dip to 0..-4 deg, lift-off throttle close + cut transition)

## Flash #3: v3_fuelcut20 = v2 + decel fuel cut delay 40 -> 20 (table + gear change floor) -- FLASHED 2026-10-30, SUCCESS
- [x] Flashed flash\v3_fuelcut20.rwd 19:44: 496/496, 71 01 FF 01 (KNOWLEDGE "Flash #3 FLASHED")
- [x] After the flash: start (warm idle ~1000), codes in all modules (56-31, 65-11, 61-11, U0100, U0127, B1234,
      B1241), cleared: only ABS 65-11/61-11 (known) + U0127 (no TPMS sensors) remain
- [x] Idle relearn until the radiator fan (done, user confirmed 2026-10-30)
- [x] HVAC codes B1234 / B1241: heat + A/C work fine, not back after the HVAC test (2026-10-30) = set by the flash
- [x] Tool: progress bar stuck at 95 % FIXED 2026-10-30 (DarkProgressBar.LockGoingBack = false), self test 51/52,
      deployed = built E2DFC687 (KNOWLEDGE). Checklist A2/A5 updated. Watch the bar on the next flash or dry run
- [x] Built flash\v3_fuelcut20.rwd (src\build_v3.py), verify_rwd OK, emulated on the built files (19 ticks in every
      case, src\emu_v3file.txt), self test 51/52 (only the hard-coded v1 check), SHA256 in KNOWLEDGE.md, read-only
      (2026-10-30)
- [x] Car day: docs\CHECKLIST_FLASH_DAY.md with flash\v3_fuelcut20.rwd (dry run first) -- 2026-10-30
- [x] After: HDS Snapshot lift-offs 2026-10-30 (docs\logs\2026-10-30_v3): FCDEC median 0.62 s (v2 0.81), above
      4000 rpm 0.47-0.54, "FCDEC - settle" 0.41 -> 0.18, MAP settle unchanged 0.41. Tick = crank (rms 0.066 vs 0.099)
- [x] The ~0.4-0.5 s rest of the delay TRACED (2026-10-30): MAP must settle first (|dMAP| < 0.8 kPa, 0xB1F4), in
      series with the timer -> v3 keeps its full gain. 0xB1F4 left alone (Honda guard, KNOWLEDGE)

## Open from flash #1
- [ ] Check what "Market Cal Index" 1 -> 5 means (changed after the 2026-10-24 recovery flash; 6 on 2026-10-25)
- [ ] ABS 61-11 / 65-11 would not clear in HDS (65-11 pre-existing, ABS light never on): retry later, low priority
- [ ] Head unit draws ~0.1 A+ (seen on reboot); for future flashes use the 10 A charger mode, or shut it down via ADB
      (unknown if the MCU wakes it back up -- give brand/model + USB/Wi-Fi to prepare)

## Engine
- [x] Log analysis of the lean condition (2026-10-30, see KNOWLEDGE): flat proportional +11-16 % from idle to full
      load, no vacuum-leak signature, rear O2 confirms real stoich after correction.
- [ ] Find the lean condition cause: fuel pressure gauge test (get the spec from the service manual first),
      clean the MAF / refit the stock intake and compare trims; smoke test only if cheap (low probability now)
      (previous owner: "don't drive with little fuel" -> test pressure at idle AND under load, full vs low tank)
- [x] Fuel pump replaced 2026-11-01 + logs: correction unchanged (~1.17-1.21) -> the pump was not the cause
- [x] Intake tube measured: kit 7 cm vs stock ~6 cm inside (MAF under-reads, matches the lean trims)
- [x] MAF recal step 1: MAF table found (descriptor 0xA75C, data 0x13BF2, 64 pts), proven on logs, 2 code users
- [x] MAF recal step 2: correction ~1.15 flat (CL 1.11-1.24, WOT 1.12-1.24), 0xA748 = separate 2D table, 0x700F0 = data record
- [x] MAF recal step 3: work\v5_maf115 built (v3 + MAF table x1.15), verify_rwd OK, read-only, not in flash\
- [x] MAF recal step 4: EmuMaf v3 vs v5 on the built files: v5 = v3 x1.15 (A/D 232-952), no stop, no overflow
- [x] MAF recal step 5 (home part): self test v5 51/52 (expected), flash\v5_maf115.rwd, checklist updated
- [x] MAF recal step 5 (car): flash #4 v5_maf115 SUCCESS 2026-11-01 16:32, car runs v5
- [x] After flash #4: static test (idle/2500/3500): total 1.04 / 1.02 / 1.00 (was 1.20 / 1.15), see KNOWLEDGE
- [x] Part E5 driving log: idle/light 0.96-1.02 OK; load 0.91-0.94 and WOT lambda 0.76-0.78 vs 0.848 = 5-9 % rich
- [x] v6 step 1: need per point (maf_need.py), curve proposed: 1.15 to A/D 376, linear to 1.08 at 488, 1.08 above
- [x] v6 step 2: build_v6.py -> work\v6_maf_taper.bin/.rwd (SHA 4BBAD449 / 49724F5D), verified, read-only
- [x] v6 step 3: emulation EmuMaf on v6: = v5 up to A/D 376, x1.08 vs stock from 488, no stop/overflow (emu_v6_raw.txt)
- [x] v6 step 4: self test 51/52 (expected), flash\v6_maf_taper.rwd, checklist rewritten for flash #5
- [x] v6 step 5: flash #5 v6_maf_taper SUCCESS 2026-11-01 17:31, car runs v6
- [x] After flash #5: codes unchanged (no new), idle ST 0.98 LT 0.98 lambda 1.00, knock 0, misfire 0
- [x] Part E6 logs: WOT lambda 0.806-0.840 (cmd 0.848), MAP>=70 0.976, MAP 45-70 low rpm 0.916 (table can't fix), misfire 0 -> keep v6
- [ ] Watch misfire counters (v5 drive: cyl1 2, cyl4 3, no DTC; same level as before v5)
- [ ] Clear the old codes (SRS 56-31, ABS 65-11 / 61-11) if not done
- [ ] Knock retard at part-throttle tip-in 1400-2500 rpm (up to ~12-14 deg, same since stock 25/10, KNOWLEDGE
      "General health check"): try a tank of 91+ octane and compare KNRTD with the same logs; check valve clearance
      (291k km, no hydraulic lifters). Analysis only, no flash change.
      2026-11-07: traced in the ROM (KNOWLEDGE "KNRTD / KIGKREF TRACED"): KNRTD is mostly programmed retard = learned
      reference x load map, not a fault. Compare fuels with KIGKREF level and rises: log again after more driving on
      super (below 88 = better than ever seen on 87). Watch LT (0.875 at the end of today's log, still falling; the 1/11 0.977 was not settled). v7 MAF table only once LT is stable on the chosen fuel. No flash change.
      2026-11-07 user reports a stronger fuel smell this week, like running rich (place and start date not known yet). FIRST exclude a leak at the pump module / lines (pump replaced 2026-11-01, tank now full), then open loop richness (warm-up, full load), purge / canister, fuel pressure. The ECU only corrects in closed loop.
      Smell is at the exhaust, on a cold start. Logs: not rich from 82 s after start (lambda 1.00). Next: cold start log from key on (first 82 s never logged on v5/v6).
      2026-11-07 cold start logged: v6 NOT richer than stock at cold start, lambda 1.00 from 13 s. Real finding: the ECU removes ~18 % fuel since this week (total 0.82 vs 0.98 on 1/11), purge closed. Next: oil dipstick (level, fuel smell), then purge valve test, then log again on 87. No v7 until the cause is known.
      2026-11-07 logs: at warm idle MAF reading and final injection per air are the SAME as 1/11, lambda 1, only ST x LT moved. Trace TOUT and the trim chain in the ROM before the pressure test.
      Done in part: TOUT = RAM 0xFFFF43EE / 2 but it does NOT follow ST in the logs, so the "same fuel" result is withdrawn. Back to car tests: oil, purge pinch, then fuel pressure. Manual disassembly of 0x23xxx only if needed.
      ROM 2026-11-07: real ST = 0xFFFF4472, injection = 4-cylinder array 43EE (writer by index, not found). Trim entry into the pulse still not found.
      NEW LEAD: last fill overfilled 2-3 clicks, and the excess first shows in the log after that fill -> check the purge valve / charcoal canister FIRST (leak test when closed), then fuel pressure.
      BUT the smell was there BEFORE that fill: the overfill is not the start. Order: oil dipstick (free), purge valve test, fuel pressure test, injectors.
      Oil dipstick done 7/11: no clear fuel smell, light amber, level at / just above full mark (baseline: recheck in ~1 week, same conditions; rising = fuel in oil). Owner: level unchanged vs last week, high only from parking slope -> fuel in oil unlikely.
      Logs 7/11: excess ~same % at idle, cruise and load (proportional, not a fixed leak); purge effect normal (3-5 %). Next: fuel pressure test with a gauge (garage), then injectors. Optional log: hot restart after 15-20 min off.
      Owner cannot test fuel pressure. Open-loop test 7/11: full throttle only 2.7 % richer than 1/11 -> pressure idea holds ONLY if the long-term correction applies in open loop; otherwise a fixed leak fits better. Next: find in the ROM whether LT applies in open loop. DONE 7/11: the HDS long-term value (9304) is NOT used by the injection at all (only learning, DTC monitor, display); real correction = ST: 1.000 (1/11 v6) -> 0.922 (7/11) = ~8 % excess in closed loop, ~3 % at full throttle (see KNOWLEDGE "ROM ANSWER"). Pressure idea weaker. Split by purge (7/11): ~3-4 % flat (purge closed + full throttle), cause open (premium fill: the brand says all its gas may contain up to 10% ethanol, so ethanol-free NOT proven); + ~4-5 % extra only with purge open = more canister vapour (full tank / overfill). Smell not explained by the mixture -> owner: look and smell around the pump access under the rear seat (seal, lock ring, connectors), engine off, no flame. Next fill: regular, stop at first click, log. Oil change soon (due by time) + log after it as a test. Next: purge valve.
      OWNER 7/11: the smell is a RICH EXHAUST smell (not raw fuel). Ask the owner: smell only after hard accelerations, or also at idle / steady cruise?
      OWNER DECISION 7/11: NOTHING is prepared or flashed until the cause of the drift is known.
- [ ] NEXT TUNE (only after the drift cause is known, full checklist): MAF transfer table high-flow part x1.08 -> x1.04
      (A/D >= 488 and the taper from 376 to 488 rescaled to end at 1.04). Low / mid flow stays as v6 (x1.15).
      Expected full throttle lambda ~0.85 (= Honda command 0.848) on the 1/11 baseline, instead of ~0.82 (v6 margin).
      Recompute from the latest logs before building (the drift may change the baseline). Optional: tip-in back toward stock.
- [ ] (Alternative) refit the stock intake (MAF in its original housing), drive 20-30 min warm, log, compare trims
      (py -I src\hds_snapshot\compare_sessions.py <raw dir>). If unchanged: fuel pressure gauge (only the pump was
      replaced: regulator and filter are the old ones), then injector flow test

## Research
- [ ] Rev hang: find the code in Ghidra, then flash #2
      - [x] Throttle sensors A/B, pedal D/E, final throttle/pedal, driver demand path found (2026-10-25, KNOWLEDGE.md)
      - [x] Candidate found: lift-off decay in 0x5752A (tables 0xAC68/0xAC80 moving, 0xAC74/0xAC8C stopped) -- 55 %
      - [x] Emulate 0x5752A stock: lift-off hold = floor (~25 % at 3000 rpm moving warm) ramped to 0 in ~30 cycles,
            0 at once with fuel cut (src\emu_decay.txt). Real but partial: 45 % it is the felt rev hang
      - [x] Task cycle time: vector 151 = ATU CMI7D, 3.3 ms (if Pphi = 20 MHz, 75 %), 0x56830 runs every interrupt
            -> 0x5752A decay ~0.1 s: too short to be the whole felt hang (KNOWLEDGE.md)
      - [ ] Compare with the hang felt on the car (datalog RPM drop time during a shift, if possible)
- [ ] Pedal delay (KTuner "DBW responsiveness"): emulate the tip-in ramp 0x56F6A and the pedal slew path in 0x3DB70
      (ROM 0x993C = 5/cycle) to measure the delay they add; same rules as above before any change
      - [x] Emulated 0x56F6A (2026-10-25): S-shaped ramp, 0.2-0.6 s to reach a big demand step (counter tick rate
            unknown); 0x993C slew = sensor mismatch path only; speed smoothing / gear limit add no delay
      - [x] Writer of 0xFFFF4162 = previous demand (0x56980); writer of 3DC2 = 0x5083A (idle only); Pphi 20 MHz
            confirmed by the CAN bit timing
      - [ ] Tick rate of counter 0xFFFF7852 (not in any interrupt handler; probably the background loop)
            2026-10-25: fuel cut function reached from vector 135 handler 0x2C37A (source "reserved" in the manual),
            decrementer of 0xFFFF76C0 not found statically, log fit can't separate time vs crank. Only a live RAM read
            on the car or the flash #2 log can settle it (not needed for flash #2: both models give 0.73-0.92 s).
      - [x] Candidate changes emulated, draft in docs\PROPOSAL_FLASH2.md (A2 = tip-in table 0xAB40 x2 recommended)
      - [ ] Rev hang: throttle path ruled out (decay 0.1 s, dashpot idle only): research decel fuel cut delay /
            ignition retard on lift-off
      - [ ] Check nothing else holds the throttle open after lift-off (0x57BB0 conversion, idle air / dashpot)
            -> FOUND in the log (2026-10-25): moving, target holds 6.7 deg at 3250 rpm / 9.3 at 4800 (stopped 3.3),
            MAP 18 vs 9 kPa = overrun throttle opening (Hondata/KTuner rev hang setting). Trace it in Ghidra (read only).
            -> TRACED 2026-10-25: 0x4F52A, tables 0x1232E / 0x1230E (KNOWLEDGE "Confidence research"). Honda RAISED
            them in A240 vs A220. A240 = the bulletin 11-049 oil consumption fix (listed for the 2011 M/T 2-door).
      - [x] Option D (lower the overrun air) DROPPED 2026-10-25: it would partly undo Honda's oil consumption fix.
      - [ ] Only then: decide the change, emulate stock vs modified, full CLAUDE.md checklist
- [x] Baseline log done 2026-10-25 (HDS Snapshot, decoded; docs\logs\2026-10-25_baseline, KNOWLEDGE.md):
      pedal lag 0.23 s median moving (up to 1.5 s at low speed); rev hang = decel fuel cut 1.2-1.4 s late when moving
- [x] Rev hang: decel fuel cut entry delay found (0x580DE, timer 0xFFFF76C0, table 0x15AC2 per gear 80/80/80/40/40),
      emulated stock vs patched (EmuFuelCut.java); option C in PROPOSAL_FLASH2.md
- [x] Rev hang: lift-offs with no decel cut = pedal back (0.6-1.9 %) before the 1.2 s delay ended (log, KNOWLEDGE.md)
- [ ] Old item: BEFORE flash #2: baseline log of normal driving on the stock ECU (RPM, speed, pedal, throttle, commanded
      throttle, MAP, coolant), same route/values again after the flash to compare. First try HDS Data List recording
      with the GODIAG (check duration + export); if not enough, add an OBD2 Mode 01 CSV logger to FlashToolTest
      (read-only, single-frame requests over the raw CAN + software ISO-TP path)
- [ ] Optional flash #3: VTEC (the generated definition address is wrong, find the real table first)
- [ ] Compare behavior with the KTuner firmware through Ghidra
- [x] Tuner docs checked 2026-10-30 (KNOWLEDGE "Tuner documentation for THIS car"): Hondata has no FlashPro for the
      US 08-12 Accord; KTuner supports it, base map contents not published
- [ ] Optional: read the ECU hardware label (expected 37820-R42-A24, in KTuner's supported list) next time it is visible
- [ ] Laptop "live tuning": test a tune without flashing every change, original ECU kept unflashed
- [ ] Rev limiter: keep the SAME rev limit (never go over it), but make the limiter softer so the engine does not
      fully cut and lose all power when it touches the limit: hold the RPM at the limit with a partial cut
      (example: cut only some cylinders/cycles, or ignition retard) instead of the full fuel cut. Never remove the
      limit itself (over-rev = engine damage). Was out of scope in the original plan: first find in Ghidra how the
      limiter works (fuel cut flags list at 0x15B5C, RPM thresholds), emulate stock vs modified like the speed
      limiter, then decide.
      - [x] 2026-10-30: FOUND = 0x58898, flag 0x4E40 cut 7100 / resume 6900 (or 7300/7100 if 0xFFFF3D0D set),
            full fuel cut, 200 rpm hysteresis; stopped protection down to 3500 (KNOWLEDGE "Rev limiter research")
      - [x] 0xFFFF3D0D = VTEC engaged (70 %): limit 7300/7100 with VTEC, 7100/6900 without; stopped 4000/3700
            proven by the logs (fc at 4105 rpm, 0 km/h). 0xFFFF3403 = fail-safe mode (not decoded, low priority)
      - [ ] Optional: confirm the moving limit (7100 or 7300) with an HDS log on a closed track / dyno only
      - [x] Soft limiter options emulated 2026-10-30 (src\emu_revlim.txt): smaller hysteresis = 3 resume words
            0x15C06 / 0x15C0E / 0x15C32, cut points unchanged (KNOWLEDGE "Rev limiter research")
      - [x] User chose hyst100 (hyst50 dropped: outside Hondata's 100-300 range)
      - [x] v4 built 2026-10-30: work\v4_revlim100.bin/.rwd (src\build_v4.py), verify_rwd OK, diff vs v3 = 6 bytes +
            checksum, emulated on the built file (7301/7200, 7101/7000, 4001/3700; fuel cut 19 ticks; speed 240),
            self test 51/52 (only the hard-coded v1 check). SHA256 in KNOWLEDGE.md, read-only
      - [ ] Decide with the user whether to flash v4. If yes: copy to flash\ (read-only, hash check), dry run, then
            CHECKLIST_FLASH_DAY.md. Fallback = flash\v3_fuelcut20.rwd
