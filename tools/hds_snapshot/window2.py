# Like window.py, plus the real throttle and the idle target: window2.py all.csv <t_s> [<t_s> ...] (-0.2 s to +2.5 s)
import csv, sys
R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(sys.argv[1]))]
appmax = max(r['app_raw'] for r in R)
for t0 in map(float, sys.argv[2:]):
    print(f'=== {t0}')
    print('   dt   rpm kmh  app%  map   th  tgt idle   ig fc fcdec')
    for r in R:
        if t0 - 0.2 <= r['t_s'] <= t0 + 2.5:
            print(f"{r['t_s']-t0:5.2f} {r['rpm']/4:5.0f} {r['kmh']:3.0f} {100*r['app_raw']/appmax:5.1f} {r['map_kpa']:4.0f}"
                  f" {r['th_deg']:4.1f} {r['tgt_deg']:4.1f} {r['idle_tgt_deg']:4.1f} {r['ig_deg']:5.1f} {r['fc']:2.0f} {r['fcdec']:2.0f}")
