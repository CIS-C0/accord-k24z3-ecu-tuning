# Checks that the logged MAF airflow (GAIR, 2610:22-23) is the 1D table at descriptor 0xA75C applied to the MAF A/D value:
# AFM (2610:21, 8 bits) is assumed = A/D 10 bits >> 2, so GAIR must lie between table(4*AFM) and table(4*AFM + 3).
# Only frames where AFM is the same on the frame before and after (steady) are tested (GAIR and AFM are not sampled at
# the same instant). Usage: py -I maf_check.py <bin (ROM from 0x8000)> <raw csv dir>
import csv, glob, os, struct, sys

R = 0x8000
b = open(sys.argv[1], 'rb').read()
u16 = lambda a: struct.unpack_from('>H', b, a - R)[0]
u32 = lambda a: struct.unpack_from('>I', b, a - R)[0]
D = 0xA75C
n, ax, dt = b[D - R], u32(D + 4), u32(D + 8)
axis = [u16(ax + 2 * i) for i in range(n)]
data = [u16(dt + 2 * i) for i in range(n)]


def table(x):
    if x <= axis[0]:
        return data[0]
    for i in range(1, n):
        if x <= axis[i]:
            if axis[i] == axis[i - 1]:
                return data[i]
            return data[i - 1] + (data[i] - data[i - 1]) * (x - axis[i - 1]) / (axis[i] - axis[i - 1])
    return data[-1]


ok = tot = 0
near = 0
bad = []
for p in sorted(glob.glob(os.path.join(sys.argv[2], '*.csv'))):
    rows = [r for r in csv.DictReader(open(p)) if r['AFM'] != '' and r['GAIR'] != '']
    for k in range(1, len(rows) - 1):
        a = int(rows[k]['AFM'])
        if int(rows[k - 1]['AFM']) != a or int(rows[k + 1]['AFM']) != a:
            continue
        g = int(rows[k]['GAIR'])
        lo, hi = table(4 * a), table(4 * a + 3)
        tot += 1
        if lo - 1 <= g <= hi + 1:
            ok += 1
        elif lo * 0.95 - 2 <= g <= hi * 1.05 + 2:
            near += 1
        else:
            bad.append((os.path.basename(p)[:15], rows[k]['t'], a, g, round(lo), round(hi)))
print(f'descriptor {D:X}: n={n} axis {ax:X} data {dt:X}')
print(f'steady frames {tot}: GAIR inside table(4*AFM .. 4*AFM+3) {ok} ({100 * ok / tot:.1f} %), within 5 % {near} '
      f'({100 * near / tot:.1f} %), outside {len(bad)} ({100 * len(bad) / tot:.1f} %)')
for x in bad[:15]:
    print('  outside:', x)
