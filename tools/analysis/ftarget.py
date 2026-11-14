import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
l = lambda a: struct.unpack_from('>I', b, a - base)[0]
w = lambda a: struct.unpack_from('>H', b, a - base)[0]
targets = set()
for a in range(base, base + len(b) - 4, 2):
    v = l(a)
    if 0x9000 <= v < 0x100000 and v % 2 == 0: targets.add(v)
# also bsr targets
for a in range(base, base + len(b) - 2, 2):
    x = w(a)
    if x >> 12 == 0xB:
        d = x & 0xFFF; d = d - 0x1000 if d & 0x800 else d
        targets.add(a + 4 + d * 2)
for t in (0x23f9a, 0x81070, 0x81604):
    c = sorted(v for v in targets if t - 0x1000 < v <= t)
    print(hex(t), 'nearest call targets before:', [hex(v) for v in c[-4:]])
