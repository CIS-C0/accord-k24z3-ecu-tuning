# rpm = raw/4 (same as ECU 3E30 = RPM x 4). Tip-in lag summary + lift-off (rev hang) events.
# ana2.py all.csv [both|tip|lift] [t_min s, default 1000] [pedal raw for 100 %, default = max in the log]
# (the 2026-10-25 baseline max is 14543: pass it to compare other logs with the same % thresholds)
import csv, sys, statistics as st
R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(sys.argv[1]))]
R = [r for r in R if r['t_s'] > (float(sys.argv[3]) if len(sys.argv) > 3 else 1000)]
for r in R:
    r['rpm'] /= 4
appmax = float(sys.argv[4]) if len(sys.argv) > 4 else max(r['app_raw'] for r in R)
mode = sys.argv[2] if len(sys.argv) > 2 else 'both'


def win(k, dur):
    t0 = R[k]['t_s']
    return [r for r in R[k:k + 80] if r['t_s'] - t0 <= dur]


if mode in ('both', 'tip'):
    print('=== TIP-IN: lag = time target reaches 90 % of its rise  minus  time pedal reaches 90 % of its rise ===')
    groups = {'stopped': [], 'moving': []}
    last = -10
    for k in range(1, len(R) - 60):
        a0, a1 = R[k - 1]['app_raw'], R[k]['app_raw']
        if not (a0 < 0.03 * appmax and a1 > a0 + 0.02 * appmax and R[k]['t_s'] - last > 3):
            continue
        w = win(k - 1, 2.5)
        peak = max(r['app_raw'] for r in w)
        if peak < 0.25 * appmax:
            continue
        # stop the window when the pedal is released again (below 50 % of peak after the peak)
        ip = max(range(len(w)), key=lambda i: w[i]['app_raw'])
        cut = next((i for i in range(ip, len(w)) if w[i]['app_raw'] < 0.5 * peak), len(w))
        w = w[:cut]
        t0 = w[0]['t_s']
        tg0, tgm = w[0]['tgt_deg'], max(r['tgt_deg'] for r in w)
        ta = next(r['t_s'] for r in w if r['app_raw'] >= 0.9 * peak) - t0
        tt = next((r['t_s'] for r in w if r['tgt_deg'] >= tg0 + 0.9 * (tgm - tg0)), None)
        th = next((r['t_s'] for r in w if r['th_deg'] >= tg0 + 0.9 * (tgm - tg0)), None)
        if tt is None:
            continue
        tt -= t0
        g = 'stopped' if w[0]['kmh'] < 5 else 'moving'
        groups[g].append(tt - ta)
        print(f"{t0:8.2f} {g:7} {w[0]['kmh']:3.0f} km/h {w[0]['rpm']:5.0f} rpm pedal {100*peak/appmax:3.0f}%  "
              f"target {tg0:4.1f}->{tgm:4.1f} deg  pedal90 {ta:.2f}s target90 {tt:.2f}s  LAG {tt-ta:+.2f}s"
              f"  throttle90 {'-' if th is None else f'{th-t0:.2f}'}s")
        last = t0
    for g, v in groups.items():
        if v:
            print(f"{g}: n={len(v)} median lag {st.median(v):+.2f}s  min {min(v):+.2f}  max {max(v):+.2f}")

if mode in ('both', 'lift'):
    print('\n=== LIFT-OFF: pedal from > 15 % to 0 at > 2500 rpm ===')
    last = -10
    for k in range(1, len(R) - 60):
        if not (R[k - 1]['app_raw'] > 0.15 * appmax and R[k]['app_raw'] < 0.02 * appmax and R[k - 1]['rpm'] > 2500
                and R[k]['t_s'] - last > 3):
            continue
        w = win(k - 1, 3.0)
        t0, n0 = w[0]['t_s'], w[0]['rpm']
        def at(dt):
            r = min(w, key=lambda r: abs(r['t_s'] - t0 - dt))
            return r
        # throttle target back near idle target
        tid = next((r['t_s'] - t0 for r in w if r['tgt_deg'] <= r['idle_tgt_deg'] + 0.5), None)
        fcd = next((r['t_s'] - t0 for r in w if r['fcdec'] >= 1), None)
        fc = next((r['t_s'] - t0 for r in w if r['fc'] >= 1), None)
        line = ' '.join(f"{at(d)['rpm']:5.0f}" for d in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0))
        igs = ' '.join(f"{at(d)['ig_deg']:5.1f}" for d in (0, 0.25, 0.5, 1.0))
        print(f"{t0:8.2f} {w[0]['kmh']:3.0f}km/h rpm {n0:5.0f} -> [.25 .5 .75 1 1.5 2s] {line} | kmh@1s {at(1)['kmh']:3.0f}"
              f" | tgt {w[0]['tgt_deg']:4.1f}->idle@{tid if tid is None else round(tid,2)}s"
              f" | FCDEC@{fcd if fcd is None else round(fcd,2)} FC@{fc if fc is None else round(fc,2)} | IG {igs}"
              f" | MAP@0.5 {at(0.5)['map_kpa']:.0f} | ECT {w[0]['ect_c']:.0f}")
        last = t0
