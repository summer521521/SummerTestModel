"""Generic deterministic renderer. Truth-sensitive parameters come only from ignored private specs."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def font():
    for p in (Path("C:/Windows/Fonts/msyh.ttc"),Path("C:/Windows/Fonts/arial.ttf"),Path("C:/Windows/Fonts/segoeui.ttf")):
        if p.exists():
            try: return ImageFont.truetype(str(p), 30), p.stem
            except OSError: pass
    return ImageFont.load_default(), "default"

def numbers(text): return [int(x) for x in re.findall(r"(?<![A-Za-z])\d+", text)]
def render(spec, out):
    image=Image.new("RGB",(spec["width"],spec["height"]),"white"); draw=ImageDraw.Draw(image); f,_=font(); aid=spec["asset_id"]; text=spec["render_text"]
    if aid.startswith("OCR_"):
        match=re.search(r"(?ms)^(?:Truth|GT)(?: exactly)?[:：]\s*\n?(.*?)(?=^={5,}|^-----------------------|\Z)",text)
        content=(match.group(1).strip() if match else aid)
        contrast=aid=="OCR_08"; fill=(170,170,170) if contrast else "black"
        draw.multiline_text((70,220),content,fill=fill,font=f,spacing=14)
        if aid=="OCR_07": image=image.rotate(7,expand=False,fillcolor="white")
        if aid=="OCR_09": image.save(out,format="JPEG",quality=35); return
        image.save(out,format="PNG"); return
    if aid=="VIS_01":
        red=int(re.search(r"(\d+) red circles",text).group(1)); blue=int(re.search(r"(\d+) blue squares",text).group(1))
        for i in range(red):
            x=120+(i%4)*180; y=150+(i//4)*180; draw.ellipse((x,y,x+80,y+80),fill="red")
        for i in range(blue):
            x=150+(i%3)*250; y=500+(i//3)*120; draw.rectangle((x,y,x+70,y+70),fill="blue")
    elif aid=="VIS_02":
        draw.ellipse((460,320,560,420),fill="black"); draw.polygon([(510,150),(450,260),(570,260)],fill="green"); draw.rectangle((300,330,400,430),fill="orange"); draw.polygon([(720,350),(770,400),(720,450),(670,400)],fill="blue")
    elif aid in {"VIS_03","VIS_04"}:
        values=[(k,int(v)) for k,v in re.findall(r"(?m)^\s*([A-Za-z]+)=([0-9]+)",text)]
        if aid=="VIS_03":
            for i,(label,value) in enumerate(values):
                x=120+i*190; y=650-value*25; draw.rectangle((x,y,x+90,650),fill="steelblue"); draw.text((x,670),label,fill="black",font=f)
        else:
            points=[]
            for i,(label,value) in enumerate(values):
                point=(150+i*220,650-value*40); points.append(point); draw.ellipse((point[0]-8,point[1]-8,point[0]+8,point[1]+8),fill="black"); draw.text((point[0]-20,680),label,fill="black",font=f)
            if len(points)>1: draw.line(points,fill="black",width=4)
    elif aid=="VIS_05":
        for c in range(4):
            for r in range(4):
                x=180+c*170; y=120+r*130; draw.rectangle((x,y,x+120,y+90),outline="black",width=2); draw.ellipse((x+55,y+38,x+65,y+48),fill="gray")
        star=re.search(r"star in ([A-D][1-4])",text,re.I).group(1).upper(); c=ord(star[0])-65; r=int(star[1])-1; x=180+c*170+45; y=120+r*130+25; draw.regular_polygon((x+15,y+20,35),5,fill="gold")
    elif aid=="VIS_06":
        lines=[x.strip() for x in text.splitlines() if x.strip() and ("->" in x or x.strip().lower().startswith("start") or "score" in x.lower())]
        draw.multiline_text((150,120),"\n".join(lines),fill="black",font=f,spacing=18)
    elif aid=="VIS_07":
        options=re.findall(r"\[[x ]\]\s*(.+)",text,re.I); draw.multiline_text((150,250),"\n".join(("☒ " if "[x]" in line.lower() else "☐ ")+line.split("]",1)[-1].strip() for line in re.findall(r"(?m)^\[[x ]\].*$",text,re.I)),fill="black",font=f,spacing=25)
    elif aid=="VIS_08":
        vals=[int(v) for v in re.findall(r"(?m)^\s*[A-Za-z]+\s+(\d+)%",text)]; total=sum(vals); vals.append(100-total); colors=["#4472c4","#ed7d31","#70ad47"]; start=0
        for value,color in zip(vals,colors): draw.pieslice((250,150,650,550),start*3.6,(start+value)*3.6,fill=color); start+=value
        draw.multiline_text((700,180),text,fill="black",font=f,spacing=12)
    image.save(out,format="PNG")

def main(private):
    root=Path(private); specs=json.loads((root/"assets/specs.json").read_text(encoding="utf-8")); _,family=font(); metadata=[]
    for spec in specs:
        suffix="jpg" if spec["format"]=="JPEG" else "png"; out=root/"assets"/(spec["asset_id"]+"."+suffix); render(spec,out); metadata.append({"asset_id":spec["asset_id"],"path":out.relative_to(root).as_posix(),"font_family":family,"width":spec["width"],"height":spec["height"]})
    (root/"assets/metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"assets":len(metadata),"font_family":family},ensure_ascii=False))
if __name__=="__main__": main(sys.argv[1])
