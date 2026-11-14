# find runs of increasing 16-bit words (MAF curve candidates: long, convex, from small to large values)
import struct, sys
b = open(sys.argv[1], 'rb').read()
R = 0x8000
n = len(b) // 2
for off in (0, 1):
    pass
w = struct.unpack('>%dH' % n, b[:2 * n])
i = 0
while i < n - 1:
    j = i
    while j + 1 < n and w[j + 1] > w[j]:
        j += 1
    L = j - i + 1
    if L >= 20 and w[j] >= 5000 and w[i] < 500:
        seg = w[i:j + 1]
        d = [seg[k + 1] - seg[k] for k in range(L - 1)]
        conv = sum(1 for k in range(len(d) - 1) if d[k + 1] >= d[k]) / max(1, len(d) - 1)
        print(f'0x{2 * i + R:06X} len {L} {seg[0]}..{seg[-1]} convex {conv:.2f}')
        print('   ', list(seg))
    i = j + 1
