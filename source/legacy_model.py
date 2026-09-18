"""Gayang Library: drawing-informed, editable 3D reconstruction (metres).
No network calls. Requires numpy, shapely, trimesh (installed in authoring runtime).
Architectural plans override older schematic background plans for room layout.
Furniture and minor construction details are illustrative, not an as-built survey.
"""
from pathlib import Path
import json, base64, math, random
from collections import defaultdict
import numpy as np
import trimesh
from shapely.geometry import Polygon, box as rect, Point
from shapely.ops import unary_union, triangulate

ROOT=Path(__file__).resolve().parent.parent
ROOT.mkdir(exist_ok=True)
random.seed(24)
MATS={
 'facade':('#eee9de',0.90,0,0), 'brick':('#b77559',0.91,0,1),
 'wall':('#eeeae1',0.88,0,0), 'concrete':('#c2c3bf',0.92,0,0),
 'floor':('#dcd7ca',0.86,0,2), 'wood':('#b78b5e',0.73,0,3),
 'dark':('#36454a',0.48,0.40,0), 'glass':('#86b8c6',0.16,0.10,0),
 'roof':('#b0b6b0',0.93,0,0), 'deck':('#a57b54',0.81,0,3),
 'green':('#68896d',0.96,0,0), 'leaf2':('#91aa76',0.97,0,0),
 'asphalt':('#74818a',0.97,0,0), 'white':('#f4f2e9',0.70,0,0),
 'teal':('#417c83',0.62,0,0), 'orange':('#c28b5d',0.84,0,0),
 'blue':('#718ba6',0.8,0,0), 'book1':('#9b775f',0.88,0,0),
 'book2':('#5d8385',0.88,0,0), 'book3':('#d4b06f',0.88,0,0),
 'soil':('#807265',0.95,0,0), 'metal':('#98a4a6',0.38,0.55,0),
 'solar':('#344f6b',0.30,0.20,0), 'copper':('#af7950',0.50,0.55,0),
 'water':('#5eabc1',0.55,0.2,0), 'toilet':('#e8eee9',0.43,0,0),
 'floorStudy':('#d4ded7',0.9,0,2), 'floorCommunity':('#dde2e7',0.9,0,2),
 'floorService':('#d5dce0',0.9,0,2), 'floorKids':('#e5dbc6',0.9,0,2),
 'floorCulture':('#ded2d0',0.9,0,2), 'line':('#f2eddd',0.9,0,0)
}
parts=defaultdict(list); rooms=[]; roomPolys={}; sources=[]; object_count=0
BASE={-1:-4.2,0:0.,1:3.3,2:6.6,3:9.9,4:14.1,9:0}
H={-1:4.2,0:3.3,1:3.3,2:3.3,3:4.2,4:4.,9:0}

def add(mesh,mat='wall',level=0,layer='interior',name=''):
 global object_count
 if len(mesh.faces)==0:return
 mesh.metadata={'name':name,'level':level,'layer':layer}
 parts[(level,layer,mat)].append(mesh);object_count+=1

def box(x,z,y,w,d,h,mat='wall',level=0,layer='interior',name=''):
 if min(w,d,h)<=0.000001:return
 m=trimesh.creation.box(extents=[w,h,d]);m.apply_translation([x+w/2,y+h/2,z+d/2]);add(m,mat,level,layer,name)

def cyl(x,z,y,r,h,mat='metal',level=0,layer='interior',n=14):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=n)
 m.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]));m.apply_translation([x,y+h/2,z]);add(m,mat,level,layer)

def beam(a,b,r,mat,level,layer,n=8):
 a=np.array(a);b=np.array(b);v=b-a
 if np.linalg.norm(v)<1e-5:return
 m=trimesh.creation.cylinder(radius=r,height=np.linalg.norm(v),sections=n)
 m.apply_transform(trimesh.geometry.align_vectors([0,0,1],v));m.apply_translation((a+b)/2);add(m,mat,level,layer)

def prism(poly,y,h,mat,level,layer,axis='y',fixed=0):
 """Extrude shapely polygons, including holes. Triangles must be fully covered."""
 if poly.is_empty:return
 if poly.geom_type!='Polygon':
  for p in poly.geoms:prism(p,y,h,mat,level,layer,axis,fixed)
  return
 verts=[];faces=[]
 def pt(u,v,t):
  if axis=='y':return [u,t,v]
  if axis=='z':return [u,v,t]
  return [t,v,u]
 def tri(coords, t, flip):
  i=len(verts);verts.extend(pt(u,v,t) for u,v in coords)
  faces.append([i,i+2,i+1] if flip else [i,i+1,i+2])
 for t in triangulate(poly):
  if not poly.covers(t):continue
  c=list(t.exterior.coords)[:3]
  tri(c,y,False);tri(c,y+h,True)
 for ring in [poly.exterior,*poly.interiors]:
  cs=list(ring.coords)
  for a,b in zip(cs,cs[1:]):
   i=len(verts);verts.extend([pt(*a,y),pt(*b,y),pt(*b,y+h),pt(*a,y+h)])
   faces.extend([[i,i+1,i+2],[i,i+2,i+3]])
 m=trimesh.Trimesh(vertices=verts,faces=faces,process=True);m.fix_normals();add(m,mat,level,layer)

def slab(poly,level,mat='floor',thickness=.20,offset=0,layer='slab'):
 prism(poly,BASE[level]+offset-thickness,thickness,mat,level,layer)

def wall(x,z,length,axis='x',level=0,mat='wall',height=None,doors=(),windows=(),layer='interior',th=.16,y=None):
 """Axis-aligned wall with actual empty openings, not painted door shapes."""
 y=BASE[level] if y is None else y; height=height or (2.7 if level!=3 else 3.1)
 panel=rect(0,0,length,height)
 for c,w in doors:panel=panel.difference(rect(c-w/2,-.01,c+w/2,2.16))
 for c,w,sill,wh in windows:panel=panel.difference(rect(c-w/2,sill,c+w/2,min(sill+wh,height-.06)))
 # translate 2D horizontal/vertical coordinates then extrude perpendicular
 from shapely.affinity import translate
 poly=translate(panel,xoff=(x if axis=='x' else z),yoff=y)
 prism(poly,(z if axis=='x' else x)-th/2,th,mat,level,layer,axis=('z' if axis=='x' else 'x'))
 for c,w in doors:
  # Lintel frame and open leaf are separate furniture-like elements.
  u=(x+c if axis=='x' else z+c)
  for dc in [-w/2,w/2]:
   if axis=='x':box(u+dc-.028,z-.10,y,.056,.20,2.18,'dark',level,'doors')
   else:box(x-.10,u+dc-.028,y,.20,.056,2.18,'dark',level,'doors')
  if axis=='x':box(u-w/2,z-.08,y,w*.08,w*.80,2.06,'wood',level,'doors')
  else:box(x-.08,u-w/2,y,w*.80,w*.08,2.06,'wood',level,'doors')

