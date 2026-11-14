# Find SH-2 code storing to given RAM bytes through a base register + displacement (GBR or Rn), which FindRefs.java
# (direct "mov.l pool -> Rn ; mov.x Rm,@Rn") does not see. Raw linear scan (no branch following), a candidate list
# to confirm in Ghidra. Rn is followed until it is overwritten ("add #imm,Rn" moves the base); GBR until rts.
# find_base_stores.py <bin (ROM from 0x8000)> <hex target> [...]
import struct, sys

ROM = 0x8000
b = open(sys.argv[1], 'rb').read()
targets = [int(t, 16) for t in sys.argv[2:]]
u16 = lambda a: struct.unpack_from('>H', b, a - ROM)[0]
u32 = lambda a: struct.unpack_from('>I', b, a - ROM)[0]
END = ROM + len(b)


def writes_rn(o, rn):
    # instructions whose destination is Rn (n field = bits 8-11), other than stores and compares
    n, top = (o >> 8) & 0xF, o >> 12
    if n != rn:
        return False
    if top in (0x5, 0x9, 0xD, 0xE):
        return True
    if top == 0x6:
        return True
    if top == 0x3 and o & 0xF not in (0x0, 0x2, 0x3, 0x6, 0x7):   # not cmp/xx
        return True
    if top == 0x2 and o & 0xF in (0x9, 0xA, 0xB, 0xD, 0xE, 0xF):   # and/xor/or/xtrct/mul
        return True
    if top == 0x0 and o & 0xF in (0x9, 0xA, 0xC, 0xD, 0xE, 0x2):   # movt/sts/mov.x @(R0,Rm),Rn/stc
        return True
    if top == 0x4 and o & 0xFF in (0x00, 0x01, 0x04, 0x05, 0x08, 0x09, 0x18, 0x19, 0x28, 0x29, 0x20, 0x21, 0x24, 0x25):
        return True
    return False


for pc in range(ROM, END - 2, 2):
    op = u16(pc)
    if op & 0xF000 != 0xD000:            # mov.l @(disp,PC),Rn
        continue
    pool = (pc & ~3) + 4 + (op & 0xFF) * 4
    if pool + 4 > END:
        continue
    base0 = u32(pool)
    if not any(-0x80 <= t - base0 <= 0x3FC for t in targets):
        continue
    rn, base, gbr, rn_live = (op >> 8) & 0xF, base0, None, True
    a = pc + 2
    for _ in range(3000):
        o = u16(a)
        if o == 0x000B:                  # rts
            break
        hits = []
        if rn_live and o & 0xF0FF == 0x401E and (o >> 8) & 0xF == rn:     # ldc Rn,GBR
            gbr = base
        if gbr is not None and o & 0xFC00 == 0xC000:                    # mov.b/w/l R0,@(disp,GBR)
            sz = 1 << ((o >> 8) & 3)
            hits.append((gbr + (o & 0xFF) * sz, sz, 'GBR'))
        if gbr is not None and o & 0xF0FF in (0x401E, 0x4017) and (o >> 8) & 0xF != rn:
            gbr = None                   # GBR reloaded from another register / restored
        if rn_live:
            if o & 0xFF00 in (0x8000, 0x8100) and (o >> 4) & 0xF == rn:     # mov.b/w R0,@(disp,Rn)
                sz = 1 if o & 0xFF00 == 0x8000 else 2
                hits.append((base + (o & 0xF) * sz, sz, 'Rn'))
            if o & 0xF000 == 0x1000 and (o >> 8) & 0xF == rn:               # mov.l Rm,@(disp,Rn)
                hits.append((base + (o & 0xF) * 4, 4, 'Rn'))
            if o & 0xF00F in (0x2000, 0x2001, 0x2002) and (o >> 8) & 0xF == rn:   # mov.x Rm,@Rn
                hits.append((base, 1 << (o & 3), 'Rn'))
            if o & 0xF000 == 0x7000 and (o >> 8) & 0xF == rn:               # add #imm,Rn
                imm = o & 0xFF
                base += imm - 256 if imm & 0x80 else imm
            elif writes_rn(o, rn):
                rn_live = False
        if not rn_live and gbr is None and _ > 200:
            break
        for addr, sz, kind in hits:
            for t in targets:
                if addr <= t < addr + sz:
                    print(f'0x{t:08X}: {kind} base 0x{base0:08X} loaded at 0x{pc:X}, store 0x{o:04X} at 0x{a:X}')
        a += 2
