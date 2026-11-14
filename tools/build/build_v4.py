# Builds work\v4_revlim100.bin/.rwd from the flash #3 firmware (work\v3_fuelcut20.bin/.rwd).
# Change: rev limiter (function 0x58898) resume points 100 rpm under the cut points instead of 200 (Hondata FlashPro
# guidance: recovery 100-300 rpm under activation). Cut points NOT changed. Moving values (second point of each
# table, speed axis); the 0 km/h points are not changed (CPU addresses, file offset = address - 0x8000):
#   0x15C06 resume without VTEC (desc 0xB238, main flag 0x4E40):        6900 -> 7000 (cut 7100 at 0x15BF6)
#   0x15C0E resume with VTEC    (desc 0xB244, main flag 0x4E40):        7100 -> 7200 (cut 7300 at 0x15BFE)
#   0x15C32 resume moving       (desc 0xB294, second limiter 0x438A):   7100 -> 7200 (cut 7300 at 0x15C2A)
#   checksum byte 0x8400: firmware area 0x8000-0xFFFFF byte sum = 0 mod 256
# The .rwd keeps the v3 header; only the changed bytes are re-encrypted and the file checksum is recomputed.
# Stops on any unexpected value. Usage: py -I src\build_v4.py <out_dir>
import hashlib, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x8000
K0, K1, K2 = 0x2A, 0x6C, 0xD7  # firmware keys 2A 6C D7
V3_BIN_SHA = '1D3F2779'  # start of the recorded SHA256 (KNOWLEDGE.md)
V3_RWD_SHA = 'F8836DEC'
CHANGES = [  # address, old words, new words
    (0x15C06, [6900], [7000]),
    (0x15C0E, [7100], [7200]),
    (0x15C32, [7100], [7200]),
]
UNCHANGED = [  # address, expected words (the cut points and the 0 km/h points must stay as they are)
    (0x15BF4, [3500, 7100]),   # cut without VTEC (desc 0xB220)
    (0x15BFC, [3500, 7300]),   # cut with VTEC (desc 0xB22C)
    (0x15C04, [2500]),         # resume without VTEC at 0 km/h
    (0x15C0C, [2500]),         # resume with VTEC at 0 km/h
    (0x15C28, [4000, 7300]),   # second limiter cut (desc 0xB288)
    (0x15C30, [3700]),         # second limiter resume at 0 km/h
]
DESCRIPTORS = [  # descriptor, expected axis pointer, expected data pointer, expected axis (proves the data addresses)
    (0xB220, 0x15BF8, 0x15BF4, [0, 20]),
    (0xB22C, 0x15C00, 0x15BFC, [0, 20]),
    (0xB238, 0x15C08, 0x15C04, [0, 20]),
    (0xB244, 0x15C10, 0x15C0C, [0, 20]),
    (0xB288, 0x15C24, 0x15C28, [0, 5]),
    (0xB294, 0x15C2C, 0x15C30, [0, 5]),
]
# every ROM literal pointing at the changed tables (all in the rev limiter 0x58898, or its descriptors)
POINTERS = {0x15C04: [0xB240], 0x15C06: [], 0x15C0C: [0xB24C], 0x15C0E: [], 0x15C30: [0xB29C], 0x15C32: [],
            0xB238: [], 0xB244: [], 0xB294: [0x58E30], 0xB218: [0x58BA4]}


def dec(e):
    return (((e ^ K2) + K1) - K0) & 0xFF


def enc(p):
    return ((p + K0 - K1) & 0xFF) ^ K2


def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)


out = sys.argv[1]
v3bin = bytearray(open(os.path.join(ROOT, 'work', 'v3_fuelcut20.bin'), 'rb').read())
v3rwd = bytearray(open(os.path.join(ROOT, 'work', 'v3_fuelcut20.rwd'), 'rb').read())
hdr = len(v3rwd) - len(v3bin) - 4
print('v3 bin', len(v3bin), 'v3 rwd', len(v3rwd), 'header', hdr)
for name, data, ref in (('bin', v3bin, V3_BIN_SHA), ('rwd', v3rwd, V3_RWD_SHA)):
    h = hashlib.sha256(data).hexdigest().upper()
    print(f'v3 {name} sha256 {h}')
    if not h.startswith(ref):
        fail(f'v3 {name} is not the flashed v3 file')