def railing(x,z,l,axis,level,yoff=0,glass=False):
 y=BASE[level]+yoff
 for t in np.linspace(0,l,max(2,int(l/1.1)+1)):
  xx,zz=(x+t,z) if axis=='x' else (x,z+t)
  cyl(xx,zz,y,.025,1.08,'dark',level,'rail')
 a=[x,y+1.08,z]; b=[x+l,y+1.08,z] if axis=='x' else [x,y+1.08,z+l]
 beam(a,b,.032,'dark',level,'rail')
 if glass:
  if axis=='x':box(x,z-.015,y+.10,l,.03,.85,'glass',level,'rail')
  else:box(x-.015,z,y+.10,.03,l,.85,'glass',level,'rail')
 else:
  for t in [.38,.73]:
   a=[x,y+t,z];b=[x+l,y+t,z] if axis=='x' else [x,y+t,z+l];beam(a,b,.014,'metal',level,'rail')

# Drawn primary axes: X4=0, X3=6, X2=15, X1=21, 6=27 ... 1=55.
NEW=rect(0,0,21,24)
OLD=unary_union([rect(21,12,27,21.5),rect(27,12,45,22),rect(45,12,55,31),rect(47.5,9,51.5,12)])
VOID={0:[],1:[rect(6,6,15,18)],2:[rect(0,6,6,18),rect(6,19.5,15,24)],3:[rect(0,0,6,12),rect(15,0,21,12),rect(0,18,6,24),rect(15,20,21,24)],4:[rect(0,0,6,12),rect(15,0,21,12),rect(0,18,6,24),rect(15,20,21,24)]}
SLABS={};INDOOR={}
for f in range(4):
 p=NEW.difference(unary_union(VOID[f])) if VOID[f] else NEW
 o=OLD
 if f in [1,2]:o=o.union(rect(27,10,36,12))
 if f==1:o=o.difference(rect(47.5,12,55,16.6))
 # actual core openings in the slabs
 if f>0:o=o.difference(rect(21.2,15.7,26.5,20.6))
 SLABS[f]=p.union(o)
 if f==0:indo=NEW
 elif f==1:indo=NEW.difference(unary_union([rect(6,6,15,18),rect(0,6,6,18)]))
 elif f==2:indo=unary_union([rect(6,0,15,19.5),rect(15,12,21,18)])
 else:indo=unary_union([rect(6,0,15,20),rect(15,12,21,20)])
 INDOOR[f]=indo
 slab(SLABS[f],f)
 prism(SLABS[f],BASE[f]+H[f]-.21,.08,'white',f,'ceiling')
 # structural perimeter columns; no fabricated 5th occupied floor
 for x in [0,6,15,21]:
  for z in [0,6,12,18,24]:
   box(x-.20,z-.20,BASE[f],.40,.40,H[f],'concrete',f,'structure')
 for x in [27,31.5,36,40.5,45,47.5,51.5,55]:
  for z in [12,17,22]:
   if OLD.buffer(.1).covers(Point(x,z)):box(x-.18,z-.18,BASE[f],.36,.36,min(H[f],3.3),'concrete',f,'structure')
 for z in [26.5,31]:
  for x in [45,47.5,51.5,55]:box(x-.18,z-.18,BASE[f],.36,.36,min(H[f],3.3),'concrete',f,'structure')

# Perimeter white architectural screen, true openings and selective glazing.
def facade_side(x,z,L,axis,f):
 y=BASE[f];height=H[f]
 # horizontal stone/stucco belt; modelled separately from slabs
 if axis=='x':box(x,z-.18,y,L,.36,.23,'facade',f,'exterior');box(x,z-.18,y+height-.35,L,.36,.35,'facade',f,'exterior')
 else:box(x-.18,z,y,.36,L,.23,'facade',f,'exterior');box(x-.18,z,y+height-.35,.36,L,.35,'facade',f,'exterior')
 if f==0:
  pitch=3.;n=round(L/pitch)
  for i in range(n):
   s=i*pitch; opening=2.1; r=opening/2; spring=1.48
   pts=[(s+.45,-.01),(s+2.55,-.01),(s+2.55,spring)]
   for ang in np.linspace(0,math.pi,18):pts.append((s+1.5+r*math.cos(ang),spring+r*math.sin(ang)))
   pts.append((s+.45,-.01))
   panel=rect(s,0,s+pitch,height-.26)
   # Revised western central openings are rectangular.
   rectangular=(axis=='z' and x==0 and 6<=s<21) or (axis=='x' and z==24 and 15<=s<18)
   panel=panel.difference(rect(s+.45,-.01,s+2.55,2.4) if rectangular else Polygon(pts))
   from shapely.affinity import translate
   pp=translate(panel,xoff=x if axis=='x' else z,yoff=y)
   prism(pp,(z if axis=='x' else x)-.18,.36,'facade',f,'exterior',axis='z' if axis=='x' else 'x')
   if axis=='x':box(x+s+.47,z,y+.03,2.06,.035,2.35,'glass',f,'exterior')
   else:box(x,z+s+.47,y+.03,.035,2.06,2.35,'glass',f,'exterior')
 else:
  # Variable-width openings preserve the long narrow rhythm and occasional large bay.
  n=round(L/1.5)
  for i in range(n):
   u=i*1.5;ww=.60
   if i in [4,10] and i+1<n:ww=2.10
   if i in [5,11]:continue
   edge=.45
   wall(x+u if axis=='x' else x,z if axis=='x' else z+u,min(3 if ww>1 else 1.5,L-u),axis,f,'facade',height,windows=[((min(3 if ww>1 else 1.5,L-u))/2,ww,.82,height-1.23)],layer='exterior',th=.33,y=y)
   # only glazed where plan has an enclosed room behind the outer screen
   mid=u+(1.5 if ww>1 else .75)
   xx,zz=(x+mid,z+(0.25 if z==0 else -.25)) if axis=='x' else (x+(.25 if x==0 else -.25),z+mid)
   if f<4 and INDOOR[f].buffer(.02).covers(Point(xx,zz)):
    if axis=='x':box(x+mid-ww/2,z,y+.83,ww,.032,height-1.26,'glass',f,'exterior')
    else:box(x,z+mid-ww/2,y+.83,.032,ww,height-1.26,'glass',f,'exterior')
