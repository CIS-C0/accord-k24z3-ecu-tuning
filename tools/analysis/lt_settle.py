import csv, sys, glob, os, statistics as st
# long term fuel correction (KLAFAVE/128) over time: was it settled on 1/11 after flash #4 / #5, and where was it heading?
raw, rv5, rv6, rsup = sys.argv[1:5]
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
G = [('v3 87 (avant flash #4)', glob.glob(os.path.join(raw, '01112026*.csv'))), ('v5 87', glob.glob(os.path.join(rv5, '*.csv'))),
     ('v6 87', glob.glob(os.path.join(rv6, '*.csv'))), ('v6 super', glob.glob(os.path.join(rsup, '*.csv')))]
print('== per file (closed loop = FSS 2, warm = ECT raw >= 123)')
print(f"{'group':24} {'file':20} {'t0-t1 s':>13} {'n':>5} {'LT first':>8} {'LT last':>7} {'min':>5} {'max':>5} | warm CL n, LT med, ST med, ST no purge, DPCS med, ECT C first-last")
series = {}
for name, fs in G:
    seen, S = set(), []
    for p in sorted(fs):
        n = os.path.basename(p)[:-4]
        R = [r for r in csv.DictReader(open(p)) if r.get('KLAFAVE') not in ('', None) and r.get('NE') not in ('', None)]
        if not R: print(f'{name:24} {n:20} no LT'); continue
        L = [I(r, 'KLAFAVE') / 128 for r in R]
        C = [r for r in R if I(r, 'FSS') == 2 and (I(r, 'ECT') or 0) >= 123 and I(r, 'KLAF') is not None and not I(r, 'FC')]
        ts = [I(r, 'KLAF') / 128 for r in C]
        tn = [I(r, 'KLAF') / 128 for r in C if (I(r, 'DPCS') or 0) == 0]
        dp = [I(r, 'DPCS') or 0 for r in C]
        f = lambda x: f'{st.median(x):.3f}' if x else '  -  '
        print(f"{name:24} {n:20} {int(R[0]['t'])/1000:6.0f}-{int(R[-1]['t'])/1000:6.0f} {len(R):5} {L[0]:8.3f} {L[-1]:7.3f} {min(L):5.3f} {max(L):5.3f} | {len(C):5} {f([I(r,'KLAFAVE')/128 for r in C])} {f(ts)} {f(tn)} {st.median(dp) if dp else 0:5} {I(R[0],'ECT')-40}-{I(R[-1],'ECT')-40}")
        for r in R:
            k = (n[:11], r['t'])
            if k in seen: continue
            seen.add(k); S.append((n[:11], int(r['t']), I(r, 'KLAFAVE') / 128, r))
    series[name] = S
print('\n== LT every ~30 s, by session (session = date + hour of the file name)')
for name, S in series.items():
    S.sort(key=lambda x: (x[0], x[1]))
    for ses in sorted({s[0] for s in S}):
        P = [s for s in S if s[0] == ses]
        out, nxt = [], P[0][1]
        for s in P:
            if s[1] >= nxt: out.append(f'{(s[1]-P[0][1])/1000:.0f}s:{s[2]:.3f}'); nxt = s[1] + 30000
        print(f'{name:24} {ses} span {(P[-1][1]-P[0][1])/60000:.1f} min, LT {P[0][2]:.3f} -> {P[-1][2]:.3f}')
        print('   ' + ' '.join(out))
print('\n== warm closed loop LT and ST by load band')
for name, S in series.items():
    C = [s[3] for s in S if I(s[3], 'FSS') == 2 and (I(s[3], 'ECT') or 0) >= 123 and I(s[3], 'KLAF') is not None and not I(s[3], 'FC') and I(s[3], 'MAP') is not None]
    for lab, lo, hi in (('ralenti', 0, 30), ('MAP 30-45', 30, 45), ('MAP 45-70', 45, 70), ('MAP >=70', 70, 200)):
        F = [r for r in C if lo <= I(r, 'MAP') < hi]
        if F: print(f"{name:24} {lab:10} n {len(F):5} LT {st.median(I(r,'KLAFAVE')/128 for r in F):.3f} ST {st.median(I(r,'KLAF')/128 for r in F):.3f} total {st.median(I(r,'KLAFAVE')*I(r,'KLAF')/16384 for r in F):.3f}")
