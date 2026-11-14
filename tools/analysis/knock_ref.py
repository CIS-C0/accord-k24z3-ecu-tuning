import csv, sys, glob, os, statistics as st
# How KNRTD follows KIGKREF: per file, high-load floor of KNRTD against KIGKREF, and fuel trims
def I(r, c):
    v = r.get(c, '')
    return None if v in ('', None) else int(v)
B = {}
print('file                 KIGKREF  ECT    IAT   | WOTn KNmin KNmed KNmax IGmed | PLn KNmean | KLAF KLAFAVE(CL warm) PURGE-ish')
for d in sys.argv[1:]:
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        R = [r for r in csv.DictReader(open(p)) if I(r, 'NE') is not None and I(r, 'KNRTD') is not None and I(r, 'KIGKREF') is not None]
        if not R: continue
        n = os.path.basename(p)[:-4]
        W = [r for r in R if (I(r, 'ECT') or 0) >= 115 and (I(r, 'MAP') or 0) >= 90 and I(r, 'NE') / 4 > 3500]
        P = [r for r in R if (I(r, 'ECT') or 0) >= 115 and (I(r, 'MAP') or 0) >= 45 and 1300 <= I(r, 'NE') / 4 <= 3500]
        for r in W:
            B.setdefault(I(r, 'KIGKREF') // 10 * 10, []).append(I(r, 'KNRTD'))
        kr = [I(r, 'KIGKREF') for r in R]
        e = [I(r, 'ECT') - 40 for r in R if I(r, 'ECT') is not None]
        ia = [I(r, 'IAT') - 40 for r in R if I(r, 'IAT') is not None]
        cl = [r for r in R if I(r, 'FSS') == 2 and (I(r, 'ECT') or 0) >= 115]
        kl = [I(r, 'KLAF') / 128 for r in cl if I(r, 'KLAF') is not None]
        ka = [I(r, 'KLAFAVE') / 128 for r in cl if I(r, 'KLAFAVE') is not None]
        s = f'{n:20} {min(kr):3}-{max(kr):3} {min(e):3}-{max(e):3} {min(ia):3}-{max(ia):3} |'
        if W:
            k = [I(r, 'KNRTD') for r in W]; ig = [(I(r, 'IG') - 128) / 2 for r in W]
            s += f' {len(W):4} {min(k):3} {st.median(k):5.1f} {max(k):3} {st.median(ig):5.1f} |'
        else: s += '    -                      |'
        s += f' {len(P):4} {st.mean(I(r,"KNRTD") for r in P) if P else 0:5.1f} |'
        if kl: s += f' {st.median(kl):.3f} {st.median(ka):.3f}'
        print(s)
print('\nWOT KNRTD by KIGKREF decade:')
for k in sorted(B):
    v = B[k]; print(f'  {k:3}-{k+9:3} n {len(v):5} min {min(v)} med {st.median(v)} max {max(v)}')
