import struct,sys
b=open(sys.argv[1],'rb').read()
for t in (0x9304,0x510A,0x5108,0x9300,0x9302,0x9306):
    p=struct.pack('>H',t); i=b.find(p); out=[]
    while i>=0:
        if i%2==0: out.append(hex(i+0x8000))
        i=b.find(p,i+1)
    print(hex(t), out)