for f in range(5):
 for a in [(0,0,21,'x'),(0,24,21,'x'),(0,0,24,'z'),(21,0,12,'z'),(21,21.5,2.5,'z')]:facade_side(*a,f)

# Existing brick remodelling wing: open rectangular windows, dark frames.
for f in range(4):
 h=3.3;y=BASE[f]
 # Only exposed perimeter segments (connector opening intentionally left open).
 segs=[(27,22,18,'x'),(45,22,9,'z'),(45,31,10,'x'),(55,12,19,'z'),(51.5,12,3.5,'x'),(45,9,6.5,'x'),(45,9,3,'z'),(51.5,9,3,'z'),(36,12,9,'x')]
 for x,z,L,axis in segs:
  n=max(1,round(L/4.5));pitch=L/n
  windows=[(pitch*(i+.5),min(2.6,pitch-.75),.95,1.45) for i in range(n)]
  wall(x,z,L,axis,f,'brick',h,windows=windows,layer='exterior',th=.26)
  for c,w,s,wh in windows:
   if axis=='x':
    box(x+c-w/2,z-.022,y+s,w,.045,wh,'glass',f,'exterior')
    for q in np.linspace(-w/2,w/2,4):box(x+c+q-.023,z-.06,y+s,.046,.12,wh,'dark',f,'exterior')
    box(x+c-w/2-.06,z-.16,y+s-.07,w+.12,.32,.08,'concrete',f,'exterior')
   else:
    box(x-.022,z+c-w/2,y+s,.045,w,wh,'glass',f,'exterior')
    for q in np.linspace(-w/2,w/2,4):box(x-.06,z+c+q-.023,y+s,.12,.046,wh,'dark',f,'exterior')
    box(x-.16,z+c-w/2-.06,y+s-.07,.32,w+.12,.08,'concrete',f,'exterior')
 # Corridor curtain wall (north side); ordinary glazing, not a invented occupied atrium wing.
 z=10 if f in [1,2] else 12
 box(27,z-.04,y+.14,9,.065,h-.25,'glass',f,'exterior')
 for xx in np.arange(27,36.01,.75):box(xx-.024,z-.09,y,.048,.18,h,'dark',f,'exterior')
 for yy in [.16,2.5,3.18]:box(27,z-.09,y+yy,9,.18,.05,'dark',f,'exterior')
 for xx in [27,36]:wall(xx,z,12-z,'z',f,'brick',h,layer='exterior',th=.24)
 # Glass stair core facing the south terrace
 box(21,21.48,y,.85,.18,h,'brick',f,'exterior');box(24.25,21.45,y,2.75,.06,h,'glass',f,'exterior')
 for xx in np.arange(24.25,27.01,.55):box(xx,21.42,y,.045,.13,h,'dark',f,'exterior')

# Editable room regions and space metadata. Coordinates follow updated architectural plans.
def room(id,name,f,bounds,kind='community',note=''):
 p=rect(*bounds) if len(bounds)==4 and isinstance(bounds[0],(float,int)) else Polygon(bounds)
 p=p.intersection(SLABS[f] if f in SLABS else rect(6,9,21,22))
 if p.is_empty:return
 roomPolys[id]=p
 c=p.representative_point()
 rooms.append({'id':id,'name':name,'level':f,'kind':kind,'center':[round(c.x,3),round(BASE[f]+.08,3),round(c.y,3)],'polygon':[list(v) for v in p.exterior.coords] if p.geom_type=='Polygon' else [list(v) for v in max(p.geoms,key=lambda a:a.area).exterior.coords], 'area':round(p.area,1),'source':f'건축 PDF { {0:40,1:43,2:46,3:49,-1:37}.get(f,52)}쪽 · 수정후 평면도','note':note or '실명·대략적 구획은 도면을 따름. 표시 면적은 모델 윤곽으로 계산한 참고값.'})
 mat={'study':'floorStudy','community':'floorCommunity','service':'floorService','kids':'floorKids','culture':'floorCulture','terrace':'deck'}.get(kind,'floor')
 slab(p.buffer(-.07),f,mat,.022,.013,'roomfloor')

