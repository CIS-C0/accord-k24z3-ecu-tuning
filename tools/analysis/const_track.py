import struct, sys
# Approximate constant tracking over the ROM (linear): finds loads/stores whose address is a known constant
# (pool pointer + displacement, GBR + displacement, pointer + r0 when r0 is constant, add #imm).
# Usage: py -I const_track.py <bin> <lo hex> <hi hex>
b = open(sys.argv[1], 'rb').read(); BASE = 0x8000
w = lambda a: struct.unpack_from('>H', b, a - BASE)[0]
l = lambda a: struct.unpack_from('>I', b, a - BASE)[0]
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
s8 = lambda x: x - 256 if x & 0x80 else x
M = 0xFFFFFFFF
R = [None] * 16; gbr = None
def hit(pc, kind, size, addr):
    if addr is not None and lo <= (addr & M) <= hi:
        print(f'{pc:#07x} {kind} {size} @{addr & M:#x}')
for pc in range(0x20000, 0x8F000, 2):
    op = w(pc); t = op >> 12; n = (op >> 8) & 15; m = (op >> 4) & 15; lo4 = op & 15
    if op in (0x000B, 0x002B) or t in (0xA, 0xB) or (t == 4 and (op & 0xFF) in (0x0B, 0x2B)) or (t == 0 and (op & 0xFF) in (0x03, 0x23)):
        # keep state through the delay slot, then reset
        nxt = w(pc + 2)
        R = [None] * 16
        continue
    if t == 0xD: R[n] = l(((pc & ~3) + 4) + (op & 0xFF) * 4); continue
    if t == 9: v = w(pc + 4 + (op & 0xFF) * 2); R[n] = (v | 0xFFFF0000) if v & 0x8000 else v; continue
    if t == 0xE: R[n] = s8(op & 0xFF) & M; continue
    if t == 7: R[n] = None if R[n] is None else (R[n] + s8(op & 0xFF)) & M; continue
    if t == 6 and lo4 == 3: R[n] = R[m]; continue
    if t == 4 and (op & 0xFF) == 0x1E: gbr = R[n]; continue
    if t == 0 and (op & 0xFF) == 0x12: R[n] = gbr; continue
    if t == 3 and lo4 == 0xC: R[n] = None if R[n] is None or R[m] is None else (R[n] + R[m]) & M; continue
    # stores
    if t == 2 and lo4 in (0, 1, 2): hit(pc, 'store', 1 << lo4, R[n]); continue
    if t == 1: hit(pc, 'store', 4, None if R[n] is None else R[n] + (op & 15) * 4); continue
    if t == 8 and n in (0, 1): hit(pc, 'store', 1 << n, None if R[m] is None else R[m] + (op & 15) * (1 << n)); continue
    if t == 0 and lo4 in (4, 5, 6): hit(pc, 'store', 1 << (lo4 - 4), None if R[n] is None or R[0] is None else R[n] + R[0]); continue
    if t == 0xC and n in (0, 1, 2): hit(pc, 'store', 1 << n, None if gbr is None else gbr + (op & 0xFF) * (1 << n)); continue
    # loads (destination becomes unknown)
    if t == 6 and lo4 in (0, 1, 2): hit(pc, 'load ', 1 << lo4, R[m]); R[n] = None; continue
    if t == 5: hit(pc, 'load ', 4, None if R[m] is None else R[m] + (op & 15) * 4); R[n] = None; continue
    if t == 8 and n in (4, 5): hit(pc, 'load ', 1 << (n - 4), None if R[m] is None else R[m] + (op & 15) * (1 << (n - 4))); R[0] = None; continue
    if t == 0 and lo4 in (0xC, 0xD, 0xE): hit(pc, 'load ', 1 << (lo4 - 0xC), None if R[m] is None or R[0] is None else R[m] + R[0]); R[n] = None; continue
    if t == 0xC and n in (4, 5, 6): hit(pc, 'load ', 1 << (n - 4), None if gbr is None else gbr + (op & 0xFF) * (1 << (n - 4))); R[0] = None; continue
    if t == 0xC and n == 7: R[0] = ((pc & ~3) + 4 + (op & 0xFF) * 4); continue
    # anything else that writes Rn: unknown
    if t in (3, 6) or (t == 2 and lo4 >= 7) or t == 4 or (t == 0 and lo4 in (7, 9, 0xA, 0x2)):
        if t == 2 and lo4 == 8: continue  # tst
        if t == 3 and lo4 in (0, 2, 3, 6, 7): continue  # compares
        R[n] = None
    if t == 0xC and n >= 8: R[0] = None
