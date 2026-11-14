# Decel fuel cut: the ECU sets B+0 (conditions met, delay timer starts) only when |MAP now - MAP 3 samples ago|
# (0xFFFF29F8) < 0.80 kPa (0xB1F4 = 80, 0.01 kPa). Per lift-off: time until MAP settles in the HDS log (|step| <= 1 kPa
# between two 57 ms samples, MAP is logged in whole kPa), then FCDEC time - settle time = the delay timer part.
# mapsettle.py baseline\all.csv:80 v2\all.csv:40 v3\all.csv:20:20   (same event selection as tickfit2.py;
# optional 3rd field = N above 4000 rpm, default 40)
import csv, statistics as st, sys

for arg in sys.argv[1:]:
    parts = arg.split(':')
    if len(parts) > 2 and parts[-2].isdigit():
        path, n13, nhigh = ':'.join(parts[:-2]), parts[-2], int(parts[-1])
    else:
        path, n13, nhigh = ':'.join(parts[:-1]), parts[-1], 40
    R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(path))]
    appmax = max(r['app_raw'] for r in R)
    rows = []
    for i in range(1, len(R)):
        r, p = R[i], R[i - 1]
        if not (100 * p['app_raw'] / appmax > 10 and r['app_raw'] == 0 and r['rpm'] / 4 > 1800 and r['kmh'] > 0):
            continue
        t0 = r['t_s']
        win = [x for x in R[i - 1:] if x['t_s'] - t0 < 3]
        fc = next((x['t_s'] - t0 for x in win if x['fcdec'] == 1), None)
        back = next((x['t_s'] - t0 for x in win if x['app_raw'] > 0 and x['t_s'] > t0), None)
        if fc is None or (back is not None and back < fc):
            continue
        settle = next((win[k]['t_s'] - t0 for k in range(1, len(win))
                       if win[k]['t_s'] > t0 and abs(win[k]['map_kpa'] - win[k - 1]['map_kpa']) <= 1), None)
        rpm = [x['rpm'] / 4 for x in win if 0 <= x['t_s'] - t0 <= fc]
        n = nhigh if r['rpm'] / 4 > 4000 else int(n13)
        maps = ' '.join(f"{x['map_kpa']:.0f}" for x in win if -0.06 < x['t_s'] - t0 <= fc + 0.06)
        rows.append((n, t0, sum(rpm) / len(rpm), fc, settle, maps))
    print(f'=== {path}')
    for n in sorted({x[0] for x in rows}):
        g = [x for x in rows if x[0] == n]
        for _, t0, rm, fc, s, maps in g:
            print(f'  N {n} t {t0:8.2f} mean rpm {rm:5.0f} FCDEC {fc:.2f} settle {s:.2f} after-settle {fc - s:.2f} '
                  f'| MAP {maps}')
        print(f'  N {n}: n={len(g)} median FCDEC {st.median(x[3] for x in g):.2f} settle {st.median(x[4] for x in g):.2f}'
              f' after-settle {st.median(x[3] - x[4] for x in g):.2f}')
