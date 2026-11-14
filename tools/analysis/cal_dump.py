import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
def ws(a, n): return [struct.unpack_from('>H', b, a - base + 2 * k)[0] for k in range(n)]
for name, a, n in (('C1D4 steps', 0xC1D4, 8), ('C1E6..', 0xC1E6, 6), ('C1EC', 0xC1EC, 8), ('C230', 0xC230, 10),
                   ('C268', 0xC268, 26), ('C29A', 0xC29A, 4), ('BEEC', 0xBEEC, 2), ('BB54', 0xBB54, 4)):
    print(f'{name:12} {a:#x}: ' + ' '.join(f'{x:04X}({x})' for x in ws(a, n)))
print()
def desc(a):
    # 2D table descriptors used through 0x908C / 1D through 0x8CD8: print raw words
    print(f'{a:#x}: ' + ' '.join(f'{x:04X}' for x in ws(a, 14)) + '  longs ' + ' '.join(f'{struct.unpack_from(">I", b, a - base + 4*k)[0]:#x}' for k in range(5)))
for a in (0xB9EC, 0xBA00, 0xBA14, 0xC25C, 0xC230 + 0x2C): desc(a)