# Ground floor
room('101','개방형서가',0,[(0,0),(21,0),(21,21),(15,21),(15,15),(6,15),(6,21),(0,21)],'study')
room('103','로비 · 안내데스크',0,[6,4,15,10.5],'community')
room('102','책누리터',0,[6,10.5,15,15],'kids','계단형 책누리터를 입체적으로 표현. 단높이·서가 모듈은 단순화.')
room('116','계단실 3',0,[6,21,15,24],'service')
room('107','방풍실',0,[15,21,21,24],'community')
room('104','당직실',0,[27,14.6,31.5,18],'service')
room('105','북카페',0,[31.5,14.6,36,22],'community')
room('115','부속공간',0,[27,18,31.5,22],'service')
room('108','휴게실',0,[47.5,12,55,17],'community')
room('110','다목적실',0,[47.5,17,55,22],'community')
room('106','어르신건강교실',0,[45,23,55,31],'community')
# Second floor
room('201','자료실',1,[(6,0),(21,0),(21,12),(15,12),(15,6),(6,6)],'study')
room('202','성인열람실',1,[(0,18),(15,18),(15,12),(21,12),(21,24),(0,24)],'study')
room('203','유아실 · 이야기방',1,[0,0,6,6],'kids')
room('204','수유실',1,[0,0,2.2,2.5],'kids')
room('205','시민강의실',1,[27,14.6,31.5,22],'community')
room('206','시민커뮤니티룸',1,[31.5,14.6,36,22],'community')
room('212','서고',1,[45,16.6,55,31],'study')
room('2DECK','휴게데크',1,[0,6,6,18],'terrace')
# Third floor
room('303','마을공방',2,[6,0,15,6],'community')
room('302','청소년자료실',2,[(6,6),(15,6),(15,12),(21,12),(21,18),(15,18),(15,19.5),(6,19.5)],'study')
room('305','청소년 스튜디오',2,[27,14.6,31.5,18.5],'culture')
room('304','동아리방',2,[31.5,14.6,36,22],'community')
room('3ANNEX','부속실',2,[27,18.5,31.5,22],'service')
room('306','직원휴게실',2,[47.5,12,55,17],'community')
room('301','사무실',2,[45,17,55,26.5],'service')
room('3DIR','관장실',2,[47.5,26.5,55,31],'service','수정후 도면 하단 별도 실을 표현. 실제 운영실명은 현장 확인 필요.')
for k,b in enumerate([(0,0,6,6),(15,0,21,12),(0,18,6,24),(15,18,21,24)],1):room(f'3D{k}',f'휴게데크 {k}',2,b,'terrace')
# Fourth floor
room('401','서진홀 · 객석',3,[6,0,15,6],'culture')
room('401B','서진홀 · 소극장',3,[6,6,15,18],'culture')
room('402','준비실',3,[6,18,15,20],'service')
room('403','홀',3,[15,12,21,20],'community')
room('404','그룹회의실',3,[31.5,14.6,36,22],'community')
room('4ANNEX','부속공간',3,[27,14.6,31.5,22],'service')
room('406','소형강의실',3,[47.5,12,55,17],'community')
room('405','대형강의실',3,[47.5,17,55,26.5],'community')
room('407','미화원실',3,[45,26.5,47.5,31],'service')
room('408','창고',3,[47.5,26.5,55,31],'service')
room('4D1','휴게데크 1',3,[0,12,6,18],'terrace');room('4D2','휴게데크 2',3,[6,20,15,24],'terrace')
# Shared circulation and restrooms
for f in range(4):
 room(f'{f+1}C','연결 복도',f,[21,12,45,14.6],'community')
 room(f'{f+1}S','계단실 2 · 승강기',f,[21,15.7,27,21.5],'service') if f==0 else None
 room(f'{f+1}WCW','여자화장실',f,[36,14.6,40.5,22],'service')
 room(f'{f+1}WCM','남자화장실',f,[40.5,14.6,45,22],'service')
 room(f'{f+1}S1','계단실 1',f,[47.5,9,51.5,12],'service')

# Interior partitions with door openings (positions traced from updated main plans).
for f in range(4):
 for x in [27,31.5,36,40.5,45]:
  wall(x,14.6,7.4,'z',f,doors=[(1.3,.9)] if x in [27,36,45] else [])
 wall(27,14.6,18,'x',f,doors=[(1.8,.9),(6.5,1.25),(10.7,1),(15.2,1)])
 wall(27,22,18,'x',f,height=2.7)
 # toilet partitions and accessible cubicles
 for xx in [36.3,40.8]:
  wall(xx,17.2,3.9,'x',f,height=2.2,doors=[(1.,1.)])
  wall(xx+2.,14.8,2.4,'z',f,height=2.2)
  for z in [18.1,19.3,20.5]:
   wall(xx,z,1.6,'x',f,height=2.05)
   wall(xx+1.6,z,1.1,'z',f,height=2.05,doors=[(.55,.67)])
   # simplified toilet bowls and cisterns, no invented plumbing route
   cyl(xx+.68,z+.57,BASE[f]+.02,.23,.39,'toilet',f,'fixtures',n=12)
   box(xx+.43,z+.13,BASE[f]+.28,.48,.22,.45,'toilet',f,'fixtures')
  box(xx+2.6,18,BASE[f]+.74,.62,3.1,.14,'toilet',f,'fixtures')
  for z in [18.6,19.7,20.6]:cyl(xx+2.92,z,BASE[f]+.89,.20,.045,'metal',f,'fixtures',n=14)
 # central lift/stair core walls and door opening
 wall(21.2,15.7,5.8,'z',f,doors=[(4.7,1.2)])
 wall(21.2,15.7,2.3,'x',f,height=H[f],doors=[(1.15,1.2)])
 wall(23.5,15.7,2.7,'z',f,height=H[f])
 wall(21.2,18.4,2.3,'x',f,height=H[f])
 box(21.5,16,BASE[f]+.03,1.65,1.8,.10,'metal',f,'structure')
 box(21.7,15.67,BASE[f]+.06,1.2,.045,2.04,'metal',f,'doors')
 # rear enclosed stairs
 wall(47.5,9,4,'x',f,mat='brick',height=3.3,layer='exterior')
 wall(47.5,9,3,'z',f,height=3.3);wall(51.5,9,3,'z',f,height=3.3)
 wall(47.5,12,4,'x',f,doors=[(1,1.1)])
 # Eastern rooms opening onto a 2.5m corridor.
 wall(47.5,12,19,'z',f,doors=[(2.4,1.1),(7,1.1),(16,.95)])
 for z in ([17,22,23] if f==0 else ([17,26.5] if f in [2,3] else [])):
  wall(47.5,z,7.5,'x',f)
 if f in [2,3]:wall(45,26.5,2.5,'x',f,doors=[(1.25,.85)])
 if f==0:wall(27,18,4.5,'x',f,doors=[(2.,.9)])
 if f==2:wall(27,18.5,4.5,'x',f,doors=[(2.,.9)])
 # lift and dogleg circulation stairs (geometrical simplification)
 rise=H[f] if f<3 else 4.2
 for i in range(11):
  hh=(i+1)*rise/22
  box(24,15.8+i*.255,BASE[f],1.2,.255,hh,'concrete',f,'stairs')
  box(25.3,18.605-i*.255,BASE[f]+rise/2,1.2,.255,hh,'concrete',f,'stairs')
 box(24,18.61,BASE[f]+rise/2-.15,2.5,.9,.15,'concrete',f,'stairs')
 beam([24,BASE[f]+1,15.8],[24,BASE[f]+rise/2+1,18.6],.028,'dark',f,'rail')
 beam([26.5,BASE[f]+rise/2+1,18.6],[26.5,BASE[f]+rise+1,15.8],.028,'dark',f,'rail')
 for i in range(10):
  hh=(i+1)*3.3/20
  box(47.8+i*.16,9.2,BASE[f],.16,1.15,hh,'concrete',f,'stairs')
  box(49.4-i*.16,10.5,BASE[f]+1.65,.16,1.15,hh,'concrete',f,'stairs')
 box(49.4,9.2,BASE[f]+1.5,.5,2.45,.15,'concrete',f,'stairs')
