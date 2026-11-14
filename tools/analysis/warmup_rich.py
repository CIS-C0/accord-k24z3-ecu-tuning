import csv, sys, glob, os, statistics as st
from collections import Counter
# measured vs commanded mixture during warm-up and on tip-in, before / after the MAF change (flash #4, 2026-11-01 16:32)
raw, rv5, rv6, rsup = sys.argv[1:5]
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
def lam(r, c='LAMBDA'):
    v = I(r, c)
    return None if v in (None, 65535) else v / 32768
def load(fs):
    seen, R = set(), []
    for p in sorted(fs):
        n = os.path.basename(p)[:-4]
        for r in csv.DictReader(open(p)):
            if r.get('NE') in ('', None) or r.get('ECT') in ('', None): continue
            k = (n[:11], r['t'])
            if k in seen: continue
            seen.add(k); r['_f'] = n[:11]; r['_n'] = n; R.append(r)
    R.sort(key=lambda r: (r['_f'], int(r['t'])))
    return R
G = {'25/10 stock': load(glob.glob(raw + '/25102026*.csv')), '30/10 v1-v3': load(glob.glob(raw + '/30102026*.csv')),
     '1/11 v3': load(glob.glob(raw + '/01112026*.csv')), '1/11 v5': load(glob.glob(rv5 + '/*.csv')),
     '1/11 v6': load(glob.glob(rv6 + '/*.csv')), '7/11 v6 super': load(glob.glob(rsup + '/*.csv'))}
print('== sessions: first frame (lowest temperatures available)')
for n, R in G.items():
    for ses in sorted({r['_f'] for r in R}):
        P = [r for r in R if r['_f'] == ses]
        e = [I(r, 'ECT') - 40 for r in P]
        print(f"{n:14} {ses} frames {len(P):6} ECT first {e[0]:3} min {min(e):3} max {max(e):3} ERUNTM first {P[0].get('ERUNTM')} FSS {dict(Counter(r.get('FSS') for r in P))}")
print('\n== warm-up by ECT band: all frames with engine running, no fuel cut')
print(f"{'group':14} {'ECT':7} {'n':>5} {'FSS':22} {'lambda':>6} {'cmd':>6} {'meas/cmd':>8} {'ST':>5} {'LT':>5} | idle (VSP 0, <1300 rpm): n lambda cmd meas/cmd rpm")
for n, R in G.items():
    for lo, hi in ((0, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 200)):
        F = [r for r in R if lo <= I(r, 'ECT') - 40 < hi and I(r, 'NE') > 1600 and not I(r, 'FC') and lam(r) and lam(r, 'CMDEQRAT')]
        if not F: continue
        m = lambda x: st.median(x) if x else 0
        A = [lam(r) for r in F]; C = [lam(r, 'CMDEQRAT') for r in F]
        D = [r for r in F if (I(r, 'VSP') or 0) == 0 and I(r, 'NE') / 4 < 1300]
        print(f"{n:14} {lo:3}-{hi:3} {len(F):5} {str(dict(Counter(r['FSS'] for r in F))):22} {m(A):6.3f} {m(C):6.3f} {m([a/c for a,c in zip(A,C)]):8.3f} {m([I(r,'KLAF')/128 for r in F if I(r,'KLAF') is not None]):5.3f} {m([I(r,'KLAFAVE')/128 for r in F if I(r,'KLAFAVE') is not None]):5.3f} | {len(D):5} {m([lam(r) for r in D]):6.3f} {m([lam(r,'CMDEQRAT') for r in D]):6.3f} {m([lam(r)/lam(r,'CMDEQRAT') for r in D]):8.3f} {m([I(r,'NE')/4 for r in D]):5.0f}")
print('\n== tip-in, ECT >= 80 C: MAP up >= 15 kPa within 0.5 s from MAP <= 60, lowest lambda in the next 1.5 s (no fuel cut), sensor lag included')
for n, R in G.items():
    ev, last = [], -9999
    for i, a in enumerate(R):
        if I(a, 'ECT') - 40 < 80 or (I(a, 'MAP') or 99) > 60 or I(a, 'FC') or not lam(a): continue
        t0 = int(a['t'])
        if t0 - last < 3000: continue
        j = i + 1; hit = False; L = []
        while j < len(R) and R[j]['_f'] == a['_f'] and int(R[j]['t']) - t0 <= 1500:
            b = R[j]; dt = int(b['t']) - t0
            if dt <= 500 and (I(b, 'MAP') or 0) - I(a, 'MAP') >= 15: hit = True
            if lam(b) and not I(b, 'FC'): L.append(lam(b))
            j += 1
        if hit and L: ev.append((lam(a), min(L))); last = t0
    if ev: print(f"{n:14} events {len(ev):3} lambda before {st.median(e[0] for e in ev):.3f} lowest {st.median(e[1] for e in ev):.3f} (p10 {sorted(e[1] for e in ev)[len(ev)//10]:.3f}) share below 0.90: {100*sum(1 for e in ev if e[1]<.90)/len(ev):.0f}%")
    else: print(f'{n:14} events 0')
