# Prints every HDS sample around big tip-ins (0 -> > 80 % pedal) and fast lift-offs moving, with the rpm slope
# (rpm/s, = vehicle acceleration in a fixed gear) to look for a "two step" feel.
import csv, sys
R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(sys.argv[1]))]
for r in R:
    r['rpm'] /= 4
AMAX = 14543
def show(k, before, after, title):
    t0 = R[k]['t_s']
    print(f'\n--- {title} t={t0:.2f} {R[k]["kmh"]:.0f} km/h {R[k]["rpm"]:.0f} rpm')
    print('   dt    app%   tgt    th   MAP   IG    rpm  rpm/s  kmh fcdec')
    w = [i for i in range(len(R)) if -before <= R[i]['t_s'] - t0 <= after]
    for i in w:
        r, p = R[i], R[i - 1]
        dt = r['t_s'] - p['t_s']
        sl = (r['rpm'] - p['rpm']) / dt if 0 < dt < 0.2 else 0
        print(f"{r['t_s'] - t0:6.2f} {100 * r['app_raw'] / AMAX:5.0f} {r['tgt_deg']:5.1f} {r['th_deg']:5.1f} {r['map_kpa']:4.0f}"
              f" {r['ig_deg']:5.1f} {r['rpm']:6.0f} {sl:6.0f} {r['kmh']:3.0f} {r['fcdec']:3.0f}")
if len(sys.argv) > 2:
    for t in sys.argv[2:]:
        k = min(range(len(R)), key=lambda i: abs(R[i]['t_s'] - float(t)))
        show(k, 0.3, 2.2, 'AT')
    sys.exit()
last = -10
for k in range(1, len(R)):
    a0, a1 = R[k - 1]['app_raw'] / AMAX, R[k]['app_raw'] / AMAX
    if R[k]['t_s'] - last < 4 or R[k]['kmh'] < 5:
        continue
    if a0 < 0.03 and max(r['app_raw'] for r in R[k:k + 8]) / AMAX > 0.8:
        show(k - 1, 0.2, 1.6, 'TIP-IN')
        last = R[k]['t_s']
    elif a0 > 0.4 and max(r['app_raw'] for r in R[k:k + 4]) / AMAX < 0.02:
        show(k - 1, 0.2, 1.6, 'LIFT-OFF')
        last = R[k]['t_s']