# Special new-wing interior walls/terrace glazing
wall(0,21,21,'x',0,doors=[(7.8,1.4),(16.8,1.6)]);wall(15,21,3,'z',0,doors=[(1.5,1.2)])
wall(0,6,6,'x',1,doors=[(5.,.9)]);wall(6,0,6,'z',1,doors=[(4.9,.9)])
wall(0,2.5,2.2,'x',1,doors=[(1.2,.8)]);wall(2.2,0,2.5,'z',1)
wall(6,6,9,'x',1,mat='glass',height=2.7,layer='interior',th=.055)
wall(15,6,6,'z',1,mat='glass',height=2.7,layer='interior',th=.055)
for f in [2,3]:
 wall(6,0,12 if f==3 else 6,'z',f,mat='glass',height=2.65,layer='interior',th=.055)
 wall(15,0,12,'z',f,mat='glass',height=2.65,layer='interior',th=.055)
 wall(6,6,9,'x',f,mat='glass' if f==2 else 'wall',height=2.6,doors=[(7.8,1.1)] if f==2 else []) if f==2 else None
wall(6,18,9,'x',3,doors=[(7.8,1.1)]);wall(15,0,18,'z',3,doors=[(14.6,1.5)])
for f,items in {1:[(6,6,12,'z'),(15,6,12,'z'),(6,18,9,'x')],2:[(6,6,12,'z'),(6,19.5,9,'x')],3:[(0,12,6,'x'),(6,0,12,'z'),(15,0,12,'z'),(6,20,9,'x')]}.items():
 for x,z,l,a in items:railing(x,z,l,a,f,glass=True)

# Step-shaped reading landscape connecting the 1F / 2F opening.
for i in range(12):
 box(6+i*.65,11.2,0,.65,3.3,(i+1)*.275,'wood',0,'stairs')
 for z in [11.3,12.5,13.7]:box(6+i*.65+.02,z,(i+1)*.275,.56,.72,.065,'teal' if i%3 else 'orange',0,'furniture')
for i in range(22):box(13.8,6+i*.54,0,1.05,.54,(i+1)*.15,'concrete',0,'stairs')
# Basement shell, following PIT expanded plan. Mechanism sizes are drawn, route heights not invented.
BP=rect(6,9,21,22)
SLABS[-1]=BP
slab(BP,-1,'floorService',.32)
for x,z,L,a in [(6,9,15,'x'),(6,22,15,'x'),(6,9,13,'z'),(21,9,13,'z')]:wall(x,z,L,a,-1,'concrete',4.2,layer='exterior',th=.30)
for x,z,L,a,doors in [(12.5,9,9.5,'z',[(7.8,1.1)]),(15,9,13,'z',[(7.4,1.1)]),(6,15,6.5,'x',[]),(6,18.5,9,'x',[(7.9,1.1)]),(15,15,6,'x',[]),(12.5,12.5,2.5,'x',[(1.2,.9)])]:wall(x,z,L,a,-1,'wall',3.4,doors=doors)
room('B01','전기실',-1,[6,9,12.5,15],'service');room('B02','통신실',-1,[6,15,12.5,18.5],'service');room('B03','창고',-1,[12.5,9,15,12.5],'service');room('B04','물탱크실',-1,[15,9,21,15],'service');room('B05','기계실',-1,[15,15,21,22],'service');room('B06','계단실 3',-1,[6,18.5,15,22],'service')
for i in range(22):box(6.4+i*.36,19,BASE[-1],.36,1.3,(i+1)*4.2/22,'concrete',-1,'stairs')
box(16.2,10.2,BASE[-1]+.6,3,3,2.5,'metal',-1,'mep')
for x in [16.2,17.2,18.2,19.2]:box(x,10.18,BASE[-1]+.6,.04,.04,2.5,'dark',-1,'mep')
for y in [.65,1.45,2.25,3.05]:box(16.2,10.15,BASE[-1]+y,3,.05,.04,'dark',-1,'mep')
for x in [16.5,17.4,18.3]:
 cyl(x,17.9,BASE[-1]+.2,.18,.7,'teal',-1,'mep');cyl(x,17.9,BASE[-1]+.9,.24,.22,'dark',-1,'mep')
box(16.15,17.45,BASE[-1]+.04,2.65,1,.18,'concrete',-1,'mep');cyl(19.45,18.8,BASE[-1]+.2,.45,.916,'water',-1,'mep')
box(19.8,16,BASE[-1]+1.0,.38,.30,.7,'white',-1,'mep')
for x in [7.,8.5,10.]:box(x,9.5,BASE[-1],.9,.65,2.,'metal',-1,'fixtures')
for x in [7.4,9.4]:box(x,15.5,BASE[-1],.7,.7,1.9,'dark',-1,'fixtures')

# Furniture library (explicitly illustrative, switchable independently).
def chair(x,z,f,mat='teal',angle=0,yoff=0):
 y=BASE[f]+yoff
 group=[]
 def b(xx,zz,yy,w,d,h,m):
  mesh=trimesh.creation.box(extents=[w,h,d]);mesh.apply_translation([xx+w/2,yy+h/2,zz+d/2]);
  mesh.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,1,0],[x,y,z]));add(mesh,m,f,'furniture')
 b(x-.23,z-.22,y+.44,.46,.46,.08,mat);b(x-.23,z+.20,y+.49,.46,.075,.42,mat)
 for a in [-.16,.16]:
  for c in [-.15,.15]:b(x+a-.022,z+c-.022,y,.045,.045,.44,'dark')
def table(x,z,w,d,f,kind='wood',yoff=0):
 y=BASE[f]+yoff
 box(x,z,y+.74,w,d,.075,kind,f,'furniture')
 for xx in [x+.1,x+w-.14]:
  for zz in [z+.1,z+d-.14]:box(xx,zz,y,.045,.045,.74,'dark',f,'furniture')
