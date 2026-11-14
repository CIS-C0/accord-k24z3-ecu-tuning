# Lessons learned

Each lesson below cost something real (an erased ECU, a wrong conclusion, a near miss). Each one became a rule in
[agent/CLAUDE.md](../agent/CLAUDE.md) or a check in the tool.

## Flashing

| What happened | Why | Rule it produced |
|---|---|---|
| 2026-10-24: the ECU was erased, then the transfer never started. Recovered the same day. | The GODIAG ISO 15765 channel hangs on any request of 8+ bytes (multi-frame). Only single-frame requests had been tried before the erase; the request-download message is 11 bytes. | Test **every** message type (single and multi-frame, both directions) on the real car before any erase. ISO-TP is now done in software over raw CAN. |
| A test that "proved" multi-frame worked was a 7-byte message. | 7 bytes still fit in one CAN frame. | Check that a test really tests what it claims. |
| A destructive step (removing the dry-run file) was chained after a deploy that had failed silently (the app was open). | Commands were chained without checking each result. | Never chain a step after one that can fail. Check the deployed exe hash = built exe hash **before** anything else. |
| A security key byte-order bug. | Code review alone did not catch it. | Always test against real recorded data (the car logs had the right order). |
| The upstream checksum (mod 255) would have produced a file this ECU rejects. | The algorithm was written for other ECUs. | Prove a checksum rule on at least two stock files (A240 and A220 both sum to 0 mod 256). |
| Connect ECU got no answer: blamed on the adapter, but the key was OFF. Also: after a long raw CAN session the adapter hangs the same way. | Two causes, same symptom. | Check the key first, then unplug/replug the USB. |
| The Yes/No buttons of a custom dialog were hidden when the text was long. | UI library bug. | Flash dialogs use the standard Windows MessageBox, default button = No. |
| The progress bar stayed stuck at 95 % during the write (cosmetic). | `DarkProgressBar.LockGoingBack = true` in the UI library (read from its IL). | Read library behaviour, don't guess it. |
| Pin 12 programming voltage was planned, then found unnecessary. | The recovery flash worked without it. | Off by default (`FLASH_PIN12.txt` to enable). |

## Reverse engineering

- A community definition file had wrong addresses for VTEC, post-start idle and the second WOT table. Every address
  is traced to the code that reads it before it is trusted.
- "Previous `rts`" is a bad guess for a function start on SH-2A: it often lands in a literal pool. Look for the
  register pushes.
- Some scans only covered part of the ROM (0x20000-0x8F000); a writer was later found through a pointer table at
  0x1692C. When a search finds nothing, check what it actually searched.
- Emulating the real ECU code with Ghidra's `EmulatorHelper`, stock vs modified, caught details a reading of the
  decompiled code missed (for example the gear-change floor that would have hidden the v3 change).

## Data analysis

- An "18 % rich" result was wrong: the HDS long-term trim and the short-term trim were multiplied, but the ROM shows
  the long-term value is not applied to injection on this ECU. Real excess: about 8 %. Know what the ECU actually
  uses before combining numbers.
- "Premium fuel is ethanol-free" was an assumption; the brand's own FAQ says all its grades may contain up to 10 %
  ethanol. Label assumptions, then verify them.
- The owner's observation ("rich exhaust smell, not raw fuel") changed the list of causes. The person at the car sees
  things the logs do not.
- Day-to-day spread of the total fuel correction is about 2 %: a difference smaller than that proves nothing.

## Working with an AI agent

- Two confidence scores on every step ("it works" / "it won't break anything"), with verified vs assumed, keep
  guesses from turning into actions.
- One step at a time, with the owner's approval, especially at the car.
- A knowledge base with evidence lets each new session continue instead of starting over, and makes wrong
  conclusions visible when they are corrected.
- The agent must read the source of a tool function before asking the owner to use it.
