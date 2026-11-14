# find_access.py <bin> <ram_hex> [...]: finds code that reads or writes a RAM address through a base register
# (pool load of a nearby address + displacement / add #imm / copies), which FindRefs (exact pool word) misses.
# Tracks one register window of 80 instructions after every "mov.l @(disp,PC),Rn" loading target-0xFC..target+0x7F.
# CPU address = file offset + 0x8000.
import struct, sys
b = open(sys.argv[1], 'rb').read()
B = 0x8000


def w(a):
    return struct.unpack_from('>H', b, a - B)[0]


def s8(x):
    return x - 0x100 if x & 0x80 else x


for t in (int(x, 16) | 0xFFFF0000 for x in sys.argv[2:]):
    print(f'=== 0x{t:08X}')
    for a in range(B, B + len(b) - 1, 2):
        op = w(a)
        if op >> 12 != 0xD:
            continue
        p = (a & ~3) + 4 + (op & 0xFF) * 4
        if p - B + 4 > len(b):
            continue
        v = struct.unpack_from('>I', b, p - B)[0]
        if not (t - 0xFC <= v <= t + 0x7F):
            continue
        regs = {(op >> 8) & 0xF: v}
        for k in range(1, 80):
            pc = a + 2 * k
            if pc - B + 2 > len(b):
                break
            o = w(pc)
            n, m, lo = (o >> 8) & 0xF, (o >> 4) & 0xF, o & 0xF
            hit = None
            if o >> 12 == 0x8 and n in (0, 1, 4, 5) and m in regs:      # mov.b/w R0 <-> @(disp,Rm)
                sz = 2 if n in (1, 5) else 1
                if regs[m] + lo * sz == t:
                    hit = ('store' if n < 4 else 'load') + (' .w' if sz == 2 else ' .b')
            elif o >> 12 == 0x1 and n in regs and regs[n] + lo * 4 == t:  # mov.l Rm,@(disp,Rn)
                hit = 'store .l'
            elif o >> 12 == 0x5 and m in regs and regs[m] + lo * 4 == t:  # mov.l @(disp,Rm),Rn
                hit = 'load .l'
            elif o >> 12 == 0x2 and lo in (0, 1, 2) and n in regs and regs[n] == t:
                hit = 'store @Rn'
            elif o >> 12 == 0x6 and lo in (0, 1, 2) and m in regs and regs[m] == t:
                hit = 'load @Rm'
            if hit:
                print(f'  {hit} at 0x{pc:05X} (base 0x{v:08X} loaded at 0x{a:05X})')
            # register tracking
            if o >> 12 == 0x7 and n in regs:                 # add #imm,Rn
                regs[n] = (regs[n] + s8(o & 0xFF)) & 0xFFFFFFFF
            elif o >> 12 == 0x6 and lo == 3 and m in regs:   # mov Rm,Rn
                regs[n] = regs[m]
            elif o >> 12 == 0x6 and lo == 3:
                regs.pop(n, None)
            elif o in (0x000B, 0x002B):                      # rts / rte
                break
            elif o >> 12 in (0xD, 0x9, 0xE) and n in regs:   # register reloaded
                regs.pop(n)
            elif o >> 12 == 0x6 and lo in (0, 1, 2, 4, 5, 6) and n in regs:
                regs.pop(n)
            elif (o >> 12 == 0x8 and n in (4, 5)) or o >> 8 in (0xC4, 0xC5, 0xC6, 0xC7):  # R0 overwritten
                regs.pop(0, None)
            if not regs:
                break
