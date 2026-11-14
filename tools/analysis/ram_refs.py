import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
w = lambda a: struct.unpack_from('>H', b, a - base)[0]
l = lambda a: struct.unpack_from('>I', b, a - base)[0]
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
end = 0x8F000  # code region end guess
def fstart(a):
    x = a - 2
    while x > a - 0x3000:
        if w(x) == 0x000B:
            s = x + 4
            while w(s) == 9: s += 2
            return s
        x -= 2
    return None
hits = {}
for a in range(0x20000, end, 2):
    x = w(a)
    v = None
    if x >> 12 == 0xD:
        p = ((a + 4) & ~3) + (x & 0xFF) * 4
        if p < base + len(b) - 4: v = l(p)
    elif x >> 12 == 9:
        p = a + 4 + (x & 0xFF) * 2
        v = w(p)
        v = v | 0xFFFF0000 if v & 0x8000 else v
    if v is not None and lo <= v <= hi:
        hits.setdefault(v, []).append(a)
for v in sorted(hits):
    print(f'{v:#x}: ' + ' '.join(f'{a:#x}' for a in hits[v][:30]))
fs = {}
for v, A in hits.items():
    for a in A: fs.setdefault(fstart(a), set()).add(v & 0xFFFF)
print('functions:')
for f in sorted(k for k in fs if k): print(hex(f), ' '.join(f'{x:04X}' for x in sorted(fs[f])))
