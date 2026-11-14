import struct,sys
b=open(sys.argv[1],'rb').read()
rng=list(range(0xFFFF50C0,0xFFFF510C,2))+list(range(0xFFFF92C0,0xFFFF9306,2))
for t in rng:
    p=struct.pack('>I',t); i=b.find(p); out=[]
    while i>=0:
        if i%2==0: out.append(hex(i+0x8000))
        i=b.find(p,i+1)
    if out: print('L32',hex(t),out)
for t in range(0x92C0,0x9306,2):
    p=struct.pack('>H',t); i=b.find(p); out=[]
    while i>=0:
        if i%2==0: out.append(hex(i+0x8000))
        i=b.find(p,i+1)
    if out: print('H16',hex(t),out)
