import csv, glob, sys, math
# same test with time averaging (HDS reads 2610 and 2611 at different moments), bins of B ms, and a lag scan
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
files = []
for d in sys.argv[1:]: files += glob.glob(d + '/*.csv')
seqs = []
for p in files:
    S = []
    for r in csv.DictReader(open(p)):
        try:
            ok = r['FSS'] == '2' and r['FC'] == '0' and I(r, 'VSP') == 0 and I(r, 'ECT') >= 120 and 2800 <= I(r, 'NE') <= 3600
            air = I(r, 'MAP') * I(r, 'NE') / (I(r, 'IAT') + 233)
            S.append((int(r['t']), ok, math.log(I(r, 'KLAF') / 128), math.log(I(r, 'TOUT') * I(r, 'NE') / air), math.log(I(r, 'KLAFAVE') / 128)))
        except (TypeError, ValueError, ZeroDivisionError): S.append((int(r['t']), False, 0, 0, 0))
    seqs.append(S)
for B in (250, 1000, 3000):
    X, Y = [], []
    for S in seqs:
        bins = {}
        for t, ok, k, y, lt in S:
            if ok: bins.setdefault(t // B, []).append((k, y))
        P = [(sum(a for a, b in v) / len(v), sum(b for a, b in v) / len(v)) for v in bins.values() if len(v) >= 2]
        if len(P) < 10: continue
        mx = sum(a for a, b in P) / len(P); my = sum(b for a, b in P) / len(P)
        X += [a - mx for a, b in P]; Y += [b - my for a, b in P]
    sxx = sum(x * x for x in X); sxy = sum(x * y for x, y in zip(X, Y)); syy = sum(y * y for y in Y)
    print(f'bin {B:5} ms  n {len(X):5}  slope {sxy/sxx:.3f}  r {sxy/math.sqrt(sxx*syy):.3f}')
# lag scan on raw frames: shift TOUT by L frames relative to KLAF
for L in (-12, -6, -3, -1, 0, 1, 3, 6, 12):
    X, Y = [], []
    for S in seqs:
        Q = [(S[i][2], S[i + L][3]) for i in range(max(0, -L), min(len(S), len(S) - L)) if S[i][1] and S[i + L][1]]
        if len(Q) < 50: continue
        mx = sum(a for a, b in Q) / len(Q); my = sum(b for a, b in Q) / len(Q)
        X += [a - mx for a, b in Q]; Y += [b - my for a, b in Q]
    sxx = sum(x * x for x in X); sxy = sum(x * y for x, y in zip(X, Y)); syy = sum(y * y for y in Y)
    print(f'lag {L:3} frames  slope {sxy/sxx:.3f}  r {sxy/math.sqrt(sxx*syy):.3f}')
