import csv, glob, os, sys, statistics as st
D = sys.argv[1]
rows = []
for p in sorted(glob.glob(os.path.join(D, '*.csv'))):
    for r in csv.DictReader(open(p)):
        r['file'] = os.path.basename(p)[:-4]
        rows.append(r)
print(len(rows), 'rows')
def f(r, k):
    v = r[k]
    return int(v) if v != '' else None
keys = ['NE','VSP','ECT','TW','IAT','TA','MAP','PB','BARO','PA','AFM','GAIR','CLV','VB','TOUT','KLAF','KLAFAVE','LAMBDA','CMDEQRAT','XILAF','AFCAD','AFVAD','AFRAC','SVO2','SVO2DI','FSS','IG','KNRTD','VTCANGL','VTCCMD','ELD','ELOAD','IALSTAT','TRGIDL','DSTODO','ERUNTM','NREWR','NERAS','TW86INI','TA86INI','TCAT','IDLING','FC','FCDEC','NGP']
def pct(vs):
    vs = sorted(vs)
    n = len(vs)
    return [vs[0], vs[n//10], vs[n//2], vs[9*n//10], vs[-1]]
for name, cond in [('engine off (NE=0)', lambda r: f(r,'NE')==0),
                   ('all running', lambda r: f(r,'NE') and f(r,'NE')>0)]:
    sel = [r for r in rows if cond(r)]
    print(f'== {name}: {len(sel)} rows')
    for k in keys:
        vs = [f(r,k) for r in sel if f(r,k) is not None]
        if vs: print(f'  {k:10s} min/p10/med/p90/max {pct(vs)}')
