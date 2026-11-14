import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
def hexd(a, n):
    for i in range(a, a + n, 16):
        print(f'{i:06X} ' + ' '.join(f'{x:02X}' for x in b[i - base:i - base + 16]))
hexd(0x885C0, 0x100)
print()
# who points at the table region (32-bit pool words 0x885xx-0x887xx)
for i in range(0, len(b) - 3, 2):
    v = struct.unpack_from('>I', b, i)[0]
    if 0x88500 <= v < 0x88800: print('ptr', hex(i + base), '->', hex(v))
print()
for a, n in ((0x29200, 90),):
    print(hex(a), [f'{struct.unpack_from(">I", b, a - base + 4*k)[0] & 0xFFFF:04X}' for k in range(n)])
