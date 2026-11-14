# Builds a self-contained HTML page (inline SVG) from all.csv: tip-in examples and lift-off RPM curves.
import csv, sys, html
R = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(sys.argv[1]))]
R = [r for r in R if r['t_s'] > 1000]
for r in R:
    r['rpm'] /= 4
APPMAX = max(r['app_raw'] for r in R)
for r in R:
    r['app'] = 100 * r['app_raw'] / APPMAX

W, H, L, T, B, RM = 560, 260, 46, 16, 34, 14


def seg(t0, a, b):
    return [r for r in R if t0 + a <= r['t_s'] <= t0 + b]


def chart(title, series, x0, x1, y0, y1, ylab, shade=None, vline=None, yticks=None):
    pw, ph = W - L - RM, H - T - B
    X = lambda x: L + (x - x0) / (x1 - x0) * pw
    Y = lambda y: T + ph - (y - y0) / (y1 - y0) * ph
    s = [f'<figure><figcaption>{html.escape(title)}</figcaption><svg viewBox="0 0 {W} {H}" role="img">']
    for yt in (yticks or [y0 + (y1 - y0) * i / 4 for i in range(5)]):
        s.append(f'<line class="grid" x1="{L}" x2="{W-RM}" y1="{Y(yt):.1f}" y2="{Y(yt):.1f}"/>'
                 f'<text class="tick" x="{L-6}" y="{Y(yt)+4:.1f}" text-anchor="end">{yt:g}</text>')
    xt = -int(-x0 * 2) / 2 if x0 < 0 else x0  # first multiple of 0.5 at or after x0
    while xt <= x1 + 1e-9:
        s.append(f'<text class="tick" x="{X(xt):.1f}" y="{H-B+16}" text-anchor="middle">{xt:g}</text>')
        xt = round(xt + 0.5, 3)
    s.append(f'<text class="tick" x="{W-RM}" y="{H-4}" text-anchor="end">seconds</text>'
             f'<text class="tick" x="{L}" y="{T-4}" text-anchor="start">{ylab}</text>')
    if shade:
        for a, b in shade:
            s.append(f'<rect class="shade" x="{X(a):.1f}" y="{T}" width="{max(1, X(b)-X(a)):.1f}" height="{ph}"/>')
    if vline is not None:
        s.append(f'<line class="vline" x1="{X(vline):.1f}" x2="{X(vline):.1f}" y1="{T}" y2="{T+ph}"/>')
    for name, pts, cls in series:
        d = ' '.join(f'{X(x):.1f},{Y(min(max(y, y0), y1)):.1f}' for x, y in pts)
        s.append(f'<polyline class="{cls}" points="{d}"/>')
    s.append('</svg><div class="legend">' + ''.join(
        f'<span><i class="{c}"></i>{html.escape(n)}</span>' for n, _, c in series) + '</div></figure>')
    return ''.join(s)


def tip(t0, title):
    rows = seg(t0, -0.3, 2.7)
    x = lambda r: round(r['t_s'] - t0, 3)
    return chart(title, [('APP pedal (%)', [(x(r), r['app']) for r in rows], 's1'),
                         ('Throttle target (°)', [(x(r), r['tgt_deg']) for r in rows], 's2'),
                         ('Throttle actual (°)', [(x(r), r['th_deg']) for r in rows], 's3')],
                 -0.3, 2.7, 0, 100, '% / °', vline=0)


def lift(t0, title):
    rows = seg(t0, -0.3, 2.7)
    x = lambda r: round(r['t_s'] - t0, 3)
    sh, a = [], None
    for r in rows:
        if r['fcdec'] >= 1 and a is None:
            a = x(r)
        if r['fcdec'] < 1 and a is not None:
            sh.append((a, x(r))); a = None
    if a is not None:
        sh.append((a, 2.7))
    return chart(title, [('Engine speed (rpm)', [(x(r), r['rpm']) for r in rows], 's1'),
                         ('Throttle target ×100 (°)', [(x(r), r['tgt_deg'] * 100) for r in rows], 's2')],
                 -0.3, 2.7, 0, 7000, 'rpm', shade=sh, vline=0, yticks=[0, 1000, 2000, 3000, 4000, 5000, 6000, 7000])


def overlay():
    # every lift-off: pedal > 15 % -> 0 at > 2500 rpm, aligned at the release, rpm relative to the release
    ev, last = [], -10
    for k in range(1, len(R)):
        if R[k - 1]['app'] > 15 and R[k]['app'] < 2 and R[k - 1]['rpm'] > 2500 and R[k]['t_s'] - last > 3:
            ev.append(R[k - 1]); last = R[k]['t_s']
    ser = []
    for e in ev:
        rows = seg(e['t_s'], 0, 1.2)
        cls = 'n1' if e['kmh'] < 3 else 'n2'
        ser.append(('', [(r['t_s'] - e['t_s'], r['rpm'] - e['rpm']) for r in rows], cls))
    c = chart('All pedal lift-offs (above 2500 rpm): rpm change over 1.2 s',
              ser, 0, 1.2, -1500, 1000, 'Δ rpm', yticks=[-1500, -1000, -500, 0, 500, 1000])
    return c.replace('<div class="legend"></div>',
                     '<div class="legend"><span><i class="n1"></i>Stopped, neutral</span>'
                     '<span><i class="n2"></i>Moving (clutch / gear change)</span></div>')


