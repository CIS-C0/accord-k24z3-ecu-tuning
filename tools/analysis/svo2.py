import csv, glob, sys, statistics as st
# rear oxygen sensor (after the catalyst) in warm closed loop: arbitrates whether the front sensor tells the truth
raw, rv5, rv6, rsup, rcold = sys.argv[1:6]
G = {'25/10 stock': glob.glob(raw + '/25102026*.csv'), '30/10 v1-v3': glob.glob(raw + '/30102026*.csv'), '1/11 v3': glob.glob(raw + '/01112026*.csv'),
     '1/11 v5': glob.glob(rv5 + '/*.csv'), '1/11 v6': glob.glob(rv6 + '/*.csv'), '7/11 super': glob.glob(rsup + '/*.csv'), '7/11 cold': glob.glob(rcold + '/*.csv')}
for n, fs in G.items():
    R = []
    for p in fs: R += [r for r in csv.DictReader(open(p)) if r.get('NE') not in ('', None) and r.get('SVO2') not in ('', None)]
    for lab, lo, hi in (('ECT>=80', 120, 999), ('ECT<55', 0, 95)):
        F = [r for r in R if r['FSS'] == '2' and r['FC'] == '0' and lo <= int(r['ECT']) < hi and int(r['NE']) > 2400]
        if not F: continue
        v = sorted(int(r['SVO2']) for r in F)
        idle = [int(r['SVO2']) for r in F if r['VSP'] == '0']
        print(f"{n:12} {lab:7} n {len(v):6} SVO2 raw p10 {v[len(v)//10]:4} median {st.median(v):6.1f} p90 {v[len(v)*9//10]:4} | idle median {st.median(idle) if idle else 0:6.1f} | total corr {st.median(int(r['KLAF'])*int(r['KLAFAVE'])/16384 for r in F):.3f}")
