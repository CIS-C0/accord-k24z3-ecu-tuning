# Decodes an HDS SnapShot .dat (Teradyne HDS 3.105) into one row per frame of raw signal bytes.
# Record layout (found 2026-10-25): u16 byte position, u16 DID, u32 value, u32 time ms, u32 0xFFFFFFFF.
# Signal map from the file's own descriptors (name, DID, byte positions, mask).
import sys, struct, csv, os

SIG = [  # name, did, positions (big endian if 2), mask
    ('NE', 0x2610, (6, 7), None),
    ('VSP', 0x2610, (0x12,), None),
    ('ECT', 0x2610, (0x0B,), None),
    ('MAP', 0x2610, (0x0F,), None),
    ('IG', 0x2610, (0x15,), None),
    ('APP', 0x2612, (8, 9), None),
    ('THVLV', 0x2612, (0x0C, 0x0D), None),   # RELTHW = Throttle VLV
    ('THTGT', 0x2612, (0x0E, 0x0F), None),   # THO = Target TH VLV
    ('THIDL', 0x2612, (0x12, 0x13), None),   # THICMD = Idle Target TH
    ('FC', 0x2660, (0x16,), 0x08),
    ('FCDEC', 0x2660, (0x16,), 0x10),
]


def load(path):
    b = open(path, 'rb').read()
    i = 0x3000
    while not (b[i + 12:i + 16] == b'\xff' * 4 and b[i + 28:i + 32] == b'\xff' * 4 and b[i + 3] == 0x26
               and b[i + 19] == 0x26):
        i += 1
    n = struct.unpack_from('<I', b, i - 4)[0]
    frames = {}
    for k in range(n):
        pos, did, val, t, ff = struct.unpack_from('<HHIII', b, i + 16 * k)
        assert ff == 0xFFFFFFFF
        frames.setdefault(t, {})[(did, pos)] = val
    rows = []
    for t in sorted(frames):
        f = frames[t]
        row = {'t': t}
        for name, did, ps, mask in SIG:
            try:
                v = 0
                for p in ps:
                    v = (v << 8) | f[(did, p)]
            except KeyError:
                v = ''
            if mask is not None and v != '':
                v = 1 if v & mask else 0
            row[name] = v
        rows.append(row)
    return rows


if __name__ == '__main__':
    out = sys.argv[2]
    for path in sorted(os.listdir(sys.argv[1])):
        if not path.endswith('.dat'):
            continue
        rows = load(os.path.join(sys.argv[1], path))
        name = os.path.join(out, path[-19:-4] + '.csv')
        with open(name, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=['t'] + [s[0] for s in SIG])
            w.writeheader()
            w.writerows(rows)
        print(path[-19:-4], len(rows), 'frames')
