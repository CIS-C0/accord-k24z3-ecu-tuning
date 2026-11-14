# Lean condition analysis on the raw HDS snapshot CSVs written by snapall.py.
# Scales proven on the logs (engine off / known screens): NE raw/4 rpm, ECT/IAT raw-40 C, MAP/BARO kPa, VB raw/10 V,
# KLAF / KLAFAVE raw/128 (128 with engine off = factor 1.00), LAMBDA / CMDEQRAT raw/32768 (65535 = not available).
# GAIR (MAF) is kept RAW here (its scale is checked separately against speed density).
# Usage: py -I lean.py <raw csv dir>
import csv, glob, os, sys, statistics as st

rows, seen = [], set()
for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.csv'))):
    prev = None
    for r in csv.DictReader(open(p)):
        # snapshots saved less than 3 min apart overlap: keep each frame once (same day + HDS session clock)
        key = (os.path.basename(p)[:8], r['t'])
        if key in seen:
            prev = None
            continue
        seen.add(key)
        try:
            d = {k: int(r[k]) for k in ('t', 'NE', 'VSP', 'ECT', 'IAT', 'MAP', 'BARO', 'GAIR', 'AFM', 'TOUT', 'KLAF',
                                        'KLAFAVE', 'LAMBDA', 'CMDEQRAT', 'FC', 'FCDEC', 'IDLING', 'ERUNTM', 'NGP',
                                        'VTCANGL', 'FSS', 'CLV', 'SVO2')}
        except ValueError:
            prev = None
            continue
        d['file'] = os.path.basename(p)[:-4]
        d['rpm'] = d['NE'] / 4
        d['ect'] = d['ECT'] - 40
        d['iat'] = d['IAT'] - 40
        d['st'] = d['KLAF'] / 128
        d['lt'] = d['KLAFAVE'] / 128
        d['tot'] = d['st'] * d['lt']
        d['lam'] = d['LAMBDA'] / 32768 if d['LAMBDA'] != 65535 else None
        d['cmd'] = d['CMDEQRAT'] / 32768 if d['CMDEQRAT'] != 65535 else None
        d['steady'] = prev is not None and abs(d['NE'] - prev['NE']) < 4 * 40 and abs(d['MAP'] - prev['MAP']) <= 1 \
            and d['t'] - prev['t'] < 200
        rows.append(d)
        prev = d
print(len(rows), 'rows')

# closed loop, warm, fuelled, steady, stoichiometric command
cl = [d for d in rows if d['rpm'] > 400 and d['ect'] >= 80 and not d['FC'] and d['lam'] is not None
      and d['cmd'] is not None and abs(d['cmd'] - 1) < 0.01 and d['steady'] and d['FSS'] == 2]
print(len(cl), 'closed-loop warm steady rows (FSS == 2)')
for v in sorted({d['FSS'] for d in rows}):
    print(' FSS', v, sum(1 for d in rows if d['FSS'] == v and d['rpm'] > 400))


def show(title, key, edges, sel):
    print(f'\n== total trim (ST x LT) by {title}')
    print(f'{"bin":>14} {"n":>6} {"ST med":>7} {"LT med":>7} {"tot p10":>8} {"tot med":>8} {"tot p90":>8} {"lambda":>7}'
          f' {"rpm":>6} {"MAP":>5} {"GAIR":>6} {"files":>5}')
    for lo, hi in zip(edges, edges[1:]):
        s = [d for d in sel if lo <= key(d) < hi]
        if len(s) < 20:
            continue
        tot = sorted(d['tot'] for d in s)
        n = len(tot)
        print(f'{lo:>6}-{hi:<7} {n:6d} {st.median(d["st"] for d in s):7.3f} {st.median(d["lt"] for d in s):7.3f} '
              f'{tot[n // 10]:8.3f} {tot[n // 2]:8.3f} {tot[9 * n // 10]:8.3f} {st.median(d["lam"] for d in s):7.3f} '
              f'{st.median(d["rpm"] for d in s):6.0f} {st.median(d["MAP"] for d in s):5.0f} '
              f'{st.median(d["GAIR"] for d in s):6.0f} {len({d["file"] for d in s}):5d}')


show('MAF raw (GAIR)', lambda d: d['GAIR'], [0, 250, 300, 350, 400, 500, 650, 800, 1000, 1300, 1700, 2200, 3000, 4500,
                                             7000, 20000], cl)
show('MAP kPa', lambda d: d['MAP'], [0, 20, 25, 30, 35, 40, 50, 60, 70, 80, 110], cl)
show('rpm', lambda d: d['rpm'], [0, 900, 1500, 2000, 2500, 3000, 3500, 4500, 7500], cl)
show('IAT C', lambda d: d['iat'], [-40, 15, 20, 25, 30, 40], cl)
show('idle (IDLING=1, VSP=0) by file', lambda d: int(d['file'][:8] + d['file'][9:13]) if d['IDLING'] and d['VSP'] == 0
     else -1, sorted({int(d['file'][:8] + d['file'][9:13]) for d in cl}) + [10 ** 13], cl)

# model: needed fuel factor = 1 + a + b / GAIR. A fixed unmetered air leak adds b / GAIR (big at idle, ~0 at load);
# a proportional error (MAF scale, fuel pressure, injectors) is a. Least squares on the closed-loop rows.
xs = [1 / d['GAIR'] for d in cl if d['GAIR'] > 100]
ys = [d['tot'] - 1 for d in cl if d['GAIR'] > 100]
n = len(xs)
mx, my = sum(xs) / n, sum(ys) / n
b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
a = my - b * mx
res = [y - a - b * x for x, y in zip(xs, ys)]
se_b = (sum(r * r for r in res) / (n - 2) / sum((x - mx) ** 2 for x in xs)) ** 0.5
print(f'\n== fit tot - 1 = a + b / GAIR on {n} rows: a = {a:+.4f}, b = {b:+.2f} (+-{2 * se_b:.2f} at 2 sigma)')
for g in (250, 500, 1000, 3000, 6000):
    print(f'   GAIR {g:5d}: leak part {b / g:+.4f}, proportional part {a:+.4f}, total {a + b / g:+.4f}')

print('\n== LT (KLAFAVE) per file: first / last running value, engine run time (ERUNTM raw) first/last, ECT start')
for f in sorted({d['file'] for d in rows}):
    s = [d for d in rows if d['file'] == f and d['rpm'] > 400]
    if s:
        print(f'{f}: LT {s[0]["lt"]:.3f} -> {s[-1]["lt"]:.3f}  ERUNTM {s[0]["ERUNTM"]} -> {s[-1]["ERUNTM"]}  '
              f'ECT {s[0]["ect"]} -> {s[-1]["ect"]}  IAT {s[0]["iat"]} -> {s[-1]["iat"]}')
