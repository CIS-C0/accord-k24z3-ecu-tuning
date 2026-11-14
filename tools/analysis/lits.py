import struct,sys
b=open(sys.argv[1],'rb').read()
for t in range(0xFFFF45F0,0xFFFF4610,2):
    for v in (t,):
        p=struct.pack('>I',v); i=b.find(p)
        while i>=0:
            if i%2==0: print(hex(v),'literal at',hex(i+0x8000))
            i=b.find(p,i+1)
for t in (0xFFFF510A,0xFFFF5102,0xFFFF9304,0xFFFF9300):
    p=struct.pack('>I',t); i=b.find(p)
    while i>=0:
        print(hex(t),'literal at',hex(i+0x8000)); i=b.find(p,i+1)
