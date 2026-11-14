import csv, sys, glob
# Hot restarts: engine start (ERUNTM small, first frames with NE > 0) with ECT >= 50 C. A leaking injector drips fuel
# while the engine is off, so the first seconds after a hot restart read rich (lambda < 1) more than before.
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
def lam(r, c='LAMBDA'):
    v = I(r, c)
    return None if v in (None, 65535) else v / 32768
for d in sys.argv[1:]:
    for p in sorted(glob.glob(d + '/*.csv')):
        R = [r for r in csv.DictReader(open(p)) if r.get('NE') not in ('', None) and r.get('ECT') not in ('', None)]
        R.sort(key=lambda r: int(r['t']))
        prev = None
        for i, r in enumerate(R):
            run = I(r, 'ERUNTM')
            start = run is not None and run <= 2 and I(r, 'NE') > 0 and (prev is None or prev > run or I(R[i - 1], 'NE') == 0)
            if start and I(r, 'ECT') - 40 >= 50:
                print(f'\n{p[-19:]}  start at t {int(r["t"])/1000:.1f} s, ECT {I(r, "ECT") - 40} C, IAT {I(r, "IAT") - 40} C, off before: {"yes" if i and I(R[i-1], "NE") == 0 else "?"}')
                print('  run   rpm FSS lambda  cmd    ST    LT  TOUT SVO2')
                t0 = int(r['t'])
                for q in R[i:]:
                    if int(q['t']) - t0 > 40000: break
                    if (int(q['t']) - t0) % 2000 < 260:
                        f = lambda x: '  na ' if x is None else f'{x:.3f}'
                        print(f"  {q.get('ERUNTM'):>3} {I(q, 'NE') / 4:5.0f} {q['FSS']:>3} {f(lam(q))} {f(lam(q, 'CMDEQRAT'))} {I(q, 'KLAF') / 128:5.3f} {I(q, 'KLAFAVE') / 128:5.3f} {q['TOUT']:>5} {q.get('SVO2', '')}")
            prev = run if run is not None else prev
