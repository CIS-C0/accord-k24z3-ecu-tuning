# Words that differ between two calibrations in a range, ignoring 32-bit pointers into 0x10000-0x1FFFF (table moves):
# cmp_scalars.py <a.rwd.gz> <b.rwd.gz> <lo_hex> <hi_hex>
import struct, sys
ns = {}
exec(open(__file__.replace('cmp_scalars.py', 'cmp_cal.py')).read().split('\na, b = load')[0], ns)
a, b = ns['load'](sys.argv[1]), ns['load'](sys.argv[2])
lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
ptr = set()
for x in (a, b):
    for o in range(lo - 0x8000, hi - 0x8000, 2):
        if 0x10000 <= struct.unpack_from('>I', x, o)[0] < 0x20000:
            ptr.update((o, o + 2))
n = 0
for o in range(lo - 0x8000, hi - 0x8000, 2):
    if o in ptr or a[o:o + 2] == b[o:o + 2]:
        continue
    n += 1
    print(f'0x{o + 0x8000:05X}: A {struct.unpack_from(">h", a, o)[0]:6d}  B {struct.unpack_from(">h", b, o)[0]:6d}')
print('differing non-pointer words:', n)
