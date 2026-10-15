import cv2, numpy as np, json, os, sys
from photos import path
BH=600          # rectified band height (measuring canvas)
H=340           # output strip height
_c={}
def img(pid):
    if pid not in _c: _c[pid]=cv2.imread(path(pid))
    return _c[pid]
def J(f, d=None):
    return json.load(open(f)) if os.path.exists(f) else (d if d is not None else {})
def save(f, o): json.dump(o, open(f,'w'), ensure_ascii=False, indent=1)
def font(): return cv2.FONT_HERSHEY_SIMPLEX

def ov(pid, box=None, width=1400, step=100, out=None):
    im=img(pid); x0,y0,x1,y1=box or (0,0,im.shape[1],im.shape[0])
    c=im[y0:y1,x0:x1]; sc=width/(x1-x0); c=cv2.resize(c,(width,int((y1-y0)*sc)),interpolation=cv2.INTER_AREA)
    for x in range((x0//step+1)*step,x1,step):
        X=int((x-x0)*sc); big=x%(step*2)==0 if step<100 else True
        cv2.line(c,(X,0),(X,c.shape[0]),(255,255,0) if x%500 else (0,0,255),1)
        cv2.putText(c,str(x),(X+2,14),font(),0.45,(0,255,255),1)
    for y in range((y0//step+1)*step,y1,step):
        Y=int((y-y0)*sc)
        cv2.line(c,(0,Y),(c.shape[1],Y),(0,255,0) if y%500 else (0,0,255),1)
        cv2.putText(c,str(y),(2,Y-2),font(),0.45,(0,255,255),1)
    out=out or f'v/ov_{pid}.jpg'; cv2.imwrite(out,c,[cv2.IMWRITE_JPEG_QUALITY,82]); return out

def qdims(q):
    q=np.array(q,float).reshape(4,2)   # TL TR BR BL
    w=(np.linalg.norm(q[1]-q[0])+np.linalg.norm(q[2]-q[3]))/2
    h=(np.linalg.norm(q[3]-q[0])+np.linalg.norm(q[2]-q[1]))/2
    return w,h
def band_h(q):
    w,h=qdims(q); BW=int(round(BH*w/h))
    M=cv2.getPerspectiveTransform(np.float32(np.array(q).reshape(4,2)),np.float32([(0,0),(BW,0),(BW,BH),(0,BH)]))
    return M,BW
def band_img(pid,q):
    M,BW=band_h(q)
    return cv2.warpPerspective(img(pid),M,(BW,BH),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)

def band_view(pid,lv,q,chunk=None,out=None,x_from=0,x_to=None):
    b=band_img(pid,q); BWf=b.shape[1]
    x_to=x_to or BWf
    if chunk is None:
        import math; n=math.ceil((x_to-x_from)/1250); chunk=math.ceil((x_to-x_from)/n)
    pad=26; outs=[]
    for c0 in range(x_from,x_to,chunk):
        c1=min(x_to,c0+chunk)
        v=cv2.copyMakeBorder(b[:,c0:c1],pad,0,0,0,cv2.BORDER_CONSTANT,value=(30,30,30))
        for x in range((c0//10)*10,c1,10):
            if x<c0: continue
            X=x-c0; maj=x%50==0
            cv2.line(v,(X,pad if maj else pad),(X,pad+(BH if maj else 14)),(0,255,255) if x%100==0 else ((255,0,255) if maj else (200,200,200)),1)
            if x%50==0: cv2.putText(v,str(x),(X+1,18),font(),0.42,(0,255,255),1)
        for y in range(50,BH,50):
            cv2.line(v,(0,pad+y),(12,pad+y),(0,255,0),1); cv2.putText(v,str(y),(14,pad+y+4),font(),0.38,(0,255,0),1)
        f=out or f'v/b_{pid}_{lv}_{c0}.jpg'; cv2.imwrite(f,v,[cv2.IMWRITE_JPEG_QUALITY,85]); outs.append(f)
    return outs, BWf

def warp_item(pid,quad):
    q=np.float32(np.array(quad).reshape(4,2)); w,h=qdims(q); W=max(2,int(round(H*w/h)))
    M=cv2.getPerspectiveTransform(q,np.float32([(0,0),(W,0),(W,H),(0,H)]))
    return cv2.warpPerspective(img(pid),M,(W,H),flags=cv2.INTER_AREA,borderMode=cv2.BORDER_REPLICATE)

def band_to_orig(q,pts):
    M,_=band_h(q); Mi=np.linalg.inv(M)
    p=np.array(pts,float).reshape(-1,1,2)
    return cv2.perspectiveTransform(p,Mi).reshape(-1,2)

def snap_x(b,x,r=5,y0=None,y1=None):
    """move a boundary to the strongest vertical edge within +-r px (band coords)"""
    g=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY).astype(float)
    y0=y0 if y0 is not None else int(BH*0.35); y1=y1 or BH-8
    gx=np.abs(np.diff(g[y0:y1],axis=1)).sum(0)
    lo=max(1,int(x-r)); hi=min(g.shape[1]-2,int(x+r))
    if hi<=lo: return x
    k=lo+int(np.argmax(gx[lo-1:hi]))  # edge between k-1 and k -> boundary at k
    return k

def edges(pid,lv,x,r=30,y0=None,y1=None,k=4):
    W=J('work.json'); b=band_img(pid,W['bands'][pid][lv])
    g=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY).astype(float)
    y0=y0 or int(BH*0.3); y1=y1 or int(BH*0.85)
    gx=np.abs(np.diff(g[y0:y1],axis=1)).mean(0)
    lo=max(0,x-r); hi=min(len(gx)-1,x+r)
    seg=gx[lo:hi]; idx=np.argsort(seg)[::-1]
    picks=[]
    for j in idx:
        if all(abs(j-p)>4 for p in picks): picks.append(j)
        if len(picks)==k: break
    return [(lo+p+1, round(seg[p],1)) for p in picks]

def valleys(pid,lv,x,r=30,y0=None,y1=None,k=3):
    """darkest thin columns (gaps between books) near x, in band coords"""
    W=J('work.json'); b=band_img(pid,W['bands'][pid][lv])
    g=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY).astype(float)
    y0=y0 or int(BH*0.15); y1=y1 or int(BH*0.92)
    col=np.percentile(g[y0:y1],70,axis=0)          # a gap is dark over most of its height
    col=np.convolve(col,np.ones(3)/3,'same')
    lo=max(1,x-r); hi=min(len(col)-2,x+r)
    mins=[(j, col[j]) for j in range(lo,hi) if col[j]<=col[j-1] and col[j]<=col[j+1]]
    base=np.median(col[lo:hi])
    mins=sorted(mins,key=lambda t:t[1])[:k]
    return [(int(j), round(base-v,1)) for j,v in mins]

def zoom(pid,lv,x0,x1,y0=0,y1=None,s=2.0,out=None):
    W=J('work.json'); b=band_img(pid,W['bands'][pid][lv]); y1=y1 or BH
    c=b[y0:y1,x0:x1]; c=cv2.resize(c,None,fx=s,fy=s,interpolation=cv2.INTER_CUBIC)
    pad=18; c=cv2.copyMakeBorder(c,pad,0,0,0,cv2.BORDER_CONSTANT,value=(30,30,30))
    for x in range((x0//5+1)*5,x1,5):
        X=int((x-x0)*s); m=x%10==0
        cv2.line(c,(X,pad),(X,pad+(c.shape[0] if x%50==0 else (10 if m else 5))),(0,255,255) if x%50==0 else (255,0,255),1)
        if m: cv2.putText(c,str(x),(X+1,13),font(),0.38,(0,255,255),1)
    for y in range((y0//25+1)*25,y1,25):
        Y=pad+int((y-y0)*s); cv2.line(c,(0,Y),(10,Y),(0,255,0),1); cv2.putText(c,str(y),(12,Y+4),font(),0.38,(0,255,0),1)
    out=out or f'v/z_{pid}_{lv}_{x0}.jpg'; cv2.imwrite(out,c,[cv2.IMWRITE_JPEG_QUALITY,85]); return out

def orig_to_band(q,pts):
    M,_=band_h(q); p=np.array(pts,float).reshape(-1,1,2)
    return cv2.perspectiveTransform(p,M).reshape(-1,2)
def bview(pid,lv,ox0,ox1):
    """band view of the part of the band between original x ox0..ox1"""
    W=J('work.json'); q=W['bands'][pid][lv]
    ym=(q[1]+q[7])/2*0.5+(q[3]+q[5])/2*0.5
    b=orig_to_band(q,[(ox0,ym),(ox1,ym)])
    x0=max(0,int(b[0][0])-10); x1=int(b[1][0])+10
    return band_view(pid,lv,q,x_from=x0,x_to=x1)

def stack(files,out,cols=2,gap=8):
    ims=[cv2.imread(f) for f in files]
    rows=[ims[i:i+cols] for i in range(0,len(ims),cols)]
    W=max(sum(i.shape[1]+gap for i in r) for r in rows)
    outs=[]
    for r in rows:
        h=max(i.shape[0] for i in r)
        x=np.hstack([cv2.copyMakeBorder(i,0,h-i.shape[0],0,gap,cv2.BORDER_CONSTANT) for i in r])
        outs.append(cv2.copyMakeBorder(x,0,gap,0,W-x.shape[1],cv2.BORDER_CONSTANT))
    cv2.imwrite(out,np.vstack(outs)); return out

def rot_M(c,ang):
    return cv2.getRotationMatrix2D((float(c[0]),float(c[1])),float(ang),1.0)
def rot_view(pid,c,ang,box,s=1.0,step=10,out=None):
    """rotate the photo by ang (deg, counter-clockwise) about c, show box=(x0,y0,x1,y1) in rotated coords with grid"""
    M=rot_M(c,ang); im=cv2.warpAffine(img(pid),M,(img(pid).shape[1],img(pid).shape[0]),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    x0,y0,x1,y1=box; cr=cv2.resize(im[y0:y1,x0:x1],None,fx=s,fy=s,interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
    pad=18; cr=cv2.copyMakeBorder(cr,pad,0,0,0,cv2.BORDER_CONSTANT,value=(30,30,30))
    for x in range((x0//step+1)*step,x1,step):
        X=int((x-x0)*s); maj=x%50==0
        cv2.line(cr,(X,pad),(X,pad+(cr.shape[0] if maj else 8)),(0,255,255) if maj else (255,0,255),1)
        if x%50==0: cv2.putText(cr,str(x),(X+1,13),font(),0.4,(0,255,255),1)
    for y in range((y0//50+1)*50,y1,50):
        Y=pad+int((y-y0)*s); cv2.line(cr,(0,Y),(12,Y),(0,255,0),1); cv2.putText(cr,str(y),(14,Y+4),font(),0.4,(0,255,0),1)
    out=out or f'v/r_{pid}.jpg'; cv2.imwrite(out,cr,[cv2.IMWRITE_JPEG_QUALITY,85]); return out
def rot_quad(c,ang,x0,y0,x1,y1):
    M=np.vstack([rot_M(c,ang),[0,0,1]]); Mi=np.linalg.inv(M)
    p=np.array([[x0,y0,1],[x1,y0,1],[x1,y1,1],[x0,y1,1]],float).T
    o=(Mi@p)[:2].T
    return o.flatten().tolist()

def rot_pts(c,ang,pts):
    M=np.vstack([rot_M(c,ang),[0,0,1]]); Mi=np.linalg.inv(M)
    p=np.array([[x,y,1] for x,y in pts],float).T
    return [round(v,1) for v in (Mi@p)[:2].T.flatten().tolist()]
