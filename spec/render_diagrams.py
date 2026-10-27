"""Render editable draw.io nodes/edges to SVG previews; no external dependencies.

Routes are written back as draw.io waypoints. SVG previews are for reading;
the draw.io file remains the editable source. Labels and connections are shared.
"""
from pathlib import Path
import xml.etree.ElementTree as E
import re, html, heapq, math

ROOT = Path(__file__).resolve().parent
S = 10

def width(text, size=15):
    return sum(1 if ord(c)>255 else .56 for c in text)*size

def lines(value, max_width, size):
    raw = html.unescape(re.sub('<[^>]+>', '', re.sub(r'<br\s*/?>', '\n', value)))
    result=[]
    for line in raw.splitlines():
        buf=''
        for char in line:
            if width(buf+char,size)>max_width and buf:
                result.append(buf);buf=''
            buf+=char
        result.append(buf)
    return result

def anchor(b, direction):
    x,y,w,h=b
    if direction==0:return (x+w/2,y), (x+w/2,y-15),(.5,0)
    if direction==1:return (x+w,y+h/2), (x+w+15,y+h/2),(1,.5)
    if direction==2:return (x+w/2,y+h), (x+w/2,y+h+15),(.5,1)
    return (x,y+h/2), (x-15,y+h/2),(0,.5)

def grid(p):return tuple(round(v/S) for v in p)
def compact(points):
    out=[]
    for p in points:
        if out and p==out[-1]:continue
        while len(out)>1 and ((out[-2][0]==out[-1][0]==p[0]) or (out[-2][1]==out[-1][1]==p[1])):out.pop()
        out.append(p)
    return out

