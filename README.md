# 2011 Honda Accord coupe (K24Z3, 5MT): ECU reverse engineering and reflash with an AI agent

> [!CAUTION]
> ## DISCLAIMER: USE AT YOUR OWN RISK, THE AUTHOR IS NOT RESPONSIBLE
> **This repository is shared for educational and research purposes only. The author accepts NO responsibility and
> NO liability for any damage, loss, injury, fine or legal consequence resulting from its use.**
>
> - Reflashing an ECU can brick it, damage the engine or the vehicle, and cause a breakdown, a fire, injury or death.
> - Modifying fuelling, emissions calibration or a speed limiter can be **illegal** where you live, void your
>   warranty and affect your insurance. Obeying the law is your responsibility.
> - Everything is provided **"AS IS", with no warranty of any kind**. Much of it was produced with an AI agent and
>   may contain errors. Nothing here is professional, legal or safety advice.
> - The firmware files are for ECU **37805-R42-A240** only. Not affiliated with Honda or any vendor.
>
> **By using anything in this repository you accept the full [DISCLAIMER](DISCLAIMER.md). If you do not accept it,
> do not use this repository.**

This repository documents a complete, real-world project: reading, understanding, modifying and reflashing the
engine ECU of a 2011 Honda Accord EX coupe (2.4 L K24Z3, 5-speed manual, Canadian market) over the OBD-II port with a
cheap J2534 adapter. Almost all of the work (reverse engineering, tool fixes, test harness, firmware builds, log
analysis) was done by an AI coding agent (Claude Code), driven and supervised by the car owner.

Everything is here: the method, the agent rules, the forked flash tool source, the Ghidra scripts, the analysis
scripts, the logs, every firmware file that was built and flashed, and what was learned on the way (including an ECU
that was erased mid-flash and recovered the same day).

## Results at a glance

| # | Date | File | Change (vs the previous one) | Result |
|---|---|---|---|---|
| - | 2026-10-24 | - | first flash attempt: the adapter hung after the erase, ECU left blank | recovered the same day (stock A240) with the fixed tool |
| 1 | 2026-10-25 | `v1_speedlimiter` | speed limiter 200 -> 240 km/h | success |
| 2 | 2026-10-30 | `v2_tipin_fuelcut` | tip-in (pedal) table x2, decel fuel cut delay 80 -> 40 | success |
| 3 | 2026-10-30 | `v3_fuelcut20` | decel fuel cut delay 40 -> 20, gear change floor 40 -> 20 | success |
| - | - | `v4_revlim100` | rev limiter resume points +100 rpm (cut points unchanged) | built and emulated, **never flashed** |
| 4 | 2026-11-01 | `v5_maf115` | v3 + MAF transfer table x1.15 (short aftermarket intake) | success |
| 5 | 2026-11-01 | `v6_maf_taper` | v3 + MAF x1.15 at low flow, tapering to x1.08 at high flow | success, car runs this |

Details, addresses, hashes and byte diffs: [docs/FIRMWARE.md](docs/FIRMWARE.md).
Open question at the time of publishing: a slow rich drift of the fuel trim after flash #5 (see
[docs/TODO.md](docs/TODO.md) and the end of [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md)). No new flash is planned until its
cause is known.

## Main technical findings

- **GODIAG J2534 (FW 1.14):** its ISO 15765 channel hangs on any multi-frame *request* (8+ bytes) until the USB cable
  is replugged. Single-frame requests and multi-frame responses work. This is what bricked the ECU on the first try
  (only single-frame requests had been tested before the erase). Fix: software ISO-TP over a raw CAN channel
  (`Class_FlashEngine.cs` in the fork). The raw CAN pass filter needs `TxFlags = CAN_29BIT_ID`.
- **Internal checksum of this SH7058 (1 MB, Keihin) ECU:** the byte at ROM `0x8400` makes the byte sum of the firmware
  area `0x8000-0xFFFFF` equal to **0 mod 256**. Verified on the stock A240 and A220 files. The algorithm in upstream
  HondaReflashTool (mod 255) is wrong for this ECU.
- **Security key:** `27 01` seed / `27 02` key; the key bytes go out low byte first. Found by comparing with real car
  logs, not by reading code.
- Full reflash sequence (UDS) accepted by the ECU, `.rwd` format, decryption formula, ROM map, RAM variables, the
  speed limiter, decel fuel cut, tip-in, rev limiter and MAF logic: all in [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md),
  each fact with its evidence and a confidence score.
- **Fuel trims:** on this ROM the long-term trim that HDS displays is *not* applied to the injection; the short-term
  trim carries the real correction. Reading HDS LT x ST double-counts.
- **MAF scaling:** the measured/commanded fuel ratio scales as 1 / (MAF table multiplier) (predicted 1.065, measured
  1.069).

## Repository map

