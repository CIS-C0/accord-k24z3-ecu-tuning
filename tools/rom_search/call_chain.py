# call_chain.py <bin> <func_hex>: walks callers upward. For each function: bsr/bra callers and 32-bit words equal to
# its address; a word inside a literal pool is mapped to the "mov.l @(disp,PC)" that loads it, and that caller's start
# is the first register push (2Fx6 / 4F22 / 4F12 / 4F13) of the block found scanning back. Words not loaded by any
# mov.l are reported as data (task / vector tables). CPU address = file offset + 0x8000.
import struct, sys
b = open(sys.argv[1], 'rb').read()
B = 0x8000


def w(a):
    return struct.unpack_from('>H', b, a - B)[0]


def is_push(o):
    return o & 0xFF0F == 0x2F06 or o in (0x4F22, 0x4F12, 0x4F13)


def func_start(a):
    p = a
    while p > a - 0x3000:
        if w(p) == 0x4F22 or w(p) & 0xFF0F == 0x2F06:
            s = p
            while is_push(w(s - 2)):
                s -= 2
            if not is_push(w(s - 2)):
                return s
        p -= 2
    return None


def callers(t):
    out = []
    for a in range(B, B + len(b) - 1, 2):
        o = w(a)
        if o >> 12 in (0xA, 0xB):
            d = o & 0xFFF
            d = d - 0x1000 if d & 0x800 else d
            if a + 4 + d * 2 == t:
                out.append(('bsr' if o >> 12 == 0xB else 'bra', a, func_start(a)))
    p = struct.pack('>I', t)
    i = b.find(p)
    while i >= 0:
        pa = i + B
        ld = None
        for a in range(max(B, pa - 1020), pa, 2):
            o = w(a)
            if o >> 12 == 0xD and (a & ~3) + 4 + (o & 0xFF) * 4 == pa:
                ld = a
                break
        out.append(('mov.l', ld, func_start(ld)) if ld else ('data word', pa, None))
        i = b.find(p, i + 1)
    return out


seen, todo = set(), [(int(sys.argv[1 + 1], 16), 0)]
while todo:
    f, depth = todo.pop()
    if f in seen or depth > 8:
        continue
    seen.add(f)
    for kind, a, s in callers(f):
        print('  ' * depth + f'0x{f:05X} <- {kind} at 0x{a:05X}' + (f' in func 0x{s:05X}' if s else ''))
        if s:
            todo.append((s, depth + 1))
