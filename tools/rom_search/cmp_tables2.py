# Content-aligned table comparison (handles inserted/moved entries): every 1D descriptor found in the range in each
# calibration, in order, aligned with difflib on the axis values; prints changed tables.
# cmp_tables2.py <a.rwd.gz> <b.rwd.gz> <lo_hex> <hi_hex>
import difflib, struct, sys
ns = {}
exec(open(__file__.replace('cmp_tables2.py', 'cmp_cal.py')).read().split('\na, b = load')[0], ns)
a, b = ns['load'](sys.argv[1]), ns['load'](sys.argv[2])
lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)


def descs(x):
    out = []
    for d in range(lo, hi, 2):
        o = d - 0x8000
        n = x[o]
        ax, dp = struct.unpack_from('>II', x, o + 4)
        if 2 <= n <= 32 and 0x10000 <= ax < 0x20000 and 0x10000 <= dp < 0x20000 and x[o + 1:o + 4] in (
                b'\x66\x66\x00', b'\x66\x02\x00', b'\x65\x66\x00', b'\x66\x65\x00', b'\x65\x65\x00', b'\x66\x01\x00'):
            out.append((d, tuple(struct.unpack_from(f'>{n}h', x, ax - 0x8000)),
                        tuple(struct.unpack_from(f'>{n}h', x, dp - 0x8000)), x[o + 1:o + 4].hex()))
    return out


A, B = descs(a), descs(b)
sm = difflib.SequenceMatcher(None, [(t[1], t[3]) for t in A], [(t[1], t[3]) for t in B], autojunk=False)
changed = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        for i, j in zip(range(i1, i2), range(j1, j2)):
            if A[i][2] != B[j][2]:
                changed += 1
                print(f'desc A 0x{A[i][0]:05X} / B 0x{B[j][0]:05X} fmt {B[j][3]} axis {list(B[j][1])}')
                print('   data A', list(A[i][2]), '\n   data B', list(B[j][2]))
    else:
        print(f'{tag}: A {[hex(t[0]) for t in A[i1:i2]]} B {[hex(t[0]) for t in B[j1:j2]]}')
print('tables A', len(A), 'B', len(B), 'changed data', changed)
