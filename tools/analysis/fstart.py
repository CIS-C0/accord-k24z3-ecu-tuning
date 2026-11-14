import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
w = lambda a: struct.unpack_from('>H', b, a - base)[0]
for t in (0x23f9a, 0x81070, 0x81604, 0x8108a):
    rts = [a for a in range(t - 2, t - 0x1400, -2) if w(a) == 0x000B][:3]
    pr = [a for a in range(t - 2, t - 0x1400, -2) if w(a) == 0x4F22][:3]
    print(hex(t), 'previous rts', [hex(a) for a in rts], 'previous sts.l pr', [hex(a) for a in pr])
