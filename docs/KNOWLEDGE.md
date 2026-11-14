# Project knowledge base (verified facts, with evidence)

Keep this file up to date. Every fact here has its evidence and a confidence score. Rules: ../CLAUDE.md. Tasks: ../TODO.md.

## Folder layout (after 2026-10-25 cleanup)
- FlashToolTest_v2\  : the ONLY tool to use (current build). FLASH_DRYRUN.txt present = dry run only. flash_logs\ = per-flash logs.
- stock\  : original firmware, read-only. 37805-R42-A240 (.RWD.gz + decrypted .0x8000.bin) is the recovery file. A220 = checksum reference.
- work\   : edited firmware (v1_speedlimiter, v2_tipin_fuelcut .bin/.rwd), read-only.
- flash\  : the .rwd files to flash (v1_speedlimiter.rwd flashed; v2_tipin_fuelcut.rwd built, not flashed), read-only.
- src\    : tool source (HondaReflashTool-main), build output (build), Ghidra + JDK + Roslyn (tools), Ghidra scripts/project, helper .ps1 and analysis outputs. ~1.95 GB, keep for future work.
- docs\   : this file + CHECKLIST_FLASH_DAY.md.
- Important_data\ : the user's HDS captures (PDF).
- _archive_old_builds\ : the superseded intermediate tool builds (diag/fix/raw...), kept only for reference, do not use.

## Vehicle and ECU
| Item | Value | Evidence | Conf. |
|---|---|---|---|
| Car | 2011 Honda Accord EX coupe, K24Z3 2.4, 5MT, Canada | HDS, VIN | 100 % |
| VIN | XXXXXXXXXXXXXXXXX | ECU 22 F1 90, HDS | 100 % |
| ECU calibration | 37805-R42-A240 | ECU 22 F1 81, HDS header | 100 % |
| Bootloader ID (22 F1 81 while erased) | 37805-R42-A210 | car log, raw CAN test | 100 % |
| CPU / ROM | Renesas SH7058, 1 MB, firmware area 0x8000-0xFFFFF | rwd header start 0x8000 size 0xF8000 | 100 % |
| CAN | 500 kbit/s, 29-bit IDs, request 18 DA 10 F1, response 18 DA F1 10 | car logs | 100 % |
| ECU padding | 0x55 | car logs | 100 % |
| Odometer | (removed from the public copy) | HDS | - |

## Adapter: GODIAG J2534 (SN XXXXXXXX, FW 1.14, driver 1.0.0.3, API 04.04)
- ISO15765 channel: single-frame requests OK, multi-frame RESPONSES OK, multi-frame REQUESTS (8+ bytes) HANG the adapter
  (~1 s blocked, nothing sent, adapter unusable until USB replug). Proven 3 times on 34 request download. 100 %.
- Returns TX_INDICATION, TX echo (loopback), START_OF_MESSAGE then the reply: stock HondaReflashTool positional reading
  is wrong with it. 100 %.
- Raw CAN channel (Protocol.CAN, CAN_29BIT_ID) works; its PASS filter needs TxFlags = CAN_29BIT_ID, otherwise
  INVALID_MSG "min/max violation". 100 %.
- J2534-Sharp quirks: GetConfig(Parameter) throws; some GODIAG errors show as message "OK". 100 %.
- Battery voltage read (pin 16) works: MeasureBatteryVoltage. 100 %.
- Only one program at a time can use it (HDS, HondaReflashTool, GODIAG J1979 tool). 100 %.

## Reflash protocol (UDS) accepted by this ECU
| Step | Request | Response seen | Conf. |
|---|---|---|---|
| Diagnostic session | 10 03 | 50 03 | 100 % |
| Seed | 27 01 | 67 01 S1 S2 (2 bytes) | 100 % |
| Key | 27 02 K1 K2 | 67 02 | 100 % |
| Programming session | 10 02 | 7F 10 78 then 50 02 | 100 % |
| Erase | 31 01 FF 00 | 7F 31 78 (~4 s) then 71 01 FF 00 | 100 % |
| Firmware keys | 2E F1 01 2A 6C D7 | 6E F1 01 | 100 % |
| Request download | 34 00 44 00 00 80 00 00 0F 80 00 | 74 20 08 02 (max block 0x802) | 100 % |
| Transfer | 36 <counter> + 0x800 encrypted bytes, 496 blocks | 76 <counter> | 100 % |
| Transfer exit | 37 | 77 | 100 % |
| Check dependencies | 31 01 FF 01 | 7F 31 78 then 71 01 FF 01 | 100 % |
- ECU flow control: 30 00 00 (no block size, no STmin). 100 %.
- Key: Class_Cypher.GetKey01(seed, "37805-R42-A240") with ECUS_KEYS.txt line 30383250584C; bytes sent LOW byte first
  (BitConverter order). Pairs accepted by the ECU: 70A3->8B93, 7CBE->B186, D1B4->3EC8, 8D56->F30E, 1028->0170. 100 %.
- R42-A210..A240 share the same security keys in ECUS_KEYS.txt. 100 % (file), recovery unlock proven on the car.
- Same sequence works with the ECU erased (bootloader). 100 % (recovery flash 2026-10-24).
- Transfer time: 2 min 15 s for 496 blocks over raw CAN. 100 %.
- Pin 12 programming voltage: not needed (recovery flash done without it). 100 %.
- After the flash: ignition OFF 10 s, ON, start. Other modules log codes (ABS 61-11 low voltage, SRS 56-31 lost
  communication with PCM). 100 %.

## Firmware files (.rwd, 0x5A format)
- Header: 5A 0D 0A, 6 groups (count, then len+bytes); group 2 = CAN address (0x10 MT), group 3 = supported versions
  (16 bytes each), group 4 = security keys (6 bytes each), group 5 = firmware keys (3 bytes: 2A 6C D7), then start and
  size (uint32 BE), encrypted data, 4-byte file checksum. 100 %.
- File checksum: byte sum of everything before the last 4 bytes, stored little-endian. 100 % (stock file).
- Decryption: plain = (((e ^ k[2]) + k[1]) - k[0]) & 0xFF, k = firmware keys. Matches the tool's .bin byte for byte
  for stock and v1. 100 %. (rwd-xray uses a different formula, marked unverified by its author.)
- The flashed data is the encrypted data as is; the ECU decrypts it with the keys from 2E F1 01. 100 %.
- INTERNAL CHECKSUM: byte at ROM 0x8400 makes the byte sum of the firmware area 0x8000-0xFFFFF = 0 mod 256.
  Evidence: stock A240 and A220 both sum to exactly 0 (1 in 65536 by chance). 95 % (99 % once a third file confirms).
  HondaReflashTool's algorithm (mod 255 + bootloader sum 177) is WRONG (A220 would need 0x76).

