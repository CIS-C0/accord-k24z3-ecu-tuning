import csv, sys, glob, os, statistics as st
seen = set(); R = []
for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.csv'))):
    n = os.path.basename(p)[:-4]
    for r in csv.DictReader(open(p)):
        if (n[:8], r['t']) in seen or r['NE'] == '': continue
        seen.add((n[:8], r['t'])); r['_f'] = n; R.append(r)
R.sort(key=lambda r: int(r['t'])); t0 = int(R[0]['t'])
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
def ok(r, *cs): return all(I(r, c) is not None for c in cs)
T = lambda r: (I(r, 't') - t0) / 1000
print('frames', len(R), 'span', T(R[-1]))

print('\n== knock: changes of KNRTD/KIGKREF')
prev = None; n = 0
for r in R:
    if not ok(r, 'KNRTD', 'KIGKREF'): continue
    k = (r['KNRTD'], r['KIGKREF'])
    if k != prev and n < 60:
        lam = r.get('LAMBDA', '')
        lam = 'n/a' if lam in ('', '65535') else f"{int(lam)/32768:.3f}"
        ig = I(r, 'IG'); ig = '' if ig is None else f'{(ig-128)/2:5.1f}'
        print(f"{T(r):7.2f}s rpm {I(r,'NE')/4:5.0f} MAP {r['MAP']:>3} THO {r.get('THO','')} KNRTD {r['KNRTD']:>2} KIGKREF {r['KIGKREF']} IG {ig} FSS {r['FSS']} lam {lam} IAT {r['IAT']} ECT {r['ECT']}")
        n += 1
    prev = k
kn = [r for r in R if (I(r, 'KNRTD') or 0) > 0]
print('frames KNRTD>0:', len(kn), 'of', len(R))

def stat(name, vals):
    vals = [v for v in vals if v is not None]
    if not vals: print(name, 'no data'); return
    q = sorted(vals)
    print(f'{name}: n {len(q)} min {q[0]:.2f} p5 {q[len(q)//20]:.2f} med {st.median(q):.2f} p95 {q[len(q)*19//20]:.2f} max {q[-1]:.2f}')

print('\n== VTC: angle - cmd (all running, and steady |dcmd|<=1 over 0.3 s)')
stat('VTC err all', [I(r,'VTCANGL')-I(r,'VTCCMD') for r in R if ok(r,'VTCANGL','VTCCMD')])
st_err = []
for i in range(5, len(R)):
    a, b = R[i-5], R[i]
    if ok(a,'VTCCMD') and ok(b,'VTCCMD','VTCANGL') and I(b,'t')-I(a,'t') < 600 and abs(I(b,'VTCCMD')-I(a,'VTCCMD')) <= 1:
        st_err.append(I(b,'VTCANGL')-I(b,'VTCCMD'))
stat('VTC err steady', st_err)
stat('VTCCMD', [I(r,'VTCCMD') for r in R]); stat('VTCANGL', [I(r,'VTCANGL') for r in R])
stat('VTCANGL idle', [I(r,'VTCANGL') for r in R if I(r,'IDLING') == 1])

print('\n== throttle')
stat('THO-THICMD', [I(r,'THO')-I(r,'THICMD') for r in R if ok(r,'THO','THICMD')])
stat('TH-1+TH-2', [I(r,'TH-1')+I(r,'TH-2') for r in R if ok(r,'TH-1','TH-2')])
stat('TH-2-TH-1', [I(r,'TH-2')-I(r,'TH-1') for r in R if ok(r,'TH-1','TH-2')])
stat('APPS1/APPS2', [I(r,'APPS1')/I(r,'APPS2') for r in R if ok(r,'APPS1','APPS2') and I(r,'APPS2')])
stat('APPS1-2*APPS2', [I(r,'APPS1')-2*I(r,'APPS2') for r in R if ok(r,'APPS1','APPS2')])
print('APPS1/APPS2 at extremes:', sorted({(I(r,'APPS1'),I(r,'APPS2')) for r in R if ok(r,'APPS1','APPS2')})[:5], '...', sorted({(I(r,'APPS1'),I(r,'APPS2')) for r in R if ok(r,'APPS1','APPS2')})[-5:])
print('TH-1/TH-2 extremes:', sorted({(I(r,'TH-1'),I(r,'TH-2')) for r in R if ok(r,'TH-1','TH-2')})[:4], sorted({(I(r,'TH-1'),I(r,'TH-2')) for r in R if ok(r,'TH-1','TH-2')})[-4:])
stat('MDUTYF idle', [I(r,'MDUTYF') for r in R if I(r,'IDLING') == 1])

