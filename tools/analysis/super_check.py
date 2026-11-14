import csv, sys, glob, os, statistics as st
# usage: py -I super_check.py <raw dir> <raw_v5 dir> <raw_v6 dir> <raw_super dir>
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
            if r.get('NE') in ('', None) or r.get('KNRTD') in ('', None): continue
            k = (n[:8], r['t'])
            if k in seen: continue
            seen.add(k); r['_f'] = n; R.append(r)
    R.sort(key=lambda r: (r['_f'][:8], int(r['t'])))
    return R
G = {'stock intake 30/10': load(raw, '30102026'), 'stock intake 25/10': load(raw, '25102026'),
     'Amazon v3 1/11': load(raw, '01112026'), 'v6 87': load(rv6), 'super': load(rsup)}
warm = lambda r: (I(r, 'ECT') or 0) >= 115
print('== A. KNRTD at equal KIGKREF, warm, 1300-3500 rpm')
cells = (('MAP 45-60', 45, 60), ('MAP 60-80', 60, 80), ('MAP 80+', 80, 200))
for name in ('stock intake 25/10', 'stock intake 30/10', 'Amazon v3 1/11', 'v6 87', 'super'):
    for lo, hi in ((90, 110), (110, 120), (120, 130), (130, 150)):
        s = f'{name:20} KIGKREF {lo}-{hi-1}:'
        for cn, a, b in cells:
            F = [I(r, 'KNRTD') for r in G[name] if warm(r) and 1300 <= I(r, 'NE') / 4 <= 3500 and a <= (I(r, 'MAP') or 0) < b
                 and I(r, 'KIGKREF') is not None and lo <= I(r, 'KIGKREF') < hi]
            s += f'  {cn} n {len(F):4} mean {st.mean(F) if F else 0:5.1f} >0 {100*sum(1 for x in F if x)/max(1,len(F)):3.0f}%'
        print(s)
print('\n== B. KIGKREF timeline today (per 30 s), KNRTD mean/max, ECT, IAT')
R = G['super']; t0 = int(R[0]['t']); b = {}
for r in R: b.setdefault((r['_f'], (int(r['t']) - t0) // 30000), []).append(r)
for k in sorted(b, key=lambda x: x[1]):
    F = b[k]; kr = [I(r, 'KIGKREF') for r in F if I(r, 'KIGKREF') is not None]; kn = [I(r, 'KNRTD') for r in F]
    if not kr: continue
    print(f"{k[1]*30:5}s KIGKREF {kr[0]:3}->{kr[-1]:3} KNRTD mean {st.mean(kn):5.1f} max {max(kn):2} ECT {I(F[-1],'ECT')-40} IAT {I(F[-1],'IAT')-40} rpm max {max(I(r,'NE') for r in F)/4:.0f} MAP max {max(I(r,'MAP') or 0 for r in F)}")
print('\n== C. fuel trim vs purge (warm closed loop)')
for name in ('v6 87', 'super'):
    cl = [r for r in G[name] if warm(r) and I(r, 'FSS') == 2 and I(r, 'KLAF') is not None and I(r, 'DPCS') is not None and not I(r, 'FC')]
    for lab, f in (('DPCS 0', lambda x: x == 0), ('DPCS >0', lambda x: x > 0)):
        F = [r for r in cl if f(I(r, 'DPCS'))]
        if F: print(f"{name:8} {lab:8} n {len(F):5} ST {st.median(I(r,'KLAF')/128 for r in F):.3f} LT {st.median(I(r,'KLAFAVE')/128 for r in F):.3f} DPCS med {st.median(I(r,'DPCS') for r in F)}")
print('\n== D. AFM at same rpm/MAP, steady cruise warm (median), IAT med')
def steady(R):
    out = []
    for i in range(3, len(R) - 3):
        a, m, z = R[i - 3], R[i], R[i + 3]
        if None in (I(a, 'MAP'), I(m, 'MAP'), I(z, 'MAP'), I(m, 'AFM')) or not warm(m) or I(m, 'FSS') != 2: continue
        if abs(I(a, 'MAP') - I(z, 'MAP')) <= 2 and abs(I(a, 'NE') - I(z, 'NE')) <= 200 and abs(int(a['t']) - int(z['t'])) < 600: out.append(m)
    return out
S = {k: steady(v) for k, v in G.items()}
names = ('stock intake 25/10', 'stock intake 30/10', 'Amazon v3 1/11', 'v6 87', 'super')
print(f"{'cell':18}" + ''.join(f'{n[:18]:>20}' for n in names))
for rl in (1500, 2000, 2500, 3000):
    for ml in (25, 30, 35, 40, 45, 50):
        s, any_ = f'{rl}-{rl+500} MAP {ml}-{ml+5}', 0
        s = f'{s:18}'
        for n in names:
            F = [r for r in S[n] if rl <= I(r, 'NE') / 4 < rl + 500 and ml <= I(r, 'MAP') < ml + 5]
            if len(F) >= 8: s += f"{st.median(I(r,'AFM') for r in F):9.0f} ({len(F):3},{st.median(I(r,'IAT')-40 for r in F):3.0f}C)"; any_ = 1
            else: s += f"{'-':>20}"
        if any_: print(s)
print('\n== E. WOT lambda / cmd (MAP>=90, open loop)')
for name in ('v6 87', 'super'):
    for lo, hi in ((3000, 4000), (4000, 5000), (5000, 6000), (6000, 7000)):
        F = [r for r in G[name] if warm(r) and (I(r, 'MAP') or 0) >= 90 and I(r, 'FSS') == 4 and lo <= I(r, 'NE') / 4 < hi and I(r, 'LAMBDA') not in (None, 65535)]
        if F: print(f"{name:8} {lo}-{hi} n {len(F):4} lambda {st.median(I(r,'LAMBDA')/32768 for r in F):.3f} cmd {st.median(I(r,'CMDEQRAT')/32768 for r in F):.3f} IG {st.median((I(r,'IG')-128)/2 for r in F):.1f} KNRTD {st.median(I(r,'KNRTD') for r in F)}")
print('\n== F. first frames today'); r = G['super'][0]
print({c: r.get(c) for c in ('t', 'ECT', 'IAT', 'KIGKREF', 'KLAF', 'KLAFAVE', 'FSS', 'VB', 'MAP')})
