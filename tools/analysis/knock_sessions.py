import csv, sys, glob, os, statistics as st
# knock retard per file: frames, frames KNRTD>0 among warm part-load (MAP>=45, rpm 1300-3500), max, KIGKREF range,
# IAT, also CMP counters, to compare v6 with older sessions
for d in sys.argv[1:]:
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        R = [r for r in csv.DictReader(open(p)) if r.get('NE') not in ('', None) and r.get('KNRTD') not in ('', None)]
        if not R: continue
        I = lambda r, c: int(r[c]) if r.get(c) not in ('', None) else None
        pl = [r for r in R if (I(r, 'MAP') or 0) >= 45 and 1300 <= I(r, 'NE') / 4 <= 3500 and (I(r, 'ECT') or 0) >= 115]
        k = [I(r, 'KNRTD') for r in R]
        kr = sorted({I(r, 'KIGKREF') for r in R if I(r, 'KIGKREF') is not None})
        iat = [I(r, 'IAT') - 40 for r in R if I(r, 'IAT') is not None]
        kpl = [I(r, 'KNRTD') for r in pl]
        print(f"{os.path.basename(p)[:-4]:22} n {len(R):5} KNRTD>0 {sum(1 for x in k if x):4} max {max(k):2} | partload n {len(pl):4} "
              f"KNRTD>0 {sum(1 for x in kpl if x):4} ({100*sum(1 for x in kpl if x)/max(1,len(pl)):3.0f}%) | KIGKREF {kr[0] if kr else ''}-{kr[-1] if kr else ''} "
              f"IAT {min(iat)}-{max(iat)} DCAM {sorted({r.get('DCAM') for r in R})} NCAM {sorted({r.get('NCAM') for r in R})}")