if len(v3bin) != 0xF8000:
    fail('bin size')

# cipher check: every encrypted byte of v3 rwd must decode to v3 bin, and enc must invert dec
if any(enc(dec(e)) != e for e in range(256)):
    fail('enc is not the inverse of dec')
bad = sum(1 for i in range(len(v3bin)) if dec(v3rwd[hdr + i]) != v3bin[i])
print('v3 rwd decodes to v3 bin, mismatches:', bad)
if bad:
    fail('cipher/offset')
if sum(v3bin) % 256:
    fail('v3 internal checksum not 0')

for d, axis, data, axv in DESCRIPTORS:
    o = d - BASE
    a, p = struct.unpack_from('>II', v3bin, o + 4)
    ax = list(struct.unpack_from(f'>{v3bin[o]}h', v3bin, a - BASE))
    print(f'descriptor 0x{d:X}: count {v3bin[o]} fmt {v3bin[o+1:o+4].hex()} axis 0x{a:X} {ax} data 0x{p:X}')
    if p != data or a != axis or v3bin[o] != 2 or ax != axv:
        fail(f'descriptor 0x{d:X}')

for v, expected in POINTERS.items():
    pat, found, i = v.to_bytes(4, 'big'), [], v3bin.find(v.to_bytes(4, 'big'))
    while i >= 0:
        found.append(i + BASE)
        i = v3bin.find(pat, i + 1)
    print(f'ROM literals 0x{v:X}: ' + ' '.join(f'0x{x:X}' for x in found))
    if found != expected:
        fail(f'literals of 0x{v:X} are {found}, expected {expected}')

for addr, expected in UNCHANGED:
    cur = list(struct.unpack_from(f'>{len(expected)}h', v3bin, addr - BASE))
    if cur != expected:
        fail(f'0x{addr:X} is {cur}, expected {expected}')

new = bytearray(v3bin)
for addr, old, val in CHANGES:
    o = addr - BASE
    cur = list(struct.unpack_from(f'>{len(old)}h', new, o))
    if cur != old:
        fail(f'0x{addr:X} is {cur}, expected {old}')
    struct.pack_into(f'>{len(val)}h', new, o, *val)
    print(f'0x{addr:X}: {old} -> {val}')

ck = 0x8400 - BASE
new[ck] = 0
new[ck] = (-sum(new)) % 256
print(f'checksum byte 0x8400: 0x{v3bin[ck]:02X} -> 0x{new[ck]:02X}, sum mod 256 = {sum(new) % 256}')

rwd = bytearray(v3rwd)
for i in range(len(new)):
    if new[i] != v3bin[i]:
        rwd[hdr + i] = enc(new[i])
s = sum(rwd[:-4]) & 0xFFFFFFFF
rwd[-4:] = struct.pack('<I', s)
if any(dec(rwd[hdr + i]) != new[i] for i in range(len(new))):
    fail('new rwd does not decode to new bin')
if rwd[:hdr] != v3rwd[:hdr]:
    fail('header changed')

stock = open(os.path.join(ROOT, 'stock', '37805-R42-A240-M1.0x8000.bin'), 'rb').read()
for name, ref in (('v3', v3bin), ('stock', stock)):
    diff = [i + BASE for i in range(len(new)) if new[i] != ref[i]]
    print(f'diff vs {name}: {len(diff)} bytes: ' + ' '.join(f'0x{a:X}' for a in diff))

os.makedirs(out, exist_ok=True)
for ext, data in (('bin', new), ('rwd', rwd)):
    path = os.path.join(out, 'v4_revlim100.' + ext)
    if os.path.exists(path):
        fail(path + ' already exists')
    open(path, 'wb').write(data)
    print(path, len(data), hashlib.sha256(data).hexdigest().upper())
print('BUILD OK')
