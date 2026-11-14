# Builds work\v6_maf_taper.bin/.rwd from the flash #3 firmware (work\v3_fuelcut20.bin/.rwd), like v5.
# Change: MAF transfer table (descriptor 0xA75C, n=64, axis 0x13C72 = MAF A/D 10-bit, data 0x13BF2 = airflow, HDS GAIR)
# x mult(A/D): 1.15 for A/D <= 376 (= v5), linear down to 1.08 at A/D 488, 1.08 above; rounded, capped at 32767
# (16-bit signed max; point 62 only, A/D 992, never reached). Reason: v6 step 1 (src\hds_snapshot\maf_need.py): the
# MAF under-read is ~15 % at low flow but only ~5 % at WOT flow (v5 x1.15 everywhere = WOT lambda 0.76-0.78 vs cmd
# 0.848). 1.08 keeps WOT ~3 % richer than cmd on purpose. Also checks: points A/D <= 376 equal v5, the others below v5.
#   checksum byte 0x8400: firmware area 0x8000-0xFFFFF byte sum = 0 mod 256
# The .rwd keeps the v3 header; only the changed bytes are re-encrypted and the file checksum is recomputed.
# Stops on any unexpected value. Usage: py -I src\build_v6.py <out_dir>
import hashlib, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x8000
K0, K1, K2 = 0x2A, 0x6C, 0xD7  # firmware keys 2A 6C D7
V3_BIN_SHA = '1D3F2779'  # start of the recorded SHA256 (KNOWLEDGE.md)
V3_RWD_SHA = 'F8836DEC'
V5_BIN_SHA = '765D5E96'
LOW_AD, LOW_M, HIGH_AD, HIGH_M = 376, 1.15, 488, 1.08
DESC, AXIS, DATA, N = 0xA75C, 0x13C72, 0x13BF2, 64
AXIS_V = [0, 0, 72, 88, 104, 120, 136, 152, 168, 184, 200, 216, 232, 248, 264, 272, 280, 288, 296, 312, 320, 328, 344,
          352, 360, 376, 384, 392, 408, 416, 424, 440, 448, 456, 472, 480, 488, 504, 512, 520, 536, 552, 568, 584, 600,
          616, 632, 648, 664, 680, 696, 712, 728, 744, 760, 776, 792, 824, 856, 888, 920, 952, 992, 1015]
DATA_V = [0, 0, 0, 0, 4, 12, 24, 41, 64, 93, 128, 172, 222, 285, 357, 398, 441, 485, 534, 639, 698, 756, 887, 957, 1032,
          1197, 1287, 1381, 1582, 1690, 1803, 2043, 2170, 2302, 2582, 2732, 2888, 3220, 3397, 3582, 3977, 4405, 4866,
          5351, 5863, 6404, 6973, 7571, 8201, 8865, 9565, 10301, 11073, 11881, 12719, 13594, 14509, 16476, 18649, 21035,
          23648, 26447, 30319, 32767]
# every ROM literal pointing at the descriptor / its axis / its data (code pool words + the descriptor itself)
POINTERS = {DESC: [0x539B0, 0x703AC], AXIS: [0xA760], DATA: [0xA764]}


def dec(e):
    return (((e ^ K2) + K1) - K0) & 0xFF


def enc(p):
    return ((p + K0 - K1) & 0xFF) ^ K2


def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)


def mult(ad):
    if ad <= LOW_AD:
        return LOW_M
    if ad >= HIGH_AD:
        return HIGH_M
    return LOW_M + (HIGH_M - LOW_M) * (ad - LOW_AD) / (HIGH_AD - LOW_AD)


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

o = DESC - BASE
a, p = struct.unpack_from('>II', v3bin, o + 4)
print(f'descriptor 0x{DESC:X}: count {v3bin[o]} fmt {v3bin[o + 1:o + 4].hex()} axis 0x{a:X} data 0x{p:X}')
if v3bin[o] != N or v3bin[o + 1:o + 4] != b'\x66\x66\x00' or a != AXIS or p != DATA:
    fail('descriptor')
