import csv, glob, sys, math
# Does TOUT (2610 b18-19 = RAM 0xFFFF43EE / 2) follow the short term trim KLAF? At warm idle, within each snapshot file,
# regress log(TOUT x rpm / air) on log(KLAF). Slope ~1: TOUT is the final pulse (trim applied). Slope ~0: TOUT is before trim.
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
X, Y = [], []
files = []
for d in sys.argv[1:]: files += glob.glob(d + '/*.csv')
for p in files:
    P = []
    for r in csv.DictReader(open(p)):
        try:
            if r['FSS'] != '2' or r['FC'] != '0' or I(r, 'VSP') != 0 or not (120 <= I(r, 'ECT')) or not (2800 <= I(r, 'NE') <= 3600): continue
            air = I(r, 'MAP') * I(r, 'NE') / (I(r, 'IAT') + 233)
            P.append((math.log(I(r, 'KLAF') / 128), math.log(I(r, 'TOUT') * I(r, 'NE') / air), math.log(I(r, 'GAIR') * 1.0 / air)))
        except (TypeError, ValueError, ZeroDivisionError): pass
    if len(P) < 100: continue
    mx = sum(a for a, b, c in P) / len(P); my = sum(b for a, b, c in P) / len(P)
    X += [a - mx for a, b, c in P]; Y += [b - my for a, b, c in P]
sxx = sum(x * x for x in X); sxy = sum(x * y for x, y in zip(X, Y))
slope = sxy / sxx; syy = sum(y * y for y in Y)
print(f'frames {len(X)}  KLAF spread (sd of log) {math.sqrt(sxx/len(X)):.4f}  slope TOUT-per-air vs KLAF {slope:.3f}  r {sxy/math.sqrt(sxx*syy):.3f}')
