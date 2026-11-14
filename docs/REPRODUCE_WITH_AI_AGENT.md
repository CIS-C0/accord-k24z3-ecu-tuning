# How this project was done with an AI agent, and how to reproduce it

This is the method, in the order it happened. The owner is not an ECU engineer: they supplied the car, the hardware,
the decisions and the hands on the car; the agent (Claude Code, desktop app, on Windows) did the reverse engineering,
the code, the tests and the analysis, one approved step at a time. Every claim below is backed by an entry in
[KNOWLEDGE.md](KNOWLEDGE.md).

> Read the [DISCLAIMER](../DISCLAIMER.md) first: you use all of this at your own risk. The method is general; the addresses, keys and files are
> for ECU 37805-R42-A240 only.

## 1. What you need

| Item | Used here | Notes |
|---|---|---|
| J2534 adapter | GODIAG J2534 (FW 1.14) | Cheap clone. Its ISO 15765 channel hangs on multi-frame requests; the forked tool works around it with raw CAN. |
| Battery charger | 10 A mode during the flash | Voltage must stay >= 11.5 V the whole time (about 3 minutes of transfer). |
| Windows laptop on AC power | Windows 11 | The J2534 driver is Windows only. |
| Honda HDS | 3.105 | DTCs in all modules, ECU identification, SnapShot data logging. Not required to flash. |
| Stock firmware | `.rwd.gz` from [HondaCalibFiles](https://github.com/bouletmarc/HondaCalibFiles) | Must match your ECU part number exactly; it is also your recovery file. |
| Flash tool | [CIS-C0/HondaReflashTool](https://github.com/CIS-C0/HondaReflashTool) (fork) | Built from source with MSBuild + Roslyn, no Visual Studio. |
| Ghidra | 12.2 portable + Temurin JDK 25 | Headless only. Processor `SuperH:BE:32:SH-2A`, base address `0x8000`. |
| Python 3 | any recent | Log decoding and analysis. |
| AI agent | Claude Code | Any agent that can read/write files and run commands can follow the same method. |

## 2. The working rules (the most important part)

The agent starts every session from zero. What made a several-week, safety-critical project work was a small set of
files it reads first and keeps up to date:

1. **[agent/CLAUDE.md](../agent/CLAUDE.md), the rules file.** Loaded automatically in every session. It holds:
   - the car, ECU and tool in three lines, and which files to read first;
   - **two confidence scores on everything**: "it works" and "it won't break anything", 0-100 %, with what is
     verified (and the evidence) versus assumed. This one rule stopped many guesses from becoming actions;
   - **the flash gate**: nothing is flashed until every item of a fixed checklist (file, change, tool, car) is
     green. It is listed in full in the file;
   - the lessons of the incident (section 3 there), so they are never forgotten;
   - working style: short answers, one step at a time on the car, read the tool source before asking the owner to
     click anything.
2. **[KNOWLEDGE.md](KNOWLEDGE.md), the knowledge base.** Every proven fact: protocol, file format, ROM addresses,
   RAM variables, emulation results, log results, car state, each with its evidence and a confidence score. The
   agent updates it whenever something new is proven, and the next session continues from it instead of
   re-deriving. Wrong earlier conclusions are corrected in place, with the reason.
3. **[TODO.md](TODO.md)**: open tasks and the owner's decisions (for example "nothing is flashed until the cause of
   the drift is known").
4. **[CHECKLIST_FLASH_DAY.md](CHECKLIST_FLASH_DAY.md)**: rewritten for each flash with the exact expected hashes,
   byte lists and gates, so the car day is mechanical.
5. **A persistent memory rule** ([agent/MEMORY.md](../agent/MEMORY.md)): the agent stops and asks for approval before
   every next step, analysis included; only updates to KNOWLEDGE/TODO need no approval.

If you reproduce this, write these files on day one, before any code.

## 3. The phases

### Phase 1: identify the ECU and get the stock file
- In HDS (or the tool's Connect ECU), read the VIN (`22 F1 90`) and the calibration ID (`22 F1 81`):
  37805-R42-A240 here.
- Download the matching `.rwd.gz` (and a sibling version, A220 here, for comparison). Record its SHA256, make it
  read-only. This file is your only way back if a flash fails.

### Phase 2: understand and fix the flash tool
- The agent read the whole upstream HondaReflashTool source before anything was run, then added
  `FirmwareValidator` (header, file checksum, start/size, CAN address, part number count, supported versions, key
  entry present), a dry-run mode (`FLASH_DRYRUN.txt` next to the exe), battery voltage checks, and per-flash logs
  of every CAN frame.
- Firmware format: `.rwd` header groups, decryption formula, file checksum. The decrypted `.bin` was checked byte for
  byte against the tool's own conversion.
- **Internal checksum**: the agent summed the firmware area of A240 and of A220: both are exactly 0 mod 256, which
  happens by chance 1 time in 65536. The upstream mod-255 rule was wrong for this ECU, so a file built with it
  would have been refused by the ECU (or worse). Fixed in `Class_Checksums.cs`.
- Build (from the tool folder):
  `MSBuild.exe FlashToolTest.csproj /t:Rebuild /p:Configuration=Debug /p:OutputPath=..\build\ /p:CscToolPath=<roslyn>\tasks\net472 /p:CscToolExe=csc.exe`
  (MSBuild from the .NET Framework 4 folder; Roslyn from its compiler NuGet package.)

### Phase 3: the incident, and what it changed
The first real flash attempt (2026-10-24) erased the ECU, then hung: the adapter's ISO 15765 channel
blocks on any request longer than 7 bytes, and the `34` request-download message is 11 bytes. Before the erase only
single-frame requests had been tried. The ECU stayed in its bootloader, which still answers the same unlock and
download sequence, so a rebuilt tool that does ISO-TP in software over a raw CAN channel flashed the stock A240 file
back the same day.

What came out of it, and is now in the fork and the rules:
- `Class_FlashEngine.cs`: software ISO-TP over raw CAN (`Protocol.CAN`, 29-bit IDs, pass filter with
  `TxFlags = CAN_29BIT_ID`).
- `Class_FlashSelfTest.cs`: a simulated ECU that replays the real UDS sequence (seed/key, erase, 496 transfer
  blocks, checks), run with `FlashToolTest.exe --selftest <stock.gz> <stock.bin> <custom.rwd> <custom.bin> <log>`.
- On the car, before any erase: a multi-frame request (`22 F1 90 F1 81 F1 8C F1 87`) must be answered, and a full
  dry run (unlock only) must pass.
- See [LESSONS_LEARNED.md](LESSONS_LEARNED.md) for the full list.

### Phase 4: find what to change, in the real code
For each wanted change (speed limiter, pedal response, rev hang after lift-off, rev limiter, MAF scaling):
1. Find candidate calibration addresses (community definition files are a start; three of their addresses were wrong
   here).
2. Ghidra headless on the decrypted `.bin`:
   `analyzeHeadless.bat <proj> <name> -import <bin> -overwrite -loader BinaryLoader -loader-baseAddr 0x8000 -processor SuperH:BE:32:SH-2A -noanalysis -scriptPath tools/ghidra_scripts -postScript <script> <args>`
   - `FindRefs.java <hex>...`: every instruction that loads the address (or stores through it);
   - `DecompAt.java start@target`: decompile the reader, with literal pools replaced by their values.
3. Confirm the address is read only by the expected code (no other users).
4. **Emulate** the real ECU function with Ghidra's `EmulatorHelper` (`EmuLimiter`, `EmuFuelCut`, `EmuTipIn`,
   `EmuRevLim`, `EmuMaf`...): stock vs modified bytes, same inputs, compare outputs. The change is only accepted when
   the emulated behaviour is exactly the intended one.
5. Cross-check with logs from the car where possible (the decel fuel cut delay was matched to HDS logs at ~10-12 ms
   per tick).

### Phase 5: build, verify, flash
- `tools/build/build_vN.py`: start from the previous version and check its SHA256, patch only the intended words,
  check the neighbouring bytes are unchanged, recompute the checksum byte at 0x8400, encrypt to `.rwd`.
- Verify independently (`verify_bin.ps1`, `verify_rwd.ps1`): decode the `.rwd` back, file checksum, byte sum
  0 mod 256, one part number, diff vs stock = exactly the listed bytes. Run the self test. Make the files read-only.
- Rewrite the flash-day checklist with the exact hashes and byte list, then on the car: battery on the charger,
  everything electrical off, DTCs read in all modules, Connect ECU (VIN + cal ID), multi-frame test, dry run, then the
  flash (about 3 minutes), ignition off 10 s, start, DTCs again (ABS/SRS log low-voltage / lost-communication codes
  during any flash; clear them).

### Phase 6: log, measure, iterate
- HDS SnapShot records `.dat` files. `tools/hds_snapshot/snapall.py` decodes all signals to CSV (record layout and
  descriptors were reverse engineered from the files); `merge.py`, `compare_versions.py`, `plot*.py` and the
  scripts in `tools/analysis/` do the rest.
- Each flash was followed by the same drive pattern (idle, steady cruise, gentle and full-pedal tip-ins, lift-offs)
  and compared with the previous version.
- The MAF change came from the logs: a short aftermarket intake read about 15 % low; the table was scaled, then
  tapered at high flow when wide-open-throttle logs showed it was 5-9 % rich there.
- Open at publication: a slow rich drift of the short-term trim after flash #5. The agent traced in the ROM that the
  long-term trim shown by HDS is not applied to injection, which corrected an earlier over-estimate (18 % -> about
  8 %). The owner decided: no new tune until the cause is known.

## 4. How the owner talked to the agent

Plain requests, one at a time, in their own language, for example (paraphrased, translated from French):
- "Find where the speed limiter is and what else reads it. Don't change anything."
- "Prepare flash #3 but don't flash. Show me the confidence scores."
- "Re-check the causes." / "You said the fuel is ethanol-free: verify it." (the agent was wrong and corrected it)
- "It's not a raw fuel smell, it's a rich exhaust smell." (an owner observation that changed the hypotheses)
- "Don't flash or prepare anything until we know the cause, but note x1.04 instead of x1.08 for the next tune."

The owner's corrections were frequent and decisive. The agent's job was to say what it knew, how sure it was, and
to stop when unsure.

## 5. Reproducing on another car

- Car-specific: ECU part number, stock file, CAN IDs, security keys (`ECUS_KEYS.txt` in the tool), checksum rule,
  every ROM address and table, and your adapter's quirks. Re-prove each one; do not copy addresses from here.
- General: the rules files, the flash gate, the simulated-ECU self test, "test every message type on the real car
  before an erase", emulation before flashing, logging after.
- Start with the rules file and a knowledge base, then: identify the ECU, get the stock file, prove the checksum on
  two files, build the tool from source with a self test, test all message types on the car, do a dry run, and
  only then flash an **unchanged** stock file once (as recovery practice). Changes come after that.
