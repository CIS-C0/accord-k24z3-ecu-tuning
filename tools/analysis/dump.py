import struct,sys
b=open(sys.argv[1],'rb').read()
for a in range(0x16900,0x16960,4): print(hex(a), ' '.join('%08x'%struct.unpack_from('>I',b,a-0x8000+i)[0] for i in (0,)))
