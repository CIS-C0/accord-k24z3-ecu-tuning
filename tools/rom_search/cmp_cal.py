# Compares two stock calibrations: cmp_cal.py <a.rwd.gz> <b.rwd.gz> [addr_hex:words ...]
# Decrypts both (.rwd 0x5A, firmware keys from header group 5, header = file - 0xF8000 - 4), prints the differing
# ranges in the calibration area 0x8000-0x1FFFF and the words at the given CPU addresses in both files.
import gzip, struct, sys


def load(p):
    d = gzip.open(p).read() if p.endswith('.gz') else open(p, 'rb').read()
    h = len(d) - 0xF8000 - 4
    if d[:3] != b'\x5a\x0d\x0a' or h < 0:
        sys.exit('bad file ' + p)
    i, groups = 3, []
    for _ in range(6):
        n, i, g = d[i], i + 1, []
        for _ in range(n):
            g.append(d[i + 1:i + 1 + d[i]])
            i += 1 + d[i]
        groups.append(g)
    k0, k1, k2 = b''.join(groups[5])  # group index 5 = firmware keys (same as FirmwareValidator H5)
    print(p, 'firmware keys', bytes((k0, k1, k2)).hex(' '))
    return bytes((((e ^ k2) + k1) - k0) & 0xFF for e in d[h:h + 0xF8000])


a, b = load(sys.argv[1]), load(sys.argv[2])
print('sum mod 256:', sum(a) % 256, sum(b) % 256, '| part numbers:', a.count(b'37805-R42-A2'), b.count(b'37805-R42-A2'))
rng, start = [], None
for i in range(0, 0x18000):
    if a[i] != b[i] and start is None:
        start = i
    if a[i] == b[i] and start is not None:
        rng.append((start, i))
        start = None
print('calibration diffs (0x8000-0x1FFFF):', len(rng), 'ranges,', sum(e - s for s, e in rng), 'bytes')
for s, e in rng:
    print(f'  0x{s + 0x8000:05X}-0x{e + 0x8000 - 1:05X}')
code = sum(1 for i in range(0x18000, 0xF8000) if a[i] != b[i])
print('code area 0x20000+ differing bytes:', code)
for arg in sys.argv[3:]:
    if arg.startswith('D'):  # D<descriptor hex>: table descriptor (count byte, format, axis ptr, data ptr) in each file
        ad = int(arg[1:], 16)
        for name, x in (('A', a), ('B', b)):
            n = x[ad - 0x8000]
            ax, dp = struct.unpack_from('>II', x, ad - 0x8000 + 4)
            print(f'desc 0x{ad:05X} {name}: axis 0x{ax:05X}', list(struct.unpack_from(f'>{n}h', x, ax - 0x8000)),
                  f'data 0x{dp:05X}', list(struct.unpack_from(f'>{n}h', x, dp - 0x8000)))
        continue
    ad, n = arg.split(':')
    ad, n = int(ad, 16), int(n)
    for name, x in (('A', a), ('B', b)):
        print(f'0x{ad:05X} {name}:', list(struct.unpack_from(f'>{n}h', x, ad - 0x8000)))
