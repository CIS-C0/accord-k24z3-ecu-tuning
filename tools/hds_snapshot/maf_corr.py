# MAF recalibration step 2: fuel correction the ECU needs, per point of the MAF table (descriptor 0xA75C).
# Needed factor on each frame = ST x LT x (measured lambda / commanded lambda): in closed loop the trims carry the error
# (lambda ~ cmd), in open loop (WOT) the trims are frozen and the rest of the error shows as lambda vs cmd.
# Frames: warm (ECT >= 80), running, not fuel cut, valid lambda + cmd, steady MAF (AFM same on the frame before/after),
# deduplicated by day + HDS clock. A frame's MAF A/D (4*AFM .. 4*AFM+3) is given to the nearest table axis point.
# Usage: py -I maf_corr.py <bin (ROM from 0x8000)> <raw csv dir>
import bisect, csv, glob, os, struct, sys, statistics as st

R = 0x8000
b = open(sys.argv[1], 'rb').read()
u16 = lambda a: struct.unpack_from('>H', b, a - R)[0]
u32 = lambda a: struct.unpack_from('>I', b, a - R)[0]
D = 0xA75C
n, ax, dt = b[D - R], u32(D + 4), u32(D + 8)
axis = [u16(ax + 2 * i) for i in range(n)]
data = [u16(dt + 2 * i) for i in range(n)]


def nearest(x):
    i = bisect.bisect_left(axis, x)
    c = [j for j in (i - 1, i) if 0 <= j < n]
    return min(c, key=lambda j: abs(axis[j] - x))


seen = set()
P = {}  # axis index -> list of (factor, closed loop?)
for p in sorted(glob.glob(os.path.join(sys.argv[2], '*.csv'))):
    day = os.path.basename(p)[:8]
    rows = [r for r in csv.DictReader(open(p)) if r['AFM'] != '' and r['NE'] != '']
    for k in range(1, len(rows) - 1):
        r = rows[k]
        if (day, r['t']) in seen:
            continue
        seen.add((day, r['t']))
        a = int(r['AFM'])
        if int(rows[k - 1]['AFM']) != a or int(rows[k + 1]['AFM']) != a:
            continue
        if int(r['NE']) / 4 < 400 or int(r['ECT']) - 40 < 80 or int(r['FC']) or '65535' in (r['LAMBDA'], r['CMDEQRAT']):
            continue
        fss = int(r['FSS'])
        if fss not in (2, 4):
            continue
        f = int(r['KLAF']) * int(r['KLAFAVE']) / 16384 * int(r['LAMBDA']) / int(r['CMDEQRAT'])
        P.setdefault(nearest(4 * a + 1.5), []).append((f, fss == 2, int(r['GAIR'])))

print(f'descriptor {D:X}: n={n} axis {ax:X} data {dt:X}')
print(f'{"i":>3} {"A/D":>5} {"table":>6} {"GAIR med":>8} {"n CL":>5} {"CL med":>7} {"CL p25-p75":>12} '
      f'{"n OL":>5} {"OL med":>7} {"all med":>8}')
for i in range(n):
    v = P.get(i, [])
    if not v:
        print(f'{i:3d} {axis[i]:5d} {data[i]:6d}        -     0')
        continue
    cl = sorted(f for f, c, g in v if c)
    ol = sorted(f for f, c, g in v if not c)
    q = lambda s, x: s[min(len(s) - 1, int(x * len(s)))]
    print(f'{i:3d} {axis[i]:5d} {data[i]:6d} {st.median(g for f, c, g in v):8.0f} {len(cl):5d} '
          + (f'{st.median(cl):7.3f} {q(cl, .25):5.3f}-{q(cl, .75):5.3f} ' if cl else f'{"-":>7} {"":12} ')
          + f'{len(ol):5d} ' + (f'{st.median(ol):7.3f} ' if ol else f'{"-":>7} ')
          + f'{st.median(f for f, c, g in v):8.3f}')