def shelf(x,z,w,f,axis='x',height=1.6):
 y=BASE[f];dep=.40
 for h in np.arange(.10,height+.01,.35):
  box(x,z,y+h,w if axis=='x' else dep,dep if axis=='x' else w,.055,'wood',f,'furniture')
  if h+.25<height:
   for i in range(max(1,int(w/.11))):
    bh=random.uniform(.16,.25);mat=['book1','book2','book3'][i%3]
    if axis=='x':box(x+i*.11+.02,z+.04,y+h+.055,.075,.28,bh,mat,f,'furniture')
    else:box(x+.04,z+i*.11+.02,y+h+.055,.28,.075,bh,mat,f,'furniture')
 for s in [0,w-.05]:box(x+s if axis=='x' else x,z if axis=='x' else z+s,y,.05 if axis=='x' else dep,dep if axis=='x' else .05,height,'wood',f,'furniture')
def round_table(x,z,f,r=.6):
 cyl(x,z,BASE[f]+.74,r,.07,'wood',f,'furniture',n=22);cyl(x,z,BASE[f],.07,.74,'dark',f,'furniture')
for x in [1,18.6]:
 for z in [2,6,16]:shelf(x,z,2.8,0,'z',1.3)
box(7.6,4.2,0,5.2,.75,.98,'wood',0,'furniture');box(7.6,4.12,.98,5.2,.95,.07,'white',0,'furniture')
for x in [8.4,10.6]:box(x,4.1,1.05,.6,.08,.40,'dark',0,'furniture')
for x,z in [(3.5,10),(3.5,16),(17.9,6),(18.5,17.5)]:round_table(x,z,0);chair(x,z+.9,0);chair(x,z-.9,0,angle=math.pi)
for x in [8.2,11.6,17.4]:
 for z in [1.3,3.6]:shelf(x,z,2.4,1,'x',1.55)
for x in [2.,5.,8.,11.,17.,19.]:
 table(x-.7,21,1.4,.72,1);chair(x,22.05,1)
for z in [8,10.5]:table(17,z,2.6,1.1,1);chair(17.6,z+1.4,1);chair(19,z+1.4,1)
for z in [19,22,25,28]:
 for x in [48.3,51.9]:shelf(x,z,2.0,1,'x',2.0)
round_table(3.3,3.6,1,.6)
for x in [2.4,4.2]:chair(x,4.3,1,'orange')
for z in [1.6,4.2]:table(7,z,6.5,1.1,2);[chair(x,z+1.45,2) for x in [8,10,12]]
for z in [8.2,11.2,14.2]:shelf(7.2,z,4.6,2,height=1.25)
for z in [13.3,16]:table(16,z,3.6,.8,2);chair(17,z+1.1,2);chair(18.5,z+1.1,2)
# Theater tier seating, rising northwards.
for row in range(5):
 z=.8+row*.91;off=(4-row)*.23
 box(6.3,z,BASE[3],8.3,.91,max(.03,off),'wood',3,'stairs')
 for col in range(9):chair(6.85+col*.83,z+.37,3,'orange',angle=math.pi,yoff=off)
box(6.4,8.5,BASE[3],8.0,3.1,.28,'wood',3,'furniture')
box(7,8.7,BASE[3]+.28,6.8,.055,2.35,'dark',3,'furniture')
# Community rooms, classrooms, office furnishings (illustrative)
for f in range(4):
 for x in [28,32.5]:
  if f==0 and x==28:continue
  table(x,17,2.4,1.0,f);chair(x+.6,18.4,f);chair(x+1.8,18.4,f);chair(x+.6,16.6,f,angle=math.pi)
 for z in [13.3,15.2]:
  table(49,z,3.8,.70,f)
  for x in [49.6,51,52.4]:chair(x,z+1,f)
 if f in [2,3]:
  for z in [19,22,24]:
   for x in [48.4,51.7]:table(x,z,2.1,.8,f);chair(x+.8,z+1.1,f)
for z in [25,27.2,29.4]:box(47,z,.025,5,1.25,.07,'blue',0,'furniture')
# Terrace surfaces and light-weight planting units
for r in rooms:
 if r['kind']!='terrace':continue
 p=roomPolys[r['id']];x0,z0,x1,z1=p.bounds;f=r['level']
 for zz in np.arange(z0+.3,z1-.1,.3):box(x0+.13,zz,BASE[f]+.025,x1-x0-.26,.015,.006,'wood',f,'furniture')
 for xx in [x0+.45,x1-.85]:
  box(xx,z0+.35,BASE[f],.52,min(2.8,z1-z0-.7),.48,'facade',f,'landscape')
  box(xx+.04,z0+.39,BASE[f]+.47,.44,min(2.7,z1-z0-.8),.22,'green',f,'landscape')
 round_table((x0+x1)/2,(z0+z1)/2,f,.52)
 chair((x0+x1)/2,(z0+z1)/2+.9,f);chair((x0+x1)/2,(z0+z1)/2-.9,f,angle=math.pi)

# Roof garden / actual service roof. Decorative screen remains on separate roof level.
roofnew=NEW.difference(unary_union(VOID[4]));slab(roofnew,4,'roof',.24)
# old roof is 13.2m, 0.9m below new rooftop terrace.
prism(OLD,13.02,.18,'roof',4,'slab')
for x,z,l,a in [(27,22,18,'x'),(45,31,10,'x'),(55,12,19,'z'),(45,22,9,'z')]:wall(x,z,l,a,4,'brick',.90,layer='exterior',y=13.2,th=.23)
for x,z,L,a in [(6,0,12,'z'),(15,0,12,'z'),(0,12,6,'x'),(6,20,9,'x')]:railing(x,z,L,a,4,glass=False)
for x,z,w,d in [(1,12.5,1,4.5),(6.5,17.8,7.7,1),(16,14,1,4.5)]:
 box(x,z,14.1,w,d,.45,'facade',4,'landscape');box(x+.08,z+.08,14.55,w-.16,d-.16,.26,'green',4,'landscape')
