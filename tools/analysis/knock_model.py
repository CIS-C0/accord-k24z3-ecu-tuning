import csv, sys, glob, os, statistics as st
# 1. model test at full load: KNRTD = KIGKREF/128 * (2*map) / 5, map = 50 (no VTEC table BA14 rows 8-9, >= 1750 rpm)
# 2. KIGKREF up/down moves per warm minute (it can only go up after the knock flag raised the live reference)
raw, rv5, rv6, rsup = sys.argv[1:5]
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
def load(d, pre=''):
    seen, R = set(), []
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        n = os.path.basename(p)[:-4]
        if pre and not n.startswith(pre): continue
        for r in csv.DictReader(open(p)):
            if r.get('NE') in ('', None) or r.get('KNRTD') in ('', None) or r.get('KIGKREF') in ('', None): continue
            k = (n[:11], r['t'])
            if k in seen: continue
            seen.add(k); r['_f'] = n[:11]; R.append(r)
    R.sort(key=lambda r: (r['_f'], int(r['t'])))
    return R
G = {'25/10 stock 87': load(raw, '25102026'), '30/10 87': load(raw, '30102026'), '1/11 v3 87': load(raw, '01112026'),
     '1/11 v5 87': load(rv5), '1/11 v6 87': load(rv6), '7/11 v6 super': load(rsup)}
print('== 1. full load, MAP>=95, 2500-4800 rpm, no VTEC: KNRTD - model')
for n, R in G.items():
    F = [r for r in R if (I(r, 'MAP') or 0) >= 90 and 2500 <= I(r, 'NE') / 4 <= 4400 and (I(r, 'ECT') or 0) >= 115]
    if not F: print(f'{n:16} n 0'); continue
    E = sorted(I(r, 'KNRTD') - I(r, 'KIGKREF') * 100 / 640 for r in F)
    print(f'{n:16} n {len(E):4} excess med {st.median(E):5.1f} p10 {E[len(E)//10]:5.1f} p90 {E[len(E)*9//10]:5.1f} max {E[-1]:5.1f} | frames excess>=3: {100*sum(1 for x in E if x>=3)/len(E):3.0f}%')
print('\n== 2. KIGKREF moves')
print(f"{'group':16} warm-min(ECT>=83) load-min(MAP>=45) up-counts down-counts ups/events first last min max")
for n, R in G.items():
    up = dn = ev = epi = 0; lastup = -99999; wm = lm = 0.0; first = last = None; lo = 999; hi = 0
    for a, b in zip(R, R[1:]):
        if a['_f'] != b['_f']: continue
        dt = int(b['t']) - int(a['t'])
        if dt <= 0 or dt > 4000: continue
        if (I(b, 'ECT') or 0) >= 123:
            wm += dt / 60000
            if (I(b, 'MAP') or 0) >= 45: lm += dt / 60000
        d = I(b, 'KIGKREF') - I(a, 'KIGKREF')
        if d > 0:
            up += d; ev += 1
            if int(b['t']) - lastup > 3000: epi += 1
            lastup = int(b['t'])
        elif d < 0: dn -= d
    k = [I(r, 'KIGKREF') for r in R]
    print(f'{n:16} {wm:6.1f} {lm:6.1f}  up {up:4} down {dn:4} episodes {epi:3} | {k[0]:3} -> {k[-1]:3} range {min(k)}-{max(k)} | episodes per load-min {epi/max(lm,.01):4.1f}')
print('\n== 3. every KIGKREF rise today and on 1/11 v6 (time, rpm, MAP, KNRTD)')
for n in ('1/11 v6 87', '7/11 v6 super'):
    R = G[n]; t0 = int(R[0]['t']); c = 0
    for a, b in zip(R, R[1:]):
        if a['_f'] == b['_f'] and I(b, 'KIGKREF') > I(a, 'KIGKREF') and int(b['t']) - int(a['t']) < 4000:
            c += 1
            if c <= 12: print(f"{n} {(int(b['t'])-t0)/1000:7.1f}s {I(a,'KIGKREF')}->{I(b,'KIGKREF')} rpm {I(b,'NE')/4:.0f} MAP {b['MAP']} KNRTD {b['KNRTD']} ECT {I(b,'ECT')-40}")
    print(n, 'rises', c)
