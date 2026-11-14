# Pedal response per condition for several logs (v1 baseline, v2, v3), same pedal scale (14543 = 100 %).
# Tip-in lag = ana2.py method (target 90 % time - pedal 90 % time). Lift-off = time from pedal 0 to FCDEC (decel
# fuel cut), mapsettle.py selection for moving lift-offs, ana2.py selection for stopped blips.
# compare_versions.py v1=2026-10-25_baseline\all.csv v2=2026-10-30_v2\all.csv v3=2026-10-30_v3\all.csv > out.json
import csv, json, statistics as st, sys

APPMAX = 14543.0


def load(path):
    R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(path))]
    for r in R:
        r['rpm'] /= 4
    return R


def tipins(R):
    out, last = [], -10
    for k in range(1, len(R) - 60):
        a0, a1 = R[k - 1]['app_raw'], R[k]['app_raw']
        if not (a0 < 0.03 * APPMAX and a1 > a0 + 0.02 * APPMAX and R[k]['t_s'] - last > 3):
            continue
        t0 = R[k - 1]['t_s']
        w = [r for r in R[k - 1:k + 79] if r['t_s'] - t0 <= 2.5]
        peak = max(r['app_raw'] for r in w)
        if peak < 0.25 * APPMAX:
            continue
        ip = max(range(len(w)), key=lambda i: w[i]['app_raw'])
        cut = next((i for i in range(ip, len(w)) if w[i]['app_raw'] < 0.5 * peak), len(w))
        w = w[:cut]
        tg0, tgm = w[0]['tgt_deg'], max(r['tgt_deg'] for r in w)
        ta = next(r['t_s'] for r in w if r['app_raw'] >= 0.9 * peak) - t0
        tt = next((r['t_s'] for r in w if r['tgt_deg'] >= tg0 + 0.9 * (tgm - tg0)), None)
        if tt is None:
            continue
        kmh, pct = w[0]['kmh'], 100 * peak / APPMAX
        if kmh < 1:
            cond = 'tip_stopped'
        elif kmh < 10:
            cond = 'tip_creep'
        elif pct < 50:
            cond = 'tip_light'
        else:
            cond = 'tip_big'
        out.append({'cond': cond, 't': round(t0, 2), 'kmh': kmh, 'rpm': round(w[0]['rpm']), 'pedal': round(pct),
                    'v': round(tt - t0 - ta, 3)})
        last = t0
    return out


def liftoffs(R):
    out = []
    for i in range(1, len(R)):     # moving, mapsettle.py selection
        r, p = R[i], R[i - 1]
        if not (100 * p['app_raw'] / APPMAX > 10 and r['app_raw'] == 0 and r['rpm'] > 1800 and r['kmh'] > 0):
            continue
        t0 = r['t_s']
        win = [x for x in R[i - 1:] if x['t_s'] - t0 < 3]
        fc = next((x['t_s'] - t0 for x in win if x['fcdec'] == 1), None)
        back = next((x['t_s'] - t0 for x in win if x['app_raw'] > 0 and x['t_s'] > t0), None)
        if fc is None or (back is not None and back < fc):
            continue
        out.append({'cond': 'lift_high' if r['rpm'] > 4000 else 'lift_low', 't': round(t0, 2), 'kmh': r['kmh'],
                    'rpm': round(r['rpm']), 'v': round(fc, 3)})
    last = -10                       # stopped blips, ana2.py selection
    for k in range(1, len(R) - 60):
        if not (R[k - 1]['app_raw'] > 0.15 * APPMAX and R[k]['app_raw'] < 0.02 * APPMAX and R[k - 1]['rpm'] > 2500
                and R[k]['t_s'] - last > 3 and R[k - 1]['kmh'] == 0):
            continue
        t0 = R[k - 1]['t_s']
        w = [r for r in R[k - 1:k + 79] if r['t_s'] - t0 <= 3]
        fcd = next((r['t_s'] - t0 for r in w if r['fcdec'] >= 1), None)
        if fcd is not None:
            out.append({'cond': 'lift_stopped', 't': round(t0, 2), 'kmh': 0, 'rpm': round(R[k - 1]['rpm']),
                        'v': round(fcd, 3)})
        last = R[k]['t_s']
    return out


res = {}
for arg in sys.argv[1:]:
    name, path = arg.split('=', 1)
    R = load(path)
    ev = tipins(R) + liftoffs(R)
    summ = {}
    for c in sorted({e['cond'] for e in ev}):
        v = [e['v'] for e in ev if e['cond'] == c]
        summ[c] = {'n': len(v), 'median': round(st.median(v), 3), 'min': min(v), 'max': max(v)}
    res[name] = {'summary': summ, 'events': ev}
    print(name, json.dumps(summ), file=sys.stderr)
print(json.dumps(res))
