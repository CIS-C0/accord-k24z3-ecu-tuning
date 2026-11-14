# Merges all snapshot CSVs (overlapping 3-min windows, same HDS session clock) into one timeline, scaled.
import csv, os, sys
d = sys.argv[1]
rows = {}
for f in sorted(os.listdir(d)):
    if not f.endswith('.csv') or f.startswith('all'):
        continue
    for r in csv.DictReader(open(os.path.join(d, f))):
        rows[int(r['t'])] = r
ts = sorted(rows)
gaps = [(ts[k], ts[k + 1] - ts[k]) for k in range(len(ts) - 1) if ts[k + 1] - ts[k] > 500]
print('frames', len(ts), 'span s', (ts[-1] - ts[0]) / 1000, 'gaps >0.5s', [(round(a / 1000, 1), b) for a, b in gaps])
with open(os.path.join(d, 'all.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['t_s', 'rpm', 'kmh', 'ect_c', 'map_kpa', 'ig_deg', 'app_raw', 'th_deg', 'tgt_deg', 'idle_tgt_deg', 'fc',
                'fcdec'])
    for t in ts:
        r = rows[t]
        if r['NE'] == '':
            continue
        w.writerow([t / 1000, r['NE'], r['VSP'], int(r['ECT']) - 40, r['MAP'], (int(r['IG']) - 128) / 2, r['APP'],
                    int(r['THVLV']) / 200, int(r['THTGT']) / 200, int(r['THIDL']) / 200, r['FC'], r['FCDEC']])
