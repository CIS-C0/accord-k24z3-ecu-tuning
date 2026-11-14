import csv, sys, glob, os, statistics as st
# Compare knock retard between log groups, frames deduplicated, same operating cells.
# Usage: py -I knock_cmp.py label=dir[,filter] ...
def load(d, flt):
    seen, R = set(), []
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        n = os.path.basename(p)[:-4]
        if flt and not n.startswith(flt): continue
        for r in csv.DictReader(open(p)):
            if r.get('NE') in ('', None) or r.get('KNRTD') in ('', None): continue
            k = (n[:8], r['t'])
            if k in seen: continue
            seen.add(k); r['_d'] = n[:8]; R.append(r)
    R.sort(key=lambda r: (r['_d'], int(r['t'])))
    return R
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
def warm(r): return (I(r, 'ECT') or 0) >= 115
def pl(r): return warm(r) and (I(r, 'MAP') or 0) >= 45 and 1300 <= I(r, 'NE') / 4 <= 3500
def line(name, F):
    if not F: print(f'  {name:24} n 0'); return
    k = [I(r, 'KNRTD') for r in F]; s = sorted(k)
    ig = [(I(r, 'IG') - 128) / 2 for r in F if I(r, 'IG') is not None]
    print(f'  {name:24} n {len(k):5} >0 {100*sum(1 for x in k if x)/len(k):4.0f}% mean {st.mean(k):5.2f} p95 {s[len(s)*19//20]:3} max {s[-1]:3} IG med {st.median(ig):5.1f}')
def events(R):
    # event = KNRTD leaves 0, peak until it is back to 0 (gap > 1 s closes it)
    ev, cur, pt = [], None, None
    for r in R:
        t, k = int(r['t']), I(r, 'KNRTD')
        if pt is not None and t - pt > 1000 and cur is not None: ev.append(cur); cur = None
        pt = t
        if k and cur is None: cur = dict(peak=k, ne=I(r, 'NE') / 4, map=I(r, 'MAP'), iat=I(r, 'IAT'), t0=t, t1=t)
        elif k: cur['peak'] = max(cur['peak'], k); cur['t1'] = t
        elif cur is not None: ev.append(cur); cur = None
    if cur: ev.append(cur)
    return ev
for a in sys.argv[1:]:
    label, rest = a.split('=', 1)
    d, _, flt = rest.partition(',')
    R = load(d, flt)
    W = [r for r in R if warm(r)]; P = [r for r in R if pl(r)]
    iat = sorted(I(r, 'IAT') - 40 for r in R if I(r, 'IAT') is not None)
    print(f'\n=== {label}: frames {len(R)} warm {len(W)} partload {len(P)} IAT {iat[0]}..{iat[-1]} med {st.median(iat)}')
    line('part load all', P)
    for lo, hi in ((1300, 1800), (1800, 2500), (2500, 3500)):
        for ml, mh in ((45, 60), (60, 80), (80, 200)):
            line(f'{lo}-{hi} MAP {ml}-{mh}', [r for r in P if lo <= I(r, 'NE') / 4 < hi and ml <= I(r, 'MAP') < mh])
    for il, ih in ((0, 15), (15, 25), (25, 35), (35, 60)):
        line(f'IAT {il}-{ih}', [r for r in P if il <= I(r, 'IAT') - 40 < ih])
    line('WOT MAP>=90 >3500', [r for r in W if (I(r, 'MAP') or 0) >= 90 and I(r, 'NE') / 4 > 3500])
    ev = events(W)
    pk = sorted(e['peak'] for e in ev)
    mins = len(P) * 0.057 / 60
    if pk:
        print(f'  events {len(ev)} peak med {st.median(pk)} p90 {pk[len(pk)*9//10]} max {pk[-1]} | >=10: {sum(1 for x in pk if x>=10)} >=20: {sum(1 for x in pk if x>=20)} | per partload min {len(ev)/max(mins,.01):.1f}')
    kr = sorted(I(r, 'KIGKREF') for r in R if I(r, 'KIGKREF') is not None)
    print(f'  KIGKREF {kr[0]}..{kr[-1]} med {st.median(kr)}')
    for c, f in (('KLAF', 128), ('KLAFAVE', 128)):
        v = [I(r, c) / f for r in W if I(r, c) is not None and I(r, 'FSS') == 2]
        if v: print(f'  {c} CL warm med {st.median(v):.3f}')
    v = [I(r, 'VB') / 10 for r in W if I(r, 'VB') is not None and I(r, 'NE') > 2400]
    if v: print(f'  VB running {min(v):.1f}..{max(v):.1f}')
    e = [I(r, 'ECT') - 40 for r in R if I(r, 'ECT') is not None]
    print(f'  ECT {min(e)}..{max(e)}')
    for c in ('DCAM', 'NCAM', 'NMCYLOBS1', 'NMCYLOBS2', 'NMCYLOBS3', 'NMCYLOBS4'):
        print(f'  {c} {sorted({r.get(c) for r in R})}', end='')
    print()
