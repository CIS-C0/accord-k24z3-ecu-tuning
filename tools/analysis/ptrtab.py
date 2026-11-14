# find ROM places holding RAM pointer 0xFFFF2C2C (vehicle speed) and 0xFFFF289C (rpm); print neighbourhood words
import struct, sys
b = open(sys.argv[1], 'rb').read()
B = 0x8000
targets = [int(x, 16) for x in sys.argv[2:]]
for t in targets:
    pat = struct.pack('>I', t)
    i = b.find(pat)
    hits = []
    while i >= 0:
        hits.append(i)
        i = b.find(pat, i + 1)
    print(f'== 0x{t:08X}: {len(hits)} hits')
    for h in hits:
        if h % 2:
            continue
        # count RAM-pointer-looking words around
        lo = max(0, h - 64)
        words = [struct.unpack_from('>I', b, x)[0] for x in range(lo - lo % 2, h + 64, 2)]
        ram = sum(1 for x in range(h - 48, h + 48, 4) if 0 <= x < len(b) - 4 and (struct.unpack_from('>I', b, x)[0] >> 16) == 0xFFFF)
        print(f'  0x{h + B:06X} ram-words(+-48, step 4)={ram}')
        if ram >= 6:
            for x in range(h - 48, h + 52, 4):
                print(f'     0x{x + B:06X}: {struct.unpack_from(">I", b, x)[0]:08X}')
