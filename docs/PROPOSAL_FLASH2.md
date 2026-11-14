# Flash #2 proposal -- 2026-10-25

Status: A2 + C BUILT AND VERIFIED, NOT FLASHED: flash\v2_tipin_fuelcut.rwd (SHA256 BD4D4F38...), details and
results in KNOWLEDGE.md "Flash #2 file". Baseline log done. Left: the car-day checklist (CHECKLIST_FLASH_DAY.md).

## What the research found (details in KNOWLEDGE.md, "Electronic throttle and rev hang research")
Chain, every 3.3 ms (Pphi = 20 MHz confirmed by the CAN bit timing, 95 %):
pedal 0x3DB70 -> 2AB6/2ACE (no delay in normal driving) -> 0x56830 map -> demand 3CFA
-> tip-in ramp 0x56F6A (output 4178) -> min(gear limit = flat 16660, 4178) -> 0x573A8 idle air add
-> 40B0 request -> 0x5752A lift-off decay -> 3DA2 -> throttle conversion 0x57BB0.

| Stage | Effect in emulation | Delay / hang it adds |
|---|---|---|
| 0x3DB70 pedal slew 0x993C | only on a D/E sensor mismatch | none in normal driving |
| 0x56830 speed smoothing | holds the speed/RPM axes, not the pedal | none on the pedal |
| per-gear limit 0xAC9C.. | tables flat (32767), cap 16660 | none |
| tip-in 0x56F6A | S-shaped ramp on a demand rise > 50 per cycle | 0.2-0.6 s to reach a big step (counter tick rate unknown) |
| dashpot 0x502F4 | fires only when RPM < 1000 warm (1700 cold) | idle catch only |
| idle add 3DC2 (0x5083A) | only in idle state 6 | idle only |
| lift-off decay 0x5752A | ~5 % per cycle, then 0 | ~0.1 s |

Conclusion: the pedal delay matches the tip-in ramp (65 %). The rev hang is NOT explained by the throttle path
(decay 0.1 s, dashpot idle-only): look at decel fuel cut delay / ignition next (new research item).

## Candidate changes (emulated on the stock code, ROM patched in the emulator only)

### A2 -- tip-in ramp 2x faster (recommended first candidate)
Table 0xAB40 (ramp step vs counter 0xFFFF7852), data at CPU address 0x1419C-0x141A3 (file offset in the
.0x8000.bin = address - 0x8000): 6, 30, 100, 300 -> 12, 60, 200, 600 (4 words, 8 bytes) + checksum byte 0x8400.
All addresses in this file are CPU addresses.
- Emulation (src\emu_tipin_AB40x2_raw.txt): gear 2 2500 rpm 57/109/187 -> 42/79/135 calls (tick 1/3/8), about
  -25 %; gear 4 88 -> 63; gear 1 118 -> 86; gear 5 65 -> 47. Small demand changes (< 50/cycle) unchanged.
- Only user: descriptor 0xAB40 (pointer at 0xAB48), read only inside 0x56F6A (FindRefs ABB8/AB20/AB40/1419A).
- Risk: more driveline shunt on tip-in (the ramp is an anti-jerk filter), mostly 1st/2nd. Won't-damage 85 %.

### A1 -- tip-in ramp off (aggressive, not recommended first)
0xABBC (threshold) 50 -> 32767 (1 word). Emulation: no ramp at all, request follows the demand at once.
Risk: harsh tip-in, drivetrain jerk, more wear on mounts. Won't-damage 70 %.

### B -- lift-off decay 2x faster (low value; ruled out by the car log: throttle back to idle in 0.3 s)
Tables 0xAC68 / 0xAC80 data 0x145A0-0x145AB and 0x145D0-0x145DB: 51 -> 102 (12 words). Emulation
(src\emu_decay_102.txt): moving 3000 rpm, release -> 0 in ~15 cycles instead of ~30 (0.05 s instead of 0.1 s).
Only users: descriptors 0xAC70 / 0xAC88, read only in 0x5752A. Probably not felt. Not recommended unless the car
log shows a throttle hang.

### C -- decel fuel cut entry delay shorter (rev hang, recommended with A2)
Car log 2026-10-25: the rev hang is the delay before decel fuel cut when moving (1.2-1.4 s vs 0.35 s stopped),
not the throttle (back to idle in 0.3 s). Table 0xB158 (delay ticks per gear), data 0x15AC2-0x15AC7 (gears 1-3):
80, 80, 80 -> 40, 40, 40 (3 words, 3 changed bytes) + checksum byte 0x8400. Gears 4-5 already 40.
- Emulation (EmuFuelCut.java): 79 -> 39 ticks in gears 1-3. Expected on the car: ~1.3 s -> ~0.8 s (same as the stock
  behavior above 4000 rpm or in 4th/5th gear, which are already 40).
- Only user: descriptor 0xB158 inside 0x580DE. Gear 0 (clutch/neutral) uses the gear 1 value, so gear 1 must change.
- Risk: earlier fuel cut on a lift-off IN gear 1-3 = slightly sharper decel / driveline shunt (the delay is a
  driveability filter). Uses the same value Honda uses for 4th/5th and above 4000 rpm. No effect on the fuel cut
  exit (re-tip) or on the stopped case. Won't-damage 90 %.
- More aggressive (20 = ~0.55 s) emulated too (19 ticks); not recommended first.
- 2026-10-25 research: pedal input of the cut (0xFFFF3D0C) traced; FCDEC = 0x4341 latched flag (90 %); table named
  "Overrun fuel cut delay" in the TSX definition; 40 ticks already observed on this car at 0.67-0.81 s (> 4000 rpm).

### D -- overrun throttle opening lower: DROPPED
0x4F52A, tables 0x1232E (8 pts) and 0x1230E: second rev hang lever (MAP 18 vs 9 kPa before the cut). Bulletin 11-049
(rev. 2011-11-16) lists our 37805-R42-A24 as the oil consumption fix for the 2011 M/T 2-door, and A240 raised these
tables vs A220. Lowering them (to 0 or to A220) would partly undo that fix on a 291k km engine. Not done.
- Also found: decel cut inhibit 0xFFFF2BDC from a received frame of another module (same in stock and v2).

## Open points before any build
- Car baseline log (HDS): measure the real pedal-to-throttle delay and the RPM drop time on a shift.
- Tick rate of counter 0xFFFF7852 (and all 0xFFFF76xx-78xx timers): not in any interrupt handler that the emulator
  can run (EmuScan, 31 handlers), not in 0x4BFFC; probably the background loop. Changes the ramp time x3.
- Enable conditions of the ramp on the car (0xFFFF3FBE = 2, 0xFFFF3F0A = 0, 0xFFFF4135 = 0, speed >= 5).
- Full CLAUDE.md checklist (validator, checksum, diff, SHA256, self test, dry run, battery, recovery).