print('\n== rear O2 SVO2 (closed loop, warm, not idle, not fuel cut)')
cl = [r for r in R if ok(r,'SVO2','FSS','FC','ECT') and I(r,'FSS') == 2 and not I(r,'FC') and I(r,'ECT') >= 120]
stat('SVO2 CL', [I(r,'SVO2') for r in cl])
stat('SVO2 idle', [I(r,'SVO2') for r in cl if I(r,'IDLING') == 1])
stat('SVO2 fuelcut', [I(r,'SVO2') for r in R if ok(r,'SVO2','FC') and I(r,'FC')])
stat('SVO2 OL', [I(r,'SVO2') for r in R if ok(r,'SVO2','FSS') and I(r,'FSS') == 4])
stat('SVO2DI', [I(r,'SVO2DI') for r in R])
stat('TCAT', [I(r,'TCAT') for r in R])
print('DOCAT values', sorted({r.get('DOCAT') for r in R}))

print('\n== cooling: ECT vs ECT2 (radiator), fan')
stat('ECT C', [I(r,'ECT')-40 for r in R if ok(r,'ECT')])
stat('ECT2 raw TW2', [I(r,'TW2') for r in R]); stat('ECT2A raw', [I(r,'ECT2A') for r in R])
prev = None
for r in R:
    k = (r.get('FANH'), r.get('FANL'))
    if k != prev:
        print(f"{T(r):7.2f}s FANH {k[0]} FANL {k[1]} ECT {I(r,'ECT')-40 if ok(r,'ECT') else ''} ECT2A {r.get('ECT2A')} TW2 {r.get('TW2')} rpm {I(r,'NE')/4:.0f} VSP {r.get('VSP')} ACC {r.get('ACC', r.get('MCS'))}")
        prev = k

print('\n== electrical')
stat('VB', [I(r,'VB')/10 for r in R if ok(r,'VB')])
stat('VB idle', [I(r,'VB')/10 for r in R if ok(r,'VB') and I(r,'IDLING') == 1])
stat('ELD', [I(r,'ELD') for r in R]); stat('ACGF', [I(r,'ACGF') for r in R])

print('\n== VTEC: VTS vs PSW/RVTS/VTM transitions')
prev = None; c = 0
for r in R:
    k = tuple(r.get(x) for x in ('VTS','PSW','RVTS','VTM'))
    if k != prev and c < 40:
        print(f"{T(r):7.2f}s VTS {k[0]} PSW {k[1]} RVTS {k[2]} VTM {k[3]} rpm {I(r,'NE')/4:.0f} MAP {r['MAP']}")
        c += 1
    prev = k

print('\n== AF sensor / heaters / EVAP')
for c_ in ('AFRAC','AFVAD','AFCAD','DAFHT','DSO2HT','ISO2HT','XILAF','PTANK','EVAPVP','DPCS','ELOAD','BARO','IAT','TA'):
    stat(c_, [I(r,c_) for r in R])
print('\n== counters')
for c_ in ('DCAM','NCAM','DCTDC','DCCRK','NACTDC','NACCRK','NMCYLOBS1','NMCYLOBS2','NMCYLOBS3','NMCYLOBS4'):
    print(c_, sorted({r.get(c_) for r in R}))
