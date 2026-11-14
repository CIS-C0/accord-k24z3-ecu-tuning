import csv, glob, os, sys, statistics as st
for name, pat in (('v3', sys.argv[1] + '/01112026_15*.csv'), ('v5', sys.argv[2] + '/*.csv'), ('v6', sys.argv[3] + '/*.csv'), ('super', sys.argv[4] + '/*.csv')):
    R = []
    for p in glob.glob(pat): R += [r for r in csv.DictReader(open(p)) if r.get('NE') not in ('', None)]
    m = lambda c: st.median(float(r[c]) for r in R if r.get(c) not in ('', None))
    print(name, {c: m(c) for c in ('FLEVELF', 'FLI', 'IAT', 'BARO', 'VB', 'PTANK')})
