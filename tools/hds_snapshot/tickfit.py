# Fits the decel fuel cut delay of every lift-off (pedal > 10 % then 0, moving) with two models:
#   time:  delay = a + N * t            (timer ticks at a fixed period t)
#   crank: delay = a + N * k * 30/rpm   (timer ticks once per TDC (k = 1) or every k TDC; rpm = mean during the delay)
# N = 40 above 4000 rpm (0xB150), else 80 (gears 1-3 table). Least squares on a grid; prints residuals.
# tickfit.py all.csv
import csv, sys
R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(sys.argv[1]))]
appmax = max(r['app_raw'] for r in R)
ev = []
for i in range(1, len(R)):
    r, p = R[i], R[i - 1]
    if 100 * p['app_raw'] / appmax > 10 and r['app_raw'] == 0 and r['rpm'] / 4 > 1800 and r['kmh'] > 0:
        t0 = r['t_s']
        win = [x for x in R[i:] if x['t_s'] - t0 < 3]
        fc = next((x['t_s'] - t0 for x in win if x['fcdec'] == 1), None)
        back = next((x['t_s'] - t0 for x in win if x['app_raw'] > 0), None)
        if fc is None or (back is not None and back < fc):
            continue
        rpm = [x['rpm'] / 4 for x in win if x['t_s'] - t0 <= fc]
        ev.append((t0, r['rpm'] / 4, sum(rpm) / len(rpm), fc, 40 if r['rpm'] / 4 > 4000 else 80))


def fit(f):
    best = None
    for a10 in range(0, 61):
        a = a10 / 100
        for p in [x / 10000 for x in range(10, 400)]:
            e = sum((a + f(n, rm, p) - d) ** 2 for _, _, rm, d, n in ev)
            if best is None or e < best[0]:
                best = (e, a, p)
    return best


for name, f in (('time', lambda n, rm, p: n * p), ('crank', lambda n, rm, p: n * p * 30 * 100 / rm)):
    e, a, p = fit(f)
    print(f'{name}: a = {a:.2f} s, param = {p:.4f}, rms = {(e / len(ev)) ** 0.5:.3f} s')
    for t0, r0, rm, d, n in ev:
        print(f'   {t0:8.2f} N {n} rpm0 {r0:5.0f} mean {rm:5.0f} delay {d:.2f} model {a + f(n, rm, p):.2f}')
