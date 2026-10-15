import cv2, numpy as np, json, os, sys, collections
import geo
D='/tmp/claude-0/-home-claude-du-library/1b0dbdb4-5408-5e23-bb28-311d8f83a541/scratchpad/live21/shelves/'
def items(lv):
    E=geo.J('dbedit.json',{})
    if lv in E: return E[lv]
    d=json.load(open(D+lv+'.json')); return d.get('data',d)['items']
def L(a,b): return float(np.hypot(a[0]-b[0],a[1]-b[1]))
def oquads(s,bands,lv):
    """original-photo quads (TL,TR,BR,BL) for a segment; a 'fan' segment gives one quad per volume"""
    if 'o' in s: return [np.array(s['o'],float).reshape(4,2)]
    if 'os' in s: return [np.array(o,float).reshape(4,2) for o in s['os']]
    def tob(pts): return geo.band_to_orig(bands[s['p']][lv],pts)
    if 'q' in s:
        q=s['q']; return [tob([(q[0],q[1]),(q[2],q[3]),(q[4],q[5]),(q[6],q[7])])]
    # fan: leaning books, each volume straightened on its own
    xt,xb=s['xt'],s['xb']; (ta,tya,tb,tyb)=s['top']; (ba,bya,bb,byb)=s['bot']
    yt=lambda x: tya+(tyb-tya)*(x-ta)/((tb-ta) or 1); yb=lambda x: bya+(byb-bya)*(x-ba)/((bb-ba) or 1)
    out=[]
    for k in range(len(xt)-1):
        out.append(tob([(xt[k],yt(xt[k])),(xt[k+1],yt(xt[k+1])),(xb[k+1],yb(xb[k+1])),(xb[k],yb(xb[k]))]))
    return out
def seg_h(s,bands,lv):
    qs=oquads(s,bands,lv)
    return float(np.mean([(L(q[0],q[3])+L(q[1],q[2]))/2 for q in qs]))
def build(lv, qc=True, write=True):
    W=geo.J('work.json'); segs=W['segs'].get(lv,[]); bands=W['bands']
    its=items(lv)
    # --- per-photo scale, linked through items seen in more than one photo
    hs=collections.defaultdict(dict)
    for s in segs: hs[s['i']].setdefault(s['p'],[]).append(seg_h(s,bands,lv))
    photos=sorted({s['p'] for s in segs}, key=lambda p: -sum(1 for s in segs if s['p']==p and not s.get('meas')))
    scale={photos[0]:1.0} if photos else {}
    changed=True
    while changed:
        changed=False
        for i,d in hs.items():
            known=[p for p in d if p in scale]
            if not known: continue
            ref=np.mean([np.mean(d[p])*scale[p] for p in known])
            for p in d:
                if p not in scale: scale[p]=ref/np.mean(d[p]); changed=True
    miss=[p for p in photos if p not in scale]
    if miss: print('!! photos not linked by a shared book:',miss)
    # --- strips
    out=[]; report=[]
    os.makedirs(f'out/spines/{lv}',exist_ok=True)
    for i,it in enumerate(its):
        ss=[s for s in segs if s['i']==i and not s.get('meas')]
        if not ss: report.append(f'{i}: no photo'); continue
        tot=sum(s['n'] for s in ss)
        if tot!=it['n']: report.append(f"{i}: segments hold {tot} vols but map says {it['n']}")
        ims=[]; hh=[]
        for s in sorted(ss,key=lambda s:-s['m']):   # physical left -> right
            qs=oquads(s,bands,lv)
            if ('xt' in s or 'os' in s) and len(qs)!=s['n']: report.append(f"{i}: fan has {len(qs)} volumes but segment says {s['n']}")
            for o in qs: ims.append(geo.warp_item(s['p'],o.flatten().tolist()))
            hh.append(seg_h(s,bands,lv)*scale.get(s['p'],1))
        im=np.hstack(ims) if len(ims)>1 else ims[0]
        out.append((i,it,im,float(np.mean(hh))))
    if not out: return
    hmax=max(o[3] for o in out)
    P=geo.J('photos.json')
    # drop this level's old entries
    for k in list(P):
        P[k]=[e for e in P[k] if e['s']!=lv]
        if not P[k]: del P[k]
    for i,it,im,h in out:
        r=round(1.14*h/hmax,3); fn=f'spines/{lv}/{i+1:02d}.jpg'
        if write:
            cv2.imwrite('out/'+fn,im,[cv2.IMWRITE_JPEG_QUALITY,78,cv2.IMWRITE_JPEG_PROGRESSIVE,1])
        P.setdefault(it['b'],[]).append({'s':lv,'i':i,'n':it['n'],'src':fn,'w':int(im.shape[1]),'h':int(im.shape[0]),'r':r})
    if write: geo.save('photos.json',P)
    for r_ in report: print(lv,r_)
    if qc: qcimg(lv,out,hmax)
    return out
def qcimg(lv,out,hmax):
    QH=230; tiles=[]
    for i,it,im,h in reversed(out):            # physical left -> right
        th=int(QH*h/hmax); tw=max(2,int(im.shape[1]*th/im.shape[0]))
        t=cv2.resize(im,(tw,th),interpolation=cv2.INTER_AREA)
        c=np.full((QH+22,tw+4,3),40,np.uint8); c[22+QH-th:22+QH,2:2+tw]=t
        cv2.putText(c,str(i),(3,16),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,255),1)
        tiles.append(c)
    rows=[];cur=[];w=0
    for t in tiles:
        if w+t.shape[1]>1500 and cur: rows.append(cur);cur=[];w=0
        cur.append(t);w+=t.shape[1]
    rows.append(cur)
    Wd=max(sum(t.shape[1] for t in r) for r in rows)
    sheet=np.full((len(rows)*(QH+26),Wd,3),25,np.uint8)
    for k,r in enumerate(rows):
        x=0
        for t in r: sheet[k*(QH+26):k*(QH+26)+t.shape[0],x:x+t.shape[1]]=t; x+=t.shape[1]
    cv2.imwrite(f'v/qc_{lv}.jpg',sheet,[cv2.IMWRITE_JPEG_QUALITY,85])
if __name__=='__main__':
    for lv in sys.argv[1:]: build(lv)
