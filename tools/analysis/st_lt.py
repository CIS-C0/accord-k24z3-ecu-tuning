import csv,sys,glob,statistics as st
for name,pat in [('25/10',sys.argv[1]+'/25102026*.csv'),('1/11 v3',sys.argv[1]+'/01112026*.csv'),('1/11 v6',sys.argv[2]+'/*.csv'),('7/11',sys.argv[3]+'/*.csv')]:
    st_,lt_,tot=[],[],[]
    for p in glob.glob(pat):
        for r in csv.DictReader(open(p)):
            try:
                if r['FSS']!='2' or int(r['ECT'])-40<80: continue
                a=int(r['KLAF'])/128; b=int(r['KLAFAVE'])/128
            except: continue
            st_.append(a); lt_.append(b); tot.append(a*b)
    if st_: print(f"{name:8} n {len(st_):5}  ST med {st.median(st_):.3f} [p10 {sorted(st_)[len(st_)//10]:.3f} p90 {sorted(st_)[9*len(st_)//10]:.3f}]  LT med {st.median(lt_):.3f}  STxLT {st.median(tot):.3f}")
