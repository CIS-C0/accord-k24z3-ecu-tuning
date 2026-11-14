import struct, sys
b = open(sys.argv[1], 'rb').read(); base = 0x8000
def h(a, n): return list(struct.unpack_from(f'>{n}h', b, a - base))
def u(a, n): return list(b[a - base:a - base + n])
print('Y 0x18EA8', h(0x18EA8, 20)); print('Y 0x18ED0', h(0x18ED0, 20)); print('Y 0x18EF8', h(0x18EF8, 20)); print('X 0x18F20', h(0x18F20, 10))
for name, a in (('B9EC 16D5C', 0x16D5C), ('BA00 16E24', 0x16E24), ('BA14 16EEC', 0x16EEC)):
    print(name)
    d = u(a, 200)
    for r in range(20): print(' '.join(f'{x:3}' for x in d[r * 10:r * 10 + 10]))
    print('alt 10 rows');
    for r in range(10): print(' '.join(f'{x:3}' for x in d[r * 20:r * 20 + 20]))
