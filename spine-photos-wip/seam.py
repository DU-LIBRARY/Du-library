import cv2, numpy as np, sys, geo, mk
def seams(lv, i, half=260):
    W=geo.J('work.json'); segs=[s for s in W['segs'][lv] if s['i']==i and not s.get('meas')]
    segs=sorted(segs,key=lambda s:-s['m'])
    ws=[]
    for s in segs:
        ws.append(sum(geo.warp_item(s['p'],o.flatten().tolist()).shape[1] for o in mk.oquads(s,W['bands'],lv)))
    im=cv2.imread(f'out/spines/{lv}/{i+1:02d}.jpg'); x=0; crops=[]
    for w in ws[:-1]:
        x+=w; c=im[:,max(0,x-half):x+half].copy(); cv2.line(c,(min(half,x),0),(min(half,x),12),(0,0,255),2); crops.append(c)
    if crops:
        out=np.vstack([cv2.copyMakeBorder(c,0,6,0,2*half-c.shape[1],cv2.BORDER_CONSTANT) for c in crops])
        cv2.imwrite(f'v/seam_{lv}_{i}.jpg',out,[cv2.IMWRITE_JPEG_QUALITY,85])
if __name__=='__main__': seams(sys.argv[1],int(sys.argv[2]))
