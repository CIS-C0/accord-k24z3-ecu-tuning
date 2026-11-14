# Dump 1D table descriptors (12 bytes: count byte, 3 format bytes, axis ptr, data ptr; helper 0x8CD8) and RAM flag
# lists (null-terminated 32-bit pointers, helper 0x8CAE).
# dump_desc.py <bin (ROM from 0x8000)> d<hex descriptor> ... l<hex flag list> ...
import struct, sys

ROM = 0x8000
b = open(sys.argv[1], 'rb').read()
s16 = lambda a: struct.unpack_from('>h', b, a - ROM)[0]
u32 = lambda a: struct.unpack_from('>I', b, a - ROM)[0]
for arg in sys.argv[2:]:
    a = int(arg[1:], 16)
    if arg[0] == 'l':
        out = []
        while u32(a):
            out.append(f'{u32(a):08X}')
            a += 4
        print(f'list {int(arg[1:], 16):X}: {" ".join(out)}')
        continue
    n, fmt, ax, dt = b[a - ROM], b[a - ROM + 1:a - ROM + 4].hex(), u32(a + 4), u32(a + 8)
    print(f'desc {a:X} n={n} fmt={fmt} axis {ax:X}: {[s16(ax + 2 * i) for i in range(n)]} '
          f'data {dt:X}: {[s16(dt + 2 * i) for i in range(n)]}')
