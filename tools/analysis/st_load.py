import csv,sys,glob,statistics as st
bins=[('idle <1000 rpm',lambda n,m:n<1000),('cruise MAP<50',lambda n,m:n>=1000 and m<50),('mid MAP 50-70',lambda n,m:n>=1000 and 50<=m<70),('load MAP>=70',lambda n,m:n>=1000 and m>=70)]
for name,pat in [('1/11 v6',sys.argv[1]+'/*.csv'),('7/11',sys.argv[2]+'/*.csv')]:
    print('==',name)
    for purge in ('all','purge 0'):
        for bn,f in bins:
            v=[]
            for p in glob.glob(pat):
                for r in csv.DictReader(open(p)):
                    try:
                        if r['FSS']!='2' or int(r['ECT'])-40<80: continue
                        n=int(r['NE'])/4; m=int(r['MAP'])
                        if purge=='purge 0' and int(r['DPCS'])!=0: continue
                        if f(n,m): v.append(int(r['KLAF'])/128)
                    except: continue
            print(f"  {purge:8} {bn:16} n {len(v):5} ST {st.median(v) if len(v)>=20 else float('nan'):.3f}")
