import csv, sys, glob, statistics as st
# Open loop (FSS 1 or 4, warm, no fuel cut): measured lambda / commanded lambda per log group. The short-term correction
# is not applied there, so a real excess of fuel per injection shows as measured richer than commanded.
# Only frames after >= MINRUN consecutive open-loop frames (sensor and transport lag), commanded lambda valid.
raw, rv5, rv6, rsup = sys.argv[1:5]
MINRUN = int(sys.argv[5]) if len(sys.argv) > 5 else 15
G = [('25/10 stock', glob.glob(raw + '/25102026*.csv')), ('30/10 v1-v3', glob.glob(raw + '/30102026*.csv')),
     ('1/11 v3', glob.glob(raw + '/01112026*.csv')), ('1/11 v5', glob.glob(rv5 + '/*.csv')),
     ('1/11 v6', glob.glob(rv6 + '/*.csv')), ('7/11 super', glob.glob(rsup + '/*.csv'))]
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
def lam(r, c):
    v = I(r, c)
    return None if v in (None, 65535) else v / 32768
m = lambda x: f'{st.median(x):.3f}' if len(x) >= 10 else '  -  '
q = lambda x, p: f'{sorted(x)[int(p * (len(x) - 1))]:.3f}' if len(x) >= 10 else '  -  '
print(f'open loop warm, after {MINRUN} consecutive open-loop frames. meas/cmd median [p25 p75] (n), cmd median, rpm, MAP, ECT, FSS mix')
for n, fs in G:
    out = {'all': [], 'cmd<0.95 (enrichment)': [], 'cmd>=0.95': []}
    info = []
    files = 0
    for p in sorted(fs):
        R = [r for r in csv.DictReader(open(p)) if r.get('FSS') not in ('', None) and r.get('NE') not in ('', None)]
        R.sort(key=lambda r: int(r['t']))
        run = 0
        for r in R:
            ol = r['FSS'] in ('1', '4') and r.get('FC') == '0' and I(r, 'ECT') is not None and I(r, 'ECT') >= 120 and I(r, 'NE') > 2400
            run = run + 1 if ol else 0
            if run < MINRUN: continue
            a, c = lam(r, 'LAMBDA'), lam(r, 'CMDEQRAT')
            if not a or not c: continue
            x = a / c
            out['all'].append(x)
            out['cmd<0.95 (enrichment)' if c < 0.95 else 'cmd>=0.95'].append(x)
            info.append((c, I(r, 'NE') / 4, I(r, 'MAP'), I(r, 'ECT') - 40, r['FSS'], p[-19:-4]))
    print(f'\n== {n}')
    for k, v in out.items():
        print(f'  {k:24} {m(v)} [{q(v, .25)} {q(v, .75)}] (n {len(v)})')
    if info:
        print(f"  cmd {st.median([i[0] for i in info]):.3f}  rpm {st.median([i[1] for i in info]):.0f}  MAP {st.median([i[2] for i in info]):.0f}  ECT {st.median([i[3] for i in info]):.0f}"
              f"  FSS1 {sum(1 for i in info if i[4] == '1')} FSS4 {sum(1 for i in info if i[4] == '4')}  files {len(set(i[5] for i in info))}")
