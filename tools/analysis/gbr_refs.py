import struct, sys
# Find GBR-relative accesses (mov.x @(disp,gbr)) that reach a RAM range, using the GBR base set at each function start
# (mov.l @(pool),r0 ; ldc r0,gbr). Usage: py -I gbr_refs.py <bin> <lo hex> <hi hex>
b = open(sys.argv[1], 'rb').read(); base = 0x8000
w = lambda a: struct.unpack_from('>H', b, a - base)[0]
l = lambda a: struct.unpack_from('>I', b, a - base)[0]
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
end = base + len(b) - 4
gbr, gbr_at = None, None
for a in range(0x20000, 0x8F000, 2):
    x = w(a)
    if x == 0x401E:  # ldc r0,gbr: look back for mov.l @(disp,PC),r0
        gbr = None
        for k in range(2, 12, 2):
            y = w(a - k)
            if y >> 8 == 0xD0:
                p = ((a - k + 4) & ~3) + (y & 0xFF) * 4
                gbr = l(p); gbr_at = a
                break
        continue
    if gbr is None: continue
    if x >> 12 == 0xC:
        sub, d = (x >> 8) & 15, x & 0xFF
        size = {0: 1, 1: 2, 2: 4, 4: 1, 5: 2, 6: 4}.get(sub)
        if size is None: continue
        t = gbr + d * size
        if lo <= t <= hi:
            print(f'{a:#07x} {"store" if sub < 4 else "load "} {size} @{t:#x}  (gbr {gbr:#x} set at {gbr_at:#x})')
