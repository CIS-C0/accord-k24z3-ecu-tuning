import sys, struct
# Minimal linear SH-2 disassembler for the raw ROM image (base 0x8000). Shows literal pool values for mov.l/mov.w @(disp,PC).
# Usage: py -I shdis.py <bin> <start hex> <end hex>
data = open(sys.argv[1], 'rb').read(); BASE = 0x8000
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
def u16(a): return struct.unpack('>H', data[a - BASE:a - BASE + 2])[0]
def u32(a): return struct.unpack('>I', data[a - BASE:a - BASE + 4])[0]
def s8(x): return x - 256 if x & 0x80 else x
def s12(x): return x - 4096 if x & 0x800 else x
def dis(pc, op):
    n, m, d8, i8 = (op >> 8) & 15, (op >> 4) & 15, op & 0xFF, op & 0xFF
    t = op >> 12
    R = lambda x: f'r{x}'
    if op == 0x0009: return 'nop'
    if op == 0x000B: return 'rts'
    if op == 0x002B: return 'rte'
    if op == 0x0019: return 'div0u'
    if op == 0x0008: return 'clrt'
    if op == 0x0018: return 'sett'
    if op == 0x0028: return 'clrmac'
    if t == 0:
        low = op & 0xF
        if low == 4: return f'mov.b {R(m)},@(r0,{R(n)})'
        if low == 5: return f'mov.w {R(m)},@(r0,{R(n)})'
        if low == 6: return f'mov.l {R(m)},@(r0,{R(n)})'
        if low == 7: return f'mul.l {R(m)},{R(n)}'
        if low == 0xC: return f'mov.b @(r0,{R(m)}),{R(n)}'
        if low == 0xD: return f'mov.w @(r0,{R(m)}),{R(n)}'
        if low == 0xE: return f'mov.l @(r0,{R(m)}),{R(n)}'
        if low == 0xF: return f'mac.l @{R(m)}+,@{R(n)}+'
        sub = op & 0xFF
        if sub == 0x02: return f'stc sr,{R(n)}'
        if sub == 0x12: return f'stc gbr,{R(n)}'
        if sub == 0x0A: return f'sts mach,{R(n)}'
        if sub == 0x1A: return f'sts macl,{R(n)}'
        if sub == 0x2A: return f'sts pr,{R(n)}'
        if sub == 0x29: return f'movt {R(n)}'
        if sub == 0x03: return f'bsrf {R(n)}'
        if sub == 0x23: return f'braf {R(n)}'
    if t == 1: return f'mov.l {R(m)},@({(op & 15) * 4},{R(n)})'
    if t == 2:
        f = ['mov.b {m},@{n}', 'mov.w {m},@{n}', 'mov.l {m},@{n}', '?', 'mov.b {m},@-{n}', 'mov.w {m},@-{n}', 'mov.l {m},@-{n}', 'div0s {m},{n}',
             'tst {m},{n}', 'and {m},{n}', 'xor {m},{n}', 'or {m},{n}', 'cmp/str {m},{n}', 'xtrct {m},{n}', 'mulu.w {m},{n}', 'muls.w {m},{n}'][op & 15]
        return f.format(m=R(m), n=R(n))
    if t == 3:
        f = ['cmp/eq', '?', 'cmp/hs', 'cmp/ge', 'div1', 'dmulu.l', 'cmp/hi', 'cmp/gt', 'sub', '?', 'subc', 'subv', 'add', 'dmuls.l', 'addc', 'addv'][op & 15]
        return f'{f} {R(m)},{R(n)}'
    if t == 4:
        sub = op & 0xFF
        tbl = {0x00: 'shll', 0x01: 'shlr', 0x04: 'rotl', 0x05: 'rotr', 0x08: 'shll2', 0x09: 'shlr2', 0x10: 'dt', 0x11: 'cmp/pz', 0x15: 'cmp/pl',
               0x18: 'shll8', 0x19: 'shlr8', 0x20: 'shal', 0x21: 'shar', 0x24: 'rotcl', 0x25: 'rotcr', 0x28: 'shll16', 0x29: 'shlr16'}
        if sub in tbl: return f'{tbl[sub]} {R(n)}'
        if sub == 0x0B: return f'jsr @{R(n)}'
        if sub == 0x2B: return f'jmp @{R(n)}'
        if sub == 0x22: return f'sts.l pr,@-{R(n)}'
        if sub == 0x26: return f'lds.l @{R(n)}+,pr'
        if sub == 0x2A: return f'lds {R(n)},pr'
        if sub == 0x0A: return f'lds {R(n)},mach'
        if sub == 0x1A: return f'lds {R(n)},macl'
        if sub == 0x1E: return f'ldc {R(n)},gbr'
        if sub == 0x0E: return f'ldc {R(n)},sr'
        if sub == 0x13: return f'stc.l gbr,@-{R(n)}'
        if sub == 0x17: return f'ldc.l @{R(n)}+,gbr'
        if sub == 0x03: return f'stc.l sr,@-{R(n)}'
        if sub == 0x07: return f'ldc.l @{R(n)}+,sr'
        if sub == 0x02: return f'sts.l mach,@-{R(n)}'
        if sub == 0x12: return f'sts.l macl,@-{R(n)}'
        if sub == 0x06: return f'lds.l @{R(n)}+,mach'
        if sub == 0x16: return f'lds.l @{R(n)}+,macl'
        if sub == 0x1B: return f'tas.b @{R(n)}'
        if (op & 15) == 0xF: return f'mac.w @{R(m)}+,@{R(n)}+'
    if t == 5: return f'mov.l @({(op & 15) * 4},{R(m)}),{R(n)}'
    if t == 6:
        f = ['mov.b @{m},{n}', 'mov.w @{m},{n}', 'mov.l @{m},{n}', 'mov {m},{n}', 'mov.b @{m}+,{n}', 'mov.w @{m}+,{n}', 'mov.l @{m}+,{n}', 'not {m},{n}',
             'swap.b {m},{n}', 'swap.w {m},{n}', 'negc {m},{n}', 'neg {m},{n}', 'extu.b {m},{n}', 'extu.w {m},{n}', 'exts.b {m},{n}', 'exts.w {m},{n}'][op & 15]
        return f.format(m=R(m), n=R(n))
    if t == 7: return f'add #{s8(i8)},{R(n)}'
    if t == 8:
        sub = (op >> 8) & 15
        if sub == 0: return f'mov.b r0,@({op & 15},{R(m)})'
        if sub == 1: return f'mov.w r0,@({(op & 15) * 2},{R(m)})'
        if sub == 4: return f'mov.b @({op & 15},{R(m)}),r0'
        if sub == 5: return f'mov.w @({(op & 15) * 2},{R(m)}),r0'
        if sub == 8: return f'cmp/eq #{s8(i8)},r0'
        b = {9: 'bt', 0xB: 'bf', 0xD: 'bt/s', 0xF: 'bf/s'}.get(sub)
        if b: return f'{b} 0x{pc + 4 + s8(d8) * 2:x}'
    if t == 9:
        a = pc + 4 + d8 * 2; v = u16(a)
        return f'mov.w @(0x{a:x}),{R(n)}   ; =0x{v:04x} ({v - 65536 if v & 0x8000 else v})'
    if t == 0xA: return f'bra 0x{pc + 4 + s12(op & 0xFFF) * 2:x}'
    if t == 0xB: return f'bsr 0x{pc + 4 + s12(op & 0xFFF) * 2:x}'
    if t == 0xC:
        sub = (op >> 8) & 15
        names = {0: f'mov.b r0,@({d8},gbr)', 1: f'mov.w r0,@({d8 * 2},gbr)', 2: f'mov.l r0,@({d8 * 4},gbr)', 3: f'trapa #{d8}',
                 4: f'mov.b @({d8},gbr),r0', 5: f'mov.w @({d8 * 2},gbr),r0', 6: f'mov.l @({d8 * 4},gbr),r0', 7: f'mova @(0x{(pc & ~3) + 4 + d8 * 4:x}),r0',
                 8: f'tst #{d8},r0', 9: f'and #{d8},r0', 0xA: f'xor #{d8},r0', 0xB: f'or #{d8},r0'}
        if sub in names: return names[sub]
    if t == 0xD:
        a = (pc & ~3) + 4 + d8 * 4; v = u32(a)
        return f'mov.l @(0x{a:x}),{R(n)}   ; =0x{v:08x}'
    if t == 0xE: return f'mov #{s8(i8)},{R(n)}'
    return f'.word 0x{op:04x}'
for pc in range(lo, hi, 2):
    op = u16(pc)
    print(f'{pc:06x}: {op:04x}  {dis(pc, op)}')
