# For every lift-off (pedal > 10 % then 0) list: speed, time since the speed last became 0, time to FCDEC.
# stops.py all.csv
import csv, sys
R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(sys.argv[1]))]
appmax = max(r['app_raw'] for r in R)
last_moving = None
for i in range(1, len(R)):
    r, p = R[i], R[i - 1]
    if r['kmh'] > 0:
        last_moving = r['t_s']
    if 100 * p['app_raw'] / appmax > 10 and r['app_raw'] == 0 and r['rpm'] / 4 > 1800:
        t0 = r['t_s']
        fc = next((x['t_s'] - t0 for x in R[i:] if x['t_s'] - t0 < 3 and x['fcdec'] == 1), None)
        back = next((x['t_s'] - t0 for x in R[i:] if x['t_s'] - t0 < 3 and x['app_raw'] > 0), None)
        since = None if r['kmh'] > 0 or last_moving is None else t0 - last_moving
        print(f"{t0:8.2f} kmh {r['kmh']:3.0f} rpm {r['rpm']/4:5.0f} stopped_for {since if since is None else round(since, 2)}"
              f" fcdec_after {fc if fc is None else round(fc, 2)} pedal_back {back if back is None else round(back, 2)}")