def route(start,end,blocked,used,W,H):
    a,b=grid(start),grid(end)
    q=[(0,0,a,4)]; costs={(a,4):0}; previous={}
    final=None
    while q:
        _,cost,p,d=heapq.heappop(q)
        if cost!=costs.get((p,d)):continue
        if p==b:final=(p,d);break
        for nd,(dx,dy) in enumerate([(0,-1),(1,0),(0,1),(-1,0)]):
            n=(p[0]+dx,p[1]+dy)
            if not(2<=n[0]<=W//S-2 and 2<=n[1]<=H//S-2):continue
            if n in blocked and n not in (a,b):continue
            c=cost+1+(2 if d!=4 and d!=nd else 0)+used.get(n,0)*.2
            key=(n,nd)
            if c<costs.get(key,1e12):
                costs[key]=c;previous[key]=(p,d)
                h=abs(n[0]-b[0])+abs(n[1]-b[1])
                heapq.heappush(q,(c+h,c,n,nd))
    if final is None:raise RuntimeError('No clear edge route')
    path=[];key=final
    while key in previous:path.append(key[0]);key=previous[key]
    path.append(a);path.reverse()
    return compact([(x*S,y*S) for x,y in path]),costs[final],path

def main():
    path=ROOT/'keel-delivery.drawio'
    tree=E.parse(path);outdir=ROOT/'diagrams';outdir.mkdir(exist_ok=True)
    total=0
    for pi,page in enumerate(tree.getroot(),1):
        graph=page.find('mxGraphModel');W=int(graph.get('pageWidth'));H=int(graph.get('pageHeight'))
        cells=graph.find('root').findall('mxCell')
        nodes={c.get('id'):c for c in cells if c.get('vertex')=='1'}
        boxes={k:tuple(float(c.find('mxGeometry').get(a,0)) for a in ['x','y','width','height']) for k,c in nodes.items()}
        blocked=set()
        for x,y,w,h in boxes.values():
            for i in range(math.ceil((x-4)/S),math.floor((x+w+4)/S)+1):
                for j in range(math.ceil((y-4)/S),math.floor((y+h+4)/S)+1):blocked.add((i,j))
        used={};edges=[]
        for c in cells:
            if c.get('edge')!='1':continue
            sb,tb=boxes[c.get('source')],boxes[c.get('target')]
            dx=(tb[0]+tb[2]/2)-(sb[0]+sb[2]/2);dy=(tb[1]+tb[3]/2)-(sb[1]+sb[3]/2)
            primary=(1 if dx>=0 else 3) if abs(dx)>abs(dy) else (2 if dy>=0 else 0)
            candidates=[]
            # Try the direct pair first, then orthogonal alternatives.
            for sd,td in [(primary,(primary+2)%4),((primary+1)%4,(primary+2)%4),((primary+3)%4,(primary+2)%4),(primary,(primary+1)%4),(primary,(primary+3)%4)]:
                a,ao,af=anchor(sb,sd);b,bo,bf=anchor(tb,td)
                if grid(ao) in blocked or grid(bo) in blocked:continue
                try:r,cost,raw=route(ao,bo,blocked,used,W,H)
                except RuntimeError:continue
                candidates.append((cost,r,raw,a,b,af,bf))
                if len(candidates)==1 and cost<((abs(dx)+abs(dy))/S+8):break
            if not candidates:raise RuntimeError(f'Edge routing failed: page {pi} {c.get("id")}')
            _,r,raw,a,b,af,bf=min(candidates,key=lambda z:z[0])
            for p in raw:used[p]=used.get(p,0)+1
            # Preserve orthogonal connection from exact port to snapped grid.
            ap=[a,(a[0],r[0][1]),r[0]] if af[0]==.5 else [a,(r[0][0],a[1]),r[0]]
            bp=[r[-1],(b[0],r[-1][1]),b] if bf[0]==.5 else [r[-1],(r[-1][0],b[1]),b]
            points=compact(ap+r+bp)
            style=c.get('style','')
            style=re.sub(r'(exitX|exitY|entryX|entryY|exitPerimeter|entryPerimeter)=[^;]*;', '',style)
            c.set('style',style+f'exitX={af[0]};exitY={af[1]};entryX={bf[0]};entryY={bf[1]};exitPerimeter=0;entryPerimeter=0;')
            geom=c.find('mxGeometry')
            for old in list(geom):geom.remove(old)
            arr=E.SubElement(geom,'Array',{'as':'points'})
            for x,y in points[1:-1]:E.SubElement(arr,'mxPoint',x=str(x),y=str(y))
            edges.append((c,points));total+=1
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(page.get("name"))}">',
             '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto-start-reverse"><path d="M0 0L9 4.5L0 9Z" fill="#7560a8"/></marker><marker id="amber" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto-start-reverse"><path d="M0 0L9 4.5L0 9Z" fill="#b07920"/></marker></defs>',
             '<rect width="100%" height="100%" fill="#fff"/>','<g font-family="-apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, &quot;PingFang SC&quot;, &quot;Microsoft YaHei&quot;, &quot;Noto Sans SC&quot;, &quot;Noto Sans CJK SC&quot;, &quot;WenQuanYi Zen Hei&quot;, sans-serif">']
        labels=[]; label_boxes=[]
        for c,pts in edges:
            dashed='dashed=1' in c.get('style','');color='#b07920' if dashed else '#7560a8'
            dash=' stroke-dasharray="7 5"' if dashed else ''
            svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round" marker-end="url(#{"amber" if dashed else "arrow"})"{dash}/>')
            label=c.get('value','')
            if label:
                lw=width(label,12)+12
                def overlaps(box):
                    x,y,w,h=box
                    return any(x<bx+bw+5 and x+w>bx-5 and y<by+bh+5 and y+h>by-5 for bx,by,bw,bh in list(boxes.values())+label_boxes)
                candidates=[];dist=0;total_len=sum(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(pts,pts[1:]))
                for p,q in zip(pts,pts[1:]):
                    length=abs(p[0]-q[0])+abs(p[1]-q[1]);cx=(p[0]+q[0])/2;cy=(p[1]+q[1])/2
                    for ox in [0,lw/2+10,-lw/2-10,80,-80,160,-160]:
                        for oy in [0,-12,12,-28,28,-48,48,-72,72,-96,96,-120,120,-180,180]:
                            x=cx+ox;y=cy+oy;box=(x-lw/2,y-10,lw,20)
                            if box[0]<15 or x+lw/2>W-15 or y<15 or y>H-15 or overlaps(box):continue
                            score=math.hypot(ox,oy)+max(0,lw-length)*.15
                            candidates.append((score,x,y,cx,cy,(dist+length/2)/max(total_len,1),box))
                    dist+=length
                if not candidates:raise RuntimeError(f'No clear label placement {pi} {c.get("id")}')
                _,x,y,cx,cy,fraction,box=min(candidates,key=lambda a:a[0]);label_boxes.append(box)
                geom=c.find('mxGeometry');geom.set('x',str(2*fraction-1));geom.set('y','0')
                E.SubElement(geom,'mxPoint',{'as':'offset','x':str(x-cx),'y':str(y-cy)})
                if math.hypot(x-cx,y-cy)>30:
                    labels.append(f'<path d="M{cx} {cy} L{x} {y}" fill="none" stroke="{color}" stroke-width=".8" stroke-dasharray="2 3"/>')
                labels.append(f'<g><rect x="{x-lw/2}" y="{y-11}" width="{lw}" height="20" rx="4" fill="white" fill-opacity=".95"/><text x="{x}" y="{y+3}" text-anchor="middle" fill="{color}" font-size="12">{html.escape(label)}</text></g>')
        for k,c in nodes.items():
            x,y,w,h=boxes[k];color=re.search(r'fillColor=([^;]+)',c.get('style','')).group(1)
            size=15;ls=lines(c.get('value',''),w-30,size)
            while len(ls)*(size*1.48)>h-24 and size>11:size-=1;ls=lines(c.get('value',''),w-30,size)
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" stroke="#c4bfd5"/>')
            offset=y+(h-(len(ls)-1)*size*1.5)/2+size*.35
            for i,line in enumerate(ls):
                weight='650' if i==0 else '400'
                svg.append(f'<text x="{x+w/2}" y="{offset+i*size*1.5}" text-anchor="middle" font-size="{size}" font-weight="{weight}" fill="#25223d">{html.escape(line)}</text>')
        svg+=labels+['</g></svg>']
        (outdir/f'page-{pi}.svg').write_text('\n'.join(svg))
    tree.write(path,encoding='utf-8',xml_declaration=True)
    print(f'Rendered {len(tree.getroot())} pages and {total} editable routes')

if __name__=='__main__':main()
