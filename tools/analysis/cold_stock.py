import csv, sys, glob, os
for p in sorted(glob.glob(sys.argv[1] + '/25102026*.csv')):
    rd = csv.DictReader(open(p)); r0 = next(rd, None)
    if r0 is None or r0.get('ERUNTM') not in ('0', '1', '2', '3'): continue
    print(os.path.basename(p), 'first ERUNTM', r0.get('ERUNTM'), 'ECT', int(r0['ECT']) - 40)
    print('t_s ERUNTM ECT rpm VSP FSS lambda cmd ST LT DPCS')
    nxt, first2 = 0, None
    for r in [r0] + list(rd):
        if r.get('NE') in ('', None): continue
        t = int(r['t'])
        if r['FSS'] == '2' and first2 is None: first2 = (t / 1000, r['ERUNTM'], int(r['ECT']) - 40)
        if t >= nxt and t < 130000:
            l, c = int(r['LAMBDA']), int(r['CMDEQRAT'])
            print(t // 1000, r['ERUNTM'], int(r['ECT']) - 40, int(r['NE']) // 4, r['VSP'], r['FSS'], 'na' if l == 65535 else round(l / 32768, 3), 'na' if c == 65535 else round(c / 32768, 3), round(int(r['KLAF']) / 128, 3), round(int(r['KLAFAVE']) / 128, 3), r['DPCS'])
            nxt = t + 10000
    print('first closed loop frame (t_s, ERUNTM, ECT):', first2)
    break
