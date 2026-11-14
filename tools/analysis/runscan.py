import csv, sys, glob
for d in sys.argv[1:]:
    for p in sorted(glob.glob(d + '/*.csv')):
        R = [r for r in csv.DictReader(open(p)) if r.get('ERUNTM') not in ('', None) and r.get('ECT') not in ('', None)]
        if not R: print(p[-19:], 'no ERUNTM'); continue
        lo = min(int(r['ERUNTM']) for r in R)
        e = [int(r['ECT']) - 40 for r in R if int(r['ERUNTM']) == lo]
        print(f"{p[-19:]} frames {len(R):5} min run {lo:5} ECT at min {e[0]:4} ECT range {min(int(r['ECT']) for r in R)-40}-{max(int(r['ECT']) for r in R)-40}")
