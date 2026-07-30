import math
from pathlib import Path
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

PDF = Path("tmp/pdfs/plan-metro-stm-officiel.pdf")
OUT = Path("metro-montreal-stm-fidele-18x24-led12.svg")
OUT_NO_TEXT = Path("metro-montreal-stm-fidele-18x24-led12-sans-texte.svg")
DRILL = Path("metro-montreal-stm-fidele-percage-led12.svg")
PDF_OUT = Path("output/pdf/metro-montreal-stm-fidele-18x24-led12.pdf")
PDF_NO_TEXT = Path("output/pdf/metro-montreal-stm-fidele-18x24-led12-sans-texte.pdf")

PAGE_W, PAGE_H = 457.2, 609.6
CROP_X, CROP_Y = 220.0, 470.0
SCALE = 0.331
OX, OY = 18.0, 74.0

COLORS = {
    "green": (1.0, 0.0, 1.0, 0.0),
    "orange": (0.0, 0.6, 1.0, 0.0),
    "yellow": (0.0, 0.1, 1.0, 0.0),
    "blue": (1.0, 0.4, 0.0, 0.0),
}
HEX = {"green": "#00A651", "orange": "#F58220", "yellow": "#FFD200", "blue": "#0072BC"}

NAMES = {
    "green": ["Honoré-Beaugrand","Radisson","Langelier","Cadillac","Assomption","Viau","Pie-IX","Joliette","Préfontaine","Frontenac","Papineau","Beaudry","Berri-UQAM","Saint-Laurent","Place-des-Arts","McGill","Peel","Guy-Concordia","Atwater","Lionel-Groulx","Charlevoix","LaSalle","De l’Église","Verdun","Jolicoeur","Monk","Angrignon"],
    "orange": ["Montmorency","De la Concorde","Cartier","Henri-Bourassa","Sauvé","Crémazie","Jarry","Jean-Talon","Beaubien","Rosemont","Laurier","Mont-Royal","Sherbrooke","Berri-UQAM","Champ-de-Mars","Place-d’Armes","Square-Victoria–OACI","Bonaventure","Lucien-L’Allier","Georges-Vanier","Lionel-Groulx","Place-Saint-Henri","Vendôme","Villa-Maria","Snowdon","Côte-Sainte-Catherine","Plamondon","Namur","De la Savane","Du Collège","Côte-Vertu"],
    "yellow": ["Berri-UQAM","Jean-Drapeau","Longueuil–Université-de-Sherbrooke"],
    "blue": ["Snowdon","Côte-des-Neiges","Université-de-Montréal","Édouard-Montpetit","Outremont","Acadie","Parc","De Castelnau","Jean-Talon","Fabre","D’Iberville","Saint-Michel"],
}

RINGS = {
    "green": [(1115.0,1138.7),(838.8,1633.1)],
    "orange": [(448.0,601.1),(685.6,706.3),(829.3,850.1),(1115.0,1138.7),(1054.5,1417.3),(1006.5,1465.3),(838.8,1633.1),(534.4,1427.5)],
    "yellow": [(1115.0,1138.7)],
    "blue": [(534.4,1427.5),(719.8,957.2),(829.3,850.1)],
}

def tx(p):
    return (OX + (p[0] - CROP_X) * SCALE, OY + (p[1] - CROP_Y) * SCALE)

def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def route_key(obj):
    return obj.get("linewidth") and abs(obj["linewidth"] - 28.59) < 0.02 and not obj.get("fill")

def svg_path(path):
    out = []
    for cmd in path:
        if cmd[0] == "m":
            x,y = tx(cmd[1]); out.append(f"M{x:.2f},{y:.2f}")
        elif cmd[0] == "l":
            x,y = tx(cmd[1]); out.append(f"L{x:.2f},{y:.2f}")
        elif cmd[0] == "c":
            p1,p2,p3 = [tx(p) for p in cmd[1:]]
            out.append(f"C{p1[0]:.2f},{p1[1]:.2f} {p2[0]:.2f},{p2[1]:.2f} {p3[0]:.2f},{p3[1]:.2f}")
        elif cmd[0] == "h":
            out.append("Z")
    return " ".join(out)