box(21.1,15.65,14.1,5.85,5.85,3.85,'metal',4,'exterior')
for z in np.arange(15.65,21.5,.24):box(21.05,z,14.1,.055,.035,3.85,'dark',4,'exterior')
# GHP / EHP simplified modules at roof locations, not collision-checked MEP routing.
for i in range(6):
 x=28.1+(i%3)*1.95;z=16+(i//3)*1.4
 box(x,z,13.40,1.66,.88,2.245,'metal',4,'mep')
 for yy in np.arange(13.7,15.25,.20):box(x+.05,z-.025,yy,1.56,.025,.025,'dark',4,'mep')
for i in range(9):
 x=35+(i%3)*2.1;z=15.4+(i//3)*1.15
 box(x,z,13.40,1.86,.765,1.695,'white',4,'mep')
 for xx in [x+.48,x+1.36]:cyl(xx,z+.38,15.10,.30,.035,'dark',4,'mep',n=18)
for x in [44,47.8,51.6]:
 for z in [14,17.2,20.4,24,27]:
  m=trimesh.creation.box(extents=[3.25,.06,2.25]);m.apply_transform(trimesh.transformations.rotation_matrix(.14,[1,0,0]));m.apply_translation([x+1.625,13.7,z+1.125]);add(m,'solar',4,'fixtures')
  for dx in [.05,1.08,2.16,3.20]:box(x+dx,z,13.86,.022,2.22,.026,'metal',4,'fixtures')

# Indoor cassette units: room-based selected equipment locations, rendered separately.
unitpositions={0:[(3,3),(18,3),(3,9),(18,9),(18,18),(29,16),(34,18),(50,14),(50,19),(48,26),(52,29)],1:[(8,2),(12,2),(18,2),(18,5),(18,9),(4,21),(11,21),(18,21),(29,18),(34,18),(49,20),(52,25),(50,29)],2:[(8,3),(12,3),(9,9),(9,14),(17,14),(29,16),(34,18),(50,14),(49,20),(52,24),(51,29)],3:[(8,4),(12,4),(10,10),(18,15),(29,18),(34,18),(51,14),(50,20),(50,24),(51,29)]}
for f,pts in unitpositions.items():
 for x,z in pts:
  y=BASE[f]+min(2.6,H[f]-.45)
  box(x-.42,z-.42,y,.84,.84,.18,'white',f,'mep')
  box(x-.25,z-.25,y-.02,.5,.5,.025,'dark',f,'mep')
  for k in [-.32,.32]:box(x+k-.022,z-.30,y-.025,.045,.60,.03,'metal',f,'mep')

# Site: schematic levels, real relative position from civil/landscape plans.
site=rect(-27,-43,59,36)
slab(site,9,'floor',.55,offset=-.28,layer='site')
# avoid capping the basement in basement-only view; site entirely hidden there
prism(rect(-24,-38,-4,26),-.28,.07,'asphalt',9,'site')
prism(rect(-39,-48,-29,41),-.52,.12,'asphalt',9,'site')
prism(rect(59,-43,66,37),-.50,.1,'asphalt',9,'site')
prism(rect(-27,32,59,39),-.45,.1,'asphalt',9,'site')
# plaza and boardwalk south edge
prism(rect(0,-37,33,-7),-.18,.09,'floor',9,'site')
prism(rect(0,-6,55,-.35),-.10,.10,'deck',9,'site')
for z in np.arange(-5.8,-.3,.32):box(0,z,.005,55,.018,.008,'wood',9,'site')
# entry decks and paving
for b in [(27,6,45,12),(27,22,36,26),(0,24,21,28)]:prism(rect(*b),-.06,.06,'deck',9,'site')
# parking bay count not forced: plans contain revisions with 31/32 bays; layout schematic
for z in np.arange(-34,24.1,2.65):
 box(-23,z,-.195,5,.06,.01,'line',9,'site');box(-9,z,-.195,5,.06,.01,'line',9,'site')
for x in [-23,-18,-9,-4]:box(x,-34,-.19,.07,58,.012,'line',9,'site')
# pavement panels, small construction joints
for x in np.arange(0,33,3):box(x,-37,-.08,.018,30,.005,'concrete',9,'site')
for z in np.arange(-37,-7,3):box(0,z,-.08,33,.018,.005,'concrete',9,'site')
# Entry drive and crossing
for z in np.arange(-33,-25,1.05):box(-38,z,-.385,8,.5,.013,'line',9,'site')
for z in [-34,-12,9,29]:
 cyl(-3.1,z,-.11,.32,.045,'dark',9,'site',n=16)
box(-3.3,-38,-.04,.22,64,.025,'dark',9,'site')
# Retaining/site boundary wall; actual slopes/detail heights simplified.
box(57,-40,-.45,.35,71,.75,'concrete',9,'site')
for z in np.arange(-38,31,3):cyl(57.2,z,.3,.032,1.1,'dark',9,'site')
beam([57.2,1.3,-39],[57.2,1.3,31],.03,'dark',9,'site')
# Low-mass contextual future facility, disabled by default. Not the library.
box(35,-38,-.15,20,31,11.6,'concrete',9,'context')
box(-2,-54,-.2,50,9,12,'concrete',9,'context');box(-20,40,-.2,70,10,12,'concrete',9,'context')

def tree(x,z,r=1.6,h=5,level=9,y=0):
 cyl(x,z,y,.12,h*.60,'wood',level,'landscape',n=10)
 for dx,dz,dy,rr in [(-.5,0,.0,r*.80),(.5,.1,.45,r*.76),(0,-.4,.9,r*.76),(0,.4,1.35,r*.58)]:
  m=trimesh.creation.icosphere(subdivisions=1,radius=rr)
  m.apply_scale([1,.92,1]);m.apply_translation([x+dx,y+h*.60+dy,z+dz]);add(m,'green' if dy<.8 else 'leaf2',level,'landscape')
# Traced landscape pattern: west parking row, plaza row, building perimeter and south strip.
for z in [-32,-27,-22,-17,-12,-7,-2,3,8,13,18,23]:tree(-2.2,z,1.05,4.5)
for x in [4,10,16,22,28]:tree(x,-5,1.12,4.7)
for x,z in [(-.7,-36),(3,-37),(55.8,1),(55.8,6),(55.8,10),(55.8,16),(55.8,22),(55.8,28),(3,28),(7,29),(13,29),(24,27),(30,29),(38,28),(42,27)]:tree(x,z,1.4,5.2)
for z in range(-41,35,6):tree(-27,z,1.5,5.8)
for x,z,w,d in [(-3.6,-38,2.4,64),(0,26,14,3),(27,27,15,3),(54.8,-1,2,32),(-1,-39,7,3)]:
 box(x,z,-.20,w,d,.26,'soil',9,'landscape');box(x+.05,z+.05,.06,w-.1,d-.1,.22,'green',9,'landscape')
# Benches/plaza planters from landscape type; modelled dimensions simplified.
for x in [5,14,23]:
 box(x,-8,-.04,3,.55,.12,'concrete',9,'site');box(x,-8,.32,3,.55,.08,'wood',9,'site')
# A few parked cars for scale, switch off with site.
for i,z in enumerate([-30,-22,-14,-6,5,14,22]):
 x=-22 if i%2 else -8
 box(x,z,-.12,4.1,1.78,.75,'white' if i%3 else 'teal',9,'site')
 box(x+1.1,z+.13,.6,2.0,1.5,.48,'glass',9,'site')
 for xx in [x+.65,x+3.4]:
  for zz in [z+.08,z+1.7]:
   beam([xx,.2,zz-.07],[xx,.2,zz+.07],.31,'dark',9,'site',n=12)

# Model validation and export: both representations are made from the SAME triangles.
assert abs(SLABS[1].intersection(rect(6.02,6.02,14.98,17.98)).area)<1e-6
assert max(p.bounds[2] for p in [NEW,OLD])==55
materials=[]
for name,(hexval,rough,metal,pattern) in MATS.items():
 c=[int(hexval[i:i+2],16)/255 for i in [1,3,5]]
 materials.append({'name':name,'color':c,'roughness':rough,'metallic':metal,'pattern':pattern,'alpha':.33 if name=='glass' else 1})
matindex={m['name']:i for i,m in enumerate(materials)}
scene=trimesh.Scene();meshes=[];triangles=0
for (level,layer,mat),objs in sorted(parts.items()):
 combined=trimesh.util.concatenate(objs)
 # Keep flat normals and an interleaved binary array for a fast independent WebGL viewer.
 p=np.asarray(combined.vertices,dtype=np.float32)[combined.faces].reshape(-1,3)
 n=np.repeat(np.asarray(combined.face_normals,dtype=np.float32),3,axis=0)
 buf=np.concatenate([p,n],axis=1).astype('<f4')
 name=f'{level:02d}_{layer}_{mat}'
 meshes.append({'name':name,'level':level,'layer':layer,'mat':matindex[mat], 'count':len(buf),'data':base64.b64encode(buf.tobytes()).decode(),'bounds':combined.bounds.tolist()})
 cfg=materials[matindex[mat]]
 pbr=trimesh.visual.material.PBRMaterial(name=mat,baseColorFactor=[int(c*255) for c in cfg['color']]+[int(cfg['alpha']*255)],metallicFactor=cfg['metallic'],roughnessFactor=cfg['roughness'],alphaMode='BLEND' if mat=='glass' else 'OPAQUE',doubleSided=True)
 combined.visual=trimesh.visual.TextureVisuals(material=pbr)
 combined.metadata={'level':level,'layer':layer,'source':'User supplied architectural/civil/landscape/mechanical drawing set','status':'drawing-based simplified reconstruction, not as-built BIM'}
 scene.add_geometry(combined,node_name=name,geom_name=name)
 triangles+=len(combined.faces)
scene.metadata={'title':'강서도서관 가양관 도면기반 3D','units':'metres','y_up':True,'notice':'Not construction-grade BIM. Furniture illustrative; MEP partial; cross-drawing conflicts retained in README.'}
scene.export(str(ROOT/'Gayang_Library.glb'))
d={'title':'강서도서관 가양관','version':'1.0','units':'m','origin':'X4/Y7 grid intersection, Y up; Z follows drawing downward', 'materials':materials,'meshes':meshes,'rooms':rooms,'bases':BASE,'heights':H,
 'voids':{str(k):[list(p.bounds) for p in v] for k,v in VOID.items()},
 'sources':[{'file':'01 설계변경도면_건축.pdf','pages':'37, 40, 43, 46, 49, 52, 56, 59, 62, 65, 67, 73, 79, 82, 83','use':'수정후 평면·입면·단면 우선: 건물, 내부 구획, 외피, 보이드, 계단, 옥상'},{'file':'02 설계변경도면_토목.pdf','pages':'6, 8, 11, 13, 16, 18–21, 40','use':'부지·주차·포장·배수시설의 상대 위치. 레벨 및 상세는 단순화'},{'file':'03 설계변경도면_조경.pdf','pages':'6, 7, 9, 10, 12, 14, 16','use':'수정후 수목·데크·벤치·층별 플랜터. 수종 형상과 수량은 단순화'},{'file':'04 설계변경도면_기계설비.pdf','pages':'3–5, 9, 11–16','use':'기계실·물탱크·펌프·냉난방 장비의 일부를 별도 레이어로 재구성. 전 배관 모델 아님'}],
 'stats':{'triangles':triangles,'meshes':len(meshes),'objectsBeforeMerge':object_count,'spaces':len(rooms)},
 'limitations':['실측·준공 확인 없이 도면으로 재구성한 공간 검토용 모델입니다.','가구·서가·좌석·수목 형상과 일부 창호 세부는 이해를 위한 예시입니다.','기계설비는 주요 장비만 표시합니다. 배관·덕트의 전체 경로/높이/간섭은 검증하지 않았습니다.','도면별 층고·장비 사양·주차 대수에 차이가 있어 건축 수정후 도면을 우선하고 상세는 단순화했습니다.','지붕 위 백색 외곽 프레임은 외피 스크린으로 표현했으며 별도 점유층이 아닙니다.']}
(ROOT/'model.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
(ROOT/'spaces.json').write_text(json.dumps(rooms,ensure_ascii=False,indent=2))
print(json.dumps(d['stats'],ensure_ascii=False));print('GLB bytes', (ROOT/'Gayang_Library.glb').stat().st_size,'JSON bytes',(ROOT/'model.json').stat().st_size)
