import struct,sys
b=open(sys.argv[1],'rb').read()
for i in range(0,len(b)-3,2):
    v=struct.unpack_from('>I',b,i)[0]
    if 0x16800<=v<=0x16960: print(hex(i+0x8000),hex(v))
for a in range(0x16860,0x16900,4): print(hex(a), '%08x'%struct.unpack_from('>I',b,a-0x8000)[0])
