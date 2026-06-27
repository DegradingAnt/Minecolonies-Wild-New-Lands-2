# Batch: Downloads/<pose>.png (isolated traceur on flat bg) -> clean, COLOR-NORMALIZED 24px node icons.
# keys bg -> keeps largest blob (drops shadow/strays) -> maps every pixel to the canonical traceur palette -> 24px.
from PIL import Image, ImageDraw
from collections import deque
import os
DL=r"C:/Users/linde/Downloads"
OUT=r"C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version/_dev/art-assets/skill-icons/parkour"
os.makedirs(OUT,exist_ok=True)
POSES=["sprint","jump","leap","roll","vault","wallrun","wallcling","climb","slide","hang","flip"]
PAL=[(42,48,90),(26,30,58),(70,78,120),(232,120,42),(176,84,26),(228,178,130),(186,138,96),(22,20,30),(232,236,244)]
def nearest(c): return min(PAL,key=lambda p:(p[0]-c[0])**2+(p[1]-c[1])**2+(p[2]-c[2])**2)
def near(a,b,t): return sum((a[i]-b[i])**2 for i in range(3))<t*t
def to_icon(path, normalize=True):
    im=Image.open(path).convert("RGBA"); W,H=im.size; px=im.load()
    corners=[im.getpixel((2,2))[:3],im.getpixel((W-3,2))[:3],im.getpixel((2,H-3))[:3],im.getpixel((W-3,H-3))[:3]]
    mask=[[(not any(near(px[x,y][:3],c,62) for c in corners)) for x in range(W)] for y in range(H)]
    step=3; seen=[[False]*W for _ in range(H)]; best=None; bestn=0
    for sy in range(0,H,step):
        for sx in range(0,W,step):
            if mask[sy][sx] and not seen[sy][sx]:
                q=deque([(sx,sy)]); seen[sy][sx]=True; cells=[]
                while q:
                    x,y=q.popleft(); cells.append((x,y))
                    for dx,dy in ((step,0),(-step,0),(0,step),(0,-step)):
                        nx,ny=x+dx,y+dy
                        if 0<=nx<W and 0<=ny<H and mask[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx]=True; q.append((nx,ny))
                if len(cells)>bestn: bestn=len(cells); best=cells
    if not best: return None
    xs=[c[0] for c in best]; ys=[c[1] for c in best]
    fig=im.crop((min(xs),min(ys),max(xs)+1,max(ys)+1)); fp=fig.load()
    for y in range(fig.height):
        for x in range(fig.width):
            c=fp[x,y]
            if c[3]<128 or any(near(c[:3],cc,62) for cc in corners): fp[x,y]=(0,0,0,0)
            elif normalize: fp[x,y]=nearest(c[:3])+(255,)
    s=24/max(fig.size); r=fig.resize((max(1,int(fig.width*s)),max(1,int(fig.height*s))),Image.LANCZOS)
    cv=Image.new("RGBA",(24,24),(0,0,0,0)); cv.alpha_composite(r,((24-r.width)//2,(24-r.height)//2)); return cv
done=[]
for p in POSES:
    src=os.path.join(DL,p+".png")
    if os.path.exists(src):
        ic=to_icon(src)
        if ic: ic.save(os.path.join(OUT,p+".png")); done.append((p,ic))
def framed(ic):
    S=32; f=Image.new("RGBA",(S,S),(0,0,0,0)); d=ImageDraw.Draw(f)
    d.rounded_rectangle([1,1,S-2,S-2],radius=5,fill=(40,48,60,255),outline=(96,112,130,255),width=2)
    f.alpha_composite(ic,(4,4)); return f
if done:
    up=9; pad=8; row=Image.new("RGBA",(len(done)*(32+pad)+pad,32+2*pad),(24,28,36,255)); x=pad
    for _,ic in done: row.alpha_composite(framed(ic),(x,pad)); x+=32+pad
    row.resize((row.width*up,row.height*up),Image.NEAREST).convert("RGB").save(OUT+"/_preview.png")
print("processed:",[p for p,_ in done])
