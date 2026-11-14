import struct,sys
b=open(sys.argv[1],'rb').read()
for a in (0xb7c8,0xb7ca,0xb7cc,0xb88c+8,0xb88c+10):
    print(hex(a), hex(struct.unpack_from('>H',b,a-0x8000)[0]))
