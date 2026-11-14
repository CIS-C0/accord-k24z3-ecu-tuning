# MAF recalibration v6, step 1: fuel factor needed per MAF table point (descriptor 0xA75C), RELATIVE TO THE STOCK
# table, so logs taken on different files can be combined. Same frame selection as maf_corr.py, except:
# - closed loop (FSS 2): factor = ST x LT x (lambda / cmd), AFM steady (same on the frame before/after);
# - open loop (FSS 4): factor = lambda / cmd (ST is 1.00 and LT is not applied in open loop, 75 % deduction from the
#   2026-11-01 WOT logs), AFM within +-4 of the frames before/after (WOT pulls are never steady).
# need vs stock = factor x mult, mult = how much the logged file's table is above stock (v3 1.0, v5 1.15).
# Usage: py -I maf_need.py <stock-table bin> <raw dir>:<mult> [<raw dir>:<mult> ...]
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


P = {}  # (source, axis index) -> list of (need, closed loop?)
for arg in sys.argv[2:]:
    d, mult = arg.rsplit(':', 1)
    mult = float(mult)
    seen = set()
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        day = os.path.basename(p)[:8]
        rows = [r for r in csv.DictReader(open(p)) if r['AFM'] != '' and r['NE'] != '']
        for k in range(1, len(rows) - 1):
            r = rows[k]
            if (day, r['t']) in seen:
                continue
            seen.add((day, r['t']))
            if int(r['NE']) / 4 < 400 or int(r['ECT']) - 40 < 80 or int(r['FC']) or '65535' in (r['LAMBDA'], r['CMDEQRAT']):
                continue
            a, fss = int(r['AFM']), int(r['FSS'])
            da = max(abs(int(rows[k - 1]['AFM']) - a), abs(int(rows[k + 1]['AFM']) - a))
            lc = int(r['LAMBDA']) / int(r['CMDEQRAT'])
            if fss == 2 and da == 0:
                f = int(r['KLAF']) * int(r['KLAFAVE']) / 16384 * lc
            elif fss == 4 and da <= 4:
                f = lc
            else:
                continue
            P.setdefault((d, nearest(4 * a + 1.5)), []).append((f * mult, fss == 2))

srcs = [a.rsplit(':', 1)[0] for a in sys.argv[2:]]
print(f'descriptor {D:X}: n={n} axis {ax:X} data {dt:X}; need vs STOCK table, median [n]  CL | OL')
print(f'{"i":>3} {"A/D":>5} {"stock":>6} ' + ' '.join(f'{os.path.basename(s)[-12:]:>27}' for s in srcs))
for i in range(n):
    cells = []
    for s in srcs:
        v = P.get((s, i), [])
        cl = [f for f, c in v if c]
        ol = [f for f, c in v if not c]
        cells.append((f'{st.median(cl):6.3f} [{len(cl):3d}]' if cl else f'{"-":>6} [  0]') + ' | '
                     + (f'{st.median(ol):6.3f} [{len(ol):3d}]' if ol else f'{"-":>6} [  0]'))
    if any(P.get((s, i)) for s in srcs):
        print(f'{i:3d} {axis[i]:5d} {data[i]:6d} ' + ' '.join(f'{c:>27}' for c in cells))
