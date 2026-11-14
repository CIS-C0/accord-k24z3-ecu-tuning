# Builds work\v3_fuelcut20.bin/.rwd from the flash #2 firmware (work\v2_tipin_fuelcut.bin/.rwd).
# Changes (CPU addresses, file offset = address - 0x8000), decel fuel cut function 0x580DE, constants block 0xB138:
#   table 0xB158, data 0x15AC2-0x15ACB (gears 1-5): 40, 40, 40, 40, 40 -> 20, 20, 20, 20, 20
#   0xB13E / 0xB140 (0xB138+6 / +8, floor 0xFFFF76BE loaded on a gear change): 40, 40 -> 20, 20
#     (delay = max(table, 76BE): without this the floor could keep the delay at 40 after a shift)
#   checksum byte 0x8400: firmware area 0x8000-0xFFFFF byte sum = 0 mod 256
# The .rwd keeps the v2 header; only the changed bytes are re-encrypted and the file checksum is recomputed.
# Stops on any unexpected value. Usage: py -I src\build_v3.py <out_dir>
import hashlib, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x8000
K0, K1, K2 = 0x2A, 0x6C, 0xD7  # firmware keys 2A 6C D7
V2_BIN_SHA = '41788E02'  # start of the recorded SHA256 (KNOWLEDGE.md)
V2_RWD_SHA = 'BD4D4F38'
CHANGES = [  # address, old words, new words
    (0x15AC2, [40, 40, 40, 40, 40], [20, 20, 20, 20, 20]),
    (0xB13E, [40, 40], [20, 20]),
]
UNCHANGED = [  # address, expected words (neighbours of the changes, must stay as they are)
    (0xB138, [4000, 3800, 300]),
    (0xB150, [40, 0, 10, 510]),
    (0x15ACC, [300]),
]
DESCRIPTORS = [  # descriptor, expected axis pointer, expected data pointer (proves the data addresses)
    (0xB158, 0x15ABC, 0x15AC2),  # 6 points: axis gears 1,2,3,4,5,0
]
# every ROM literal pointing into the block must be one of these (all in the fuel cut function 0x580DE)
POINTERS = {0xB138: [0x586D4, 0x588C4], 0xB13E: [], 0xB140: [], 0xB158: [], 0x15AC2: [0xB160]}


def dec(e):
    return (((e ^ K2) + K1) - K0) & 0xFF


def enc(p):
    return ((p + K0 - K1) & 0xFF) ^ K2


def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)


out = sys.argv[1]
v2bin = bytearray(open(os.path.join(ROOT, 'work', 'v2_tipin_fuelcut.bin'), 'rb').read())
v2rwd = bytearray(open(os.path.join(ROOT, 'work', 'v2_tipin_fuelcut.rwd'), 'rb').read())
hdr = len(v2rwd) - len(v2bin) - 4
print('v2 bin', len(v2bin), 'v2 rwd', len(v2rwd), 'header', hdr)
for name, data, ref in (('bin', v2bin, V2_BIN_SHA), ('rwd', v2rwd, V2_RWD_SHA)):
    h = hashlib.sha256(data).hexdigest().upper()
    print(f'v2 {name} sha256 {h}')
    if not h.startswith(ref):
        fail(f'v2 {name} is not the flashed v2 file')
if len(v2bin) != 0xF8000:
    fail('bin size')

# cipher check: every encrypted byte of v2 rwd must decode to v2 bin, and enc must invert dec
if any(enc(dec(e)) != e for e in range(256)):
    fail('enc is not the inverse of dec')
bad = sum(1 for i in range(len(v2bin)) if dec(v2rwd[hdr + i]) != v2bin[i])
print('v2 rwd decodes to v2 bin, mismatches:', bad)
if bad:
    fail('cipher/offset')
if sum(v2bin) % 256:
    fail('v2 internal checksum not 0')

for d, axis, data in DESCRIPTORS:
    o = d - BASE
    a, p = struct.unpack_from('>II', v2bin, o + 4)
    print(f'descriptor 0x{d:X}: count {v2bin[o]} fmt {v2bin[o+1:o+4].hex()} axis 0x{a:X} data 0x{p:X}')
    if p != data or a != axis:
        fail(f'descriptor 0x{d:X} pointers')
    if list(v2bin[a - BASE:a - BASE + 6]) != [1, 2, 3, 4, 5, 0]:
        fail(f'axis 0x{a:X} is not gears 1-5')

for v, expected in POINTERS.items():
    pat, found, i = v.to_bytes(4, 'big'), [], v2bin.find(v.to_bytes(4, 'big'))
    while i >= 0:
        found.append(i + BASE)
        i = v2bin.find(pat, i + 1)
    print(f'ROM literals 0x{v:X}: ' + ' '.join(f'0x{x:X}' for x in found))
    if found != expected:
        fail(f'literals of 0x{v:X} are {found}, expected {expected}')

for addr, expected in UNCHANGED:
    cur = list(struct.unpack_from(f'>{len(expected)}h', v2bin, addr - BASE))
    if cur != expected:
        fail(f'0x{addr:X} is {cur}, expected {expected}')

new = bytearray(v2bin)
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
print(f'checksum byte 0x8400: 0x{v2bin[ck]:02X} -> 0x{new[ck]:02X}, sum mod 256 = {sum(new) % 256}')

rwd = bytearray(v2rwd)
for i in range(len(new)):
    if new[i] != v2bin[i]:
        rwd[hdr + i] = enc(new[i])
s = sum(rwd[:-4]) & 0xFFFFFFFF
rwd[-4:] = struct.pack('<I', s)
if any(dec(rwd[hdr + i]) != new[i] for i in range(len(new))):
    fail('new rwd does not decode to new bin')
if rwd[:hdr] != v2rwd[:hdr]:
    fail('header changed')

stock = open(os.path.join(ROOT, 'stock', '37805-R42-A240-M1.0x8000.bin'), 'rb').read()
for name, ref in (('v2', v2bin), ('stock', stock)):
    diff = [i + BASE for i in range(len(new)) if new[i] != ref[i]]
    print(f'diff vs {name}: {len(diff)} bytes: ' + ' '.join(f'0x{a:X}' for a in diff))

os.makedirs(out, exist_ok=True)
for ext, data in (('bin', new), ('rwd', rwd)):
    path = os.path.join(out, 'v3_fuelcut20.' + ext)
    if os.path.exists(path):
        fail(path + ' already exists')
    open(path, 'wb').write(data)
    print(path, len(data), hashlib.sha256(data).hexdigest().upper())
print('BUILD OK')
