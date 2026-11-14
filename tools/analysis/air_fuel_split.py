import csv, sys, glob, statistics as st
# Where does the new ~16 % excess come from? Compare, at the same operating points, three things per log group:
#  MAF reading per speed-density air (MAP x rpm / T): rises if the MAF reads more air than before
#  commanded fuel per speed-density air (TOUT x rpm / air): falls if each ms of injection now brings more fuel
#  total correction with purge closed (DPCS 0), by load: a fixed extra amount shows mostly at idle, a % shows everywhere
# GAIR of v5/v6 is the stock-table value x1.15 below A/D 376 (by design), so it is divided by 1.15 to compare the sensor.
raw, rv5, rv6, rsup, rcold = sys.argv[1:6]
G = [('25/10 stock', glob.glob(raw + '/25102026*.csv'), 1.0), ('30/10 v1-v3', glob.glob(raw + '/30102026*.csv'), 1.0),
     ('1/11 v3 new pump', glob.glob(raw + '/01112026*.csv'), 1.0), ('1/11 v5', glob.glob(rv5 + '/*.csv'), 1.15),
     ('1/11 v6', glob.glob(rv6 + '/*.csv'), 1.15), ('7/11 super', glob.glob(rsup + '/*.csv'), 1.15), ('7/11 cold', glob.glob(rcold + '/*.csv'), 1.15)]
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
need = ('NE', 'MAP', 'IAT', 'ECT', 'AFM', 'GAIR', 'TOUT', 'KLAF', 'KLAFAVE', 'FSS', 'FC', 'DPCS', 'VB', 'VSP')
data = {}
for n, fs, k in G:
    R, seen = [], set()
    for p in sorted(fs):
        for r in csv.DictReader(open(p)):
            if any(r.get(c) in ('', None) for c in need): continue
            key = (p[-19:-8], r['t'])
            if key in seen: continue
            seen.add(key); R.append(r)
    data[n] = (R, k)
def pts(R, k, cond):
    out = []
    for r in R:
        if r['FSS'] != '2' or r['FC'] != '0' or not cond(r): continue
        rpm = I(r, 'NE') / 4; air = I(r, 'MAP') * rpm / (I(r, 'IAT') - 40 + 273)
        if air <= 0 or I(r, 'TOUT') <= 0: continue
        out.append(dict(rpm=rpm, map=I(r, 'MAP'), iat=I(r, 'IAT') - 40, afm=I(r, 'AFM'), gair=I(r, 'GAIR') / k, tout=I(r, 'TOUT'), vb=I(r, 'VB') / 10,
                        maf_sd=I(r, 'GAIR') / k / air, fuel_sd=I(r, 'TOUT') * rpm / air, corr=I(r, 'KLAF') * I(r, 'KLAFAVE') / 16384, dpcs=I(r, 'DPCS')))
    return out
zones = [('warm idle 700-900 rpm', lambda r: I(r, 'ECT') >= 120 and I(r, 'VSP') == 0 and 2800 <= I(r, 'NE') <= 3600),
         ('warm cruise 1800-2600, MAP 35-55', lambda r: I(r, 'ECT') >= 120 and I(r, 'VSP') > 20 and 7200 <= I(r, 'NE') <= 10400 and 35 <= I(r, 'MAP') <= 55),
         ('warm load 2500-4000, MAP 60-85', lambda r: I(r, 'ECT') >= 120 and 10000 <= I(r, 'NE') <= 16000 and 60 <= I(r, 'MAP') <= 85),
         ('cold idle ECT 20-55, 1100-1600 rpm', lambda r: 60 <= I(r, 'ECT') < 95 and I(r, 'VSP') == 0 and 4400 <= I(r, 'NE') <= 6400)]
m = lambda x: st.median(x) if x else float('nan')
for zl, cond in zones:
    print(f'\n== {zl}  (purge closed only: DPCS 0)')
    print(f"{'group':18} {'n':>5} {'rpm':>5} {'MAP':>4} {'IAT':>4} {'VB':>5} {'AFM':>5} {'GAIR/k':>7} {'TOUT':>6} | {'MAF/sd':>7} {'fuel/sd':>8} {'corr':>6} | rel. to stock: MAF/sd fuel/sd corr")
    base = None
    for n, (R, k) in data.items():
        P = [p for p in pts(R, k, cond) if p['dpcs'] == 0 or len(sys.argv) > 6]
        if len(P) < 30: print(f'{n:18} {len(P):5}  too few'); continue
        a, b, c = m([p['maf_sd'] for p in P]), m([p['fuel_sd'] for p in P]), m([p['corr'] for p in P])
        if base is None and n == '25/10 stock': base = (a, b, c)
        rel = (f'{a/base[0]:6.3f} {b/base[1]:7.3f} {c/base[2]:6.3f}' if base else '') + f" | DPCS med {m([p['dpcs'] for p in P]):.0f}"
        print(f"{n:18} {len(P):5} {m([p['rpm'] for p in P]):5.0f} {m([p['map'] for p in P]):4.0f} {m([p['iat'] for p in P]):4.0f} {m([p['vb'] for p in P]):5.1f} {m([p['afm'] for p in P]):5.0f} {m([p['gair'] for p in P]):7.0f} {m([p['tout'] for p in P]):6.0f} | {a:7.4f} {b:8.2f} {c:6.3f} | {rel}")