def sample_path(path, steps=20):
    pts, current = [], None
    for cmd in path:
        if cmd[0] == "m":
            current = cmd[1]; pts.append(current)
        elif cmd[0] == "l":
            current = cmd[1]; pts.append(current)
        elif cmd[0] == "c":
            p0=current; p1,p2,p3=cmd[1:]
            for i in range(1,steps+1):
                t=i/steps; u=1-t
                pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                            u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
            current=p3
    return pts

def projection_key(p, route):
    best=(1e20,0.0); cumulative=0.0
    for a,b in zip(route,route[1:]):
        vx,vy=b[0]-a[0],b[1]-a[1]; ll=vx*vx+vy*vy
        t=max(0,min(1,((p[0]-a[0])*vx+(p[1]-a[1])*vy)/ll))
        q=(a[0]+t*vx,a[1]+t*vy); d=(p[0]-q[0])**2+(p[1]-q[1])**2
        seg=math.sqrt(ll)
        if d<best[0]: best=(d,cumulative+t*seg)
        cumulative+=seg
    return best[1]

with pdfplumber.open(PDF) as doc:
    page=doc.pages[0]
    route_objs={}
    for key,color in COLORS.items():
        objs=[x for x in page.curves if route_key(x) and x.get("stroking_color")==color]
        route_objs[key]=objs

    regular={}
    for key,color in COLORS.items():
        wanted_lw=4.548 if key=="blue" else 28.59
        pts=[]
        for x in page.curves:
            w=x["x1"]-x["x0"]; h=x["bottom"]-x["top"]
            if (x.get("fill") and x.get("non_stroking_color")== (0.0,0.0,0.0,0.0)
                and x.get("stroking_color")==color and len(x.get("pts",[]))==5
                and 9<=w<=22 and 9<=h<=22 and abs((x.get("linewidth") or 0)-wanted_lw)<0.03
                and 200<x["x0"]<1500 and 450<x["top"]<1800):
                pts.append(((x["x0"]+x["x1"])/2,(x["top"]+x["bottom"])/2))
        regular[key]=pts

stations={}
for key in COLORS:
    samples=[sample_path(obj["path"]) for obj in route_objs[key]]
    route=max(samples,key=lambda r:sum(math.dist(a,b) for a,b in zip(r,r[1:])))
    pts=regular[key]+RINGS[key]
    dedup=[]
    for p in pts:
        if not any(math.dist(p,q)<3 for q in dedup): dedup.append(p)
    dedup.sort(key=lambda p:projection_key(p,route))
    if len(dedup)!=len(NAMES[key]):
        raise RuntimeError(f"{key}: {len(dedup)} points for {len(NAMES[key])} names")
    stations[key]=list(zip(NAMES[key],dedup))

line_markup=[]
for key in ("orange","green","blue","yellow"):
    paths="\n".join(f'<path d="{svg_path(o["path"])}"/>' for o in route_objs[key])
    line_markup.append(f'<g id="ligne-{key}" inkscape:groupmode="layer" inkscape:label="Ligne {key}" fill="none" stroke="{HEX[key]}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round">{paths}</g>')

unique={}
for key,items in stations.items():
    for name,p in items:
        unique.setdefault(name,{"p":p,"lines":[]})["lines"].append(key)

def label(name,p,i):
    x,y=tx(p)
    side=-1 if i%2 else 1
    dx=8 if x<330 else -8
    anchor="start" if dx>0 else "end"
    dy=side*6
    overrides={
        "Berri-UQAM":(-11,-9,"end"),"Lionel-Groulx":(10,8,"start"),
        "Snowdon":(-10,8,"end"),"Jean-Talon":(10,-8,"start"),
        "Longueuil–Université-de-Sherbrooke":(-10,-8,"end"),
    }
    if name in overrides: dx,dy,anchor=overrides[name]
    return f'<text x="{x+dx:.2f}" y="{y+dy:.2f}" text-anchor="{anchor}">{esc(name)}</text>'

