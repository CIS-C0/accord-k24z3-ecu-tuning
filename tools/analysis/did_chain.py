import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
w = lambda a: struct.unpack_from('>H', b, a - base)[0]
res = {}
for a in range(0x88000, 0x89800, 2):
    x = w(a)
    if x >> 12 == 9 and w(a + 2) & 0xF0FF == 0x3020 | 0 or (x >> 12 == 9 and (w(a + 2) & 0xF00F) == 0x3000):
        pool = a + 4 + (x & 0xFF) * 2
        v = w(pool)
        if v >> 8 != 0x26: continue
        i = w(a + 4); j = w(a + 6)
        if i >> 8 == 0x8B and j >> 12 == 0xA:
            d = j & 0xFFF
            d = d - 0x1000 if d & 0x800 else d
            res[v] = (a, a + 6 + 4 + d * 2)
for v in sorted(res): print(hex(v), 'cmp at', hex(res[v][0]), 'target', hex(res[v][1]))