## Files (paths relative to the project folder)
| File | SHA256 / note |
|---|---|
| stock\37805-R42-A240-M1.RWD.gz | 6E4CACCB388AE50FEA40DFD3FA2EC39E95B6AD2461F15FE0A94D2A88629C9770 (git blob 34cf535c) |
| stock\37805-R42-A240-M1.0x8000.bin | 217578CB5CAB3268FE0C7AB9ABC8A463DD6F1331161A208067C67E7120EF4BE0 (decrypted firmware) |
| stock\37805-R42-A220-M1.rwd.gz | git blob d24b630f (checksum algorithm comparison) |
| work\v1_speedlimiter.bin | D70DE37A5BC2A96C9AC336E2699EC40CB30E9BA8062906F654D2309466AB08EE |
| flash\v1_speedlimiter.rwd | BE46D917D717A19B29FA8250338DB885CBD4C335F17E508A600DB2EA9C8967AB |
| work\v2_tipin_fuelcut.bin | 41788E025E1AD506505AD8971A0BAB7E2BA2888846582295802AEA97ABDD6872 (flash #2, NOT flashed) |
| work\v2_tipin_fuelcut.rwd = flash\v2_tipin_fuelcut.rwd | BD4D4F384C835F96B7AC4F1E560512A2A11F92E5BEA7B89548ABE2BF9ECBD4EC |
All are read-only. Source of stock files: github.com/bouletmarc/HondaCalibFiles (CalibFiles).

## ROM map (ROM address = .bin file offset + 0x8000)
| Address | Meaning | Evidence | Conf. |
|---|---|---|---|
| 0x8400 | internal checksum byte | see above | 95 % |
| 0x20DCC | part number string "37805-R42-A240" (only one) | search | 100 % |
| 0xB2C0 | 3500: RPM threshold of the speed limiter | code 0x587B6 | 95 % |
| 0xB2C2 | 200: speed limiter threshold (v1 = 240) | code 0x587C0, emulation | 90 % |
| 0xB2C4 | 50: delay (cycles above the limit before cut) | code + emulation | 90 % |
| 0xB2C6 | 30: hold (cycles the cut stays after) | code + emulation | 90 % |
| 0xB138/0xB13A | 4000/3800 RPM thresholds (with hysteresis) used with speed = 0 | decompile | 70 % |
| 0xB100.. | 2500, 1000, 1600, 1400 RPM thresholds (decel fuel cut?) | decompile | 60 % |
| 0x15B5C | list of fuel cut flag pointers: FFFF4382, FFFF4383, FFFF4341, FFFF4385, FFFF4384, FFFF3FB8 | data | 100 % (list) |
| 0x8CAE | helper: returns 1 if any flag of a null-terminated list is set | disassembly | 100 % |
| 0x580DE | fuel cut manager function (speed limiter at 0x587B6-0x587EC) | decompile | 85 % |
| 0x8CD8 | 1D table lookup helper (called with table descriptor + input) | decompile | 70 % |
| 0xA75C | MAF transfer descriptor: n=64, fmt 66 66 00, axis 0x13C72 (MAF A/D 10-bit 0,0,72..1015), data 0x13BF2 (airflow 0..32767 = HDS GAIR raw) | logs 100 % on grid + code 0x5382C / 0x7022C | 98 % |
| 0x138E0 | WOT determination table A, 6 x 0x35E8 (69 % at 0.005 %/bit), axis 0x138D4 1000..6000 rpm, descriptor 0xA62C | code 0x5284A | 90 % |
| 0x138C8 | WOT determination table B, 6 x 0x39D0 (74 %), axis 0x138BC, descriptor 0xA620 | code 0x52784 | 90 % |
| 0x138EC | null-terminated flag list (FFFF27BC, FFFF2F2E, FFFF2F2F, FFFF2F30, ...) read by helper 0x8CAE at 0x523B2 | data + code | 95 % |
| 0xE120-0xE1EC | A/D driver table: the 32 A/D result registers 0xFFFFF800-F84E + driver buffers 0xFFFF210C-2144 | data | 95 % |
| 0x9886/0x9888/0x988A | AN1 sensor fallback 5220, fault limits high 920 / low 48 | code 0x4A276 | 95 % |
| 0x9ADC.. | throttle sensor check limits: A 244..3932 (12-bit), B 61..983 (10-bit), debounce 20 cycles; 0x9AF0 = A/B mismatch table | code 0x3E610 | 90 % |
| 0x9A34 | 1200: throttle position used when both throttle sensors failed | code 0x3E610 | 90 % |
| 0x992C.. | pedal check limits: D 41..1004, E 41..819, debounce 20 (range) / 30 (D/E mismatch, tables 0x9950/0x995C); both failed -> 0 | code 0x3DB70 | 90 % |
| 0x141E8 | driver demand map 10x5: pedal demand x vehicle speed (descriptor 0xAB90) | code 0x56830 | 80 % |
| 0x1424C | driver demand map 15x15: result above x RPM (descriptor 0xABA4) -> 0xFFFF3CFA | code 0x56830 | 80 % |
| 0x145F4-0x1462C | per-gear (1-5) limit vs RPM, 7 points each (descriptors 0xAC9C..0xACCC) | code 0x56830 | 75 % |
| 0xAC68/0xAC80 | lift-off decay rate (moving): 51 at all RPM (step = level x rate / 1024 per cycle) | code 0x5752A | 85 % (rev hang link 55 %) |
| 0xAC74/0xAC8C | lift-off decay rate (stopped): 20/59/102 and 11/30/51 over 1000..4000+ rpm | code 0x5752A | 85 % (rev hang link 55 %) |
| 0xAC1C/0xAC1E | decay minimum step 1, period 1 cycle | code 0x5752A | 85 % |
| 0xAC98/0xAC9A | speed thresholds 1/3 (hysteresis) selecting moving/stopped decay tables | code 0x5752A | 85 % |
| 0xAD42 | 16660: upper limit of 0xFFFF3DA2 | code 0x5752A | 85 % |
- Generated definition 37805-R42-A240_Honda_Accord_2010_EX.txt: VTEC (0x18A16) and post start idle (0x12A0E)
  addresses are WRONG (values make no sense). Speedlimiter 0xB2C2 matches the code. 90 %.
  "WOT Determination 2" at 0x138F8 is WRONG too: 0x138F8 is inside a RAM flag list; the real second WOT table is
  0x138C8 (WOT 1 at 0x138E0 is right). 90 % (2026-10-25).
- Helpers: 0x8B1C clamp 0..0x7FFF, 0x8B08 clamp -0x8000..0x7FFF, 0x8CD8 1D lookup (12-byte descriptor: count,
  3 format bytes, axis ptr, data ptr), 0x908C 2D lookup, 0x91AD4 signed shift right 10 (callers add 0x3FF if
  negative). 90 % (0x91AD4 inferred from the callers' rounding, not decompiled).

## RAM variables
| Address | Meaning | Evidence | Conf. |
|---|---|---|---|
| 0xFFFF2C2C | vehicle speed (km/h assumed) | compared with 0, 100, 200; 61 refs | 85 % (units not proven) |
| 0xFFFF289C | engine RPM | compared with 4000/3800, 2500, 1600/1400, 3500; 136 refs | 90 % |
| 0xFFFF433E | flags base of the fuel cut manager (GBR in 0x580DE) | listing | 100 % |
| 0xFFFF4383 | speed limiter cut flag (GBR+0x45) | listing + emulation | 100 % |
| 0xFFFF4271 | OR of the flag list at 0x15B5C (global fuel cut?) | code; ~30 readers | 75 % (effect not traced) |
| 0xFFFF76BC | limiter timers: +0x10 delay, +0x12 hold | listing + emulation | 100 % |
| 0xFFFF2656 | AN1 raw (0xFFFFF802 >> 6, code 0x34F58); also copied to 0xFFFF25E2 | listing | 95 % |
| 0xFFFF29D8 | AN1 converted: (raw x 13750 - 384000) / 1024, fallback 5220 on fault (code 0x4A276). Probably MAP in 0.01 kPa (2.7..119.8 kPa range) | listing | 95 % (MAP 65 %) |
| 0xFFFF29B8 | written once at 0x290EE in the sensor setup code; probably barometric pressure | listing | 50 % |
| 0xFFFF3F08 / 0xFFFF3F35 | value compared with the WOT tables / WOT flag (on > 74 %, off < 69 %), function 0x52784 | decompile | 70 % / 90 % |
| 0xFFFF25EC / 0xFFFF25EA | throttle sensor A raw (12-bit) / B raw (10-bit) | P0122/P0123/P0222/P0223 checks at 0x3E610 | 90 % |
| 0xFFFF2F40 / 0xFFFF2F42 | throttle sensor A / B position (raw minus learned zero 0xFFFF8E30 / 0xFFFF8E32) | 0x3E610 | 90 % |
| 0xFFFF2C72 | final throttle position: A if OK, else B, else 1200 | 0x3E610 | 85 % (unit 0.005 % = 50 %) |
| 0xFFFF25E6 / 0xFFFF25E8 | pedal sensor D raw (AN0) / E raw | P2122/P2123/P2127/P2128 checks at 0x3DB70 | 90 % |
| 0xFFFF2C4C / 0xFFFF2C50 | pedal D / E position (learned zero 0xFFFF8DAE / 0xFFFF8DB0) | 0x3DB70 | 90 % |
| 0xFFFF2AB6 | final pedal: D, else E, min(D,E) on mismatch, 0 if both failed | 0x3DB70 | 85 % |
| 0xFFFF2ACE | pedal demand (2AB6 scaled; max with 0xFFFF6D26 when 0xFFFF6D21 = 1, maybe cruise) | 0x3DB70 | 60 % |
| 0xFFFF2C06 | current gear 1..5 (selects one table per gear) | 0x56830, 0x56F6A | 75 % |
| 0xFFFF3CFA | driver demand (probably torque) from the two demand maps | 0x56830 | 70 % |
| 0xFFFF3E18 | throttle/pedal fail-safe flag (fixed speed/RPM inputs to the demand maps) | 0x56830 | 75 % |
| 0xFFFF4198 | lift-off decay target T (base 0xFFFF4134 + 0x64) | 0x5752A | 85 % |
| 0xFFFF3DA2 | min(max(T, request), limit), 0..16660; probably engine torque request | 0x5752A | 85 % (torque 60 %) |
| DTC flags | throttle: P0122 2E3D, P0123 2E3C, P0222 2E3F, P0223 2E3E, P2135 2E40; pedal: P2122 2C3B, P2123 2C3A, P2127 2C3D, P2128 2C3C, P2138 2C22 (all 0xFFFFxxxx) | DTC table 0x42788 + writers | 95 % |

## Speed limiter logic (code 0x587B6-0x587EC, emulated)
if RPM > [0xB2C0] (3500): if speed > [0xB2C2]: when delay timer = 0 -> hold = [0xB2C6], flag = 1, else flag = 0;
if speed <= limit: flag = 1 while hold != 0, else delay = [0xB2C4] (50), flag = 0. RPM <= 3500: delay reset, flag 0.
Emulation (EmuLimiter.java): stock flag set above 200, v1 above 240, identical otherwise. 100 % for the block.

## Electronic throttle and rev hang research (2026-10-25, read only, nothing flashed)
- Sensor checks: throttle 0x3E610 (GBR 0xFFFF2E3C), pedal 0x3DB70 (GBR 0xFFFF2C0C). DTC registration table at
  0x42788 (DTC number + status flag per slot). 90 %.
- Functions ruled out: 0x2EA8A/0x2EBD0 = external 8-way analog multiplexer scan (3 select bits); 0x3E96C = byte
  conversions (probably diagnostic live data); 0x3E4CA = fail-safe mode selector; 0x3AD44 = CAN transmit scheduler
  (IDs 0x13A, 0x13F, 0x17C, 0x320, 0x324, 0x37C, 0x465, 0x6C1, rolling counter + checksum 0x39BB6, send 0x37FEC). 85 %.
- Pedal to engine request (torque based): 0x56830 (base 0xFFFF412C): pedal demand 2ACE -> map 0x141E8 (x smoothed
  speed, 4 down / 3 up per 8 cycles) -> map 0x1424C (x RPM) -> 3CFA; per-gear limit; 0x57BB0 converts request + RPM
  through 15 RPM-indexed tables (0x15780/0x15744/0x15708, axis 0x1489C), probably torque -> throttle. 80 %.
- 0x56F6A = TIP-IN ramp (acts only when the demand rises faster than a threshold; history of 5 samples; per-gear
  factor 0xADC8). Not the rev hang. 85 %.
- REV HANG CANDIDATE, 0x5752A: target T (0xFFFF4198) follows a rising request at once; on a falling request it
  drops each cycle by max(level x rate / 1024, 1) (assembly 0x5792E-0x5795A). Rate: moving (speed >= 3) 51 =
  about 5 %/cycle (0xAC68/0xAC80); stopped 11..102 by RPM (0xAC74/0xAC8C). Exception: moving + fuel cut flag
  0xFFFF4341 set -> T = 0 at once. Output 0xFFFF3DA2 = min(max(T, request), limit).
  What it computes: 85 %. That it IS the rev hang: 55 %. NOT verified: cycle time (so duration in ms unknown),
  emulation not done, a second hold-open further down (throttle conversion, idle air) not excluded.
- EMULATION of 0x5752A (EmuDecay.java, stock ROM, output src\emu_decay.txt, 2026-10-25):
  correction: T does NOT follow the request; T = min(request, floor) while rising (helper 0x8B82 = min), the
  floor depending on RPM (0xAC20/0xAC38) x coolant factor (0xAC50/0xAC5C of 0xFFFF2A1A, assumed ECT x10).
  Lift-off results (request -> 0): moving 3000 rpm warm: 4000 -> 1009 at once, then -52/cycle, then -27/cycle,
  0 after ~30 cycles; moving 6000 rpm warm: 8000 -> 2110, -110 then -69/cycle, ~30 cycles; stopped or cold:
  ~100 -> 0 in ~20 cycles; moving + fuel cut flag: 0 at once.
  Assumptions: timer 0xFFFF76B6 counts down once per cycle, unlisted flags 0, 0xFFFF2BD6 = 1, request not limited.
  What it does: 90 %. That it is the felt rev hang: 45 % (partial, ~30 cycles; depends on the cycle time).
- Task chain: 0x56830 <- 0x782D8 <- 0x4BFFC (calls the pedal check 0x3DB70, 0x4378A, 0x782D8, the throttle checks
  0x3E60C..0x3E5F8) <- 0x2C438 = an interrupt handler (clears a bit in timer register 0xFFFFF482 at entry, runs
  the sensor reads, busy-waits 200 ticks of the free-running counter 0xFFFFF430, then 0x4BFFC; odd/even cycle
  split). 80 % (chain). Period: see "Vector 151 timing" below.
- Vector 151 timing (2026-10-25, SH7058 hardware manual REJ09B0046-0300H in Important_data\SH7058.PDF + ROM):
  vector 151 = ATU-II channel 7 CMI7D (TCNT7D matches CYLR7D; in PWM mode TCNT counts 1..CYLR, then back to 1).
  Init 0x31CD6 writes: PSCR3 (0xFFFFF408, channel 7 prescaler) = 0 -> phi' = Pphi/1; TCR7B (0xFFFFF5A0) = 0x10 ->
  CKSELD = 1 -> phi'/2; CYLR7D (0xFFFFF58E) = 0x80E8 = 33000 (CYLR7A..C = 0xB400, 0x4E20, 0x4E20). Also PSCR1 =
  PSCR2 = 4 (/5), TSTR1 = 1 at the end. Registers + formula: 90 %.
  Peripheral clock Pphi (crystal, not in ROM): SCI0 init 0x3205C sets SMR0 = 0, BRR0 = 0x3B -> 10417 baud at
  Pphi = 20 MHz (K-line 10400, +0.16 %), 20833 at 40 MHz (not standard). So Pphi = 20 MHz: 75 % (SCI0 = K-line not
  proven; HCAN bit timing writes not found).
  -> one interrupt every 33000 / 10 MHz = 3.3 ms (1.65 ms if Pphi = 40 MHz): 70 %. Only the init write of CYLR7D was
  found (a runtime change through a base register is not excluded).
  Register names: 0xFFFFF430 = TCNT0L (channel 0 free-running counter, low word), 0xFFFFF482 = TIER3 (interrupt
  enable for channels 3-5; bit 14 = IME5D), NOT a status register (the CMI7D flag is in TSR7 0xFFFFF5A2). 95 %.
- Handler 0x2C438 structure (decompiled, src\decomp_2C438.txt): counter 0xFFFF21BA +1 each interrupt, reset at 200
  (events at 100 and 200 = every 100 interrupts; other tasks on (n & 1/3/7) == 0 = every 2/4/8). Mode byte
  0xFFFFBEA6 (only read, writer not found): == 1 -> sensor reads, 200-tick wait, then 0x4BFFC with NO counter
  condition; == 2 -> another task list without 0x4BFFC. 0x4BFFC calls 0x782D8 unconditionally, and 0x782D8 calls
  0x56830 unconditionally at its end. So in mode 1 the demand / lift-off code runs on EVERY interrupt (no
  odd/even split): 95 % (code). Mode 1 = normal running: 80 % (assumed, 0x4BFFC holds the pedal/throttle checks).
  -> lift-off decay of 0x5752A (~30 cycles) = ~0.1 s at 3.3 ms per cycle: 65 % (needs Pphi = 20 MHz and that
  0x5752A is called each time by 0x56830, not re-checked). Too short to explain a 0.5-1 s felt rev hang.
- Idle / base air part of the throttle request (step 16, 2026-10-25, decompiled src\decomp_56830.txt, decomp_573A8.txt):
  0x57BB0 = generic helper only (axis + list of 1D tables, interpolates; called only by 0x56830). 95 %.
  In 0x56830 (base 0xFFFF412C): REQUEST 0xFFFF40B0 = clamp0..7FFF( 2D map 0xAD2C(limited demand, X) - X ), with
  X = 0xFFFF4182 = idle/base air. 0x57BB0 (RPM axis 0x1489C) converts: demand+idle (base+0xA4) -> 0xFFFF4202,
  X alone -> 0xFFFF4208, throttle position 0xFFFF29C6 -> 0xFFFF4204 (tables 0x15780 / 0x15744 / 0x15708); then
  0x5752A. So the throttle = driver part + idle part.
  X is written by 0x573A8 (GBR 0xFFFF417E): Y = 0xFFFF4180 = idle air request:
    normal: Y = clamp(min(f(0xFFFF3D04, 0xFFFF3DD2), ROM 0xABD8) + 0xFFFF3DC2); start/other mode (0xFFFF2B11 != 0):
    Y = 1D tables 0xABE0 / 0xABEC / 0xABF8 vs coolant 0xFFFF2A1A.
    X = blend of tables 0xAC10(Y) and 0xAC04(Y) with weight 0xFFFF92D4.
  0xFFFF3D04 / 3D10 written by the idle control 0x4F432 / 0x4F534 (state byte 0xFFFF3CB9 = 5 / 7 checked here).
  0xFFFF3DC2 (added on top: dashpot candidate) writer NOT found (other base register). Structure: 85 %;
  meaning "idle air": 70 %; dashpot in 3DC2: 40 % (assumed). Not emulated.
- Step 17 (2026-10-25, src\decomp_4F4xx.txt): 0xFFFF3DC2 has ONE direct reference in the ROM (the read in
  0x573A8); no pool/GBR/base+disp store (src\base_stores.ps1, new) and no data pointer -> written through a
  computed address (index/loop/pointer) or never (stays 0). 90 % (search), writer unknown.
  Idle control 0x4F428 (base 0xFFFF3CB8): 0xFFFF3D04 = clamp(0..max 3CF2, scaled sum of 3CEE + 3D02 + 3CF4 + 3D06,
  + 3CF6 + 3CEA + 3CEC). Term 0xFFFF3D06 = 0x8B8C(3CF8, 3CFC) ONLY when idle state 0xFFFF3CB9 = 4/5/6 AND demand
  0xFFFF3CFA < ROM 0x9E18 (with hysteresis 0x9E1A), else 0 -> an air-hold term active after lift-off: strongest
  dashpot candidate (70 %). 3D08 = 2D map 0x9E20 (x 3CF0, 0xFFFF29B8) rate-limited into 3D08 (0x8BFA, step 0x9E1C).
  Idle control 0x4F52A (base 0xFFFF3CB6): 3CB6 = 0 if state = 5 or speed < ROM 0x9E36, else table 0x9E38/0x9E50
  (x 3CBA) x coolant gain 0x9E68 / table 0x9E5C(0xFFFF29B8), min table 0x9E44(coolant); 0xFFFF3D10 = clamp(3CB6 +
  3CF6 + 3CEA + 3CEC + 3CFE x 0xFFFF92A8). Structure 85 %, meanings assumed. Not emulated.
- Dashpot (2026-10-25, src\decomp_idle_hold.txt): 0x8B8C = max(a, b). Hold term 0xFFFF3D06 = max(3CF8, 3CFC).
  0xFFFF3CF8 written by 0x502F4 (base 0xFFFF3CB0, params ROM 0xA0C0..): enabled once 0xFFFF784C >= 500 (0xA0C6);
  on event flag 0xFFFF3DE0 with lockout timer 0xFFFF7668 = 0 and closing rate -(0xFFFF3158) > 0xFFFF3DDA:
    duration timer 0xFFFF766A = table vs coolant 0xA0D4 [30 x8] or 0xA0E0 [30 .. 40 hot] (axis -200..1000),
    amount = min(table 0xA0C8 (rate 0 -> 300, 800 -> 1500) x coolant gain 0xA0EC [1.0 .. 1.5] / 0xA0F8
    [1.0 .. 2.5 hot] (4096 = 1.0), cap 0xA104 = 1300 or 0xA106 = 3000 (flag 0xFFFF3403)),
    lockout 7668 = 150 (0xA0C4); while 766A != 0 the term is clamped by 0x8B1C (args hidden: decay not read);
    timer 0 -> 0. 3CFC written by the idle state machine 0x5083A (also writes the state 0xFFFF3CB9).
  Classic dashpot: extra air after a fast closing, larger when hot. 75 % (structure); duration in ms needs the call
  rate of 0x502F4 (unknown: 30 cycles = 0.1 s at 3.3 ms, 0.8 s at 26 ms); 0xFFFF3158 meaning unknown.
- Dashpot details (step 18, listing 0x502F4, corrects the decompiled view above):
  - Cadence: 0x502F4 is called only by 0x5083A, which 0x782D8 calls every interrupt (3.3 ms). But 0x5083A returns
    early while 0xFFFF3E08 > ROM 0xA1C8 = 2800 (hysteresis 0xA1CA = 2600) and counter 0xFFFF3E0A != 0
    (decremented, reloaded with 3 at 0x50910) -> 1 call in 4 = 13.2 ms above 2800. 90 % (code), ms needs Pphi.
  - 0xFFFF3E08 = 0xFFFF3E30 / 4 (0x52EB6); 0xFFFF3CBA = copy of 3E08 (0x5092A). Probably engine speed: 55 %.
  - Arm / trigger: while 3CBA > threshold 0xFFFF3DE4 (computed when the term is 0, from 0xFFFF3DDE and ROM 0xA0C2 =
    1000 through 0x8B70) -> flag 0xFFFF3DE0 = 1, term 0. When 3CBA falls back below -> amount + timer computed.
  - Decay: while timer 0xFFFF766A != 0, each call 3CF8 = clamp(3CF8 - 5) (ROM 0xA0C0 = 5, 0x8B1C); lockout
    0xFFFF7668 = 150 (0xA0C4) while 3CF8 > 5; 766A = 0 -> 3CF8 = 0. 90 %.
    So hold = min(amount / 5 calls, timer 766A ticks). Amount 1500 -> 300 calls = ~1 s at 3.3 ms, ~4 s at 13.2 ms;
    timer 30-40 ticks. Who decrements 766A (tick rate) NOT found (no direct/GBR/base store, no loop, no pointer
    table; only the RAM clear at 0x239EC with GBR 0xFFFF7664). Duration in ms still unknown.
  - 0xFFFF3158 = difference of two speed-like values computed in 0x446D4 (0x44B5A: new - (0xFFFF3144+0x10));
    also reset with the RPM at 0x28D14 / 0x43A6E -> probably RPM change rate: 60 %.
- Dashpot emulation (step 19, src\ghidra_scripts\EmuDashpot.java, output src\emu_dashpot.txt): 0x502F4 run call by
  call on the stock code. Inputs: trigger 3CBA 3000 -> 800, arm threshold 3DE4 = 1000 (3DD8 = 1, 3DDE = 0),
  3158 = -drop, timer tick rate unknown (1 tick every 1/3/8 calls tried). Results:
  - fires on the call where 3CBA <= 1000; peak = table 0xA0C8(rate) x coolant gain: rate 100, 85 C -> 900
    (450 x 2.0); cold -> 450; slow drop (rate 10, 85 C) -> 630. Cap 1300/3000 not reached.
  - then -5 per call; duration timer 766A = 35 at 85 C (table 0xA0E0 interpolated); term 0 when the timer ends
    or the term reaches 0: 35 calls (tick 1), 105 (tick 3), 180 (tick 8, limited by 900/5).
  - in time (3.3 ms per call below 2800): 0.12 s / 0.35 s / 0.6 s max. Lockout 150 ticks before it can fire again.
  Matches the code reading (100 %, emulated). Assumptions: 3CBA = engine speed (55 %), threshold 1000 (only if
  3DD8 = 1; otherwise 3DE4 = 3DDE, writer not identified). If the units are rpm, this dashpot catches the drop
  towards ~1000 rpm (idle / anti-stall), so it probably does NOT hold revs at shift speed (~2500-3500 rpm): 55 %.
- Dashpot inputs identified (step 20, read only):
  - 0xFFFF3E30 (= 3E08 x 4, copied to 3CBA) is written by 0x5381C (store 0x53A22): = RPM 0xFFFF289C x 4, or a
    filtered RPM when 0xFFFF2C0B = 0 and counter 0xFFFF3FC4 reached 6 (0x94C8/0x94E8 on 0xFFFF3166). So the dashpot
    trigger 3CBA = engine RPM (85 %).
  - 0x504F8 writes 3DDE = table 0xA108(coolant 2A1A) and 3DDA = table 0xA114(coolant).
    0xA108 (arm threshold, rpm): axis [-300 -150 200 300 500 650 800 900] (x10 C assumed) -> [1700 1700 1700 1700
    1350 1000 1000 1000]. 0xA114 (rate threshold): -> [70 70 65 50 40 20 10 10].
  - Result: warm engine, the dashpot fires when RPM falls below 1000 (1700 cold): idle catch / anti-stall, NOT the
    rev hang at shift speed (85 %).
- Not the throttle target: 0x3D610 = throttle plant model / adaptation (0xFFFF2C74 = a model parameter, ROM
  defaults 0x9A28..); 0x3C828 = throttle response monitor; 0x3E908 = throttle speed + copy 0xFFFF29C6;
  0x3A4CE = CAN 0x136 TX (throttle 29C6 + request 40B0); 0x4F39C / 0x4F3C8 = interrupt mask enter/leave. 75 %.
- Vector tables: main table at ROM 0x8000 (vector n at 0x8000 + 4n): vector 151 (0x825C) -> 0x2C438, vector 157
  (0x8274) -> 0x2B18C, vector 160 (0x8280) -> 0x2B488; unused vectors -> 0x259E4. Second table at 0x8500, loaded
  into VBR at 0x2EE56 (pool 0x2EFD8), where vector 151 is unused (other handlers: 0x2F42A, 0x2F3D6, 0x2F39A,
  0x2F1CA, 0x2F86C, 0x2F8D4, 0x2F46A). 100 % (data). Vector 151 = ATU-II CMI7D (see above).
- Timer register writers (FindIoRefs.java FFFFF400 FFFFF4FF, output src\io_atu.txt): prescaler-like byte init at
  0x31CD6 (0xFFFFF400..), channel init at 0x31DE4 / 0x328BA / 0x37838, 0xFFFFF430 = 32-bit free-running counter
  read by many functions (TCNT0L), 0xFFFFF482 = TIER3 (enable bits, not status). Names from the manual: 95 %.
- Pedal delay candidates (KTuner "DBW responsiveness"): tip-in ramp 0x56F6A (limits how fast the request rises),
  pedal slew path in 0x3DB70 (final pedal +5/cycle when D moves fast and E does not, ROM 0x993C), smoothed speed in
  0x56830 (4 down / 3 up per 8 cycles, ROM 0xAB78/0xAB7A/0xAB7E). Not emulated yet. 70 %.
- Step 21 (read only, NOT emulated, 2026-10-25):
  - 0x56F6A (tip-in ramp, RAM base 0xFFFF4134, output 0xFFFF416C / 0xFFFF4178): IS called, "bsr 0x56F6A" at
    0x56A54 in 0x56830, every cycle (step 22). The "no caller" claim of step 21 was WRONG: the PowerShell scan
    shifted a [byte] (always use [int]$r[$i] -shl 8). Path A compares the demand with itself (lag byte 0xABB8 = 0,
    threshold 0xABBA = 0 -> never true). Path B: lag 0xABB9 = 1, threshold 0xABBC = 50 (demand rise per cycle),
    max time 0xABC2 = 100 (counter 0xFFFF7852 = 0xFFFF784C + 6), step cap 0xAB3A = 160. Live candidate for the
    pedal delay, to be emulated.
  - 0x3DB70 pedal slew (+0x993C = 5 per cycle): only used when D jumps (rise > ROM limits 0x9934..0x993A) while
    E does not follow (sensor plausibility path); otherwise final pedal 0xFFFF2AB6 = D at once (line "2AB6 =
    +0x40"). No delay in normal driving: 70 %.
  - Timers 0xFFFF76xx..0xFFFF78xx (7668, 766A, 76AE, 76B2, 7852) are reloaded by the code and counted by a
    timer service not found yet; 0xFFFF784C (>= 500 enables the dashpot, compared with 6000 in 0xABC8) looks like a
    time-since-start counter (50 %).
- Step 22, 0x56830 after the pedal (read only, base 0xFFFF412C):
  - Speed / RPM axes: when timer 0xFFFF76B2 = 0, smoothed speed +0x38 moves toward 0xFFFF2C2C by -4 (0xAB78) /
    +3 (0xAB7A), the RPM sample +0x34 = 0xFFFF289C, and 76B2 is reloaded with 8 (0xAB7E). Demand 0xFFFF3CFA =
    map 0xABA4(map 0xAB90(pedal 2ACE, speed +0x38), RPM +0x34). The pedal goes in directly every cycle: only the
    axes are held, so this does not delay a pedal change (80 %); the map value can lag a fast RPM change by up to
    8 timer ticks.
  - Per-gear limit: tables 0xAC9C/0xACA8/0xACB4/0xACC0/0xACCC (gears 1-5, by RPM) are ALL 32767 (flat, no limit);
    limit = min(table, 0xAD42 = 16660); rate steps 0xADB6 / 0xADB8 = 0. Request +0xA2 = min(limit +0xCC, tip-in
    output 0xFFFF4178). The gear limit adds no delay (80 %); tip-in 0x56F6A is the only stage left between the
    pedal and the request.
- TIP-IN EMULATION (step 23, src\ghidra_scripts\EmuTipIn.java, output src\emu_tipin.txt): 0x56F6A run call by
  call on the stock code, demand 3CFA stepped 3000 -> 12000 (pedal stab), speed 50, 2C2C/3FBE = 2/3F0A = 0/
  3E2E = 0/784C = 10000, start value 0xFFFF4162 = old demand (writer unknown), counter 7852 +1 every 1/3/8 calls.
  - The ramp starts at once on the step (rise > 50 per call), output 4178 = start value, then + step per call;
    step grows with the counter (table 0xAB40: 0 at 0, 6 at 3, 30 at 10, 100 at 30) x RPM gain 0xAB58 x gear
    factor: 2 at first, ~190 at the end -> S-shaped, very slow first part (+57 out of +9000 in the first 30 calls).
  - Calls to reach the new demand (x 3.3 ms): gear 2 2500 rpm: 57 (tick 1, 0.19 s) / 109 (tick 3, 0.36 s) /
    187 (tick 8, 0.62 s); gear 4 2500: 88 (0.29 s); gear 1 1500: 118 (0.39 s); gear 5 4000: 65 (0.21 s).
    Step +40 (below 50): no ramp, no delay.
  - Code behavior emulated: 100 %. That this is the felt pedal delay: 65 %. NOT known: counter 7852 tick rate
    (changes the time x3), writer of 4162, demand units, the enable flags 4135 / 3FBE / 3F0A / 3E2E on the car.
    The step reached 195 (> 160): the 0xAB3A cap reading of step 21 was wrong or applies to another branch.
- Step 24 (read only), tick rate of counter 0xFFFF7852 NOT found:
  - Direct writers: 0xFFFF7852 only by the 0x56F6A reset (store at 0x57348, base 0xFFFF784C); 0xFFFF784C only
    cleared at 0x52F36 in 0x52E9C (when 0xFFFF3E2E is set; 0x52E9C also writes 3E08 = 3E30 / 4).
  - No other 32-bit pointer to 0xFFFF7852 in the ROM; no mov.w form; GBR bases in the timer area: 0xFFFF7664
    (0x239E0 = RAM init only), 0xFFFF7682, 0xFFFF784C (0x681BE reads only), 0xFFFF7752, 0xFFFF772A, 0xFFFF7874.
    Loop scans (counter loops with add #1 / add #-1) found nothing for this area (0x36742, 0x408C0, 0x2E0D2 are
    other things). So the up-counting is done through computed addresses not found by static scans.
  - 0xFFFF4162 (tip-in start value): no store found by base_stores.ps1 / FindRefs -writes / GBR scan.
  - PowerShell gotcha: 0xFFFF7600 etc. are negative int literals; use [long]4294901760 + 0x7600.
- Step 25, emulation of the 3.3 ms chain (src\ghidra_scripts\EmuIrq.java, output src\emu_irq.txt):
  - Whole handler 0x2C438: only ~285 instructions per call in the emulator (mode-1 branch not taken), and it has a
    busy wait on the free-running counter 0xFFFFF430 (200 counts) that needs a hardware model. Not usable as is.
  - 0x4BFFC run directly, 300 calls, about 20400 instructions per call, no stop. 0x7852 / 0x4162 / 0x784C /
    0x766A / 0x76B2 never changed. So the time counter 784C (and probably all 0xFFFF76xx-78xx timers) is NOT ticked
    inside 0x4BFFC: it is ticked by another task or interrupt (70 %). Not verified that 0x56830 was reached with
    these inputs (76B2 never reloaded -> maybe not).
  - Found on the way: 0x3DB70 checks its copies 0xFFFF2C58 / 0xFFFF2C56 (GBR 0xFFFF2C0C + 0x4C / + 0x4A) against
    pedal 0xFFFF2AB6 / 0xFFFF2ACE at entry; on a mismatch it calls 0x37BD2 -> 0x2A454 = fatal error (code 0xD8):
    saves state, writes the hardware registers, then loops forever at 0x2A4E4 (watchdog reset). 90 %.
    Any patch that changes 2AB6 / 2ACE outside 0x3DB70 would trigger this reset.
- Step 26 (2026-10-25, read only):
  - Timers 0xFFFF76xx-78xx: no interrupt handler changes 784C/7850/7852/766A/76B2/7668 when run once in the
    emulator (src\ghidra_scripts\EmuScan.java, src\emu_scan.txt: 31 vectors, most return; 0x2CC36 (vector 107) and
    0x32180 stop on hardware waits; 0x259FC/0x25A08/0x25A14/0x259F0 = fatal-error vectors). No counter loop found by
    the static scans. Probably ticked by the background loop (60 %). Still unknown.
  - 0xFFFF4162 (tip-in start value) = 0xFFFF412C + 0x36, written at 0x56980 in 0x56830 (GBR 0xFFFF412C) = the
    demand 3CFA BEFORE this cycle's update (previous demand). The tip-in emulation assumption was right. 90 %.
  - 0xFFFF3DC2 (idle air add) = 0xFFFF3CAC + 0x116, written at 0x51146 in 0x5083A (GBR 0xFFFF3CAC):
    = (0x3DC0 x gain 0x3CFE) >> 15, 0x3DC0 = tables 0xA050/0xA05C/0xA044 on 0xFFFF4F16; non-zero only when
    0xFFFF4F16 != 0, idle state 0xFFFF3CB9 = 6 and 0xFFFF4271 = 0. Idle only, not the rev hang. 75 %.
    Finding these needed a GBR store scan (ldc Rn,GBR then mov.x R0,@(disp,GBR)); base_stores.ps1 misses them.
  - Pphi CONFIRMED 20 MHz: HCAN init 0x2D2A0 writes BCR0 (0xFFFFD006) = 1 and BCR1 (0xFFFFD004) = 0xD420:
    TSEG1 13+1, TSEG2 4+1, sync 1 = 20 tq, (BRP+1) = 2 -> bit rate = Pphi / 40 = 500 kbit/s at 20 MHz (the car CAN
    speed). So the 3.3 ms cycle is confirmed: 95 %.
  - Candidate changes emulated (ROM patched in the emulator only): tip-in table 0xAB40 x2 -> about -25 % ramp time;
    tip-in threshold 0xABBC = 32767 -> no ramp; decay 0xAC68/0xAC80 51 -> 102 -> 0.05 s instead of 0.1 s. All
    constants are read only by their own function (FindRefs + pointer search). See docs\PROPOSAL_FLASH2.md.
  - The rev hang is not explained by the throttle path (decay 0.1 s, dashpot / 3DC2 idle only): next lead =
    decel fuel cut delay / ignition (50 %).

## Tools and how to run them
- Flash tool source: src\HondaReflashTool-main (C#, .NET 4.5). Build: built-in MSBuild + Roslyn in src\tools\roslyn:
  `MSBuild.exe FlashToolTest.csproj /t:Rebuild /p:Configuration=Debug /p:OutputPath=..\build\ /p:CscToolPath=<roslyn>\tasks\net472 /p:CscToolExe=csc.exe`
- Key source files: Class_FlashEngine.cs (FlashEngine, J2534RawTransport, FirmwareValidator), Class_FlashSelfTest.cs
  (SimulatedEcu, 52 tests), GForm_Main.cs (FlashRWD_DoWork, OpenRawCanChannel, Connect ECU with SendJ2534Request),
  Class_Checksums.cs (1 MB uses the sum-256 rule).
- Self test: `FlashToolTest.exe --selftest <stock.gz> <stock.bin> <custom.rwd> <custom.bin> <log>` (exit code = failures).
- Deployed build: FlashToolTest_v2 (dry run ON while FLASH_DRYRUN.txt exists). Logs: J2534_debug.log,
  flash_logs\flash_<date>.log (every CAN frame).
- Old folders FlashToolTest, _diag, _fix, _fix2, _fix3, _raw, _raw2, _raw3: intermediate builds, do not use.
  (_raw3 did the successful recovery flash.)
- Ghidra 12.2 + Temurin JDK 25 in src\tools (portable). launch.properties patched: settings/cache/temp dirs in
  src\ghidra_tmp (AppData writes fail). Headless:
  `analyzeHeadless.bat <proj> <name> -import <bin> -overwrite -loader BinaryLoader -loader-baseAddr 0x8000 -processor SuperH:BE:32:SH-2A -noanalysis -scriptPath src\ghidra_scripts -postScript <script> <args>`
  Scripts: DecompAt.java ("start@target" to force the function start; replaces pool words with their values in the
  output), FindRefs.java ("[-decomp] [-writes] <hex>...": code loading a constant / storing through it),
  EmuLimiter.java. Headless needs JAVA_HOME = src\tools\jdk\jdk-25.0.4.1+1 (not on PATH). Project REFS in
  src\ghidra_proj is a scratch import (-overwrite).
- ROM search scripts (PowerShell, run with -ExecutionPolicy Bypass from the hidden tool): src\map_adc.ps1 (A/D
  channel -> raw RAM copy), src\group_raw_readers.ps1 (functions loading 2+ given RAM vars), src\dtc_users.ps1
  (code loading DTC numbers), src\gbr_stores.ps1 ([-Loads]: GBR-relative stores/loads of given addresses),
  src\dump_tables.ps1 (decode 1D table descriptors). Python is NOT installed (only the Store stub).
  Function start guess "previous rts" is often wrong (lands in literal pools): check for the register pushes.
- Verification scripts (run with the hidden PowerShell tool, the user terminal blocks .ps1): src\verify_bin.ps1,
  src\verify_rwd.ps1, src\checksum_algo_check.ps1.

## Flash #1 (2026-10-25, v1 speed limiter 240 km/h): SUCCESS
- FlashToolTest_v2 exe 97AB3006..., raw CAN ISO-TP. Battery 12.56-12.61 V on the charger forced to 10 A
  (on 2 A it was 11.64 V with the ignition ON and the head unit on). 2 dry runs first (seeds 07 92, 59 2A accepted).
- Erase 8 s, 496 blocks in 2 min 39 s, 145338 TX frames (same count as the full simulation), 77, 71 01 FF 01.
- Ignition OFF 10 s / ON, car starts and runs normally. Connect ECU: VIN + 37805-R42-A240 (the part number string is
  unchanged in v1). HDS: PGM-FI no DTC; SRS 56-31 set again by the flash, cleared; ABS 61-11/65-11 history only
  (ABS clear fails in HDS, light was never on).
- Read-back with 23 44 00 00 B2 C2 00 00 00 02: ECU answers 7F 23 13 (not accepted), no direct read-back.
- Connect ECU gets no answer at all when the key is OFF (looks like an adapter problem, check the key first).
- DarkMessageBox hid the Yes/No buttons on long text: flash dialogs now use standard MessageBox, default = No.
- Not verified yet: behavior on the road above 200 km/h (needs a closed track or a dyno).

## Car state (2026-10-24 evening)
- Stock A240 reflashed (recovery), runs normally, no MIL. LT fuel trim and knock learning reset.
- Open codes: ABS 61-11 (IG low voltage), 65-11 (brake fluid level switch circuit), SRS 56-31 (lost comm with PCM).
  65-11 was already there before the project (user, 2026-10-25), not caused by the flash.
- HDS: EPS and BODY ELECTRICAL show no DTC function on this car (2026-10-25).
- Market Cal Index 1 and 2 changed from 1 to 5 after the reflash (meaning unknown); read 6 on 2026-10-25 after flash #1.

## HDS Snapshot logging (proven 2026-10-25)
- HDS PGM-FI > Snapshot (F8): Manual trigger, Record Time 3 Min, Trigger Point slider fully right (-180 s..0 s) =
  the 3 minutes BEFORE the camera click are saved. Line Graph in Data List is display only (no recording).
- Files: C:\Teradyne\HDS\Stored Files\Automotive\Snapshot\*.dat. HDS records ALL Data List signals whatever the
  Custom List: ~3100 frames / 3 min = one frame every ~57 ms (17 Hz). ~2.5 s gap at each save.
- Format (decoded): header with one descriptor per signal (name, DID 0x26xx, byte positions, mask), then u32 count,
  then 16-byte records: u16 byte position, u16 DID, u32 value, u32 time ms (HDS session clock), u32 0xFFFFFFFF.
- Signals: NE 2610 b6-7 (rpm = raw/4), VSP 2610 b0x12 km/h, ECT 2610 b0x0B (raw-40), MAP 2610 b0x0F kPa,
  IG 2610 b0x15 ((raw-128)/2 deg), APP 2612 b8-9 (scale unknown, max seen 14543), Throttle VLV = RELTHW 2612
  b0x0C-0D (raw/200 deg), Target TH VLV = THO 2612 b0x0E-0F (raw/200), Idle Target TH = THICMD 2612 b0x12-13,
  FC 2660 b0x16 mask 08, FCDEC 2660 b0x16 mask 10. Scales checked against the HDS screen (ECT 22.0, TH 6.4/4.1,
  IG 0.0, MAP 101).
- Tools: src\hds_snapshot\snap.py (dat -> csv), merge.py (all.csv), ana2.py (events), plot.py (HTML graph).
  Run with `py -I`.

## Baseline log 2026-10-25 (stock ECU + flash #1, warm 84-90 C, docs\logs\2026-10-25_baseline)
- Pedal delay: target throttle lags the pedal 0.12 s (median) stopped, 0.23 s moving, up to 1.5 s; the big lags
  are at 5-30 km/h, 1000-2000 rpm, 25-40 % pedal. Big pedal (> 85 %) lags only ~0.06 s. Real throttle follows the
  target within ~0.06 s (motor not the limit). Matches the tip-in ramp 0x56F6A (active only when moving) -- 75 %.
- Rev hang: on lift-off the target throttle is back to idle in 0.23-0.30 s moving (0.06 s stopped: decay 0x5752A).
  Decel fuel cut (FCDEC) starts 0.35 s after lift-off stopped in neutral, but 1.2-1.4 s moving at 2500-3400 rpm,
  0.75-0.85 s above 4200 rpm, and sometimes never (25-28 km/h). Until then the engine stays fuelled at idle air
  with IG 40-45 deg: with the clutch in the RPM falls only 100-450 rpm in 0.75 s (vs ~1100 stopped). So the felt
  rev hang = the delay before decel fuel cut when moving (70 %), not the throttle path. Clutch not logged: shift
  moments are inferred.
- CORRECTION (2026-10-25, window.py 1396.22 / 1589.91 / 1645.37): "back to idle" above means the fast drop ends in
  0.23-0.30 s, but moving the target then HOLDS above the stopped idle (3.3-3.5 deg): 6.7 deg at 3250 rpm 27 km/h,
  slowly to 5.5 deg at 1.2 s; 9.3 deg at 4800 rpm 72 km/h (kept even during FCDEC). MAP before the cut: 17-19 kPa
  moving vs 8-10 kPa stopped = about twice the air. This is the "overrun throttle opening" (Hondata "Overrun
  throttle opening enabled", KTuner "Overrun Throttle Compensation" 100 % stock, 0 % = off). Second rev hang lever,
  smaller than the fuel cut delay (RPM falls ~350 rpm/0.6 s clutch in before the cut, ~600 rpm/0.25 s after).
  Code not traced (TODO: 0x573A8 idle air add / 0x5752A floor / 0x57BB0). 85 % for the log facts.
- Forum/vendor comparison (2026-10-25): Hondata help "rev hang" = uncheck overrun throttle opening + overrun fuel cut
  delay per gear, suggested 20-50 "ms"; CR-Z stock 60, users 10-20. KTuner: OTC 0 % + fuel cut delay ~20 common;
  0/0 reported jerky in traffic / downshifts; one Civic 1.5T report of higher knock with delay 0 (unproven); Hondata
  1.5T "rev hang disable" broke cruise hold. Units vs our ticks not known (50 %), but our 40 = Honda's own 4th/5th value.

## Decel fuel cut entry delay (Ghidra + emulation, 2026-10-25) -- the rev hang
- In 0x580DE (base 0xFFFF433E): B+0 = decel cut conditions met, B+2 = delay running, B+3 = 0xFFFF4341 = decel fuel
  cut active (= HDS FCDEC, 85 %). B+3 sets only when B+0 = 1 and the delay timer 0xFFFF76C0 (0xFFFF76BC + 4) = 0.
- While the conditions are NOT met (pedal on), the timer is reloaded every cycle (0x58652-0x58720):
  - stopped (B+0x20: speed 0 for 300 ticks, 0xB13C): 0xB152 = 0 -> cut at once;
  - moving: max(table 0xB158[gear 0xFFFF3F06], 0xFFFF76BE) where 0xFFFF76BE = 40 (0xB13E/0xB140) after a gear
    change (reset to 0 only above 4000 rpm; decrementer not found, see "Flash #3 file"). Table descriptor 0xB158: axis bytes 0x15ABC = gears 1..5, data words 0x15AC2 = 80, 80, 80, 40, 40.
    Gear below 1 (clutch / neutral) clamps to gear 1 = 80;
  - RPM > 4000 (B+0x1F, off < 3800, 0xB138/0xB13A): min(that, 0xB150 = 40);
  - (B+7 and 0xFFFF2BDC): 0xB154 = 10.
  - Helpers: 0x8B8C = max(r4, r5), 0x8B82 = min(r4, r5) (disassembly, 100 %).
- Only users: descriptor 0xB158 (pool 0xB15C/0xB160) read only in 0x580DE via 0xB138 + 0x20 (FindRefs,
  src\findrefs_fcdec.txt). 0xFFFF76C0 also read (copy only) by the monitor function 0x3C126.
- Emulation src\ghidra_scripts\EmuFuelCut.java (src\emu_fuelcut*.txt), one call = one timer tick: stock gear 2/3
  3000 rpm -> 79 ticks, gear 4 -> 39, gear 2 4500 rpm -> 39, stopped -> 0. Patched 0x15AC2-0x15AC6 = 40 -> 39 ticks
  in all gears; all 20 -> 19.
- Car log fit: 0 ticks = 0.35 s, 40 = 0.75-0.87 s, 80 = 1.18-1.41 s -> one tick ~10-12 ms plus ~0.35 s of other
  latency (lift-off detection, MAP drop) -- 80 %. This also suggests the 0xFFFF76xx-78xx timers tick every ~10 ms
  (tip-in counter 0xFFFF7852: EmuTipIn "tick 3" case), 65 %.
- Lift-offs with no decel cut at all (log 1465.5 and 1493.0, 25-28 km/h, src\hds_snapshot\window.py): the pedal
  came back (0.6-1.9 %) at 1.20-1.26 s, just BEFORE the ~1.2 s delay ran out; the cut case 1396.2 at the same speed
  cut at 1.19 s with the pedal still at 0. So "never" = pedal back before the 80-tick delay ends, no other condition
  needed (now 90 %: the 0xFFFF3D0C pedal input of B+0 was traced, see "Confidence research" below). In all three the
  RPM stays at ~3100-3400 for ~1 s and only falls when the clutch is released (~1.05 s): the delay is longer than a
  normal shift, which is the felt rev hang. With option C (40 ticks, ~0.8 s) the cut would come before the clutch.

## Decel fuel cut: the "rest of the delay" = MAP must settle first (traced + logs, 2026-10-30)
- Full B+0 condition (decomp 0x580DE lines 1043-1088): B+8 (enable) and pedal off (3D0C == 0) and B+5 (RPM above
  the resume threshold B+0xE) [or the alternative B+6 path], then, while B+3 is not yet set: B+0 = 1 only if
  0xFFFF5F5B is not 0x33..0x36 AND (0xFFFF59F7 != 0 OR |0xFFFF29F8| < B+0xA). B+0xA = 0xB1F4 = 80 (0xB1F6 = 32767 =
  no check when 0xFFFF2BDB != 0). Helper 0x8AC2 = saturated abs() (disassembly).
- 0xFFFF29F8 = 0xFFFF2940 + 0xB8, written only at 0x4B658 (find_gbr.py; 0x28C64 = init to 0) in 0x4B3EE:
  = MAP(0xFFFF29D8 = 2940 + 0x98) now - MAP 3 samples ago (history 2940 + 0xAE..0xB4). So the delay timer is held
  (reloaded, B+0 = 0) until MAP changes by less than 0.80 kPa over 3 ECU samples, i.e. the manifold has emptied.
  The timer only STARTS after that: the two parts are in series (95 %).
- Logs (src\hds_snapshot\mapsettle.py, MAP step <= 1 kPa between two 57 ms HDS samples = settled):
  baseline N 80: 24 lift-offs, MAP settles at median 0.40 s, FCDEC - settle median 0.83 s;
  v2 N 40: 29 lift-offs, settle median 0.40 s (unchanged), FCDEC - settle median 0.41 s; above 4000 rpm (N 40 in
  both logs) 0.35 s. The timer part exactly halves with N (0.83 -> 0.41 = ~10.3 ms per tick at 2700-3500 rpm) and
  the settle part does not move -> the ~0.4-0.5 s "rest" is the MAP settle wait, not a limit on the table change.
  At ~2100-2400 rpm the timer part is longer (0.43-0.62 s, crank-like), above 4000 rpm shorter (0.35, not 1/rpm):
  tick rate still not settled (crude 1 kPa settle detection).
- v3 prediction from this: FCDEC ~0.40 + 0.21 = ~0.6 s at 2700-3500 rpm (v2 0.81 median), ~0.55 s above 4000.
- Possible later option (NOT proposed): raise 0xB1F4 (80) so the timer starts before MAP has fully settled. That is
  Honda's guard against cutting fuel while the manifold is still full (torque jolt / lean misfire): leave it.

## Flash #3 FLASHED 2026-10-30 19:44 (v3_fuelcut20.rwd): SUCCESS
- Car day: part A green (hashes exe 97AB3006, v3 F8836DEC, v2 BD4D4F38, stock 6E4CACCB; laptop on AC after plugging
  it), PGM-FI no confirmed/pending DTC before (HDS shows VIN + A240), HDS closed (2 SnapShotClient zombie entries
  could not be killed, "no running instance"; adapter worked anyway), 12.74 V rising after 3 min on the 10 A
  charger, Connect ECU VIN + A240, multi-frame 22 F1 90/F1 81/F1 8C/F1 87 OK both ways.
- Dry run flash_20261030_194318: 10 03 -> 50 03, seed 93 D4 -> key 94 B0 -> 67 02, 12.79 V, ECU not erased.
- Flash flash_20261030_194434: seed 35 44 -> key 37 A8, 50 02, erase 71 01 FF 00 (8 s), 74 20 08 02, 496/496 in
  2:36, battery 12.84 -> 13.07 V, 37 -> 77, 31 01 FF 01 -> 71 01 FF 01, SUCCESS. FLASH_DRYRUN.txt put back.
- Tool cosmetic bug seen: the bottom progress bar stays at 95 % (then 0 %) while the "Writing: N %" label moves.
  CAUSE (proven 2026-10-30 from the DarkUI.dll IL, read with reflection): DarkProgressBar has LockGoingBack = true by
  default (ctor). On each WM_PAINT: if Value > _lastValue, _lastValue = Value; if Value < _lastValue and _lastValue <
  Maximum, it sets Value back to _lastValue. The .rwd decrypt loop (Class_RWD.cs:1110, method_4) leaves _lastValue at
  its last percent (~95), so ResetProgressBar (0) and "Writing" 0-94 are forced back to 95; the bar only moves
  again above 95, and once it hits 100 (= Maximum) the lock lets the final 0 through. Label and bar get the same
  value (GForm_Main.method_5). Display only, no effect on the flash. Fix: darkProgressBar_0.LockGoingBack = false.
  FIXED 2026-10-30 20:35: 2 lines in GForm_Main.cs InitializeComponent (only file changed since the 97AB3006 build),
  rebuilt (0 errors, old warnings only), self test 51/52 from src\build AND from FlashToolTest_v2 (only the
  hard-coded v1 check; docs\logs\2026-10-30_progressbar_selftest). Deployed exe = built exe = E2DFC687...
  (E2DFC6872B29D798F50D0FAFB22581F1E3074C32541C334F5C85749E66A0D528). Old 97AB3006 kept in
  _archive_old_builds\FlashToolTest_v2_97AB3006. Not yet seen on the car (the bar is only checked by eye).
- After: starts, idle straight to ~1000 rpm (engine still warm from the 18:30 drive; gauge at min only means < ~50-60 C;
  flash #2 cold start was ~1100 at ECT 49 C). HDS All DTC Check (first time BODY ELECTRICAL lists codes):
  PGM-FI no DTC; SRS 56-31; ABS 65-11 + 61-11 (known); BODY ELECTRICAL U0100 (gauge lost PCM, expected from the
  flash), U0127 (gauge lost TPMS, car has no TPMS sensors), B1234 (air mix motor driver's side), B1241 (blower motor
  circuit). B1234/B1241 = climate control unit, not the ECU (v3 changes 8 fuel cut bytes only); never read before, so
  unknown if new: clear, test HVAC (blower all speeds, temp full hot/cold), re-read.
- HDS DTC CLEAR (all, engine running): PGM-FI green, BODY ELECTRICAL green, SRS red, ABS red (ABS clear always fails,
  known since flash #1).
- Re-read right after: PGM-FI no DTC, SRS no DTC (cleared despite the red dot), ABS 65-11 + 61-11 (known), BODY
  ELECTRICAL only U0127 (comes back at once: no TPMS sensors, matches the TPMS light). U0100, B1234, B1241 gone
  (HVAC not run yet, so B1234/B1241 not re-tested).
- HVAC test after clearing (user): heat and A/C work fine. All DTC re-read after it: same clean result (PGM-FI, SRS
  none; ABS 65-11/61-11 known; U0127 only). B1234/B1241 did not come back = set by the flash (power/comm loss).
- Idle relearn after flash #3 (idle until the radiator fan): done, user reports it good (2026-10-30).

## Rev limiter research (started 2026-10-30, read only)
- FOUND 2026-10-30: rev limiter = function 0x58898 (called by the fuel cut manager 0x580DE right before the speed
  limiter), GBR base 0xFFFF433C (src\decomp_58898.txt). Its result 0xFFFF4382 (+0x46) = OR of flag list 0x15BB8
  (FFFF4E40, FFFF4389, FFFF438A, FFFF438B, FFFF59FD); 0x4382 is in the fuel cut list 0x15B5C -> 0xFFFF4271. 85 %.
  Writers found with src\find_base_stores.py (GBR/base+disp stores; it also finds the known 0x4383 / 0x4341 stores).
- Main limiter flag 0xFFFF4E40, hysteresis: cut when RPM > cut (0x433C+0x50), stays cut until RPM <= resume (+0x52).
  Targets: 0xFFFF3D0D = 0 -> cut 7100 (desc 0xB220 at speed 0x7FFF) / resume 6900 (0xB238); 3D0D != 0 -> 7300
  (0xB22C) / 7100 (0xB244). Normally +0x50/+0x52 sit at the targets (ramp up 675/cycle, 0xB218).
  Stopped protection: speed <= 20 (0xB258) and RPM > 3500 (2000 once active; 0xB250/0xB252) and 0xFFFF2A1A > 500
  (0xB25A): counter +0x58 from 600 (0xB25C) down by 1 per 10 cycles (0xB21C); at 0 the cut/resume points step down
  by 23 (0xB21A) to the speed tables at 0 km/h: 3500 / 2500 (0xB220/0xB238 axis 0..20 km/h). 80 %.
- Flag 0xFFFF438A (+0x4E), second hysteresis limiter: 0xFFFF3403 = 0 -> cut 0xB288 / resume 0xB294 by speed
  (0..5 km/h): 4000 -> 7300 / 3700 -> 7100 (stopped 4000 rpm limit). 3403 != 0 -> 0xB278 / 0xB26C (5000/4700
  stopped) or 3000/2500 (0xB2A0/0xB2A2) above 5 km/h (0xB2A4/0xB2A6 hysteresis 5/3), main targets if 0xFFFF2C01 /
  2BFD / 2BFF set. 70 % (3403 meaning unknown, looks like a fail-safe mode).
- Flag 0xFFFF4389 (+0x4D): 3000/2800 rpm limits when +0x54/+0x55 set (0xB264..), or 0xFFFF4135 + RPM > table
  0xB1FC by pedal 0xFFFF2ACE (1500 at 0 pedal, 3700 above 3200) = fail-safe limits, 60 %. 0xFFFF438B (+0x4F) =
  one-cycle cut from counter +0x94 (reload 20, 0xB2F8) when 0xFFFF6265 set. 50 %.
- All these limiters are full fuel cut flags (same path as the speed limiter).
- 0xFFFF3D0D written by 0x55F5C (src\decomp_3D0D_3403.txt), params 0xAAC8: 1 when speed >= 10 km/h (5 hysteresis),
  coolant 0xFFFF2A1A >= 600, time 0xFFFF784C >= 500, RPM above ~5000/4800 (0xAADA..0xAAE0), MAP < table 0xAAE4
  (all 32767 = no limit), enable 0xFFFF33FC, on/off delays, states 0xFFFF60A8/60AC/50E1; blocked when 0xFFFF3403
  and 0xFFFF3D40 are both set. = VTEC (high cam) engaged, 70 %. So: low cam cut 7100/resume 6900, VTEC cut 7300/
  resume 7100; the second limiter 0x438A also gives 7300/7100 moving (>= 5 km/h). On a warm healthy car at the
  limit in gear: probably 7300 rpm, 65 %. 0xFFFF3403 (writer 0x3FDAA, not decoded) looks like a fail-safe mode.
- LOG PROOF of the stopped limit (0x438A, 3403 = 0 path, cut 4000 / resume 3700 at 0 km/h): in all 3 logs the max
  RPM at 0 km/h is 4014-4105, and the 2026-10-25 log shows fc = 1 at 4105 rpm with fcdec still 0 (pedal already 0,
  blip overshoot), fcdec takes over at 3750. 90 %. (The "lift_stopped" blips that reach 4000 are cut by this limiter
  before the decel cut: keep it in mind when reading stopped FCDEC times.)
- EMULATED 2026-10-30 (src\ghidra_scripts\EmuRevLim.java, whole 0x58898 called per cycle, timer 0xFFFF76C8 forced
  expired each call, fresh RAM per case, ECT 850; results src\emu_revlim.txt). Stock: VTEC on 80 km/h cut ON at
  7301 (4E40 + 438A) / OFF at 7100; VTEC off cut 7101 / 6900 (4E40); 0 km/h cut 4001 / 3700 (438A). 95 %.
- Soft limiter option "smaller hysteresis" (calibration only, 3 words, cut points unchanged): resume values
  0x15C06 (no VTEC, 6900), 0x15C0E (VTEC, 7100), 0x15C32 (2nd limiter moving, 7100). Emulated: hyst100 =
  7000/7200/7200 -> OFF at 7000 / 7200, hyst50 = 7050/7250/7250 -> OFF at 7050 / 7250; cut ON unchanged (7101 /
  7301), stopped 4001/3700 unchanged. Users: data pointers only in descriptors 0xB238/0xB244/0xB294; those only via
  base 0xB218 / 0xB294 loaded in 0x58898 (src\findrefs_revlim_resume.txt). 90 %. Not known: the real cut/resume
  cycle rate on the engine (call rate of 0x58898, RPM dynamics), so the felt effect is not proven.
- Other options: ignition retard just below the limit (Hondata advice) needs the ignition maps found first (not
  done); a real partial (cylinder) cut needs a code patch (not recommended).
- Tuner guidance (web 2026-10-30): Hondata FlashPro help (read on hondata.com): the ECU uses a fuel cut limiter;
  "Normally the recovery rpm should be set 100-300 rpm lower than the activation rpm", a larger gap = slower,
  rougher limit. So hyst100 = low end of Hondata's range, hyst50 is OUTSIDE it (do not use). Forum users (not
  Hondata staff, old posts): soften with ignition retard starting ~150-250 rpm before the limit, ~-10 deg at the
  limit. KTuner Accord owners (DriveAccord): talk about raising the limit (7100-7450), nothing found on the resume gap.
- v4 BUILT 2026-10-30 (not flashed, user asked build + emulator test only): src\build_v4.py from work\v3_fuelcut20
  (checks the v3 SHA256, cipher, descriptors 0xB220-0xB294 + axes, ROM literals, neighbours unchanged).
  0x15C06 6900 -> 7000, 0x15C0E 7100 -> 7200, 0x15C32 7100 -> 7200; checksum 0x8400 0xF6 -> 0xC7, sum 0 mod 256.
  Diff vs v3: 7 bytes (0x8400, 0x15C06-07, 0x15C0E-0F, 0x15C32-33); vs stock: 20 (v3's 14 + those 6).
  SHA256: work\v4_revlim100.bin 18500F7F767F0F91F8551F5B534D2B6152F4E4A7030532A6ED1283C7123E5DB4;
  work\v4_revlim100.rwd 0AC6119B87077F35FAF65F919F0D7FFDEAB095679662F991587725BE8BB8B3B3. Read-only. NOT in flash\.
  verify_rwd.ps1: header identical, cipher 256/256, 0 mismatches, file checksum 0x06A74ED9, RESULT OK.
  Emulation on the built file (own project src\ghidra_proj_v4, no patches, src\emu_v4file_raw.txt): rev limiter VTEC
  on 7301 / OFF 7200, VTEC off 7101 / 7000, 0 km/h 4001 / 3700 (= the hyst100 patch result); EmuFuelCut 19 ticks in
  every case, stopped 0 (= v3); EmuLimiter speed 240 (= v1). Self test FlashToolTest_v2 (E2DFC687 deployed = built):
  51/52, only the hard-coded v1 check (docs\logs\2026-10-30_v4_selftest), simulated flash 496/496, data == firmware.
  Still missing before any flash: user decision, copy to flash\, dry run on the car. Felt effect unproven.
- Tuner documentation for THIS car (web 2026-10-30):
  - Hondata: no FlashPro for the US/Canada 2008-2012 Accord (the Accord 2008-2010 FlashPro is non-US only, RL6 ECUs,
    "not for sale in the US/Canada"). US owners swap in a TSX ECU. No published contents of any base calibration.
    Official help (rev_limit_parameters.htm): fuel cut limiter; recovery 100-300 rpm under activation; the overall
    limit "may be lower when the engine is cold or when the low-speed camshaft is in use" (= our 7100 without VTEC /
    7300 with VTEC); launch (stopped) limiter fastest when cut = recover; speed limiter off = value above top speed.
  - KTuner (ktuner.com/0812accord): supports the 08-12 Accord i4, 2011-2012 ECUs listed as 37820-R42-A21..A29
    (hardware numbers; ours should be 37820-R42-A24 for software A240: assumed, label not read). "Speed Limiter Has
    Been Removed" (we set 240). Feature list: rev limiter, 2-step, VTEC window, throttle maps, fuel cut parameters,
    ignition/fuel, VTC, knock, closed loop, idle, disables. Free tunes exist but their contents are NOT published.
    Help: Rev Limits = High Limit (moving) + Low Limit (stopped, "basic 2-step"), Limit + Restart rpm, "the closer the
    limit and restart are, the faster the cut" (= our 0x58898 moving 7100/7300 and stopped 4000 limiters). Fuel Cut
    Settings = Overrun Throttle Compensation (100 % factory, 0 % = no rev hang), Fuel Cut Delay, MAP cut/recovery by
    cam, min cut rpm by MAP / TPS. Throttle Responsiveness = levels over factory (no details).
  - Forum users only (not official, unverified): KTuner base/street tunes on the 8G i4 raise the limit to ~7400 and
    keep VTEC at 5000 (lowering it lost power), 91 octane; one user set fuel cut delay "20" in all gears.
  - So our v1-v4 match what the tuners expose (speed limiter, fuel cut delay, tip-in, resume gap). Not done by us:
    overrun throttle 0 % (dropped: oil consumption bulletin 11-049), higher rev limit (user rule: never raise it).
- Web: a Honda service document for the 2008+ Accord 2.4 says the ECM cuts fuel above 7,000 rpm (LX M/T),
  7,100 rpm (EX M/T), 5,000 rpm (A/T) (as summarized by search, wording "vehicle stopped" not checked). Hondata:
  stock Honda limiter = fuel cut only; their "soft limiter" = progressive cylinder cut ~200 rpm before the limit.
- Ruled out: 0xC5DC (7100 = field of a descriptor block used by 0x661B8, MAP/baro logic, not RPM) and 0xB6E2/0xB6E4
  (7100/3800 = MAP breakpoints 71.00/38.00 kPa in the fuel calc 0x5BCB4, interpolation on 0xFFFF29D8). 0xB100-0xB1FF
  (fuel cut manager params) has no 7000-7200 value. 0x43C1 (= 0x433E+0x83) = timed cut when 0xFFFF2B11 is set
  (time from table 0xB2D8 by 0xFFFF2A1A); 0x4384 (+0x46) = its "started" flag; 0x4385 (+0x47) always 0 in 0x580DE.
- Writers of 0xFFFF4382 / 0xFFFF4385 found only in 0x23904 (init to 0); 0xFFFF3FB8: no direct writer (base+disp
  store). Next: find the GBR/base-register stores to 0x4382 / 0x4385 / 0x3FB8 (one is probably the rev limit flag).
  Output files: src\findrefs_revlim*.txt, src\decomp_revlim.txt, src\decomp_5BCB4.txt.
- Road test log 2026-10-30 20:11-20:20 (docs\logs\2026-10-30_v3: dat\ + csv + all.csv + analysis.txt; 6 snapshots,
  ECT 82-85 C). V3 WORKS AS DESIGNED (95 %):
  - mapsettle: 47 moving lift-offs, FCDEC 0.47-0.80 s, median 0.62 (v2 0.81, baseline ~1.27). MAP settle median
    0.41 (v2 0.40, unchanged as predicted), "FCDEC - settle" median 0.18 (v2 0.41, predicted ~0.21) = the timer part
    halved again.
  - Above 4000 rpm 0.47-0.54 s (v2 0.69-0.77). Lift-offs right after a shift / with an rpm rise 0.52-0.63 s = same as
    without a shift (gear change floor 76BE now 20 works). Slowest 0.79-0.80 s only at ~1850-2200 rpm (slow ticks).
  - Stopped blips 0.29-0.30 s (v2 0.35, 2 samples, ~1 sample of 57 ms; not explained yet, maybe the 76BE floor on the
    shift to neutral).
  - tickfit2 with 3 tick counts (80/40/20, n=110): crank model rms 0.066 s vs time model 0.099 s -> the delay timer
    ticks with engine rotation (75 %), ~0.0093 s per tick-unit scale (fit), a = 0.44 s fixed part (MAP settle).
  - Feel (user, 2026-10-30): pedal much more responsive; a fast stab 0 -> 50 % gives a bigger kick (tip-in x2 from v2),
    gradual pedal follows the foot very well. Rev-match downshifts much better: direct, no more random delay
    (consistent with the gear change floor 40 -> 20 and the shorter cut entry). "A lot more fun".
  - v1/v2/v3 comparison (src\hds_snapshot\compare_versions.py -> docs\logs\compare_v1_v2_v3.json, same pedal scale):
    lift-off -> FCDEC median moving < 4000 rpm 1.21 / 0.83 / 0.63 s, > 4000 0.73 / 0.70 / 0.53 (n 10/3/3), stopped
    0.36 / 0.35 / 0.29. Tip-in lag (target 90 % - pedal 90 %) moving light pedal 0.34 / 0.11 / 0.12 s, pedal > 50 %
    0.06 / 0.11 / 0.06, stopped 0.09 / 0.06 / 0.06, < 10 km/h 0.68 / 0.45 / 0.76 (clutch / 2-stage pedal, not a real
    delay, see the 2026-10-30 note). Tip-in v2 = v3 as expected (same tip-in table).

## Flash #3 file v3_fuelcut20 (2026-10-30): built and verified, flashed the same day (above)
- Goal: decel fuel cut delay 40 -> 20 ticks (KTuner-like). Starts from the flashed v2 (keeps 240 km/h + tip-in x2).
- Gear change floor 0xFFFF76BE (decomp 0x580DE, lines 1121-1171 of src\decomp_580DE.txt): 76BE = 0xB13E (40) when
  gear 0xFFFF3F06 != 0xFFFF3FD9 (0xFFFF3403 != 1), = 0xB140 (40) in the 3403 == 1 case, = 0 only when RPM > 4000
  (B+0x1F). Delay = max(table, 76BE). No code decrementing 76BE (or 76BC/76C0) found: no ROM literal for 0xFFFF76BE,
  no word-array decrement loop, 0x3C126 only copies 76C0, 0x385AA uses 0xFFFF7558/7844 but is not a timer loop.
  So with only the table at 20, the floor could keep the delay at 40 after each shift. -> v3 also sets the floor to 20.
- The block 0xB138 is referenced only by the pool words 0x586D4 / 0x588C4 (both in 0x580DE); 0x15AC2 only by 0xB160
  (descriptor 0xB158); no literal for 0xB13E / 0xB140 / 0xB150 / 0xB158 (100 %).
- src\build_v3.py (from work\v2_tipin_fuelcut, checks the v2 SHA256 first): 0x15AC2-0x15ACA 40 x5 -> 20 x5 (gears
  1-5), 0xB13E/0xB140 40,40 -> 20,20. Checksum 0x8400 0x6A -> 0xF6. Neighbours checked unchanged (4000/3800/300,
  0xB150 = 40, 0, 10, 510, 0x15ACC = 300). 0xB150 (cap 40 above 4000 rpm) kept: min(20, 40) = 20.
- Diff vs v2: 8 bytes (0x8400, 0xB13F, 0xB141, 0x15AC3, 0x15AC5, 0x15AC7, 0x15AC9, 0x15ACB); vs stock: 14 (those +
  0xB2C3, 0x1419D, 0x1419F, 0x141A1-0x141A3).
- SHA256: work\v3_fuelcut20.bin 1D3F2779EDC6B7764ECC6928C10A967139EEB963A2FC696E25E5C85361DA7145;
  work\v3_fuelcut20.rwd = flash\v3_fuelcut20.rwd F8836DEC2B820487DB542D7BE801A2FF4A15D943E462B8E01948378E03D1D79D.
  All read-only.
- verify_rwd.ps1: header identical, cipher 256/256, 0 mismatches, file checksum 0x06A74FD9, RESULT OK. Byte sum 0 mod
  256, one part number 37805-R42-A240, ECUS_KEYS line 1568.
- Emulation on the built files (EmuFuelCut.java with gear change cases added, src\emu_v3file.txt): v3 = 19 ticks in
  every case (gears 2/3/4 at 3000 rpm, gear 2 at 4500, shift 2->3 ending 5 or 100 calls before lift-off, 76BE
  decremented or not); stopped 0. v2 = 39 everywhere, stock = 79 (gears 1-3) / 39. Option A (table only, floor 40):
  34 ticks if 76BE counts down and the shift ends 5 calls before, 39 if 76BE does not count down -> the floor change
  is needed. Assumed (same as v2, which matched the car): 1 call = 1 tick, 0xFFFF3403 = 0.
- Self test FlashToolTest_v2 (exe 97AB3006 = src\build): 51/52, the only FAIL is the hard-coded "v1 = 2 bytes" check
  (docs\logs\2026-10-30_v3_selftest). Simulated flash 496/496, data == firmware.
- Expected on the car (tickfit2 crank model, rms 0.064 s): FCDEC ~0.76 s at 2000 rpm (v2 ~1.01), ~0.68 s at 3000
  (v2 0.84-0.87), ~0.62 s above 4000 (v2 ~0.73); stopped unchanged 0.35 s. The ~0.4-0.5 s rest is the MAP settle
  wait, in series with the timer (section above): the table change keeps its full gain, ~0.6 s expected at
  2700-3500 rpm. Confidence: works 92 %, no damage 92 %.

## Flash #2 FLASHED 2026-10-30 (v2_tipin_fuelcut.rwd): SUCCESS
- Car day: hashes OK (exe 97AB3006, v2 BD4D4F38), battery 12.70 V stable 3 min key ON on the 10 A charger, engine
  cold, HDS closed. Connect ECU VIN + A240. Multi-frame 22 F1 90/F1 81/F1 8C/F1 87 OK both ways (F1 8C/F1 87 not
  returned, no NRC). Dry run: 10 03, seed 26 8B -> key 4A AB, 67 02 (log flash_20261030_180534).
- Flash (FlashToolTest_v2\flash_logs\flash_20261030_180804.log): seed 75 B9 -> key 84 11, 10 02, erase 31 01 FF 00
  -> 71 (8 s), 34 -> 74 20 08 02, 496/496 blocks in 2:26, battery 12.88-13.01 V, 37 -> 77, 31 01 FF 01 -> 71 01 FF 01.
- After: starts, cold idle ~1100 rpm dropping, idle left to relearn until the fan. HDS: PGM-FI no DTC (confirmed or
  pending, ECU reports 37805-R42-A240); SRS 56-31 (lost PCM comm during the flash, same as flash #1); ABS 61-11 +
  65-11 (known). After clearing: no MIL, only the TPMS light (car has no TPMS sensors, normal). FLASH_DRYRUN.txt put
  back.
- Road test log 2026-10-30 (docs\logs\2026-10-30_v2: dat\ + csv + all.csv + analysis.txt; 7 snapshots, ~15 min,
  ECT 80-87 C, slightly cooler than the baseline 84-90). `ana2.py all.csv both 0 14543` (same pedal scale):
  - Decel cut moving below 4000 rpm (12 lift-offs, 22-57 km/h, 2650-3750 rpm): FCDEC 0.81-1.00 s, median 0.87
    (baseline 1.18-1.47, median ~1.27): -0.4 s = 40 ticks less. Predicted 0.73-0.92 (2 of 12 slightly above).
    Every moving lift-off got FCDEC (baseline: 3 without). Controls unchanged: stopped 0.35 s (was 0.34-0.41),
    above 4000 rpm 0.75-0.82 s (was 0.75-0.87). C WORKS AS DESIGNED (95 %).
  - Tip-in lag moving: median 0.11 s (baseline 0.23), lags > 0.4 s in 7/44 events (baseline ~16/42). HDS sampling
    is 57 ms, so medians are +-1 sample. A2 effect visible (80 %).
  - The remaining "big lags" (0.57-1.15 s, 998.8 / 1028.0 / 981.9) are NOT a delay (sample by sample, twostep.py):
    the target follows each pedal step within 1-2 samples (0.06-0.11 s); ana2's metric counts a 2-stage pedal press
    and the target that keeps rising with rpm at a constant pedal (pedal map depends on rpm). At those points MAP
    is already 83-88 kPa (near full load at 1000-2500 rpm), so more throttle per pedal % would add little torque;
    the 5-10 km/h cases also show the clutch engaging (rpm falls 1130 -> 842 at constant speed). Conclusion: no
    software delay left to remove on tip-in (80 %); a faster ramp would mainly make the driveline shuffle harsher.
  - Tick rate: joint fit stock 80 + v2 40 (src\hds_snapshot\tickfit2.py, 63 lift-offs): crank-linked rms 0.064 s
    (a 0.51 s + ~0.83 TDC per tick) vs fixed time rms 0.104 s (a 0.42 + 10.1 ms). The delay timer most likely
    counts engine events, not time (75 %): with 40 ticks the cut comes ~0.87 s at 3000 rpm, ~0.78 s at 5000.
  - Driver feel: "two knocks" on a sudden 0 -> 90 % tip-in and on a fast lift-off, ALREADY THERE BEFORE ANY TUNE.
    Log (scratchpad twostep.py, rpm slope at constant gear = vehicle acceleration): after every torque step the rpm
    oscillates +-700..2900 rpm/s with a ~0.2-0.25 s period (~4-5 Hz), 2-4 swings, e.g. tip-in 680.6 (+1820, -2821,
    +2821, -1052), 833.6 (+1603, -2873, +2684, -1448); same in the baseline (1962.7: +1304, -1018, +1143) =
    driveline shuffle (gear lash / CV / engine mounts winding up and springing back). On a lift-off there are also
    TWO torque drops: throttle close (0-0.2 s, -782 then +889 rpm/s at 641.0) and the decel fuel cut later (0.87 s:
    -1067 then +807). Cause most likely mechanical slack + mount wear at 291k km (60 %), not v2 (baseline same).
    Also seen: IG dips to 0..-4 deg for ~0.1 s when MAP reaches 100 kPa at 1500-1800 rpm (833.6, 1071.9) -- knock
    retard or a tip-in torque cut, not traced. HDS 57 ms sampling only shows the shape, not the exact peaks.

## Flash #2 file (2026-10-25): built and verified
- src\build_v2.py from work\v1_speedlimiter (keeps 240 km/h): A2 0x1419C 6,30,100,300 -> 12,60,200,600 (descriptor
  0xAB40 checked: axis 0x14190, data 0x1419A, first point 0 kept) and C 0x15AC2 80,80,80 -> 40,40,40 (descriptor
  0xB158 checked). Checksum 0x8400 0xA7 -> 0x6A. Only the changed bytes re-encrypted in a copy of the v1 rwd.
- Diff vs v1: 9 bytes (0x8400, 0x1419D, 0x1419F, 0x141A1-0x141A3, 0x15AC3, 0x15AC5, 0x15AC7); vs stock: those + 0xB2C3.
- src\verify_rwd.ps1: header identical, cipher 256/256, 0 mismatches, file checksum 0x06A751A9, RESULT OK.
- Emulation on the built bin (Ghidra project EMUV2, src\emu_v2file.txt): fuel cut 39 ticks moving in all gears, 0
  stopped; tip-in gear 2 42/79/135, gear 4 63, gear 1 86, gear 5 47, small step unchanged = exactly the ROM-patched
  emulations. EmuLimiter: speed limiter still 240 (cut at 241). 100 % for the file content.
- FlashToolTest_v2 exe 97AB3006... (deployed = built). --selftest (docs\logs\2026-10-25_selftest): with v1 52/52;
  with v2 51/52: the only FAIL is the hard-coded "v1 differs from stock by 2 bytes" check (v2 has 10, expected);
  v2 rwd valid (header, file checksum, start/size, CAN 0x10, 1 part number A240, supported, ECUS_KEYS, internal
  checksum), decrypt == bin, full simulated flash 496 blocks data == firmware.
- Still to do on the car day: CHECKLIST_FLASH_DAY.md (VIN/cal ID, DTCs, battery, AC, dry run, recovery), then the
  same HDS Snapshot tests to compare with the baseline.
## Confidence research for flash #2 (2026-10-25, read only, nothing flashed)
- Pedal condition TRACED (decompile 0x580DE, scratchpad dec580DE): B+7 = (0xFFFF3D0C == 0) = pedal off; B+0 is set
  only if B+8 and pedal off and B+5, else cleared (unless the hold flag). So the lift-off input of B+0 is 3D0C
  (was 80 % "not traced", now 95 %). 3D0C is also the pedal-off gate of the overrun air 0x4F52A.
- B+3 = 0xFFFF4341 = B+0 and not B+1 and (B+3 already | 0xFFFF59F7 | delay timer = 0): latched "cut active after the
  delay", exactly the HDS FCDEC behavior in the log -> FCDEC = 0x4341 now 90 %. 0x4341 is also in a list of RAM byte
  addresses at 0x15B5C (0x4382, 0x4383, 0x4341, 0x4385, 0x4384, 0x3FB8), role unknown.
- 0xFFFF2BDC = FUEL CUT INHIBIT from another module (corrected 2026-10-25, src\find_gbr.py): written GBR-relative
  (GBR 0xFFFF2B1C, disp 0xC0) at 0x3BE8E = NOT bit 7 of byte 0xFFFF2B28 of a 78-byte received frame (buffer
  0xFFFF2B1C.., byte-sum checksum, receive/validate 0x3BC08, decode 0x3BDC2); 0x3BF44 = default 0 when the frame is
  missing/invalid. Source module not identified. In 0x580E2: 2BDC != 0 -> B+8 = 0 -> NO decel cut at all (line
  "3e18 || 2bdc || 3fbf"); while it is set and the pedal is off the delay timer counts down to 0xB154 = 10 and holds;
  also changes the cut threshold (0xB1CA vs 0x4136). Same code in stock and v2 -> no effect on the v2 change. Log:
  every moving lift-off without pedal-back got FCDEC, so it was not set during the baseline (90 %).
- 0x4341 (FCDEC flag) is written only at 0x587B4 inside the fuel cut function (GBR scan, all of the ROM).
- REAL ENTRY of the fuel cut function is 0x580E2 (0x580DE-0x580E1 = pool words 0x7FFF, 0x92D8 of the previous
  function). Call chain (src\call_chain.py): 0x580E2 <- 0x5BCB4 <- 0x77F18 <- 0x49A6E <- 0x2C37A = handler in the
  vector table at 0x821C = vector 135, called on EVERY interrupt (no counter gate). Vector 135 is "reserved" in the
  SH7058 manual text (133-135 between OVI4 132 and IMI5A 136), so its hardware source is NOT known; no trapa #135.
  The handler clears TIER3 bit 4 (OVE3) at entry. The decrement of 0xFFFF76C0 was not found (no direct, base+disp,
  GBR or loop access) -> tick rate still not proven in code.
- Tick model fit (src\hds_snapshot\tickfit.py, 34 moving lift-offs): fixed time 12.3 ms/tick + 0.24 s rms 0.082 s;
  crank-linked (tick ~ 24/rpm s) + 0.54 s rms 0.067 s. Within 80-tick events the delay drops with rpm (2400 rpm
  1.31-1.41 s, 3500 rpm 1.09-1.14 s), which favors a crank-linked part OR an rpm-dependent entry condition (B+5);
  HDS sampling cannot separate them. v2 prediction below 4000 rpm: 0.73 s (time) to 0.83-0.92 s (crank), stock
  1.1-1.4 s. Both models agree within ~0.2 s. Log cross-check (src\hds_snapshot\stops.py all.csv): 0 ticks (stopped 19-47 s) FCDEC 0.29-0.41 s; 40 ticks
  (> 4000 rpm) 0.67-0.81 s; 80 ticks (< 4000 rpm, moving) 1.09-1.41 s -> ~0.3 s offset + 10-12 ms/tick, consistent.
  KEY POINT: v2 puts gears 1-3 at 40 ticks = a value the stock ECU already runs on this car (above 4000 rpm and in
  4th/5th): the v2 behavior below 4000 rpm is already observed (0.67-0.81 s), not extrapolated.
- TSX definition (FlashToolTest_v2\Definitions\Generated\37805-RL5-A030_Acura_TSX_2009_2010.txt, our address = TSX
  + 0x254 in this region) names our tables: "Overrun fuel cut delay" = 0x15AC2 (independent name confirmation, 95 %),
  "Overrun injector restart rpm (recover)" = 0x15AD0 [2200,2200,1750,1350,1350], "(cut)" = 0x15ADA
  [1900,1900,1500,1150,1150], overrun cutoff MAP tables 0x15A70-0x15AAF. Also an "Overrun throttle opening (rev hang)
  enabled" byte (TSX 0x4A1D8, CSX 0xAAC4) -- not located in our ROM.
- Overrun throttle opening = 0x4F52A (called by 0x5083A <- 0x782D8): output 0xFFFF3CB6 = 0 if idle state 0x3CB9 == 5,
  or speed 0xFFFF2C2C < 0x9E36 (= 1), or pedal on (3D0C != 0); else table by RPM 0x3CBA: desc 0x9E50 (3D0D == 0) axis
  0x1235E [1000,1500,2100,3000,3800,4600,6000,7300] data 0x1232E [500,500,1350,1800,4400,5900,6500,4700]; desc 0x9E38
  (3D0D != 0) axis 0x1233E [4000..8000] data 0x1230E [4200,5800,6600,7800,8100 x4]. Gains 0x9E68 = 16384 (coolant),
  0x9E5C = 32768; minimum 0x9E44 = 0. Summed into 0x3D10 (idle air request) -> throttle. Not changed by v2.
- A220 vs A240 (src\cmp_tables2.py, cmp_cal.py, cmp_scalars.py; stock\37805-R42-A220-M1.rwd.gz, keys 42 22 41):
  of 679/681 1D tables only 4 changed: both overrun air tables RAISED in A240 (A220 0x1232E-equiv [500,500,900,1500,
  3500,4900,5400,3600], 0x1230E-equiv [3000,4000,5100,5900 x5]), B8DC (A220 [-650,-1250,-1250,-650,-650] -> all -650),
  B910 (A220 0 -> identity, read by 0x5FB06, not traced). Fuel cut delay and tip-in tables identical. Scalars
  0x9156/0x94C6 3960 -> 5040, 0x9CCE 274 -> 306.
- Honda bulletin 11-049 (final revision 2011-11-16, NHTSA SB-10041345-9826): PGM-FI update "improve fuel injector and
  VTC timing", background: cold-start timing may create deposits on the oil control rings -> oil consumption. Its
  table lists "2011 Accord M/T 2-door, program ID 42A240, 37805-R42-A24" = OUR A240 (100 %, document). So A220 = the
  pre-campaign software and A240 = the oil consumption fix. The overrun air tables raised in A240 are part of that
  fix (the bulletin names injector/VTC timing; the overrun air link is 75 %: higher overrun air = less decel vacuum
  = less oil pulled past the rings). Only 1D tables were compared; injector/VTC 2D/3D maps not compared.
  -> Do NOT lower the overrun air (no Hondata/KTuner "rev hang off", and NOT the A220 values either: that would
  partly undo the oil fix on this 291k km engine). Option D dropped.
- Lean condition: AF FB +15-20 % at idle, +11 % at 2700 rpm (before the flash, HDS screen); suspected unmetered air.
- Lean condition, log analysis 2026-10-30 (29 HDS snapshots 25 + 30 Oct, decoded by src\hds_snapshot\snapall.py,
  analysed by lean.py / lean2.py / lean3.py, frames deduplicated by day + HDS clock because snapshots overlap):
  - Total correction ST x LT (KLAF x KLAFAVE, raw/128) in warm closed loop (FSS 2, steady, cmd 1.00 +-1 %, 2842 rows):
    idle 1.10, cruise 1.13-1.16, MAP 93 1.13; by MAP 18-93 kPa 1.11-1.15; by rpm 1.11-1.15; IAT 15-40 C no effect.
  - The ECU stays in CLOSED LOOP at full load (MAP >= 95, up to ~5500 rpm: 929 of 973 frames FSS 2, cmd ~0.96-1.0);
    total correction there 1.06-1.19 (median per file ~1.10-1.17) = same as cruise.
  - Fit (tot - 1) = a + b / GAIR: a = +0.160, b = -11.3 +- 1.5 (2 sigma). b NEGATIVE: no fixed-leak signature (a vacuum
    leak, exhaust leak before the A/F sensor or injector dead time error would give MORE correction at idle).
    => the error is PROPORTIONAL (~+11-16 %), slightly larger at load.
  - Rear O2 (SVO2 raw): fuel cut 0, enrichment 40, closed loop median 33 (p10 6, p90 41) => exhaust really at ~stoich
    after the correction; the front A/F sensor is not misleading the ECU. The extra fuel is really needed.
  - One open-loop WOT event (25 Oct 18:26, 2nd gear 4500-5200 rpm): cmd 0.848, measured lambda ~0.93-0.94
    (meas/cmd median 1.107, n = 23) because ST is frozen at 1.000 in open loop (only LT 1.055 applied).
  - LT (KLAFAVE) resets on each flash and relearns slowly (1.00 -> 1.055 in ~25 min), so ST carries most of it.
  - NOT separable from the logs: MAF under-reading (intake / dirty MAF) vs fuel delivery (pressure, pump, injectors).
    GAIR scale not proven; if raw/100 g/s, implied VE at WOT 4000-5000 rpm ~0.80-0.97 (inconclusive).
  - Next: fuel pressure gauge test (spec from the service manual), clean MAF / stock intake then compare trims.
  - User report 2026-10-30: the previous owner said not to drive the car with little fuel in the tank. The user's
    written seller notes say (translated from French) "fuel pump small problem, keep the tank full". Strongly raises the fuel delivery hypothesis. Keep the tank well filled, no long WOT.
  - Seller notes (user's car notebook): all ignition coils replaced; new battery 2024; brakes 2024; coolant summer 2025;
    power steering fluid due; transmission oil at 150k km.
  - User's work done (notebook): PCV valve cleaned, valve cover gasket + VTEC gasket replaced, cold air / short ram
    intake (MAF cleaned at install), full exhaust redone + flex pipe, timing chain tensioner / valvetrain checked,
    oil pressure sensor, starter replaced. Open: front brake discs, alignment, front right wheel bearing, power
    steering bleed, airbag recall, driver door.
  - Fuel level signals in the snapshots: FLI "Fuel Level" (2613:0B, sloshes a lot) and FLEVELF "Fuel Level(Average)"
    (2613:0C-0D); scales unknown (higher = more fuel: 698 at the start of 25 Oct, ~500 on 30 Oct 20h).
  - Total correction per session AT THE SAME LOAD (closed loop warm, cmd 1.00):
    25 Oct 18h (FLEVELF ~669, IAT 27): idle 1.112, MAP 30-45 1.137, MAP 45-70 1.120, MAP >= 70 1.145
    30 Oct 18h (FLEVELF ~548, IAT 18): idle 1.103, MAP 30-45 1.120, MAP 45-70 1.103, MAP >= 70 1.127
    30 Oct 20h (FLEVELF ~495, IAT 17): idle 1.162, MAP 30-45 1.211, MAP 45-70 1.203, MAP >= 70 1.187
    => +6-9 % more correction on the second drive of the same evening (same intake, IAT, ECT, slightly less fuel).
    Not monotonic with the fuel level (25 Oct > 30 Oct 18h). The error VARIES between drives: favours a fuel delivery
    cause (pump heat / level) over a fixed MAF/intake geometry error. Weak evidence (3 sessions, fuel temp not logged;
    v3 at 20h vs v2 at 18h, v3 only changes the decel fuel cut delay).
  - User 2026-11-01: the short ram intake is a generic Amazon kit (~150 $). If its tube is wider at the MAF than
    stock, the MAF under-reads by about (D_kit / D_stock)^2 (e.g. 5 % wider -> ~10 % lean). Measure both inside
    diameters at the sensor.
    MEASURED by the user 2026-11-01: kit tube 7 cm inside, stock ~6 cm inside (approximate, exact spot vs the sensor
    not confirmed). Area ratio (7/6)^2 = 1.36 -> up to ~36 % under-reading predicted; observed +15-21 %.
    Very sensitive to the stock value: 6.3 cm -> 1.23, 6.5 cm -> 1.16. Direction and size consistent with the logs:
    the intake is now the main suspect (~75 %). Confirm: stock intake + warm log (correction should drop to ~1.00-1.05).
  - User 2026-10-30: the MAF was cleaned when the short ram intake was installed (dirty MAF unlikely; the intake
    geometry around the MAF remains a suspect).
  - Misfire counters (logged, max per drive): 25 Oct cyl2 5, cyl3 1, cyl4 1 (CMFIRE 7); 30 Oct 18h cyl2 1, cyl4 1;
    30 Oct 20h cyl2 6, cyl3 1 (CMFIRE 7). Very few, but cylinder 2 is always the most. MFCYL = bitfield of the
    cylinders with misfires (bit0 = cyl1: 14 = cyl2-4, 6 = cyl2-3, 8 = cyl4), consistent with the per-cyl counters.
  - User 2026-10-30: spark plugs looked white / greyish when checked earlier (date, mileage, per-cylinder detail
    unknown). Consistent with lean, not proof (closed loop runs at lambda 1; modern plugs often look light grey).
  - 2026-11-01: user REPLACED THE FUEL PUMP ONLY (kept the rest of the module: pressure regulator, filter, level
    sender; new strainer unknown) and fitted 16" winter tyres instead of 17" summer (changes VSP only,
    not used in the trim analysis). Logs 01112026_144630..151752 (9 snapshots, decoded, compare_sessions.py):
    total correction closed loop: idle 1.19-1.21, MAP 30-45 1.13-1.21, MAP 45-70 1.16-1.21, MAP >= 70 1.16-1.21
    => NOT lower than before (1.10-1.19). The new pump did NOT fix the lean condition.
    Battery voltage alternated 12.5 / 14.3 V while running (Honda charging control, daytime, low electrical load;
    assumed); correction identical at 12.5 and 14.3 V => pump supply voltage and injector dead time compensation are
    not the cause. Full load open loop (126 frames, 4200-6480 rpm): cmd 0.848, measured 0.899 (meas/cmd 1.060) with
    LT 1.086 => base error ~1.15, same as 25 Oct (1.107 x 1.055 ~ 1.17). IAT 29-47 C (higher than before).
    Misfire counters very low (c2 1, c3 1, c4 1). Remaining suspects: MAF reading with the short ram intake,
    fuel pressure regulator (kept, a low setting gives exactly a flat % error: +17 % fuel ~ pressure at ~73 % of
    nominal), injectors (all 4), in-module filter (would grow with load: less likely). Fuel pressure never measured.
  - Pump vs injectors: pump error changes with fuel level / heat / load and shows on a pressure gauge; injector error
    is fixed and only a flow bench (or balance test) shows it per injector.
  - MAF TRANSFER TABLE FOUND (2026-11-01, step 1 of the MAF recalibration):
    - Descriptor 0xA75C (n = 64, fmt 66 66 00), axis 0x13C72 = MAF A/D 10-bit: 0, 0, 72, 88 .. 264 (step 16), 272 ..
      792 (step 8/16), 824 .. 992 (step 32), 1015; data 0x13BF2 = 0, 0, 0, 0, 4, 12, 24, 41, 64, 93, 128 .. 30319, 32767.
      Found by a ROM scan for long convex increasing curves (scratchpad scan_runs.py), the logged GAIR values were in it.
    - PROOF on the logs (src\hds_snapshot\maf_check.py + grid test): 100.00 % of 108371 logged GAIR frames (524
      distinct values) equal floor(linear interpolation of this table at an integer A/D value). Steady frames:
      GAIR inside table(4*AFM .. 4*AFM+3) 69 %, within 5 % 95 % (AFM 2610:21 = A/D >> 2; the rest = sampling time skew).
      => HDS GAIR raw = this table output, same units (raw, g/s scale still unknown).
    - Code users (FindRefs, pool words): only 0x539B0 and 0x703AC hold 0xA75C; the axis/data pointers only in the
      descriptor (0xA760/0xA764); no other ROM word points into 0x13BF2-0x13CF0.
      - 0x5381C (load at 0x5382C): airflow = lookup(0xA75C, MAF A/D 0xFFFF2948) -> 0xFFFF3F88 (0xFFFF3E30+0x158),
        6-sample history 0xFFFF3F72.. summed -> 0xFFFF3F8C (+0x15C), converted by 0x9128C, clamped 0x8B1C ->
        0xFFFF3E4A (+0x1A). MAIN airflow path (90 %).
      - 0x700F0 (load at 0x7022C): only when flag 0xFFFF33F0 is set, lookup(0xA75C, 0xFFFF262A) -> struct fields +10
        / +0x30 (struct with many flags; diagnostic or snapshot use, not traced: 60 %).
      - 0xA748 checked (step 2): it is its OWN 2D descriptor (0A 66 07 66 66 00 00 00, 10x7, axes 0x13A38 / 0x13A4C,
        data 0x13B50..0x13BDB, 20 bytes long so it ends just before 0xA75C), read only by the 2D lookup 0x908C in
        function 0x52E9C (call at 0x533FA). It does NOT reach the MAF table. No 3rd user.
      - 0x700F0 fills a data record at 0xFFFF5F04 (+10 / +0x30 = table output from 0xFFFF262A when flag 0xFFFF33F0;
        +10 is reused in a load-like formula 0x9F6 * airflow / (0x1280 * rpm)). Record read at 0x23060, 0x8DC4C..0x8E610,
        +0x30 at 0x81036. Looks like diagnostic / data-list values (65 %): scaling the table makes them closer to the
        real air, no new risk seen. Flag 0xFFFF33F0 is read in ~40 places (state flag, not traced).
  - MAF CORRECTION NEEDED PER TABLE POINT (step 2, src\hds_snapshot\maf_corr.py, all 38 logs 25/10 + 30/10 + 1/11,
    steady MAF frames, warm, factor = ST x LT x measured lambda / commanded lambda):
    - Closed loop, A/D 232..712 (GAIR 250..10300, every point with data): medians 1.11-1.24, mostly 1.14-1.17;
      highest around idle / light cruise A/D 264-296 (1.16-1.24).
    - Open loop WOT (MAP >= 95, 4200-6400 rpm, GAIR 8400-13300, cmd 0.848): 1.12-1.24, mostly 1.14-1.16 (1/11, LT
      1.086) and 1.12-1.20 (25/10, LT 1.055). Same value as closed loop => one flat air error, as the tube physics says,
      and it supports that LT is applied in open loop too (otherwise WOT would show only ~1.06).
    - No data below A/D 232 (engine off / cranking) or above 744 (GAIR > 12200 not reached steady).
    - Build note: data is 16-bit, last points 30319 / 32767; x1.15 would overflow point 62 (34867) -> cap at 32767
      (A/D 992+ = GAIR > 30000, never reached: max logged 13320 at 6400 rpm WOT).
  - v5 BUILT 2026-11-01 (step 3, NOT flashed): src\build_v5.py from work\v3_fuelcut20 (checks the v3 SHA256, cipher,
    descriptor 0xA75C count/fmt/pointers, exact stock axis + data values, ROM literals 0xA75C = 0x539B0/0x703AC,
    0x13C72 = 0xA760, 0x13BF2 = 0xA764, no ROM word pointing inside the data, new table increasing, every changed byte
    inside 0x13BF2-0x13C71 or 0x8400). Data x1.15 rounded (4 -> 5 .. 26447 -> 30414), points 62/63 capped 32767,
    points 0-3 stay 0. Checksum 0x8400 0xF6 -> 0x28, byte sum 0 mod 256, one part number 37805-R42-A240.
    Diff vs v3: 101 bytes (0x8400 + 100 bytes in 0x13BFB-0x13C6F); vs stock: 114 (v3's 14 + those 100).
    SHA256: work\v5_maf115.bin 765D5E966574E520532AD55E5A588416521CE682307E2071CDE9CEBFDF156B78;
    work\v5_maf115.rwd 804C3B6EE2D150428F6BD81A51A04CC268BF18F8E3D41C7F17173F0158A37A44. Read-only. NOT in flash\.
    verify_rwd.ps1: header identical, cipher 256/256, 0 mismatches, file checksum 0x06A74EC9, RESULT OK.
    Emulation (step 4, 2026-11-01): src\ghidra_scripts\EmuMaf.java on the BUILT files work\v3_fuelcut20.bin and
    work\v5_maf115.bin (own project src\ghidra_proj_v5, no patches, src\emu_v5_raw.txt). 0x5381C called 7 times per
    MAF A/D 0..1023 (0xFFFF29C4 = 0): no stop, instant 0xFFFF3F88 = python interpolation of each file's table on all
    1024 values (both files), steady average 0xFFFF3E4A = instant, never decreasing, max 32767 (no overflow).
    v5/v3 average = 1.148-1.153 on A/D 232-952 (exactly x1.15 within rounding), A/D < 232 tiny values (4 -> 5),
    A/D 970-1015 capped (ratio 1.12 -> 1.00, never reached). Step 300 -> 700: same 6-call averaging ramp, v5 = v3 x1.15
    on every call. So the change does exactly what was intended in the main airflow path. NOT emulated: the users of
    0xFFFF3E4A (fuel / ignition load) and 0x700F0; they get the stock-car value range (= what a stock intake gives).
    Step 5 (2026-11-01, at home): exe FlashToolTest_v2 = src\build = E2DFC687... (checked first). Self test with v5:
    51/52, only the hard-coded v1 2-byte check (validator: v5 rwd valid, decrypt == bin, part number A240, internal
    checksum 0x28 OK, 114 bytes vs stock, keys from ECUS_KEYS, simulated full flash 496/496, data == firmware;
    docs\logs\2026-11-01_v5_selftest). Copied to flash\v5_maf115.rwd (read-only, hash = work). FLASH_DRYRUN.txt
    present, FLASH_PIN12.txt absent. docs\CHECKLIST_FLASH_DAY.md rewritten for flash #4 (v5, fallback v3, Part E5).
    Remaining: car part of the checklist (B, C, D with the dry run) and the user's go.
  - FLASH #4 v5_maf115 FLASHED 2026-11-01 16:29-16:32: SUCCESS (FlashToolTest_v2\flash_logs\flash_20261101_162935.log).
    Gates: A hashes E2DFC687 x2 / 804C3B6E / F8836DEC / 6E4CACCB, laptop on AC; B HDS all modules: PGM-FI and SRS no
    DTC, ABS 65-11 + 61-11 (known); C Connect ECU 12.58 V, VIN + A240, voltage >= 12.5 V after 3 min (user read),
    C4 multi-frame 11-byte request (2 frames, FC from ECU) + 42-byte answer (7 frames) OK; D dry run
    flash_20261101_162802 unlock OK 12.65 V. Flash: 12.67 V, seed 3E 46 -> key 3F 22, 10 02, erase 71 01 FF 00
    (8 s), 2E F1 01, 34 -> 74 20 08 02, 496/496 blocks in 2:32 (battery 12.72-12.77 V), 37 -> 77, 71 01 FF 01.
    FLASH_DRYRUN.txt put back right after. Car now runs v5. Effect not measured yet (CHECKLIST Part E5 logs).
  - First start after flash #4 (HDS Data List 16:36, run time 127 s, ECT 68 C, IAT 23): PGM-FI no DTC (confirmed +
    pending), MIL off. Idle 874 rpm (target 876), closed loop, ST 1.00, LT 1.00 (the flash RESET the learned LT, was
    ~1.05-1.09), lambda 1.00 / cmd 0.99, MAF 3.2 g/s, CLV 17 %, MAP 26, inj 2.56 ms, spark 10.5, knock 0, misfire 0.
    => at idle the mixture is right with NO correction (before v5: total ~1.18-1.22 at idle). One sample, not warm:
    first sign only. Hypothesis (60 %): HDS MAF g/s = GAIR raw / 128 (v5 idle A/D ~264 -> 411 -> 3.21 g/s).
    CMP A No Pulse 25 / CMP A Noise 30 / CMP B No Pulse 2: never logged before (no baseline), no DTC.
    Expected: trims ~1.00, WOT closer to cmd 0.848, ECU load ~15 % higher (= what a stock intake gives: ignition and
    other air-based values come back to Honda's design). If part of the 15 % is fuel side (injectors, pressure), the
    ECU would see a bit MORE air than real: less ignition advance (safe side). Right after the flash, if the learned
    LT (1.05-1.09) is kept, mixture is rich until it relearns (safe side).
  - v5 static test (2026-11-01, snapshot docs\logs\2026-11-01_v5\..._01112026_164626.dat, 158 s, ECT 83-95, neutral,
    all closed loop FSS 2): total correction ST x LT x lambda/cmd, median [p25-p75]:
    idle 780 rpm (A/D ~232) 1.041 [1.037-1.044], end idle 1.058; 2500 rpm hold (A/D ~312) 1.020 [1.003-1.035];
    3500 rpm hold (A/D ~356) 1.000 [0.992-1.012]. Before v5 the same zones needed ~1.18-1.22 (idle) and ~1.14-1.17.
    => v5 removes the error in the 2500-3500 zone; idle keeps +4-6 % = exactly 1.20/1.15 (idle needed more than the
    flat 1.15), the LT learns it (LT moved 1.000 -> 0.984 here, still relearning after the reset). Not a reason to
    change the file. maf_corr.py on v5: points 19-24 (A/D 312-360) 0.999-1.026.
    Misfire: cylinder 1 counted 2 (at 43 s and 51 s, 2500 rpm hold), no DTC. Pre-v5 logs had the same kind of isolated
    counts (25/10: cyl2 5; 30/10: cyl2 6, cyl3 1, cyl4 1). To watch, no link with v5 proven. No knock signal in the list.
  - v5 driving log (2026-11-01 16:51-17:05, 5 snapshots 165150..170543 in docs\logs\2026-11-01_v5, gap 16:56-17:01):
    compare_sessions.py total ST x LT (warm CL, cmd 1.00): 16h idle 1.015, MAP<30 1.008, MAP 30-45 0.969, 45-70 0.942;
    17h (IAT 47, heat soak) idle 0.960, 30-45 0.952, 45-70 0.938, MAP>=70 0.908. Pre-v5 same bins 1.10-1.30.
    LT fell 0.992 -> 0.938-0.945 (ECU now REMOVING fuel). maf_corr.py v5: A/D 232-360 0.96-1.03, A/D 376-520 0.84-0.95
    (few samples). WOT open loop (cmd 0.848, warm, MAP>=90): measured lambda 0.776 (4-5k), 0.771 (5-6k), 0.760 (6-7k)
    = 0.90-0.92 x cmd, i.e. ~9 % RICH (AFR ~11.2). Pre-v5: 0.899 / 0.902 / 0.873 = 1.03-1.06 x cmd (LT was 1.086).
    => Verified: the MAF error was NOT flat. It needs ~1.18-1.22 at idle, ~1.15 at light load, only ~1.05-1.06 at WOT
    flow. v5 (flat x1.15) is right at idle/light load and 5-9 % rich at load/WOT. Rich = safe side.
    Deduction (75 %): LT (KLAFAVE) is NOT applied in open loop: pre-v5 1.06 / 1.15 = 0.922 predicted for v5 without LT,
    0.909 measured; with LT applied it would read ~1.03.
    WOT ignition (open loop, MAP>=90) 1.5-2 deg less than pre-v5 (4-5k 14.0 vs 15.5, 5-6k 12.0 vs 14.0, 6-7k 15.8 vs
    16.2): expected, the ECU sees more air (safe side, a bit of power lost). Misfire counters over the drive:
    cyl1 2, cyl4 3, no DTC (same level as pre-v5 drives). Possible v6: taper the multiplier with A/D
    (~1.15-1.18 low flow -> ~1.06 at WOT flow), only after a per-zone analysis and the full checklist.
  - v6 step 1 (src\hds_snapshot\maf_need.py: need vs STOCK table per point, CL = ST x LT x lam/cmd, OL = lam/cmd,
    pre-v5 logs x1.0 + v5 logs x1.15):
    A/D 232-360: pre 1.14-1.24, v5 1.10-1.18 (both ~1.15, large n) -> keep 1.15.
    A/D 376-520 (CL, mid/high load): pre 1.12-1.18 (n 8-86), v5 0.99-1.10 (n 1-10). DISAGREE, not explained
    (day spread pre-v5 was 1.10-1.21; v5 is the same day/fuel as now).
    A/D 680-776 WOT open loop: pre 1.03-1.06 (n 4-38), v5 1.03-1.06 (n 6-29): AGREE -> WOT needs ~1.05.
    This agreement also supports "LT not applied in open loop" (with LT applied, pre would be 1.15 and v5 1.01).
    Proposed v6 multiplier: 1.15 for A/D <= 376, linear to 1.08 at A/D 488, 1.08 above. Expected: idle/light
    unchanged (= v5), mid load CL total 0.96-1.04 (between the two data sets), WOT lambda ~0.82 (0.81-0.83,
    3 % richer than cmd 0.848, kept on the rich side on purpose), WOT ignition back up ~1 deg.
  - v6 step 2 (2026-11-01): src\build_v6.py (= build_v5 checks + mult(A/D) + points A/D <= 376 must equal v5, the
    others must be below v5, never below stock, increasing). work\v6_maf_taper.bin/.rwd (read-only), built twice
    (scratch + work) with identical hashes:
    bin SHA256 4BBAD449961BD00B19CA942D6201C5249349661DF3289069F2CEC4286EBDE8B2
    rwd SHA256 49724F5D3C9AABF2447F35B4A95C91F5404D41F3465361FE5771F2589D656EF1, rwd file checksum 0x06A752C9.
    Diff vs v3: 97 bytes (0x8400 + data 0x13BFB-0x13C6F). Diff vs v5: 68 bytes, data points 26-62 only (A/D 384-992).
    Checksum byte 0x8400 = 0x28 as in v5 (the data byte sums are equal mod 256; firmware sum re-verified = 0).
    Independent check: rwd decodes to bin (0 mismatch), file checksum OK, header = v3 header, size 0xF8000,
    ratio v6/stock 1.150 (pts <= 25) -> 1.080 (pts >= 36), part number once. Point 62 32745 (v5 capped 32767).
    Ghidra users are the same table/pointers as v5 (already proven). Next: emulation v6 (EmuMaf), self test.
  - v6 step 3 (2026-11-01): EmuMaf.java on the BUILT work\v6_maf_taper.bin (project src\ghidra_proj_v5 EMU5,
    -overwrite import; headless needs JAVA_HOME = src\tools\jdk\jdk-25.0.4.1+1, not on PATH). Output
    src\emu_v6_raw.txt (full log src\emu_v6_full_log.txt), compared with src\emu_v5_raw.txt (v3 + v5):
    no stop, "DONE"; instant 0xFFFF3F88 = interpolation of the v6 table with truncation on 1024/1024 A/D values;
    steady average 0xFFFF3E4A = instant 1024/1024; never decreasing, 0..32767 (no overflow);
    v6 == v5 exactly for A/D 0-376; v6 <= v5 above; v6 >= v3 everywhere; v6/v3 = 1.150 (<= 376), 1.145 (384),
    1.120 (424), 1.100 (456), 1.080 (488-950), 1.000 at 1015 (cap, never reached). Step 300 -> 700: same 6-call
    averaging ramp as v3, final 10528 = v3 9749 x 1.08. => the main airflow path does exactly what v6 intends.
    NOT emulated (as for v5): users of 0xFFFF3E4A (fuel / ignition load) and 0x700F0.
  - v6 step 4 (2026-11-01, at home): exe FlashToolTest_v2 = src\build = E2DFC687... (checked first). Self test with
    v6: 51/52, only the hard-coded v1 2-byte check (validator: v6 rwd valid, file checksum 0x06A752C9, part number
    A240, internal checksum 0x28 OK, 110 bytes vs stock, keys from ECUS_KEYS, simulated full flash 496/496, data ==
    firmware; docs\logs\2026-11-01_v6_selftest). Copied to flash\v6_maf_taper.rwd (read-only, hash = work 49724F5D).
    docs\CHECKLIST_FLASH_DAY.md rewritten for flash #5 (v6, fallback v5, Part E6). Remaining: car part (B, C, D with
    the dry run) and the user's go.
  - FLASH #5 v6_maf_taper SUCCESS 2026-11-01 17:31:32 (flash_logs\flash_20261101_172901.log): file SHA 49724F5D,
    110 bytes vs stock, battery 12.65 V start, 12.70-12.82 V every 50 blocks (rising, charger), 496/496 blocks, 37 +
    31 01 FF 01 positive. Gates: A2/A3/A5 hashes OK (17:19); B4 codes read: PGM-FI none, SRS 56-31 (from flash #4),
    ABS 65-11 + 61-11 (known); NOT cleared (HDS bug, user's call); B2 engine cold SKIPPED by the user (driven until
    17:05; risk = radiator fan current, covered by the 10 A charger; voltage never dropped). C3 VIN + A240 OK, C4
    multi-frame 9 bytes out / 42 bytes in OK, 12.58 V. Dry run 17:27:55 (seed 3007 -> key 28AB accepted, not erased,
    12.61 V). FLASH_DRYRUN.txt removed at D4 (user approved), recreated right after the flash. Car runs v6.
  - After flash #5 (17:58-18:00): All DTC = same as before the flash (PGM-FI none confirmed/pending, SRS 56-31,
    ABS 65-11 + 61-11), nothing new. Data List idle (run time 91 s, warm start ECT 82): 772 rpm (target 780), ECT 84,
    IAT 31, closed loop, ST 0.98, LT 0.98 (v5 had learned 0.94; reset/relearn), lambda 1.00 / cmd 1.01, MAF 3.0 g/s,
    MAP 26, inj 2.53 ms, spark 9.0, knock retard 0, misfire 0, MIL off, CMP A No Pulse 25 / Noise 30, CMP B 3
    (same values as after flash #4: probably counted at cranking after a flash). Idle = v5 (same table there).
  - v6 driving log E6 (2026-11-01 18:01-18:08, 4 snapshots 180410..180826 in docs\logs\2026-11-01_v6):
    compare_sessions total ST x LT: idle 0.999, MAP<30 1.007, 30-45 0.961, 45-70 0.916, >=70 0.976 (v5 0.908-0.942
    at MAP >= 45). LT 0.977 -> 0.969. Misfire counters 0 on all cylinders. No DTC.
    WOT open loop (cmd 0.848, MAP >= 90): measured lambda median 0.840 (4-5k, n 60), 0.830 (5-6k, n 78),
    0.806 (6-7k, n 53) = predicted 0.81-0.83 (v5 0.760-0.776, pre-v5 0.873-0.902). Ignition 16.0 / 13.5 / 17.5 deg
    (v5 14.0 / 12.0 / 15.8, pre-v5 15.5 / 14.0 / 16.2). 22 of 191 WOT frames leaner than 0.848: the first 0.1-0.2 s
    of each pull (up to 0.905, sensor lag after the switch to open loop, also seen with v5 up to 1.057) and one
    0.6 s stretch at 4600-4800 rpm at 0.849-0.868 (<= 2 % leaner than cmd, still richer than pre-v5's 0.90).
    Closed-loop need vs stock by A/D x MAP (v5 and v6 logs agree, same day): at the same A/D the need is ~1.14-1.18
    at MAP < 30 and ~1.05-1.10 at MAP 45-70 (low rpm, high MAP). So the error also depends on rpm/MAP (likely
    intake pulsation), not only on airflow: a MAF-table-only change cannot fix the low-rpm MAP 45-70 zone (0.92)
    without making light load lean. Closed loop corrects it (LT ~0.97). Verdict: v6 kept.
  - General health check (2026-11-01, all 143 signals of the 4 v6 snapshots, 6841 frames, + same checks on all 44
    decoded logs since 25/10; script scratch health.py / knock_sessions.py):
    OK: ECT 83-88 C stable, radiator ECT2 30 -> 77 C (thermostat opens), fans FANL/FANH cycle normally;
    charging VB 14.2-14.4 V running; VTC actual - cmd at steady state median 0 (p5 -1, p95 0); pedal APPS1 =
    2.0-2.2 x APPS2 over the whole range; throttle TH-1/TH-2 pairs consistent; VTEC VTS -> RVTS -> VTM consistent;
    rear O2 SVO2 steady ~35 in closed loop (cat buffering, not switching), 0 in fuel cut; misfire 0; MIL 0.
    CMP counters DCAM 25 / NCAM 30 identical in EVERY log since 25/10 (stock baseline) -> old stored counts, not
    growing (= HDS "CMP A No Pulse 25 / Noise 30").
    KNOCK RETARD (KNRTD, ~0.5 deg/count assumed from IG): rises on part-throttle tip-in at 1400-2500 rpm, MAP 50-66,
    up to 28 (~12-14 deg), decays as rpm rises; 63-88 % of warm part-load frames (MAP >= 45, 1300-3500 rpm) have
    KNRTD > 0. SAME pattern and level in the stock baseline 25/10 (max 20-33, 69-88 %) and in every tune -> not
    caused by the tunes. Real knock (fuel octane, carbon) or mechanical noise (valve clearance, no hydraulic
    lifters at 291k km) cannot be told apart from the data. KIGKREF 88-140 varies per session (learned value).
  - Super test (2026-11-07 12:00-12:10, 55 L premium grade, 5 snapshots in docs\logs\2026-11-07_v6_super, v6,
    IAT 12-27, ECT 57-86, scratch knock_cmp.py / knock_ref.py / super_check.py): raw KNRTD went UP vs v6 on 87
    (part load mean 13.1 vs 9.0, > 0 in 79 % vs 68 %, max 36 vs 28; WOT mean 20.5 vs 14.1, IG 12 vs 15 deg) although
    the air was colder. BUT KNRTD follows load x KIGKREF on every fuel and tune (WOT median 15-16 at KIGKREF 90-109,
    17 at 110-119, 18 at 120-129, 22 at 140-149; all 49 logs). KIGKREF started today at 149 (highest seen, kept
    across key off), frozen until ECT ~83, then fell to 117 in 5 min (30/10 on 87: 115 -> 90 in ~5 min, so the fall
    proves nothing). At equal KIGKREF super = 87: 120-129 mean MAP 45-60 / 60-80 / 80+ = 5.5 / 14.4 / 19.8 vs Amazon
    v3 5.2 / 13.8 / 19.8; 130-149 = 8.8 / 20.2 / 24.3 vs 25/10 10.0 / 20.6 / 21.3. No fuel effect visible YET, test
    not finished (KIGKREF never got under 117, only ~5 min warm). KNRTD is > 0 in ~100 % of MAP >= 80 frames on all
    fuels, so it does not look like pure real-time knock: part of it may be a learned/scheduled retard. Function of
    KNRTD and KIGKREF NOT traced in the ECU code (DID 2662 b08, b0A).
    Fuel trims changed: LT 0.977 -> 0.883 (already 0.898 on the first frame), ST 1.00 -> 0.922 with purge, 0.977
    with DPCS 0 (purge effect -5.5 % vs -1.6 % on 1/11). WOT lambda richer: 0.816 / 0.811 / 0.776 vs 0.840 / 0.830 /
    0.806 (4-5k / 5-6k / 6-7k). ASSUMED: less ethanol in the super (about 3 %, fits the WOT shift) + canister vapours
    after the fill. Intake and filter unchanged since 1/11 (owner, 2026-11-07), so that cause is excluded. Less ethanol can explain about 3-4 % at most (general figure, not measured), LT fell about 10 %; CHECKED (scratch lt_settle.py): the 1/11 v6 LT 0.977 was NOT settled, so "LT fell 10 %" was a wrong comparison. Flash #5 at 17:31 reset LT to 1.00, the log started 33 min later and ended at 0.969, still falling. v5 (same table up to A/D 376) went 0.992 -> 0.938 in the 22 min between 16:46 and 17:08. Today LT is not settled either: 0.898 -> 0.875 in 12 min. Fair gap on the same table: 0.938 x ST no purge ~1.01 = 0.95 (v5, 87) vs 0.883 x 0.977 = 0.86 (today, super), about 9 %, and 0.95 was still falling. Purge adds -5 % today (ST 0.91-0.93 vs 0.97-0.98; tank FLI 235 vs 126-134), about -1 to -3 % on 1/11. STILL UNEXPLAINED: total was ~1.20 at 15:15 on 1/11 (new pump, v3), x1.15 predicts 1.05, measured 0.94-0.99 within the hour and 0.86 today. Fuel pressure never measured. Stock-intake LT 1.03-1.05 / 1.15 = 0.90. Do not build a new MAF table until LT stops moving.
  - Exhaust fuel smell (user 2026-11-07: friends noticed it outside the car, cold start, idling 2-5 min, week of 11-01; scratch warmup_rich.py, first_frames.py, cold_stock.py). Today's oldest frame = engine run time 82 s, ECT 57 (user: cold engine idled 2-5 min, shut off, restarted, not driven, so run time counts from the restart; idle warm-up in the log ~6 C/min fits; the real cold start and nothing below 50 C is logged on v5/v6; engine off at 12:57 read ECT 56, ECT2 20, IAT 35): already closed loop, lambda 1.00, meas/cmd 0.99-1.00 at 50-80 C, idle 1050 rpm. So NOT rich from 82 s on. Only logged cold start (25/10 stock, ECT 22): first closed loop at run time 13 s, then ST 1.08-1.10, LT 1.00. Today at ECT 50-60: ST 0.883 x LT 0.898 = 0.79. If LT is not applied in open loop (75 %, see above) the seconds before closed loop would be about 25 % rich on v6: estimate, NO log of the first 82 s on v5/v6. Next: cold start log from key on.
    DONE 2026-11-07 18:38-18:40 (docs\logs\2026-11-07_v6_coldstart, 3 snapshots, read-only; SHA256 183834 0C22DBFA..,
    183904 D9EC5D32.., 184011 52D89DB7..; scratch cold_start.py, cold_misc.py, svo2.py). ECT 11, IAT 9, idle only then
    moving the car back. Crank: lambda 0.690 / cmd 0.848, same as stock 25/10 (ECT 22). Open loop 0-13 s: lambda 1.00 at
    5 s, 0.952 at 10 s (stock 1.00 / 0.908), meas/cmd 0.954 both. First closed loop at run time 13 s, same as stock.
    15-150 s: lambda 1.00, meas/cmd 0.99-1.00. TOUT at idle 811 vs stock 793. => v6 is NOT richer than stock at cold
    start (the "25 % rich first seconds" estimate was WRONG). Purge DPCS 0 the whole time, yet total correction 0.77-0.83
    (LT 0.875, ST 0.88-0.95) vs stock 1.08-1.09. Misfire: 1 on cyl 3. KIGKREF 117 frozen. Battery min 9.0 V at crank.
    Rear O2 SVO2 raw median in warm closed loop: stock 32, v1-v3 33, v3 36, v5 31, v6 35, super 37, cold 34 => after the
    catalyst the mixture looks the same as stock, so the front sensor is believed (scale assumed 0.02 V/count).
    Total correction warm closed loop: stock 1.145, v3 1.15-1.23, v5 0.984, v6 0.977 (1/11 18:08), super 0.821 (7/11).
    Expected with x1.15: 1.145/1.15 = 0.996, matched on 1/11. So a NEW ~16 % fuel excess appeared between 1/11 18:08 and
    7/11 12:00, not from the tune, not from purge (DPCS 0 at cold start). Final mixture is still lambda 1 (ECU removes it).
    Suspects (none tested): EVAP purge valve leaking while closed (tank full), fuel in the oil (PCV), fuel pressure high,
    leaking injector, ethanol content (3-4 % at most). The smell is NOT explained by a measured rich mixture.
    Air / fuel split (scratch air_fuel_split.py, speed-density air = MAP x rpm / IAT K, GAIR of v5/v6 / 1.15, TOUT x rpm
    per air; all purge states). Best matched point = warm idle 782 rpm, MAP 26-28, DPCS 71-80 in every group:
    MAF/air rel. to stock: v6 1/11 0.980, super 7/11 0.979 (MAF reading UNCHANGED). TOUT/air: v6 1.029, super 1.023
    (final pulse per air UNCHANGED). Lambda 1.00 both. Yet ST x LT 0.969 -> 0.821. TOUT is the final pulse (assumed,
    75 %: stock vs v6 have the same TOUT/air although the v6 base is +13 %). If so, the engine physically gets the same
    fuel as on 1/11 at warm idle; pressure, injector, oil or vapour excess would have pushed TOUT/air down, so they are
    unlikely to be large. Only the ECU's own split changed: base about +15 % at the same MAF air, correction -15 %.
    Cause of that unknown (another learned value not in HDS? to trace). Cruise / load: n 80-200, rpm and IAT differ,
    MAF/air 0.93-0.95 vs 0.87-0.92: not conclusive. Cold idle vs stock 25/10: rpm 1216 vs 1456, not comparable.
    Next without the car: trace in the ROM what DID gives TOUT and how ST / LT enter the injection time.
    TRACE 2026-11-07 (Ghidra DecompAt, scratch decomp_did2610.txt, decomp_tout.txt): DID 2610 -> 0x89174 -> 0x83000,
    DID 2611 -> 0x8916A -> 0x83594 (2612 -> 0x89160, 2613 -> 0x89156). Sources: TOUT = u16 0xFFFF43EE / 2 (b18-19),
    GAIR = 0xFFFF5F34 (b22-23), XILAF = 0xFFFF2938, LAMBDA = 0xFFFF5F22, KLAF = byte 0xFFFF5F3D, KLAFAVE = byte
    0xFFFF5F30, CMDEQRAT = 0xFFFF5F1C (all 2611). 0x80F24 (a freeze-frame style recorder) copies the same values.
    KLAF / KLAFAVE are display bytes; their writers use base+offset addressing, not found yet. 0xFFFF43EE is
    referenced at 0x23F9A (with 0xFFFF43E6 at 0x23F8A) and in 0x79916; the 0x23xxx code does not decompile (bad
    instruction / nested delay slot from the guessed starts 0x23904, 0x23CB4): manual disassembly needed.
    LOG TEST (scratch tout_vs_klaf.py, tout_vs_klaf2.py, 28264 warm idle frames, all groups): slope of log(TOUT x rpm /
    air) on log(KLAF) = 0.21 (r 0.14); 0.25 with 1 s bins, 0.30 with 3 s bins; lag scan -12..+12 frames 0.18-0.23.
    A final pulse with ~70 % effective time would give ~0.7. So TOUT does NOT follow ST as expected: it is either
    before the trims, or heavily filtered, or another quantity. The "same physical fuel as 1/11 at warm idle"
    conclusion above is therefore NOT supported (the 75 % assumption failed). Physical fuel question is open again.
    MANUAL DISASSEMBLY 2026-11-07 (scratch shdis.py = linear SH-2 disassembler, gbr_refs.py = GBR-relative access finder):
    - 0x23F9A is only the power-on RAM init (0x23904 block). 0xFFFF43EE is an ARRAY OF 4 WORDS (43EE..43F4, one per
      cylinder, init with 43E6 and 4DFC arrays); the DID shows the first one. No code writes it through a direct pointer:
      its writer uses base+index, NOT FOUND. 0x79916 is a history recorder (copies 4472, 43EE, 4276... into arrays).
    - Real short-term correction = u16 0xFFFF4472, 0x8000 = 1.00 (init 1.00 at 0x23E64). Its writer is the function
      at 0x591BC (GBR 0xFFFF4402). Display byte 5F3D (KLAF) = 4472 >> 8 rounded, written at 0x701F6-0x7020E, ONLY when
      byte 0xFFFF427E is 2 or 16 (closed loop), else 0x80 = 1.00. The 0x70106 function (GBR 0xFFFF5F04) builds the
      display block (5F1C CMDEQRAT, 5F22 LAMBDA, 5F34 GAIR, 5F3D KLAF). 5F30 (KLAFAVE) is copied at 0x81604, writer
      not found.
    - Users of 4472: 0x5A490 (x gbr word, / 0x08000000 - other value), 0x5A5EC (sum of ratios: + 92DE - 4472 + 430E
      - 4276), 0x5B82E/0x5B8A8 (filter 0x8BFA), 0x5C80E-0x5C83E (value x 4472 >> 15 -> 0xFFFF4424), 0x5FA7E (4472 x
      0xFFFF4276), 0x7802C. 0xFFFF4424, 4426, 4276 are other ratios (init = same as 4472). 4276 is likely the long-term
      or purge correction (assumed, not proven). Where the trims enter the per-cylinder pulse is NOT found yet.
    - Overfill: owner filled 2-3 clicks past the first click at the last fill (before the 7/11 super log). Known cause of
      a liquid-flooded charcoal canister; with a purge valve that leaks when closed, it adds fuel even at DPCS 0. The
      first log showing the ~16 % excess (7/11 12:00) is after that fill. Fits, not proven.
      Then 20 min of hard driving right after that fill (sloshing can push liquid into the vapor line).
      BUT owner: the exhaust smell was noticed BEFORE that fill. So the overfill cannot be the start of the problem
      (it may have made it worse). The start is between 1/11 18:08 (total correction ~0.98, no excess) and the smell
      earlier this week: something that changed over days. Suspects: purge valve leaking, fuel in the oil (crankcase
      vapors), fuel pressure (regulator kept with the new pump), leaking injector.
      Oil dipstick 2026-11-07 (owner): no particular fuel smell, "oil that got a bit hot", nothing alarming (owner not
      used to judging oil smell; level not reported). Oil change due soon by time (not by km), lots of hard driving.
      Fuel in oil less likely but not ruled out. Idea: change the oil, then log; if the correction goes back toward 1.00,
      fuel in the oil was a part.
      Dipstick photos 2026-11-07 (night, hot engine, ~5 min after stop): oil light amber (fairly clean), level AT or
      SLIGHTLY ABOVE the upper hole (full mark). Read from photos, ~70 % sure. Baseline only: if the level rises over the
      next week at the same check conditions, fuel is getting into the oil.
      Owner: level UNCHANGED since last week's check (the week the excess appeared); slightly high because the parking
      slopes toward the front of the car. Fuel in the oil now unlikely (~75 %), purge valve is the next suspect.
      Owner: the pressure regulator is a separate part (not inside the pump), under the rear seat, kept, NOT touched
      during the pump change. The 1/11 18:08 log (after the pump change) had no excess, so the pump change did not
      cause it right away. Regulator still possible (it can fail on its own) but lower than the purge valve.
    LOG TESTS 2026-11-07 (scratch air_fuel_split.py "all", purge_effect.py, hot_restart.py, runscan.py):
    - By load, total correction 1/11 v6 -> 7/11 super: warm idle 0.969 -> 0.821 (-15 %), cruise 0.938 -> 0.800 (-15 %),
      load 2500-4000 / MAP 60-85 0.984 -> 0.855 (-13 %) (n 80-3149, purge open in most frames). ST alone (LT shown is
      one value): idle 0.984 -> 0.922, driving 1.000 -> 0.922 to 0.969. Fuel flow at load is ~11x idle, so a FIXED
      extra (purge leak, dripping injector, oil vapors) would be ~15 % at idle but ~1-2 % at load. Seen: about the
      same % everywhere -> the excess is PROPORTIONAL: more fuel per ms of injection (fuel pressure / regulator,
      injector flow) or the fuel itself (super vs regular ethanol content could explain ~3-4 % at most, assumed).
      ~65 % sure (few load frames, purge open, LT is a single value).
    - Purge: ST drop from purge closed to fully open, driving: stock 25/10 -2.8 %, v1-v3 -2.7 %, 1/11 v3 -3.4 %,
      v6 -0.8 %, 7/11 super -4.8 %; idle similar (stock -4.9 %, super -3.3 %). Normal size, canister not overloaded,
      and the excess is there with the purge closed (driving DPCS 0: ST 0.969, LT 0.883). Purge = not the main cause.
    - Hot restart: no snapshot covers a hot engine start (7/11 12:00 log starts at run 82 s). Not testable with the
      current logs. To test: warm drive, engine off 15-20 min, restart, snapshot within 2 min.
    - The 7/11 cold log ran at 14.3 V with the same low correction, so the 12.6 V of the super log is not the cause.
    New order: fuel pressure test (gauge, garage) first, then injectors; purge and oil low.
    (Owner cannot do a fuel pressure test.)
    OPEN-LOOP TEST 2026-11-07 (scratch open_loop.py, ol_zone.py): FSS 4 enrichment frames, warm, after 15 open-loop
    frames: full throttle, 5100-5700 rpm, MAP 97-100, commanded lambda 0.848 in all groups. Measured / commanded:
    stock 25/10 1.064 (n 20, LT 1.055), 1/11 v3 1.058 (n 222, LT 1.086), 1/11 v5 0.903 (n 154, LT 0.969),
    1/11 v6 0.965 (n 304, LT 0.977), 7/11 super 0.939 (n 255, LT 0.898). FSS 1 frames are mostly closed-throttle
    decel (MAP 25), not usable.
    - Method check: v5 -> v6 differ by 1.15 -> 1.08 at high air: predicted ratio 1.065, measured 1.069. The test works.
    - 1/11 v6 -> 7/11: only 2.7 % richer at full throttle. Two readings fit, and they depend on one unknown:
      (A) the long-term correction IS applied in open loop -> real proportional excess ~12 % (fits the pressure idea);
      (B) it is NOT applied -> almost no extra fuel at full throttle (~3 %, maybe the fuel type), so the excess is
      mostly at low flow -> a fixed extra (leak, purge, drip) fits better. A fixed extra with (A) would give ~5 %
      LEANER at full throttle: excluded. A proportional 18 % with (B) would give ~15 % richer: excluded.
    - Error in my earlier claim: this test cannot separate front-sensor drift from real fuel (closed loop cancels both
      the same way); only the rear O2 does (it reads slightly richer, so drift is unlikely).
    - Safety: at full throttle the real lambda is now ~0.80 (0.848 x 0.939) vs ~0.82 on 1/11: rich side, no lean risk.
    KEY UNKNOWN: is the long-term correction applied in open loop? Answer in the ROM (or a log right after a trim reset).
    ROM ANSWER 2026-11-07 (stock A240 disassembly, scratch shdis.py / gbr_refs.py / const_track.py / lits.py / h16b.py):
    - Real LT = u16 0xFFFF9304 (backup RAM, 0x8000 = 1.00); copy 0xFFFF510A. Display KLAFAVE 5F30 = 9304 >> 8 at 0x753E8.
      Learning 0x644F6 (GBR 0xFFFF5102): 9304 moves half-way toward 0xFFFF511A, clamped by table 0xC49C, write 0x645B0.
      0x643D6: 511A = filter(0x8BFA) of sat(0xFFFF4424 - 0xFFFF465E). 0x5C80E: 4424 = [4606] x ST(4472) >> 15.
      Fuel system monitor (DTC) 0x640FC compares 9304 to table 0xC470.
    - VERIFIED: 9304 / 510A have NO other reader in the whole ROM (32-bit and 16-bit literal search, GBR and pointer
      tables): only init (0x210B0-0x21336, 0x2151C, 0x2529C), learning, monitor, display. So the HDS "long-term
      correction" is NOT multiplied into the injection anywhere: it is a slow follower of ST, used for the DTC.
    - Logs agree (closed loop, ECT >= 80): ST / LT medians 25/10 1.094 / 1.047, 1/11 v3 1.133 / 1.086, 1/11 v6
      1.000 / 0.977, 7/11 0.922 / 0.883. LT never pulls ST back to 1.00 (an applied LT would); LT = ST - ~0.045 always.
    - Injection path: 0x5FA88 uses 4472 (ST) x 0xFFFF4276. 4276 = r14 x [4044] >> 15 (0x5A27C, stored 0x5A3F8).
      r14 = ramp toward 4606 in normal mode, but interp(463E, 4622) (enrichment ratio, 4622 written 0x5B534 from
      rpm tables 0xB430 / 0xB02E) when byte 0xFFFF3F36 is set.
      3F36 writer 0x52A26 (GBR 0xFFFF3F04 set at 0x5279A) = OR of 4 high-load flags (load 0xFFFF29D8 vs rpm tables
      0xA620 / 0xA62C / 0xA6E8 / 0xA6D8 with delay counter 0xFFFF784E) = the power enrichment flag (ASSUMED = FSS 4).
      4606 writer found: 0x5DE02 via pointer table 0x1692C (bank 0 -> 4606, bank 1 -> 48F4):
      4606 = sat(0x8000 - [0xFFFF92E0] + term) (term 0 / 0x500 / [48F0] / [48EC]); 92E0 = backup RAM, front O2 related
      (also used by 0x5C54C, 0x5F5xx, 0x64A62 diagnostics). Its size is unknown (not in the HDS list).
    => Reading (B) holds, ~80 %: no learned correction at full throttle (only ST and LT-like terms in closed loop).
       CORRECTION of earlier numbers: the real closed-loop correction is ST alone (x 4606, unknown, ~1): 1.000 on 1/11 v6
       -> 0.922 on 7/11 = ~8 % excess, NOT 18 % (ST x LT double counted). At full throttle ~3 %.
       Excess bigger in closed loop (~8 %) than at full throttle (~3 %): a pure proportional cause (pressure, fuel
       type) alone does not fit well; something that acts mainly at low / mid flow or only in closed loop fits better.
    SPLIT BY PURGE, ST ONLY (scratch st_load.py, closed loop, ECT >= 80), 1/11 v6 -> 7/11:
      purge open (all frames): idle 1.000 -> 0.922, cruise MAP<50 0.992 -> 0.922, MAP 50-70 0.984 -> 0.930, MAP>=70 1.008 -> 0.984
      purge closed (DPCS 0):   idle 1.016 -> 0.984 (n 86 / 33), cruise 1.016 -> 0.977 (n 138 / 121), MAP>=70 1.008 -> 0.969 (n 71 / 41)
    => Two parts: (1) ~3-4 % FLAT with purge closed, same as full throttle (~3 %): a proportional cause. Best fit: the
       7/11 fill is super (often no ethanol) vs regular E10 before: E0 vs E10 = ~4 % more fuel per air (ASSUMED, pump
       label not checked). CHECKED 2026-11-07: the fuel brand's official FAQ says only that its gasolines may contain up
       to 10% ethanol, for all grades, with no per-grade figure (brand removed from the public copy). So the premium
       fill is NOT known to be ethanol-free; the fuel
       type idea is NOT proven (down to ~25 %). The flat 3-4 % part stays open: fuel type, fuel pressure, normal
       day-to-day spread, injectors. (2) purge effect grew from ~1.6 % to ~6 % at idle / cruise: much more vapour from the
       canister (full tank, filled 2-3 clicks past the first click on 6/11, hard driving after). Small purge-closed
       samples (33-121 frames): ~70 % sure of the split.
    The mixture itself stays at lambda 1 in closed loop, so the fuel SMELL is not explained by the mixture. The smell
    started the week of the pump change (1/11), before the fill: check the pump module seal / lock ring, fuel and
    vapour line connections under the rear seat (visual + smell only, engine off, no flame, no sparks).
    OWNER CORRECTION 2026-11-07: it is NOT a raw fuel smell, it is a "rich running engine" exhaust smell. So the pump
    leak idea drops (a look is still cheap). Closed loop is at lambda 1, so the rich smell must come from the phases the
    ECU does not correct: full throttle (real ~0.80 on 7/11, ~0.82 on 1/11 v6; stock real was ~0.87-0.90 = 0.848 x
    1.03-1.06, ASSUMED from the pre-v5 WOT data) and tip-in (x2 since v2). v5 / v6 started 1/11 = same week as the
    smell; owner drives hard a lot. ~60 % the smell is the tune's open-loop richness (+ the new ~3 % drift), not a
    fault. Test: does the smell come after hard accelerations only, or also at idle / steady cruise?
    OWNER DECISION 2026-11-07: nothing prepared or flashed until the drift cause is known. For the NEXT tune: high-flow
    MAF multiplier x1.04 instead of x1.08 (v6). Method: meas/cmd scales as 1 / multiplier (validated v5 -> v6: predicted
    1.065, measured 1.069). 1/11 v6 meas/cmd 0.965 x 1.08 / 1.04 = ~1.00 -> real ~0.85 = Honda command. Low / mid flow
    unchanged: on 1/11 v6 ST was 1.000 there, so the 7/11 -8 % is the drift, not the tune.
    Tip-in, ECT >= 80, lowest lambda median / share below 0.90 (sensor lag included): stock 0.929 / 17 %, v1-v3 0.922 / 23 %, v3 1/11 0.899 / 51 %, v5 0.878 / 77 %, v6 0.913 / 32 %, v6 super 0.912 / 29 %: a little richer than stock, brief. Misfire 0, DCAM 25 / NCAM
    30 unchanged, ECT 83-86 warm.
  - KNRTD / KIGKREF TRACED IN THE ROM (2026-11-07, stock A240, Ghidra DecompAt; scratch knock_model.py). CORRECTION of
    the entries above: KNRTD > 0 is NOT by itself knock, it is mostly programmed retard.
    Mode 22 dispatch: DID list at 0x88626, compare chain 0x884BA.., DID 2662 -> 0x89060 -> 0x84BC4 (DID 2610 -> 0x83000,
    2660 -> 0x84428, 2661 -> 0x847D8). 2662 data offsets = HDS byte positions: b08 KNRTD, b09 NLSMPL (0xFFFF2787),
    b0A KIGKREF = high byte of 0xFFFF92F8, b0B = high byte of 0xFFFF92FC (not in HDS), b0C-0D TCAT.
    KNRTD (0x82AD8) = clamp 0..255 of (0xFFFF4EF6 - max(0xFFFF4E6E, 0)) / 5 (0x9128C = divide helper, operand order
    inferred, fits the logs). Main ignition correction 0x60FD6 (base 0xFFFF4E62 = load index):
    4E6E = 4E66 (margin map by rpm x load x 0xFFFF3346) + transient 4E6A + 4E6C;
    4E64 = 2 x map byte, table by rpm x load: 0xB9EC / 0xBA14 (data 0x16D5C / 0x16EEC) or 0xBA00 when 0xFFFF4134 set
    (data 0x16E24, probably VTEC, rpm axis 0x18ED0), 10 load rows (axis 0x18F20, 900..7800) x 20 rpm columns;
    4EF6 = 4E70 x 4E64 >> 15 (0x8000 = 1.0); 4F04 = 4E6E - 4EFE - 4EFC - 4EF6 - 4EF8 + 4F00, 4F02 = min(4F04, 0).
    So ignition is retarded from the base by reference x delta map minus margin: looks like a high octane / low
    octane interpolation (name assumed). Map byte: 100-115 at mid load, 50 at full load (>= 1750 rpm, no VTEC).
    Reference 0xFFFF4E70 (0x62540, base 0xFFFF4F18; floor/ceiling 4FE4 / 4FD4 from 0x62A26): knock flag 0xFFFF4FE2
    set -> +4260 or +6554 (= +17 / +26 KIGKREF counts) and hold 50 ticks; no knock -> -262 every 20 ticks. Start:
    learned + 3277 (+13 counts). Disabled (0xFFFF3326 = 0): 0x7333 = 29491 = KIGKREF 115 = 0.90, the value seen after
    each flash. Fail-safe (0xFFFF4FE0): 0xC000. Learned 0xFFFF92F8 (0xFFFF92FC when 0xFFFF4E5E != 0): rises towards the
    target by 2.4 % of the gap per call, falls by 33-98 per 40 ticks, limits 0x4000..0xA666 = KIGKREF 64..166.
    Sensor: 0x63B9E compares knock level 0xFFFF2788 per cylinder (0xFFFF3127) with a threshold from a learned noise
    level; above -> 0xFFFF5022 -> 0x63750 copies to 4FE2.
    PROOF on the logs: full load, MAP >= 90, 2500-4400 rpm, model KNRTD = KIGKREF x 100 / 640: 1977 frames, 6 groups,
    median error -0.2..-0.6, 0-2 % of frames >= +3. Today's WOT KNRTD rise = KIGKREF only. 0.5 deg/count still measured,
    not from the code (WOT KNRTD +6.4, IG -3).
    Better test of a fuel = KIGKREF level and its rises. Rise episodes (> 3 s apart): 87 octane 29 in 12.3 min at
    MAP >= 45 and ECT >= 83 (2.4 / min; 0.8 on v6), super 0 in 0.9 min = expected ~2, P(0) ~12 %: not significant yet.
    A rise can also follow the +13 start offset, so rise = knock is likely, not proven. Lowest KIGKREF on 87: 88.
    Floor 64 would give WOT KNRTD ~10 instead of 16.
- Battery: 12.52 V at rest on the maintainer, ~11.9 V stable with ignition ON (headlights off).
