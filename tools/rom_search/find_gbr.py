# find_gbr.py <bin> <ram_hex> [...]: finds GBR-relative accesses (mov.x R0,@(disp,GBR) / mov.x @(disp,GBR),R0) that
# reach a RAM address. GBR is taken from the pool load just before each "ldc Rm,GBR"; the scan runs until the next
# ldc GBR (max 1500 instructions). CPU address = file offset + 0x8000.
import struct, sys
b = open(sys.argv[1], 'rb').read()
B = 0x8000


def w(a):
    return struct.unpack_from('>H', b, a - B)[0]


gbr = []
for a in range(B, B + len(b) - 1, 2):
    o = w(a)
    if o & 0xF0FF == 0x401E:
        m = (o >> 8) & 0xF
        for k in range(1, 30):
            q = w(a - 2 * k)
            if q >> 12 == 0xD and (q >> 8) & 0xF == m:
                gbr.append((a, struct.unpack_from('>I', b, ((a - 2 * k) & ~3) + 4 + (q & 0xFF) * 4 - B)[0]))
                break
starts = sorted(a for a, _ in gbr)
for t in (int(x, 16) | 0xFFFF0000 for x in sys.argv[2:]):
    print(f'=== 0x{t:08X}')
    for a, v in gbr:
        nxt = next((s for s in starts if s > a), a + 3000)
        for pc in range(a + 2, min(nxt, a + 3000, B + len(b) - 1), 2):
            o = w(pc)
            hi, d = o >> 8, o & 0xFF
            sz = {0xC0: 1, 0xC4: 1, 0xC1: 2, 0xC5: 2, 0xC2: 4, 0xC6: 4}.get(hi)
            if sz and v + d * sz <= t < v + d * sz + sz:
                kind = 'store' if hi < 0xC4 else 'load'
                print(f'  {kind} .{ {1: "b", 2: "w", 4: "l"}[sz]} at 0x{pc:05X} (GBR 0x{v:08X} set at 0x{a:05X})')