CSS = '''
:root{--bg:#f7f7f5;--fg:#1d1d1b;--mut:#6b6b66;--grid:#e2e2dc;--card:#fff;--c1:#2563eb;--c2:#d97706;--c3:#059669;--sh:rgba(220,38,38,.13);--n1:rgba(5,150,105,.75);--n2:rgba(220,38,38,.55)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecece8;--mut:#9a9a94;--grid:#2c2c29;--card:#1f1f1d;--c1:#60a5fa;--c2:#fbbf24;--c3:#34d399;--sh:rgba(248,113,113,.18);--n1:rgba(52,211,153,.8);--n2:rgba(248,113,113,.6)}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecece8;--mut:#9a9a94;--grid:#2c2c29;--card:#1f1f1d;--c1:#60a5fa;--c2:#fbbf24;--c3:#34d399;--sh:rgba(248,113,113,.18);--n1:rgba(52,211,153,.8);--n2:rgba(248,113,113,.6)}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px 16px}
main{max-width:1180px;margin:auto}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}
p,li{color:var(--fg)}.mut{color:var(--mut);font-size:13px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
figure{background:var(--card);border-radius:10px;margin:0;padding:12px}figcaption{font-weight:600;font-size:13px;margin-bottom:4px}
svg{width:100%;height:auto;display:block}.grid{stroke:var(--grid)}.tick{fill:var(--mut);font-size:11px}
polyline{fill:none;stroke-width:2;stroke-linejoin:round}.s1{stroke:var(--c1)}.s2{stroke:var(--c2)}.s3{stroke:var(--c3);stroke-dasharray:5 3}
.n1{stroke:var(--n1);stroke-width:1.5}.n2{stroke:var(--n2);stroke-width:1.5}
.shade{fill:var(--sh)}.vline{stroke:var(--mut);stroke-dasharray:3 3}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--mut);margin-top:4px}
.legend i{display:inline-block;width:16px;height:0;border-top:3px solid;margin-right:5px;vertical-align:middle}
.legend i.s1{border-color:var(--c1)}.legend i.s2{border-color:var(--c2)}.legend i.s3{border-color:var(--c3);border-top-style:dashed}
.legend i.n1{border-color:var(--n1)}.legend i.n2{border-color:var(--n2)}
table{border-collapse:collapse;font-size:14px;background:var(--card);border-radius:10px;overflow:hidden}td,th{padding:6px 12px;text-align:left;border-bottom:1px solid var(--grid)}
'''

body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Accord baseline log</title><style>{CSS}</style></head><body><main>
<h1>Accord 2011 K24: baseline log before flash #2</h1>
<p class="mut">HDS Snapshot, 25 October 2026, 18:14 to 18:31, stock ECU 37805-R42-A240 (after flash #1, speed limiter). One sample every 57 ms (about 17 per second). Warm engine, 84 to 90 °C. Dashed vertical line = moment the pedal moves.</p>

<h2>Summary</h2>
<table><tr><th>Measure</th><th>Stopped</th><th>Moving</th></tr>
<tr><td>Throttle target delay after the pedal (median)</td><td>0.12 s (11 events)</td><td>0.23 s (42 events), up to 1.5 s</td></tr>
<tr><td>Largest delays</td><td>-</td><td>5 to 30 km/h, 1000 to 2000 rpm, pedal 25 to 40 %</td></tr>
<tr><td>Throttle target back to idle after lift-off</td><td>0.06 s</td><td>0.23 to 0.30 s</td></tr>
<tr><td>Decel fuel cut (Fuel Cut Decel) after lift-off</td><td>0.35 s</td><td>1.2 to 1.4 s at 2500-3400 rpm, 0.75 to 0.85 s above 4200, sometimes never</td></tr>
<tr><td>RPM drop in 0.75 s after the peak (clutch in or neutral)</td><td>about 1100 rpm</td><td>100 to 450 rpm below 3400 rpm (rev hang)</td></tr></table>

<h2>Pedal delay: same input, stopped and moving</h2><div class="grid2">
{tip(1573.10, "Stopped, neutral, pedal 65 %: the throttle follows almost at once")}
{tip(1494.32, "Moving, 28 km/h, 2055 rpm, pedal 32 %: the throttle follows 1.5 s later")}
{tip(1146.67, "Moving, 28 km/h, 1856 rpm, pedal 33 %: 0.9 s delay")}
{tip(1962.66, "Moving, 27 km/h, 2608 rpm, pedal 96 %: only 0.2 s delay")}
</div>

<h2>Rev hang: rpm after lift-off (red zone = Fuel Cut Decel active)</h2><div class="grid2">
{lift(1589.91, "Stopped, neutral: the cut comes at 0.36 s, rpm drops at once")}
{lift(1402.64, "Gear change, 51 km/h: rpm stays near 3300 for 1 s, the cut comes at 1.2 s")}
{lift(1465.53, "Gear change, 28 km/h: no cut, rpm only drops when the clutch re-engages")}
{lift(1674.36, "Gear change at 5478 rpm: the cut comes at 0.83 s")}
</div>
<h2>Overview</h2><div class="grid2">{overlay()}</div>
<p class="mut">How it is read: decoded HDS .dat files (16-byte records: byte position, DID, value, time in ms). Scales checked against the HDS screen: rpm = raw / 4, ECT = raw − 40, throttle = raw / 200 °, ignition advance = (raw − 128) / 2. The pedal is shown as a percentage of the recorded maximum. The clutch is not logged; the gear is derived from the rpm / speed ratio.</p>
</main></body></html>'''
open(sys.argv[2], 'w', encoding='utf-8').write(body)
print('ok', sys.argv[2])
