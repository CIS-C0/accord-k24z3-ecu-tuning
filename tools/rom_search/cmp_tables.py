# Lists every 1D table descriptor (count, 3 format bytes, axis ptr, data ptr) at the same address in two calibrations
# whose axis or data differ: cmp_tables.py <a.rwd.gz> <b.rwd.gz> [desc_lo_hex desc_hi_hex]
import struct, sys
sys.argv, files = sys.argv[:1] + sys.argv[3:], sys.argv[1:3]
import importlib.util
spec = importlib.util.spec_from_file_location('cmp_cal_load', __file__.replace('cmp_tables.py', 'cmp_cal.py'))
src = open(spec.origin).read().split('\na, b = load')[0]  # reuse load() only
ns = {}
exec(src, ns)
a, b = ns['load'](files[0]), ns['load'](files[1])
lo, hi = (int(sys.argv[1], 16), int(sys.argv[2], 16)) if len(sys.argv) > 2 else (0x9000, 0xB800)


def desc(x, d):
    o = d - 0x8000
    n = x[o]
    ax, dp = struct.unpack_from('>II', x, o + 4)
    if not (2 <= n <= 32 and 0x10000 <= ax < 0x20000 and 0x10000 <= dp < 0x20000):
        return None
    return list(struct.unpack_from(f'>{n}h', x, ax - 0x8000)), list(struct.unpack_from(f'>{n}h', x, dp - 0x8000)), ax, dp


same = diff = 0
for d in range(lo, hi, 2):
    A, B = desc(a, d), desc(b, d)
    if not A or not B or len(A[0]) != len(B[0]):
        continue
    if A[0] == B[0] and A[1] == B[1]:
        same += 1
        continue
    diff += 1
    print(f'desc 0x{d:05X} (B data 0x{B[3]:05X})')
    if A[0] != B[0]:
        print('   axis A', A[0], '\n   axis B', B[0])
    else:
        print('   axis  ', B[0])
    print('   data A', A[1], '\n   data B', B[1])
print('descriptors identical:', same, 'different:', diff)
