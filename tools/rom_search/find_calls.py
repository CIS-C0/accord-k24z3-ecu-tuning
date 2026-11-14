# find_calls.py <bin> <target_hex> [...]: bsr/bra instructions reaching the target and raw 32-bit words equal to it
# (function pointer tables). CPU address = file offset + 0x8000.
import struct, sys
b = open(sys.argv[1], 'rb').read()
for t in (int(x, 16) for x in sys.argv[2:]):
    print(f'=== 0x{t:05X}')
    for o in range(0, len(b) - 1, 2):
        w = struct.unpack_from('>H', b, o)[0]
        if w >> 12 in (0xA, 0xB):  # bra / bsr disp12
            d = w & 0xFFF
            d = d - 0x1000 if d & 0x800 else d
            if o + 0x8000 + 4 + d * 2 == t:
                print(f'  {"bsr" if w >> 12 == 0xB else "bra"} at 0x{o + 0x8000:05X}')
    p = struct.pack('>I', t)
    i = b.find(p)
    while i >= 0:
        print(f'  32-bit word at 0x{i + 0x8000:05X}')
        i = b.find(p, i + 1)
