import csv, sys, glob, statistics as st
# Purge effect: warm closed loop, short-term correction (KLAF) and total correction by purge duty (DPCS) bins, per log group.
# Loaded canister -> ST falls more when the purge opens. Also: ST in the first 20 s after each purge opening.
raw, rv5, rv6, rsup = sys.argv[1:5]
G = [('25/10 stock', glob.glob(raw + '/25102026*.csv')), ('30/10 v1-v3', glob.glob(raw + '/30102026*.csv')),
     ('1/11 v3', glob.glob(raw + '/01112026*.csv')), ('1/11 v5', glob.glob(rv5 + '/*.csv')),
     ('1/11 v6', glob.glob(rv6 + '/*.csv')), ('7/11 super', glob.glob(rsup + '/*.csv'))]
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
bins = [(0, 0), (1, 60), (61, 120), (121, 200), (201, 255)]
m = lambda x: f'{st.median(x):.3f}' if len(x) >= 20 else '  -  '
print('warm (ECT>=80 C) closed loop, no fuel cut. ST = KLAF/128 median, n in brackets, by DPCS bin; idle = VSP 0 and 600-1000 rpm')
for zone, zc in (('idle', lambda r: I(r, 'VSP') == 0 and 2400 <= I(r, 'NE') <= 4000), ('driving', lambda r: I(r, 'VSP') > 15)):
    print(f'\n== {zone}')
    print(f"{'group':12} " + ' '.join(f'{f"DPCS {a}-{b}":>18}' for a, b in bins) + '   LT med')
    for n, fs in G:
        R, seen = [], set()
        for p in sorted(fs):
            for r in csv.DictReader(open(p)):
                if any(r.get(c) in ('', None) for c in ('KLAF', 'KLAFAVE', 'DPCS', 'FSS', 'FC', 'ECT', 'NE', 'VSP')): continue
                k = (p[-19:-8], r['t'])
                if k in seen: continue
                seen.add(k)
                if r['FSS'] == '2' and r['FC'] == '0' and I(r, 'ECT') >= 120 and zc(r): R.append(r)
        cells = []
        for a, b in bins:
            x = [I(r, 'KLAF') / 128 for r in R if a <= I(r, 'DPCS') <= b]
            cells.append(f'{m(x)} [{len(x):5}]')
        print(f'{n:12} ' + ' '.join(f'{c:>18}' for c in cells) + f"   {m([I(r, 'KLAFAVE') / 128 for r in R])}")
