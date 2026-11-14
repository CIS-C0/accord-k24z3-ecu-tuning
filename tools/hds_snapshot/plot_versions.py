# Line charts (SVG, no library) of compare_versions.py output: one line per version, x = condition.
# plot_versions.py compare_v1_v2_v3.json out.svg
import json, sys
from html import escape

D = json.load(open(sys.argv[1], encoding='utf-8-sig'))   # PowerShell > writes a BOM
VER = [('v1', 'v1 (stock pedal, cut delay 80)'), ('v2', 'v2 (tip-in x2, cut delay 40)'), ('v3', 'v3 (tip-in x2, cut delay 20)')]
PANELS = [
    ("Lift-off -> fuel cut (median, lower = more direct)",
     [('lift_low', ['Moving', '< 4000 rpm']), ('lift_high', ['Moving', '> 4000 rpm']),
      ('lift_stopped', ['Stopped', '(neutral)'])]),
    ('Pedal pressed -> throttle follows (median delay, lower = more direct)',
     [('tip_light', ['Moving,', 'light pedal']), ('tip_big', ['Moving,', 'pedal > 50 %']),
      ('tip_stopped', ['Stopped', '(neutral)']), ('tip_creep', ['Pull-away < 10 km/h', '(clutch, not', 'a real delay)'])]),
]
COL = ['#888780', '#eb6834', '#2a78d6']
DASH = ['6,4', '', '']
W, PH, L, R, T = 640, 470, 60, 20, 50
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{PH * len(PANELS)}" viewBox="0 0 {W} {PH * len(PANELS)}" '
       f'font-family="Segoe UI, Arial, sans-serif"><rect width="100%" height="100%" fill="#ffffff"/>']
for p, (title, conds) in enumerate(PANELS):
    y0 = p * PH
    top, bot = y0 + T + 25, y0 + PH - 135
    vmax = max(D[v]['summary'][c]['median'] for c, _ in conds for v, _ in VER)
    ymax = max(0.2, round(vmax * 1.15 + 0.05, 1))
    step = (W - L - R) / len(conds)
    X = lambda i: L + step * (i + 0.5)
    Y = lambda v: bot - (bot - top) * v / ymax
    out.append(f'<text x="10" y="{y0 + 28}" font-size="15" fill="#222">{escape(title)}</text>')
    for j, (v, name) in enumerate(VER):   # legend above the chart
        lx, ly = 10 + j * 195, y0 + 52
        out.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 25}" y2="{ly}" stroke="{COL[j]}" stroke-width="3" '
                   f'stroke-dasharray="{DASH[j]}"/>')
        out.append(f'<text x="{lx + 31}" y="{ly + 4}" font-size="12" fill="#333">{escape(name)}</text>')
    for k in range(6):
        v = ymax * k / 5
        out.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W - R}" y2="{Y(v):.1f}" stroke="#e1e0d9"/>')
        out.append(f'<text x="{L - 8}" y="{Y(v) + 4:.1f}" font-size="12" fill="#666" text-anchor="end">{v:.2f} s</text>')
    for i, (c, lines) in enumerate(conds):
        for m, s in enumerate(lines):
            out.append(f'<text x="{X(i):.1f}" y="{bot + 20 + m * 15}" font-size="12" fill="#444" '
                       f'text-anchor="middle">{escape(s)}</text>')
    labels = {i: [] for i in range(len(conds))}
    for j, (v, name) in enumerate(VER):
        pts = [(X(i), Y(D[v]['summary'][c]['median']), D[v]['summary'][c]) for i, (c, _) in enumerate(conds)]
        out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)}" fill="none" '
                   f'stroke="{COL[j]}" stroke-width="3" stroke-dasharray="{DASH[j]}" stroke-linejoin="round"/>')
        for i, (x, y, s) in enumerate(pts):
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{COL[j]}" stroke="#fff" stroke-width="2"/>')
            labels[i].append([y, x, s, j])
    for i, lab in labels.items():      # values under each condition name, one colored line per version
        for y, x, s, j in lab:
            out.append(f'<text x="{x:.1f}" y="{bot + 72 + j * 15}" font-size="12" fill="{COL[j]}" text-anchor="middle">'
                       f'{VER[j][0]}: {s["median"]:.2f} s <tspan fill="#999">(n{s["n"]})</tspan></text>')
out.append('</svg>')
open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(out))
print('written', sys.argv[2])
