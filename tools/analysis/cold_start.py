import csv, sys, glob, os, statistics as st
# cold start: v6 today (18:38 session) vs the only stock cold start (25/10 18:05), every N seconds from engine start
cold, stock = sys.argv[1], sys.argv[2]
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
def lam(r, c='LAMBDA'):
    v = I(r, c)
    return None if v in (None, 65535) else v / 32768
def load(fs):
    seen, R = set(), []
    for p in sorted(fs):
        for r in csv.DictReader(open(p)):
            if r.get('NE') in ('', None) or r.get('ECT') in ('', None): continue
            if r['t'] in seen: continue
            seen.add(r['t']); R.append(r)
    R.sort(key=lambda r: int(r['t']))
    return R
def show(name, R, step):
    print(f'\n== {name}: {len(R)} frames, {int(R[0]["t"])/1000:.0f}-{int(R[-1]["t"])/1000:.0f} s')
    print('  t_s run ECT IAT  rpm VSP APP FSS lambda   cmd    ST    LT  TOUT  MAF  IG DPCS FC')
    nxt, start, first_cl, prev_run = 0, None, None, None
    for r in R:
        t = int(r['t'])
        run = I(r, 'ERUNTM')
        if start is None and I(r, 'NE') > 0: start = t
        if first_cl is None and r['FSS'] == '2': first_cl = (t / 1000, run, I(r, 'ECT') - 40)
        if t >= nxt or (prev_run is not None and run is not None and run < prev_run):
            f = lambda x: 'na' if x is None else f'{x:.3f}'
            print(f"{t/1000:5.0f} {run} {I(r,'ECT')-40:3} {I(r,'IAT')-40:3} {I(r,'NE')/4:5.0f} {r['VSP']:>3} {r['APP']:>3} {r['FSS']:>3} {f(lam(r)):>6} {f(lam(r,'CMDEQRAT')):>6} {I(r,'KLAF')/128:5.3f} {I(r,'KLAFAVE')/128:5.3f} {r['TOUT']:>5} {r['AFM']:>4} {r['IG']:>3} {r['DPCS']:>4} {r['FC']}")
            nxt = t + step
        prev_run = run
    print('  first closed loop frame (t_s, run s, ECT C):', first_cl)
    return R
C = show('v6 cold start 7/11 18:38', load(glob.glob(cold + '/*.csv')), 5000)
S = show('stock cold start 25/10 18:05', load([stock]), 5000)
print('\n== by engine run time (first 2.5 min, idle, VSP 0): open loop share, lambda, cmd, measured/cmd, total correction')
for name, R in (('v6 7/11', C), ('stock 25/10', S)):
    for lo, hi in ((0, 15), (15, 30), (30, 60), (60, 90), (90, 150)):
        F = [r for r in R if I(r, 'ERUNTM') is not None and lo <= I(r, 'ERUNTM') < hi and (I(r, 'VSP') or 0) == 0 and I(r, 'NE') > 1600]
        if not F: print(f'{name:12} run {lo:3}-{hi:3}s n 0'); continue
        A = [(lam(r), lam(r, 'CMDEQRAT')) for r in F if lam(r) and lam(r, 'CMDEQRAT')]
        m = lambda x: f'{st.median(x):.3f}' if x else '  na '
        print(f"{name:12} run {lo:3}-{hi:3}s n {len(F):4} open {100*sum(1 for r in F if r['FSS']!='2')/len(F):3.0f}% ECT {I(F[0],'ECT')-40}-{I(F[-1],'ECT')-40} lambda {m([a for a,c in A])} cmd {m([c for a,c in A])} meas/cmd {m([a/c for a,c in A])} min {min([a for a,c in A], default=0):.3f} total {m([I(r,'KLAF')*I(r,'KLAFAVE')/16384 for r in F])} TOUT {m([I(r,'TOUT') for r in F])}")
