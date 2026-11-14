import csv, glob, sys
R = []
for p in sorted(glob.glob(sys.argv[1] + '/*.csv')): R += [r for r in csv.DictReader(open(p)) if r.get('NE') not in ('', None)]
for c in ('CMFIRE', 'MFCYL', 'NMFACYL1', 'NMFACYL2', 'NMFACYL3', 'NMFACYL4', 'NMFBCYL1', 'NMFBCYL2', 'NMFBCYL3', 'NMFBCYL4', 'DPCS', 'VB', 'FLI', 'TCAT', 'KIGKREF', 'KNRTD'):
    v = [int(r[c]) for r in R if r.get(c) not in ('', None)]
    print(c, 'min', min(v), 'max', max(v), 'last', v[-1])