def label_info(name,p,i):
    x,y=tx(p)
    side=-1 if i%2 else 1
    dx=8 if x<330 else -8
    anchor="start" if dx>0 else "end"
    dy=side*6
    overrides={
        "Berri-UQAM":(-11,-9,"end"),"Lionel-Groulx":(10,8,"start"),
        "Snowdon":(-10,8,"end"),"Jean-Talon":(10,-8,"start"),
        "Longueuil–Université-de-Sherbrooke":(-10,-8,"end"),
    }
    if name in overrides: dx,dy,anchor=overrides[name]
    return x+dx,y+dy,anchor

points=[]; labels=[]
for i,(name,data) in enumerate(unique.items()):
    x,y=tx(data["p"])
    sw=1.3 if len(data["lines"])>1 else 0.55
    points.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#252728" stroke="#F4F1E8" stroke-width="{sw}"/>')
    labels.append(label(name,data["p"],i))

svg=f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="18in" height="24in" viewBox="0 0 {PAGE_W} {PAGE_H}">
<rect width="{PAGE_W}" height="{PAGE_H}" fill="#252728"/>
<g inkscape:groupmode="layer" inkscape:label="Titre"><text class="title" x="24" y="35">Métro Montréal</text><text class="subtitle" x="24" y="47">Réseau STM - 68 stations</text></g>
{''.join(line_markup)}
<g inkscape:groupmode="layer" inkscape:label="Stations DEL 12 mm">{''.join(points)}</g>
<g inkscape:groupmode="layer" inkscape:label="Noms officiels">{''.join(labels)}</g>
<style>
text{{fill:#F4F1E8;font-family:Arial,Helvetica,sans-serif;font-size:2.75px;font-weight:400;paint-order:stroke;stroke:#252728;stroke-width:1.2px;stroke-linejoin:round}}
.title{{font-size:10px;font-weight:700;stroke-width:0}} .subtitle{{font-size:3.4px;stroke-width:0}}
</style></svg>'''
OUT.write_text(svg,encoding="utf-8")
OUT_NO_TEXT.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="18in" height="24in" viewBox="0 0 {PAGE_W} {PAGE_H}">
<rect width="{PAGE_W}" height="{PAGE_H}" fill="#252728"/>
{''.join(line_markup)}
<g inkscape:groupmode="layer" inkscape:label="Stations DEL 12 mm">{''.join(points)}</g>
</svg>''',encoding="utf-8")

drill_points=[]
for name,data in unique.items():
    x,y=tx(data["p"])
    drill_points.append(f'<g><circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="none" stroke="#000" stroke-width=".25"/><path d="M{x-2:.2f},{y:.2f}H{x+2:.2f} M{x:.2f},{y-2:.2f}V{x:.2f},{y+2:.2f}" stroke="#000" stroke-width=".18"/></g>')
DRILL.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="18in" height="24in" viewBox="0 0 {PAGE_W} {PAGE_H}">
<rect width="{PAGE_W}" height="{PAGE_H}" fill="#fff"/>{''.join(drill_points)}
<path d="M20,585H120" stroke="#000" stroke-width=".5"/><text x="20" y="580" font-family="Arial" font-size="4">BARRE DE CONTRÔLE 100 mm - IMPRIMER À 100 %</text>
</svg>''',encoding="utf-8")

PDF_OUT.parent.mkdir(parents=True,exist_ok=True)
c=canvas.Canvas(str(PDF_OUT),pagesize=(PAGE_W*mm,PAGE_H*mm))
c.setFillColorRGB(37/255,39/255,40/255)
c.rect(0,0,PAGE_W*mm,PAGE_H*mm,fill=1,stroke=0)
c.setLineCap(1); c.setLineJoin(1); c.setLineWidth(14*mm)
rgb={"green":(0,166/255,81/255),"orange":(245/255,130/255,32/255),"yellow":(1,210/255,0),"blue":(0,114/255,188/255)}
for key in ("orange","green","blue","yellow"):
    c.setStrokeColorRGB(*rgb[key])
    for obj in route_objs[key]:
        rp=c.beginPath()
        for cmd in obj["path"]:
            if cmd[0]=="m":
                x,y=tx(cmd[1]); rp.moveTo(x*mm,(PAGE_H-y)*mm)
            elif cmd[0]=="l":
                x,y=tx(cmd[1]); rp.lineTo(x*mm,(PAGE_H-y)*mm)
            elif cmd[0]=="c":
                p1,p2,p3=[tx(p) for p in cmd[1:]]
                rp.curveTo(p1[0]*mm,(PAGE_H-p1[1])*mm,p2[0]*mm,(PAGE_H-p2[1])*mm,p3[0]*mm,(PAGE_H-p3[1])*mm)
        c.drawPath(rp,stroke=1,fill=0)
c.setFillColorRGB(37/255,39/255,40/255)
c.setStrokeColorRGB(244/255,241/255,232/255)
for name,data in unique.items():
    x,y=tx(data["p"]); c.setLineWidth((1.3 if len(data["lines"])>1 else .55)*mm)
    c.circle(x*mm,(PAGE_H-y)*mm,6*mm,fill=1,stroke=1)
c.setFillColorRGB(244/255,241/255,232/255)
c.setFont("Helvetica-Bold",10*mm)
c.drawString(24*mm,(PAGE_H-35)*mm,"Métro Montréal")
c.setFont("Helvetica",3.4*mm)
c.drawString(24*mm,(PAGE_H-47)*mm,"Réseau STM - 68 stations")
c.setFont("Helvetica",2.75*mm)
for i,(name,data) in enumerate(unique.items()):
    x,y,anchor=label_info(name,data["p"],i)
    width=stringWidth(name,"Helvetica",2.75*mm)
    xx=x*mm if anchor=="start" else x*mm-width
    c.drawString(xx,(PAGE_H-y)*mm,name)
c.showPage(); c.save()

c=canvas.Canvas(str(PDF_NO_TEXT),pagesize=(PAGE_W*mm,PAGE_H*mm))
c.setFillColorRGB(37/255,39/255,40/255)
c.rect(0,0,PAGE_W*mm,PAGE_H*mm,fill=1,stroke=0)
c.setLineCap(1); c.setLineJoin(1); c.setLineWidth(14*mm)
for key in ("orange","green","blue","yellow"):
    c.setStrokeColorRGB(*rgb[key])
    for obj in route_objs[key]:
        rp=c.beginPath()
        for cmd in obj["path"]:
            if cmd[0]=="m":
                x,y=tx(cmd[1]); rp.moveTo(x*mm,(PAGE_H-y)*mm)
            elif cmd[0]=="l":
                x,y=tx(cmd[1]); rp.lineTo(x*mm,(PAGE_H-y)*mm)
            elif cmd[0]=="c":
                p1,p2,p3=[tx(p) for p in cmd[1:]]
                rp.curveTo(p1[0]*mm,(PAGE_H-p1[1])*mm,p2[0]*mm,(PAGE_H-p2[1])*mm,p3[0]*mm,(PAGE_H-p3[1])*mm)
        c.drawPath(rp,stroke=1,fill=0)
c.setFillColorRGB(37/255,39/255,40/255)
c.setStrokeColorRGB(244/255,241/255,232/255)
for name,data in unique.items():
    x,y=tx(data["p"]); c.setLineWidth((1.3 if len(data["lines"])>1 else .55)*mm)
    c.circle(x*mm,(PAGE_H-y)*mm,6*mm,fill=1,stroke=1)
c.showPage(); c.save()

print(f"{OUT}\n{OUT_NO_TEXT}\n{DRILL}\n{PDF_OUT}\n{PDF_NO_TEXT}\n{len(unique)} stations")
