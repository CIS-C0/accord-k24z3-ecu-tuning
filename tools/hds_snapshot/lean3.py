# Lean condition, part 3: every open-loop enrichment event (command < 0.95), frame by frame, with knock retard,
# ignition, MAF raw, A/F lambda vs command (lambda lags the command by the transport delay: look at the held part).
# Usage: py -I lean3.py <raw csv dir>
import csv, glob, os, sys

for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.csv'))):
    rows = []
    for r in csv.DictReader(open(p)):
        try:
            rows.append({k: int(r[k]) for k in ('t', 'NE', 'VSP', 'ECT', 'IAT', 'MAP', 'GAIR', 'KLAF', 'KLAFAVE', 'LAMBDA',
                                                 'CMDEQRAT', 'FC', 'FSS', 'SVO2', 'TOUT', 'APP', 'KNRTD', 'IG', 'NGP',
                                                 'VB', 'VTS')})
        except ValueError:
            pass
    idx = [i for i, d in enumerate(rows) if d['CMDEQRAT'] != 65535 and d['CMDEQRAT'] < 0.95 * 32768 and not d['FC']]
    if not idx:
        continue
    shown = set()
    for i in idx:
        if i in shown:
            continue
        a, b = max(0, i - 8), min(len(rows), i + 40)
        print(f'--- {os.path.basename(p)[:-4]} frames {a}-{b}')
        print('    t_ms   rpm kmh gear MAP  GAIR APP   cmd   lam lam/cmd   ST    LT  IG  KNRTD VTS SVO2 TOUT   VB')
        for j in range(a, b):
            d = rows[j]
            shown.add(j)
            lam = d['LAMBDA'] / 32768 if d['LAMBDA'] != 65535 else float('nan')
            cmd = d['CMDEQRAT'] / 32768 if d['CMDEQRAT'] != 65535 else float('nan')
            print(f'{d["t"]:8d} {d["NE"] / 4:5.0f} {d["VSP"]:3d} {d["NGP"]:4d} {d["MAP"]:3d} {d["GAIR"]:5d} {d["APP"]:5d} '
                  f'{cmd:5.3f} {lam:5.3f} {lam / cmd if cmd == cmd else float("nan"):7.3f} {d["KLAF"] / 128:5.3f} '
                  f'{d["KLAFAVE"] / 128:5.3f} {(d["IG"] - 128) / 2:4.1f} {d["KNRTD"]:5d} {d["VTS"]:3d} {d["SVO2"]:4d} '
                  f'{d["TOUT"]:5d} {d["VB"] / 10:4.1f}{"  FC" if d["FC"] else ""}')
