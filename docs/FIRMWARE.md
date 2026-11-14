# Firmware files

ECU 37805-R42-A240 (Renesas SH7058, 1 MB). The `.rwd` files are the flashable, encrypted Honda format (0x5A). The
`.bin` files are the decrypted firmware area only (ROM 0x8000-0xFFFFF, 0xF8000 bytes): ROM address = file offset +
0x8000. There is no bootloader in these files and no full ROM dump (a full dump would contain the VIN).

Every `.bin` below has a byte sum of 0 mod 256 over the whole file (the internal checksum rule of this ECU, byte at
ROM 0x8400). Each `.rwd` was checked with the fork's `FirmwareValidator` (header, file checksum, start 0x8000 / size
0xF8000, CAN address 0x10, exactly one part number, supported versions, security key entry present) and with the
self test before it was flashed.

## SHA256

| File | SHA256 |
|---|---|
| stock/37805-R42-A240-M1.RWD.gz | 6E4CACCB388AE50FEA40DFD3FA2EC39E95B6AD2461F15FE0A94D2A88629C9770 |
| stock/37805-R42-A240-M1.0x8000.bin | 217578CB5CAB3268FE0C7AB9ABC8A463DD6F1331161A208067C67E7120EF4BE0 |
| stock/37805-R42-A220-M1.rwd.gz | AEB5B942C946B3524533CFA80B299192FB94315A7C3380049E34D7BCF5FDAC1D |
| work/v1_speedlimiter.bin | D70DE37A5BC2A96C9AC336E2699EC40CB30E9BA8062906F654D2309466AB08EE |
| work/v1_speedlimiter.rwd = flashed/ | BE46D917D717A19B29FA8250338DB885CBD4C335F17E508A600DB2EA9C8967AB |
| work/v2_tipin_fuelcut.bin | 41788E025E1AD506505AD8971A0BAB7E2BA2888846582295802AEA97ABDD6872 |
| work/v2_tipin_fuelcut.rwd = flashed/ | BD4D4F384C835F96B7AC4F1E560512A2A11F92E5BEA7B89548ABE2BF9ECBD4EC |
| work/v3_fuelcut20.bin | 1D3F2779EDC6B7764ECC6928C10A967139EEB963A2FC696E25E5C85361DA7145 |
| work/v3_fuelcut20.rwd = flashed/ | F8836DEC2B820487DB542D7BE801A2FF4A15D943E462B8E01948378E03D1D79D |
| work/v4_revlim100.bin | 18500F7F767F0F91F8551F5B534D2B6152F4E4A7030532A6ED1283C7123E5DB4 |
| work/v4_revlim100.rwd (never flashed) | 0AC6119B87077F35FAF65F919F0D7FFDEAB095679662F991587725BE8BB8B3B3 |
| work/v5_maf115.bin | 765D5E966574E520532AD55E5A588416521CE682307E2071CDE9CEBFDF156B78 |
| work/v5_maf115.rwd = flashed/ | 804C3B6EE2D150428F6BD81A51A04CC268BF18F8E3D41C7F17173F0158A37A44 |
| work/v6_maf_taper.bin | 4BBAD449961BD00B19CA942D6201C5249349661DF3289069F2CEC4286EBDE8B2 |
| work/v6_maf_taper.rwd = flashed/ | 49724F5D3C9AABF2447F35B4A95C91F5404D41F3465361FE5771F2589D656EF1 |

Stock files come from the public [bouletmarc/HondaCalibFiles](https://github.com/bouletmarc/HondaCalibFiles).

## Changed bytes vs stock (ROM addresses)

| Version | Changed ranges | Built from |
|---|---|---|
| v1_speedlimiter | 0x8400 (1), 0xB2C3 (1) | stock |
| v2_tipin_fuelcut | v1 + 0x1419D (7), 0x15AC3 (5) | v1 |
| v3_fuelcut20 | v2 + 0xB13F (3), 0x15AC3 (9) | v2 |
| v4_revlim100 | v3 + 0x15C06 (2), 0x15C0E (2), 0x15C32 (2) | v3 (never flashed) |
| v5_maf115 | v3 + 0x13BFB (117) | v3 |
| v6_maf_taper | v3 + 0x13BFB (117), different values from v5 | v3 |

(The ranges are the contiguous runs of changed bytes; 16-bit big-endian values often change only their low byte.)

## What each change does

All addresses below were traced in Ghidra to the code that reads them (no other users found), and the stock vs
modified behaviour was emulated on the real ECU code with Ghidra's `EmulatorHelper` before flashing
(`tools/ghidra_scripts/Emu*.java`). Evidence and confidence for each item: [KNOWLEDGE.md](KNOWLEDGE.md).

- **0x8400**: internal checksum byte, recomputed so the firmware area sums to 0 mod 256.
- **0xB2C2** (word): speed limiter threshold, 200 -> 240 km/h (v1). Read by the fuel cut manager at 0x587C0.
- **0x1419C-0x141A3** (words): tip-in table (descriptor 0xAB40), 6, 30, 100, 300 -> 12, 60, 200, 600 (first point 0
  kept). Faster throttle response to the pedal (v2).
- **0x15AC2-0x15ACB** (words, gears 1-5, descriptor 0xB158): decel fuel cut entry delay ("overrun fuel cut delay").
  Stock 80, 80, 80, 40, 40 -> v2 40 x5 -> v3 20 x5. Shorter "rev hang" after lifting off.
- **0xB13E / 0xB140** (words): gear change floor of the same delay (0xFFFF76BE), 40, 40 -> 20, 20 (v3). Without it,
  the v3 table change would be hidden right after a gear change.
- **0x15C06 / 0x15C0E / 0x15C32** (words): rev limiter *resume* points 6900 / 7100 / 7100 -> 7000 / 7200 / 7200
  (smaller hysteresis, cut points unchanged). Built and emulated, never flashed (v4).
- **0x13BF2-0x13C71** (64 words, descriptor 0xA75C): MAF transfer table (A/D -> airflow). v5: every point x1.15,
  capped at 32767. v6: x1.15 up to A/D 376, linear to x1.08 at A/D 488, x1.08 above. Made for a short aftermarket
  intake tube that reads low. Next tune (not built): x1.04 instead of x1.08 at high flow, recomputed from fresh logs.

## Rebuilding a file

The scripts that produced these files are in [`tools/build/`](../tools/build) (`build_v2.py` ... `build_v6.py`;
v1 was built with the tool's own editor). Their paths point to the original folder layout (`work\`, `stock\`), so
adjust them first. Each one: starts from the previous version, checks its SHA256, patches only the intended words,
checks the neighbours are unchanged, recomputes 0x8400, re-encrypts to `.rwd`, then the result is validated, diffed
and self-tested (`verify_bin.ps1`, `verify_rwd.ps1`, `FlashToolTest.exe --selftest`). The step-by-step record is in
KNOWLEDGE.md ("Flash #2 file", "Flash #3 file", "v5 BUILT", "v6 step 2"). Compare your result with the SHA256 above.
