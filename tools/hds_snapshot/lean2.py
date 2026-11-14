# Lean condition, part 2: secondary O2 (SVO2, SVO2DI) by state, and measured lambda vs command in open loop.
# Usage: py -I lean2.py <raw csv dir>
import csv, glob, os, sys, statistics as st

rows, seen = [], set()
for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.csv'))):
    seq = []
    for r in csv.DictReader(open(p)):
        # snapshots saved less than 3 min apart overlap: keep each frame once (same day + HDS session clock)
        key = (os.path.basename(p)[:8], r['t'])
        if key in seen:
            continue
        seen.add(key)
        try:
            d = {k: int(r[k]) for k in ('t', 'NE', 'VSP', 'ECT', 'MAP', 'GAIR', 'KLAF', 'KLAFAVE', 'LAMBDA', 'CMDEQRAT',
                                        'FC', 'FSS', 'SVO2', 'SVO2DI', 'TOUT', 'APP', 'TCAT', 'XILAF')}
        except ValueError:
            continue
        d['file'] = os.path.basename(p)[:-4]
        seq.append(d)
    # seconds since the last fuel cut ended / since cut started, for the O2 calibration
    last_fc, fc_start = -10 ** 9, None
    for d in seq:
        if d['FC']:
            fc_start = d['t'] if fc_start is None else fc_start
            d['fc_for'] = (d['t'] - fc_start) / 1000
            last_fc = d['t']
        else:
            fc_start = None
            d['fc_for'] = None
        d['since_fc'] = (d['t'] - last_fc) / 1000
    rows += seq


def q(vs):
    vs = sorted(vs)
    n = len(vs)
    return f'n={n:5d} p10 {vs[n // 10]:6} med {vs[n // 2]:6} p90 {vs[9 * n // 10]:6}' if n else 'n=0'


warm = [d for d in rows if d['NE'] > 1600 and d['ECT'] - 40 >= 80]
print('== secondary O2 raw by state (warm, running)')
for name, sel in [
    ('fuel cut > 2 s', [d for d in warm if d['FC'] and d['fc_for'] and d['fc_for'] > 2]),
    ('closed loop FSS 2, > 5 s after fuel cut', [d for d in warm if d['FSS'] == 2 and d['since_fc'] > 5]),
    ('open loop rich cmd < 0.95 (enrichment)', [d for d in warm if d['CMDEQRAT'] != 65535 and d['CMDEQRAT'] < 0.95 * 32768
                                                 and not d['FC']]),
    ('FSS 4', [d for d in warm if d['FSS'] == 4 and not d['FC']]),
    ('FSS 1', [d for d in warm if d['FSS'] == 1 and not d['FC']]),
]:
    print(f'{name:45s} SVO2 {q([d["SVO2"] for d in sel])} | SVO2DI {q([d["SVO2DI"] for d in sel])}')

print('\n== front A/F lambda by state')
for name, sel in [
    ('fuel cut > 2 s', [d for d in warm if d['FC'] and d['fc_for'] and d['fc_for'] > 2]),
    ('closed loop FSS 2', [d for d in warm if d['FSS'] == 2 and d['since_fc'] > 5]),
]:
    print(f'{name:45s} LAMBDA {q([d["LAMBDA"] for d in sel])} | XILAF {q([d["XILAF"] for d in sel])}')

print('\n== open loop with a rich command: measured lambda / commanded (1.00 = on target, > 1 = leaner than asked)')
ol = [d for d in rows if d['ECT'] - 40 >= 80 and not d['FC'] and d['CMDEQRAT'] != 65535 and d['LAMBDA'] != 65535
      and d['CMDEQRAT'] < 0.97 * 32768]
print(len(ol), 'rows')
for lo, hi in [(0.80, 0.86), (0.86, 0.90), (0.90, 0.94), (0.94, 0.97)]:
    s = [d for d in ol if lo <= d['CMDEQRAT'] / 32768 < hi]
    if not s:
        continue
    ratio = sorted((d['LAMBDA'] / d['CMDEQRAT']) for d in s)
    n = len(ratio)
    print(f'cmd {lo:.2f}-{hi:.2f}: n={n:4d} meas/cmd p10 {ratio[n // 10]:.3f} med {ratio[n // 2]:.3f} p90 '
          f'{ratio[9 * n // 10]:.3f} | FSS {sorted({d["FSS"] for d in s})} | ST med {st.median(d["KLAF"] for d in s) / 128:.3f}'
          f' LT med {st.median(d["KLAFAVE"] for d in s) / 128:.3f} | MAP med {st.median(d["MAP"] for d in s)} '
          f'rpm med {st.median(d["NE"] for d in s) / 4:.0f} | files {len({d["file"] for d in s})}')
# steady part of enrichment only: same command for 5+ consecutive frames
print('\n== open loop, command held (5 frames same cmd +-1 %), measured/cmd')
for f in sorted({d['file'] for d in ol}):
    pass
