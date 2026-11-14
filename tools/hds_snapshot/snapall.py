# Decodes ALL signals of HDS SnapShot .dat files (Teradyne HDS 3.105) into raw-value CSVs (no scaling).
# Descriptor per signal (found 2026-10-30): ... "HIMPIDV2", u32 len + UTF-16 name, 8 bytes, 01, 00/01, n,
# n x (u16 byte position, u16 DID), n x u32 mask, then 00 + u16 DID + 00 00.
# Records (snap.py): u16 byte position, u16 DID, u32 value, u32 time ms, u32 0xFFFFFFFF.
# Multi-byte signals are big endian over their positions; a mask other than 0xFF keeps only those bits (shifted down).
# Usage: py -I snapall.py <out_dir> <dat files...>   -> <out_dir>\<ddmmyyyy_hhmmss>.csv + signals.txt
import os, struct, sys, csv

TAG = 'HIMPIDV2'.encode('utf-16le')


def descriptors(b, end):
    sig, i = [], b.find(TAG)
    while 0 <= i < end:
        j = i + len(TAG)
        n = struct.unpack_from('<I', b, j)[0]
        name = b[j + 4:j + 4 + n].decode('utf-16le')
        k = j + 4 + n
        # k..k+7: usually 0 (APP1: 00 00 00 A0 ...), k+9: 0 on TW, AFM (meanings unknown)
        if b[k + 8] != 1 or b[k + 9] not in (0, 1) or b[k + 10] not in (1, 2, 3, 4):
            raise ValueError(f'unexpected descriptor layout for {name} at {k:#x}')
        cnt = b[k + 10]
        pos = [struct.unpack_from('<HH', b, k + 11 + 4 * m) for m in range(cnt)]
        masks = [struct.unpack_from('<I', b, k + 11 + 4 * cnt + 4 * m)[0] for m in range(cnt)]
        sig.append((name, pos, masks))
        i = b.find(TAG, j)
    return sig


def records(b):
    i = 0x3000
    while not (b[i + 12:i + 16] == b'\xff' * 4 and b[i + 28:i + 32] == b'\xff' * 4 and b[i + 3] == 0x26
               and b[i + 19] == 0x26):
        i += 1
    n = struct.unpack_from('<I', b, i - 4)[0]
    frames = {}
    for k in range(n):
        p, did, val, t, ff = struct.unpack_from('<HHIII', b, i + 16 * k)
        if ff != 0xFFFFFFFF:
            raise ValueError('record layout')
        frames.setdefault(t, {})[(did, p)] = val
    return i, frames


def value(f, pos, masks):
    v = 0
    for (p, did), m in zip(pos, masks):
        if (did, p) not in f:
            return ''
        x = f[(did, p)] & 0xFF
        if m & 0xFF != 0xFF:
            x &= m
            while m and not m & 1:
                m >>= 1
                x >>= 1
        v = (v << 8) | x
    return v


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for path in sys.argv[2:]:
        b = open(path, 'rb').read()
        start, frames = records(b)
        sig = descriptors(b, start)
        names = [s[0] for s in sig]
        if len(set(names)) != len(names):
            raise ValueError('duplicate signal names')
        base = os.path.basename(path)[-19:-4]
        with open(os.path.join(out, base + '.csv'), 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['t'] + names)
            for t in sorted(frames):
                w.writerow([t] + [value(frames[t], p, m) for _, p, m in sig])
        with open(os.path.join(out, 'signals.txt'), 'w') as fh:
            for name, pos, masks in sig:
                fh.write(f'{name} ' + ' '.join(f'{did:04X}:{p:02X}/{m:02X}' for (p, did), m in zip(pos, masks)) + '\n')
        print(base, len(frames), 'frames', len(sig), 'signals')