| Path | What |
|---|---|
| [docs/REPRODUCE_WITH_AI_AGENT.md](docs/REPRODUCE_WITH_AI_AGENT.md) | **Start here**: how the project was run with an AI agent, step by step, and how to reproduce it |
| [docs/LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md) | What went wrong, why, and the rule it produced |
| [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md) | The knowledge base the agent kept: every verified fact, with evidence and confidence |
| [docs/FIRMWARE.md](docs/FIRMWARE.md) | Every firmware file: SHA256, byte diff vs stock, what each change does |
| [docs/CHECKLIST_FLASH_DAY.md](docs/CHECKLIST_FLASH_DAY.md) | The procedure used on the car on each flash day |
| [docs/TODO.md](docs/TODO.md) | Task list as it stood when published (open items included) |
| [docs/LOG_PLAN_LEAN.md](docs/LOG_PLAN_LEAN.md), [docs/PROPOSAL_FLASH2.md](docs/PROPOSAL_FLASH2.md) | Examples of plans the agent wrote for the owner |
| [agent/CLAUDE.md](agent/CLAUDE.md) | The project rules file loaded by the agent in every session |
| [agent/MEMORY.md](agent/MEMORY.md) | The persistent working rule the owner gave the agent |
| `firmware/stock/` | Stock A240 (`.RWD.gz` + decrypted firmware area `.0x8000.bin`) and A220 (checksum reference) |
| `firmware/work/` | Every built version, `.bin` (decrypted) + `.rwd` (flashable) |
| `firmware/flashed/` | The exact `.rwd` files that went into the car |
| `logs/` | HDS SnapShot logs decoded to CSV (one folder per session), flash tool logs (every CAN frame), self-test logs |
| `tools/ghidra_scripts/` | Ghidra headless scripts: decompile at an address, find references, emulate the real ECU code (EmuLimiter, EmuFuelCut, EmuTipIn, EmuMaf, EmuRevLim, ...) |
| `tools/hds_snapshot/` | Decoder for HDS SnapShot `.dat` files and the log analysis / plotting scripts |
| `tools/build/` | The scripts that built each firmware version (`build_v2.py` ... `build_v6.py`) and the `.bin` / `.rwd` verification scripts |
| `tools/rom_search/` | ROM search helpers (callers, GBR-relative stores, A/D channel map, table descriptor dumps, calibration compare) |
| `tools/analysis/` | One-off analysis scripts written by the agent during the sessions (ROM tracing, trims, knock, cold start, ...) |

The flash tool is a fork of [bouletmarc/HondaReflashTool](https://github.com/bouletmarc/HondaReflashTool):
**[CIS-C0/HondaReflashTool](https://github.com/CIS-C0/HondaReflashTool)** (see its `FORK_NOTES.md`).

Paths inside `docs/` and `agent/` still use the original working folder layout (`stock\`, `work\`, `flash\`,
`src\`, `docs\logs\`, `FlashToolTest_v2\`). Mapping: `stock\` -> `firmware/stock/`, `work\` -> `firmware/work/`,
`flash\` -> `firmware/flashed/`, `docs\logs\` -> `logs/`, `src\ghidra_scripts\` -> `tools/ghidra_scripts/`,
`src\hds_snapshot\` -> `tools/hds_snapshot/`, `FlashToolTest_v2\flash_logs\` -> `logs/flash_tool/flash_logs/`.

## Hardware and software used

- Car: 2011 Honda Accord EX coupe, K24Z3, 5MT. ECU 37805-R42-A240 (Renesas SH7058, 1 MB, Keihin), CAN 500 kbit/s,
  29-bit IDs (request `18DA10F1`, response `18DAF110`).
- Adapter: GODIAG J2534 (firmware 1.14, driver 1.0.0.3, API 04.04), USB, Windows 11 laptop on AC power.
- Battery charger on the car during every flash (voltage must stay >= 11.5 V; the tool refuses below).
- Honda HDS 3.105 (diagnostics, DTCs, SnapShot data logging).
- Ghidra 12.2 (portable) + Temurin JDK 25, headless, processor `SuperH:BE:32:SH-2A`, base address `0x8000`.
- .NET Framework MSBuild + Roslyn `csc` to build the flash tool (no Visual Studio).
- Python 3 for the analysis scripts.
- Claude Code (desktop app) as the agent.

## Privacy

The VIN, serial numbers, the owner's identity, computer name, location details and odometer reading were removed from
this copy. Raw HDS `.dat` files are not published (they embed the VIN and dealer data); they were decoded to CSV with
`tools/hds_snapshot/snapall.py`, and the odometer column was dropped.

## License

The documentation, scripts and analysis in this repository are released under the MIT license ([LICENSE](LICENSE)).
**The firmware files in `firmware/` are not covered by it**: they are Honda calibration data (the stock files come
from the public [bouletmarc/HondaCalibFiles](https://github.com/bouletmarc/HondaCalibFiles) collection) and are
included only for research and interoperability. The forked flash tool keeps the terms of its upstream project.
