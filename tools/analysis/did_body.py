import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
w = lambda a: struct.unpack_from('>H', b, a - base)[0]
l = lambda a: struct.unpack_from('>I', b, a - base)[0]
for t in (0x89060, 0x89074, 0x89174):
    print('--', hex(t))
    for a in range(t, t + 0x14, 2):
        x = w(a); s = f'{a:06X} {x:04X}'
        if x >> 12 == 0xD:
            p = ((a + 4) & ~3) + (x & 0xFF) * 4
            s += f'  mov.l @{p:#x},r{(x>>8)&15} = {l(p):#x}'
        elif x >> 12 == 0x9:
            p = a + 4 + (x & 0xFF) * 2
            s += f'  mov.w @{p:#x},r{(x>>8)&15} = {w(p):#x}'
        elif x >> 12 == 0xA:
            d = x & 0xFFF; d = d - 0x1000 if d & 0x800 else d
            s += f'  bra {a + 4 + d*2:#x}'
        elif x >> 12 == 0xB:
            d = x & 0xFFF; d = d - 0x1000 if d & 0x800 else d
            s += f'  bsr {a + 4 + d*2:#x}'
        print(s)
