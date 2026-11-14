# scan the ROM for 1D descriptors (count, 3 fmt bytes, axis ptr, data ptr) with a long increasing axis and a
# steeply increasing data curve (MAF transfer function candidates)
import struct, sys
b = open(sys.argv[1], 'rb').read()
R = 0x8000
u16 = lambda a: struct.unpack_from('>H', b, a - R)[0]
u32 = lambda a: struct.unpack_from('>I', b, a - R)[0]
minn = int(sys.argv[2]) if len(sys.argv) > 2 else 12
out = []
for a in range(R, R + len(b) - 12, 2):
    n = b[a - R]
    if n < minn or n > 200:
        continue
    ax, dt = u32(a + 4), u32(a + 8)
    if not (R <= ax < R + len(b) - 2 * n and R <= dt < R + len(b) - 2 * n):
        continue
    axis = [u16(ax + 2 * i) for i in range(n)]
    if any(axis[i] >= axis[i + 1] for i in range(n - 1)):
        continue
    data = [u16(dt + 2 * i) for i in range(n)]
    inc = all(data[i] <= data[i + 1] for i in range(n - 1))
    out.append((a, n, b[a - R + 1:a - R + 4].hex(), ax, dt, axis, data, inc))
for a, n, fmt, ax, dt, axis, data, inc in out:
    if inc and data[-1] > 20 * max(data[0], 1):
        print(f'desc {a:X} n={n} fmt={fmt} axis {ax:X} {axis[0]}..{axis[-1]} data {dt:X} {data[0]}..{data[-1]}')
        print(f'   axis {axis}')
        print(f'   data {data}')
print(len(out), 'descriptors with n >=', minn)
