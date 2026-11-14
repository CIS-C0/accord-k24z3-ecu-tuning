# Builds work\v2_tipin_fuelcut.bin/.rwd from the flash #1 firmware (work\v1_speedlimiter.bin/.rwd).
# Changes (CPU addresses, file offset = address - 0x8000), see docs\PROPOSAL_FLASH2.md:
#   A2: tip-in ramp table 0xAB40, data 0x1419C-0x141A3: 6, 30, 100, 300 -> 12, 60, 200, 600
#   C : decel fuel cut delay table 0xB158, data 0x15AC2-0x15AC7 (gears 1-3): 80, 80, 80 -> 40, 40, 40
#   checksum byte 0x8400: firmware area 0x8000-0xFFFFF byte sum = 0 mod 256
# The .rwd keeps the v1 header; only the changed bytes are re-encrypted and the file checksum is recomputed.
# Stops on any unexpected value. Usage: py -I src\build_v2.py <out_dir>
import hashlib, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x8000
K0, K1, K2 = 0x2A, 0x6C, 0xD7  # firmware keys 2A 6C D7
CHANGES = [  # address, old words, new words
    (0x1419C, [6, 30, 100, 300], [12, 60, 200, 600]),
    (0x15AC2, [80, 80, 80], [40, 40, 40]),
]
DESCRIPTORS = [  # descriptor, expected axis pointer, expected data pointer (proves the data addresses)
    (0xAB40, 0x14190, 0x1419A),  # 5 points: axis 0,3,10,30,60 / data 0 (kept), 6, 30, 100, 300
    (0xB158, 0x15ABC, 0x15AC2),
]


def dec(e):
    return (((e ^ K2) + K1) - K0) & 0xFF


def enc(p):
    return ((p + K0 - K1) & 0xFF) ^ K2


def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)


out = sys.argv[1]
v1bin = bytearray(open(os.path.join(ROOT, 'work', 'v1_speedlimiter.bin'), 'rb').read())
v1rwd = bytearray(open(os.path.join(ROOT, 'work', 'v1_speedlimiter.rwd'), 'rb').read())
hdr = len(v1rwd) - len(v1bin) - 4
print('v1 bin', len(v1bin), 'v1 rwd', len(v1rwd), 'header', hdr)
if len(v1bin) != 0xF8000:
    fail('bin size')

# cipher check: every encrypted byte of v1 rwd must decode to v1 bin, and enc must invert dec
if any(enc(dec(e)) != e for e in range(256)):
    fail('enc is not the inverse of dec')
bad = sum(1 for i in range(len(v1bin)) if dec(v1rwd[hdr + i]) != v1bin[i])
print('v1 rwd decodes to v1 bin, mismatches:', bad)
if bad:
    fail('cipher/offset')
if sum(v1bin) % 256:
    fail('v1 internal checksum not 0')

for d, axis, data in DESCRIPTORS:
    o = d - BASE
    a, p = struct.unpack_from('>II', v1bin, o + 4)
    print(f'descriptor 0x{d:X}: count {v1bin[o]} fmt {v1bin[o+1:o+4].hex()} axis 0x{a:X} data 0x{p:X}')
    if p != data or a != axis:
        fail(f'descriptor 0x{d:X} pointers')

new = bytearray(v1bin)
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
print(f'checksum byte 0x8400: 0x{v1bin[ck]:02X} -> 0x{new[ck]:02X}, sum mod 256 = {sum(new) % 256}')

rwd = bytearray(v1rwd)
for i in range(len(new)):
    if new[i] != v1bin[i]:
        rwd[hdr + i] = enc(new[i])
s = sum(rwd[:-4]) & 0xFFFFFFFF
rwd[-4:] = struct.pack('<I', s)
if any(dec(rwd[hdr + i]) != new[i] for i in range(len(new))):
    fail('new rwd does not decode to new bin')

stock = open(os.path.join(ROOT, 'stock', '37805-R42-A240-M1.0x8000.bin'), 'rb').read()
for name, ref in (('v1', v1bin), ('stock', stock)):
    diff = [i + BASE for i in range(len(new)) if new[i] != ref[i]]
    print(f'diff vs {name}: {len(diff)} bytes: ' + ' '.join(f'0x{a:X}' for a in diff))

os.makedirs(out, exist_ok=True)
for ext, data in (('bin', new), ('rwd', rwd)):
    path = os.path.join(out, 'v2_tipin_fuelcut.' + ext)
    if os.path.exists(path):
        fail(path + ' already exists')
    open(path, 'wb').write(data)
    print(path, len(data), hashlib.sha256(data).hexdigest().upper())
print('BUILD OK')
