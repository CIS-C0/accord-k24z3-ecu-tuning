import csv, sys, glob, statistics as st
raw, rv5, rv6, rsup = sys.argv[1:5]
G = [('25/10 stock', glob.glob(raw + '/25102026*.csv')), ('1/11 v3', glob.glob(raw + '/01112026*.csv')), ('1/11 v5', glob.glob(rv5 + '/*.csv')), ('1/11 v6', glob.glob(rv6 + '/*.csv')), ('7/11 super', glob.glob(rsup + '/*.csv'))]
I = lambda r, c: None if r.get(c) in ('', None) else int(r[c])
for n, fs in G:
    X = []
    for p in sorted(fs):
        R = sorted([r for r in csv.DictReader(open(p)) if r.get('FSS') not in ('', None)], key=lambda r: int(r['t']))
        run = 0
        for r in R:
            ol = r['FSS'] == '4' and r.get('FC') == '0' and (I(r, 'ECT') or 0) >= 120
            run = run + 1 if ol else 0
            if run < 15: continue
            a, c = I(r, 'LAMBDA'), I(r, 'CMDEQRAT')
            if a in (None, 65535) or c in (None, 65535): continue
            X.append((a / c, c / 32768, I(r, 'NE') / 4, I(r, 'MAP'), I(r, 'KLAFAVE') / 128, I(r, 'GAIR'), I(r, 'DPCS')))
    if len(X) < 10: print(n, 'n', len(X)); continue
    md = lambda i: st.median([x[i] for x in X])
    print(f'{n:12} n {len(X):4}  meas/cmd {md(0):.3f}  cmd {md(1):.3f}  rpm {md(2):.0f}  MAP {md(3):.0f}  GAIR {md(5):.0f}  LT {md(4):.3f}  DPCS {md(6):.0f}')
