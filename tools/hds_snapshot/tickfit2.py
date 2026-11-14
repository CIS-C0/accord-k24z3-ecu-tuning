# Joint fit of the decel fuel cut delay over several logs with different gear 1-3 tick counts (stock 80, v2 40):
#   time:  delay = a + N * t        crank: delay = a + N * p * 30/mean_rpm
# tickfit2.py baseline\all.csv:80 v2\all.csv:40 v3\all.csv:20:20
#   (optional 3rd field = N above 4000 rpm, default 40 = cap 0xB150; v3 has 20 everywhere)
import csv, sys
ev = []
for arg in sys.argv[1:]:
    parts = arg.split(':')
    if len(parts) > 2 and len(parts[-2]) <= 3 and parts[-2].isdigit():
        path, n13, nhigh = ':'.join(parts[:-2]), parts[-2], int(parts[-1])
    else:
        path, n13, nhigh = ':'.join(parts[:-1]), parts[-1], 40
    R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(path))]
    appmax = max(r['app_raw'] for r in R)
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
            ev.append((path[-25:], t0, r['rpm'] / 4, sum(rpm) / len(rpm), fc, nhigh if r['rpm'] / 4 > 4000 else int(n13)))


def fit(f):
    best = None
    for a10 in range(0, 81):
        a = a10 / 100
        for p in [x / 10000 for x in range(10, 400)]:
            e = sum((a + f(n, rm, p) - d) ** 2 for _, _, _, rm, d, n in ev)
            if best is None or e < best[0]:
                best = (e, a, p)
    return best


for name, f in (('time', lambda n, rm, p: n * p), ('crank', lambda n, rm, p: n * p * 30 * 100 / rm)):
    e, a, p = fit(f)
    print(f'{name}: a = {a:.2f} s, param = {p:.4f}, rms = {(e / len(ev)) ** 0.5:.3f} s, n = {len(ev)}')
    for src, t0, r0, rm, d, n in ev:
        print(f'   {src} {t0:8.2f} N {n} rpm0 {r0:5.0f} mean {rm:5.0f} delay {d:.2f} model {a + f(n, rm, p):.2f}')