if list(struct.unpack_from(f'>{N}h', v3bin, AXIS - BASE)) != AXIS_V:
    fail('axis values')
if list(struct.unpack_from(f'>{N}h', v3bin, DATA - BASE)) != DATA_V:
    fail('data values (not the stock MAF table)')

for v, expected in POINTERS.items():
    pat, found, i = v.to_bytes(4, 'big'), [], v3bin.find(v.to_bytes(4, 'big'))
    while i >= 0:
        found.append(i + BASE)
        i = v3bin.find(pat, i + 1)
    print(f'ROM literals 0x{v:X}: ' + ' '.join(f'0x{x:X}' for x in found))
    if found != expected:
        fail(f'literals of 0x{v:X} are {found}, expected {expected}')
# no other aligned ROM word may point inside the data array (would be a second, hidden user)
inside = [i + BASE for i in range(0, len(v3bin) - 3, 2)
          if DATA < struct.unpack_from('>I', v3bin, i)[0] < DATA + 2 * N]
print('ROM words pointing inside the data (not at its start):', inside)
if inside:
    fail('word pointing inside the MAF data')

v5bin = open(os.path.join(ROOT, 'work', 'v5_maf115.bin'), 'rb').read()
if not hashlib.sha256(v5bin).hexdigest().upper().startswith(V5_BIN_SHA):
    fail('v5 bin is not the flashed v5 file')
v5v = list(struct.unpack_from(f'>{N}h', v5bin, DATA - BASE))

newv = [min(32767, int(v * mult(ad) + 0.5)) for v, ad in zip(DATA_V, AXIS_V)]
if any(newv[i] < newv[i - 1] for i in range(1, N)):
    fail('new table not increasing')
if any(nv < ov for nv, ov in zip(newv, DATA_V)):
    fail('a point went below stock')
for i in range(N):
    if (AXIS_V[i] <= LOW_AD and newv[i] != v5v[i]) or (AXIS_V[i] > LOW_AD and newv[i] > v5v[i]):
        fail(f'point {i} vs v5')
for i, (ov, nv) in enumerate(zip(DATA_V, newv)):
    m = mult(AXIS_V[i])
    print(f'  {i:2d} A/D {AXIS_V[i]:4d}: x{m:.4f} {ov:5d} -> {nv:5d} (v5 {v5v[i]:5d})'
          + ('  (capped)' if nv != int(ov * m + 0.5) else ''))

new = bytearray(v3bin)
struct.pack_into(f'>{N}h', new, DATA - BASE, *newv)

ck = 0x8400 - BASE
new[ck] = 0
new[ck] = (-sum(new)) % 256
print(f'checksum byte 0x8400: 0x{v3bin[ck]:02X} -> 0x{new[ck]:02X}, sum mod 256 = {sum(new) % 256}')

diff = [i + BASE for i in range(len(new)) if new[i] != v3bin[i]]
if any(not (DATA <= d < DATA + 2 * N or d == 0x8400) for d in diff):
    fail('a changed byte is outside the MAF data and the checksum byte')

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
print(f'rwd file checksum 0x{s:08X}')

stock = open(os.path.join(ROOT, 'stock', '37805-R42-A240-M1.0x8000.bin'), 'rb').read()
for name, ref in (('v3', v3bin), ('v5', v5bin), ('stock', stock)):
    d = [i + BASE for i in range(len(new)) if new[i] != ref[i]]
    print(f'diff vs {name}: {len(d)} bytes: ' + ' '.join(f'0x{x:X}' for x in d))

os.makedirs(out, exist_ok=True)
for ext, data in (('bin', new), ('rwd', rwd)):
    path = os.path.join(out, 'v6_maf_taper.' + ext)
    if os.path.exists(path):
        fail(path + ' already exists')
    open(path, 'wb').write(data)
    print(path, len(data), hashlib.sha256(data).hexdigest().upper())
print('BUILD OK')
