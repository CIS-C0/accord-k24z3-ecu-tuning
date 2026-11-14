# Lean condition: compare driving sessions at the SAME load (total correction ST x LT in warm closed loop, cmd 1.00).
# Same selection as lean.py (FSS 2, ECT >= 80, not fuel cut, cmd 1.00 +-1 %), frames deduplicated by day + HDS clock.
# Session = day + hour block (snapshots of one drive). Also prints per-file LT, fuel level, battery, rear O2, misfires.
# Usage: py -I compare_sessions.py <raw csv dir>
import csv, glob, os, sys, statistics as st

MISF = ['NMCYLOBS1', 'NMCYLOBS2', 'NMCYLOBS3', 'NMCYLOBS4']


def session(name):
    d, h = name[:8], int(name[9:11])
    return f'{d[4:8]}-{d[2:4]}-{d[0:2]} {"18h" if h == 18 and d == "30102026" else "20h" if h == 20 else f"{h}h"}'


seen, S, files = set(), {}, {}
for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.csv'))):
    name = os.path.basename(p)[:-4]
    s = session(name)
    for r in csv.DictReader(open(p)):
        key = (name[:8], r['t'])
        if key in seen or any(r[k] == '' for k in ('NE', 'ECT', 'FSS', 'FC', 'CMDEQRAT', 'KLAF', 'KLAFAVE', 'MAP',
                                                     'IDLING')):
            continue  # frames with a blank field (HDS gap) are skipped
        seen.add(key)
        files.setdefault(name, []).append(r)
        if int(r['NE']) / 4 > 400 and int(r['ECT']) - 40 >= 80 and int(r['FSS']) == 2 and not int(r['FC']) \
                and r['CMDEQRAT'] != '65535' and abs(int(r['CMDEQRAT']) / 32768 - 1) < 0.01:
            S.setdefault(s, []).append(r)


def tot(r):
    return int(r['KLAF']) * int(r['KLAFAVE']) / 16384


bins = [('idle', lambda r: int(r['IDLING']) == 1),
        ('MAP<30 rolling', lambda r: not int(r['IDLING']) and int(r['MAP']) < 30),
        ('MAP 30-45', lambda r: 30 <= int(r['MAP']) < 45),
        ('MAP 45-70', lambda r: 45 <= int(r['MAP']) < 70),
        ('MAP>=70', lambda r: int(r['MAP']) >= 70),
        ('all', lambda r: True)]
print('== total correction (ST x LT) median [n] by session and load')
print(f'{"":16}' + ''.join(f'{s:>22}' for s in S))
for name, f in bins:
    line = f'{name:16}'
    for s, v in S.items():
        t = [tot(r) for r in v if f(r)]
        line += f'{st.median(t):>15.3f} [{len(t):4d}]' if len(t) >= 15 else f'{"-":>15} [{len(t):4d}]'
    print(line)
print('\n== session context (closed-loop rows): medians')
for s, v in S.items():
    g = lambda k: st.median(int(r[k]) for r in v)
    print(f'{s}: ST {g("KLAF") / 128:.3f} LT {g("KLAFAVE") / 128:.3f} ST max {max(int(r["KLAF"]) for r in v) / 128:.3f} '
          f'IAT {g("IAT") - 40} ECT {g("ECT") - 40} BARO {g("BARO")} VB {g("VB") / 10:.1f} FLEVELF {g("FLEVELF")} '
          f'SVO2 {g("SVO2")}')
print('\n== per file: LT first -> last, fuel level, misfire counters max, running rows')
for name, v in files.items():
    run = [r for r in v if int(r['NE']) > 1600]
    if not run:
        print(f'{name}: engine not running')
        continue
    mis = ' '.join(f'c{i + 1}={max(int(r[k]) for r in v if r[k] != "")}' for i, k in enumerate(MISF))
    print(f'{name}: LT {int(run[0]["KLAFAVE"]) / 128:.3f} -> {int(run[-1]["KLAFAVE"]) / 128:.3f}  '
          f'ECT {int(run[0]["ECT"]) - 40}->{int(run[-1]["ECT"]) - 40}  FLEVELF {st.median(int(r["FLEVELF"]) for r in run if r["FLEVELF"] != ""):.0f}  '
          f'{mis}  rows {len(run)}')
