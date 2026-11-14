import csv, sys
R = [r for r in csv.DictReader(open(sys.argv[1])) if r.get('NE') not in ('', None)]
nxt = 0
print('t_s ERUNTM ECT IAT rpm VSP FSS lambda cmd ST LT TCAT DPCS MAP')
for r in R:
    t = int(r['t'])
    if t >= nxt:
        l = int(r['LAMBDA']); c = int(r['CMDEQRAT'])
        print(t // 1000, r['ERUNTM'], int(r['ECT']) - 40, int(r['IAT']) - 40, int(r['NE']) // 4, r['VSP'], r['FSS'], 'na' if l == 65535 else round(l / 32768, 3), 'na' if c == 65535 else round(c / 32768, 3), round(int(r['KLAF']) / 128, 3), round(int(r['KLAFAVE']) / 128, 3), r['TCAT'], r['DPCS'], r['MAP'])
        nxt = t + 10000
