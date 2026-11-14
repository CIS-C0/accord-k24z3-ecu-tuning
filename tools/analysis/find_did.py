import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
print('size', hex(len(b)))
# 1. DID constants as BE16
for did in (0x2610, 0x2611, 0x2612, 0x2613, 0x2660, 0x2661, 0x2662):
    pat = struct.pack('>H', did); o = []; i = b.find(pat)
    while i >= 0:
        o.append(hex(i + base)); i = b.find(pat, i + 1)
    print(hex(did), len(o), o[:24])
# 2. low bytes adjacent: 10 11 12 13 / 60 61 62 style sequences
for pat in (bytes([0x10, 0x11, 0x12, 0x13]), bytes([0x60, 0x61, 0x62]), bytes([0, 0x60, 0, 0x61, 0, 0x62])):
    i = b.find(pat); o = []
    while i >= 0:
        o.append(hex(i + base)); i = b.find(pat, i + 1)
    print(pat.hex(), len(o), o[:20])
# 3. runs of RAM pointers
i, runs = 0, []
while i + 4 <= len(b):
    j = i
    while j + 4 <= len(b) and 0xFFFF0000 <= struct.unpack_from('>I', b, j)[0] < 0xFFFFC000: j += 4
    if j - i >= 32: runs.append((i + base, (j - i) // 4)); i = j
    else: i += 2 if j == i else (j - i)
print('pointer runs >= 8:', len(runs))
for a, n in sorted(runs, key=lambda x: -x[1])[:40]:
    w = [struct.unpack_from('>I', b, a - base + 4 * k)[0] for k in range(min(n, 8))]
    print(hex(a), n, ' '.join(f'{x & 0xFFFF:04X}' for x in w))
# 4. occurrences of RPM pointer and others outside function pools
for v in (0xFFFF289C, 0xFFFF3E30, 0xFFFF29D8):
    pat = struct.pack('>I', v); o = []; i = b.find(pat)
    while i >= 0:
        o.append(i + base); i = b.find(pat, i + 1)
    print(hex(v), len(o), [hex(x) for x in o if x % 4 == 0][:60])
