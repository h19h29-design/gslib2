"""Video-guided delta for Gayang 1F. Rebuilds original building, then edits only observed wing.
This is manual parametric reconstruction using drawing scale + MP4 frames, NOT photogrammetry.
The inherited MEP routing is a conceptual display, not traced/as-built pipework.
No network. Python 3; numpy, trimesh, shapely.
"""
from pathlib import Path
import json, base64, math, random
from collections import defaultdict
import numpy as np
import trimesh
from shapely.geometry import Polygon, box as rect, Point
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent.parent
legacy=Path(__file__).with_name('legacy_model.py').read_text()
# Execute the existing geometry only; use the same builders and material definitions.
exec(compile(legacy.split('# Model validation and export:')[0], str(Path(__file__).with_name('legacy_model.py')), 'exec'), globals())
random.seed(918)
VIDEO='811411999.732333_62881789719209.MP4'
removed=defaultdict(int)
# Remove illustrative furnishing and the incorrectly directed staircase in filmed new wing.
for key, meshes0 in list(parts.items()):
 lv,layer,mat=key; keep=[]
 for mesh in meshes0:
  lo,hi=mesh.bounds
  inside=lo[0]>=-.45 and hi[0]<=21.05 and lo[2]>=-.45 and hi[2]<=24.1
  kill=False
  if lv==0 and layer=='furniture' and (inside or (lo[0]>=31.4 and hi[0]<=36.1 and lo[2]>=14.6 and hi[2]<=22.1)):kill=True
  if lv==0 and layer=='stairs' and hi[0]<=15.1:kill=True
  if lv==0 and layer=='interior' and hi[0]<=21.1:kill=True
  if lv==0 and layer=='doors' and hi[0]<=21.1:kill=True
  if lv==0 and layer=='roomfloor' and hi[0]<=21.1:kill=True
  # No low flat ceiling over the double-height book stairs.
  if lv==0 and layer=='ceiling':kill=True
  if lv==0 and layer=='structure' and inside:
   parts[(0,'structure','v_limewall')].append(mesh);removed['column_finish']+=1
  elif lv==0 and layer=='interior' and lo[0]>=21 and hi[0]<=27.1 and lo[2]>=15.5 and hi[2]<=21.65:
   parts[(0,'videoWall','v_stairgreen')].append(mesh);removed['stair_core_finish']+=1
  elif kill:removed[layer]+=1
  else:keep.append(mesh)
 parts[key]=keep
# Rebuild 0F low ceiling outside revised wing; others are kept from original.
prism(OLD,3.09,.08,'white',0,'ceiling')
# New video-driven palette. No photorealistic texture is claimed.
MATS.update({
 'v_oak':('#ccb493',.8,0,3), 'v_woodwall':('#bfa17e',.83,0,6),
 'v_stairoak':('#be916a',.8,0,5), 'v_seat':('#c6c1ac',.93,0,0),
 'v_limewall':('#e1e5d1',.94,0,0), 'v_stairgreen':('#d9e9ae',.94,0,0), 'v_white':('#f3f1e7',.83,0,0),
 'v_floor':('#d6cbb7',.89,0,4), 'v_dark':('#373d3d',.6,.12,0),
 'v_rib':('#bcc0b5',.88,0,0), 'v_ceiling':('#d0d3c8',.9,0,0),
 'v_void':('#4f5652',.9,0,0), 'v_metal':('#a0a5a2',.42,.52,0),
 'v_glass':('#a2bdba',.18,.1,0), 'v_light':('#fff6db',.45,0,0),
 'v_door':('#818c8b',.74,.05,0), 'v_grass':('#8eac73',.95,0,0),
 'v_books0':('#e9e4d9',.87,0,0),'v_books1':('#788e87',.87,0,0),
 'v_books2':('#b8bbce',.87,0,0),'v_books3':('#aa7164',.87,0,0),
 'v_books4':('#bf9b4d',.87,0,0),'v_books5':('#657e96',.87,0,0),
 'v_books6':('#7f6257',.87,0,0),'v_books7':('#b3b095',.87,0,0),
 'power_orange':('#f2a448',.6,.1,0),'comm_purple':('#9270ce',.6,.1,0),
 'fire_red':('#d94d42',.6,.1,0),'plumbing_blue':('#418fd6',.6,.1,0),
 'hvac_teal':('#38aaa2',.6,.1,0),
})
# Tags separate video walls/ceiling/furniture so existing section and floor controls remain useful.
def B(x,z,y,w,d,h,mat='v_oak',layer='videoBuilt',lv=0):
 box(x,z,y,w,d,h,mat,lv,layer)
def C(x,z,y,r,h,mat='v_metal',layer='videoBuilt',n=16):
 cyl(x,z,y,r,h,mat,0,layer,n=n)
def L(a,b,r=.02,mat='v_metal',layer='videoBuilt',n=10):
 beam(a,b,r,mat,0,layer,n=n)
def W(x,z,l,axis='x',y=0,h=2.48,mat='v_limewall',th=.12,doors=(),layer='videoWall'):
 wall(x,z,l,axis,0,mat,height=h,doors=doors,layer=layer,th=th,y=y)

# Continuous warm floor, like the filmed paving. Colour/texture only; no invented floor boundaries.
B(.03,.03,.006,20.94,23.94,.032,'v_floor')
# Double-height central atrium: X3-X2 (9m), Y6-Y4 (12m).
# Main stair rises along +Z, unlike the legacy diagonal example.
N=8;RISE=3.30/N;TREAD=.95;Z0=10.40
for i in range(N):
 z=Z0+i*TREAD;top=(i+1)*RISE
 B(6.16,z,top-.12,7.60,TREAD,.12,'v_stairoak')
 B(6.16,z,top-RISE,7.60,.065,RISE,'v_stairoak')
 # Continuous pale seat pads and small white sockets seen on the riser.
 B(6.28,z+.018,top+.010,7.32,.37,.042,'v_seat')
 B(11.94,z-.006,top-.26,.075,.016,.12,'v_white','videoFurniture')
 for yy in [top-.218,top-.19]:C(11.965,z-.013,yy,.004,.006,'v_dark','videoFurniture',n=6)
# Left-in-view narrow walking flight (on model +X side), final top = 2F datum.
for i in range(22):
 z=Z0+i*(7.60/22);top=(i+1)*3.3/22
 B(13.80,z,top-.11,1.03,7.60/22,.11,'v_stairoak')
 B(13.80,z,top-3.3/22,1.03,.035,3.3/22,'v_stairoak')
 B(13.83,z,top+.004,.97,.07,.014,'v_seat')
L([14.99,.96,Z0-.25],[14.99,4.25,18.0],.026)
L([14.99,.96,Z0-.6],[14.99,.96,Z0-.25],.026)
for j in [0,5,10,15,21]:
 z=Z0+j*7.60/22;L([14.97,j*3.3/22+.55,z],[14.97,j*3.3/22+.98,z],.012)
# Timber cheek wall under the stepped seating; profile closed to model real visible enclosure.
profile=[(Z0,0),(18.0,0),(18.0,3.3)]
for i in range(N-1,-1,-1):profile.extend([(Z0+i*TREAD,(i+1)*RISE),(Z0+i*TREAD,i*RISE)])
prism(Polygon(profile).buffer(0),6.035,.13,'v_woodwall',0,'videoBuilt',axis='x')
# Storage backside of stair, with a modest door opening; exact backroom interior unobserved.
W(6.1,18.07,8.75,'x',h=2.50,mat='v_woodwall',doors=[(5.45,.9)])
# Dense vertical timber screens at both front edges (seen at 0:47 and 0:52).
for x0 in [5.82,15.02]:
 for z in np.arange(9.75,11.65,.27):B(x0,z,.04,.10,.15,2.44,'v_woodwall')
# Upper gallery walls and the actual high windows / railing.
W(6.025,6.0,12,'z',y=2.52,h=1.62,mat='v_limewall',th=.15,layer='videoUpper')
W(6.025,6.0,12,'z',y=5.86,h=.45,mat='v_limewall',th=.15,layer='videoUpper')
for z in np.arange(6,18,.0+1.50):
 B(5.96,z,4.10,.14,.16,1.82,'v_rib','videoUpper')
 B(5.99,z+.16,4.13,.036,1.28,1.69,'v_glass','videoGlass')
 B(5.945,z+.07,4.10,.20,1.45,.04,'v_dark','videoUpper')
 B(5.945,z+.07,5.82,.20,1.45,.04,'v_dark','videoUpper')
 B(5.945,z+.74,4.12,.075,.038,1.7,'v_metal','videoUpper')
# Left gallery has low masonry edge and dark balustrade, not all-glass solid wall.
W(15.04,6.,12.,'z',y=2.53,h=.70,mat='v_limewall',th=.15,layer='videoUpper')
B(15.08,6,3.21,2.0,12,.09,'v_floor','videoUpper')
for z in np.arange(6.05,18,.16):L([15.12,3.3,z],[15.12,4.30,z],.010,'v_dark','videoUpper',n=6)
L([15.12,4.30,6.0],[15.12,4.30,18.0],.022,'v_dark','videoUpper')
# Upper mezzanine beyond the last tier: representative visible shelves, no extra occupied storey.
B(6.0,18.0,3.22,9.0,3.05,.08,'v_floor','videoUpper')
# Opaque cover and ribs over the double-height stairs, actual height constrained to drawing levels.
B(6,6,6.34,9,12,.06,'v_void','videoCeiling')
for idx,z in enumerate(np.arange(6,18,.38)):
 B(6,z,6.12,9,.065,.21,'v_rib','videoCeiling')
 if idx%3==0:
  B(6.4,z-.012,6.105,8.2,.052,.021,'v_light','videoLights')
 if idx%4==2:
  for x in [7.1,13.9]:
   C(x,z,6.09,.070,.020,'v_dark','videoLights')
   C(x,z,6.072,.046,.020,'v_light','videoLights')
# Projector and 4 black speakers are visible in stair video; simplified casings.
B(10.25,13.65,5.84,.42,.31,.13,'v_white','videoBuilt')
L([10.46,6.29,13.80],[10.46,5.98,13.80],.020,'v_white','videoBuilt')
for x in [6.25,14.70]:
 for z in [7.7,15.75]:B(x,z,5.20,.25,.30,.40,'v_dark','videoBuilt')
# Low ceiling bands around the atrium (kept out of orbit so floor plans stay readable).
LOW=NEW.difference(rect(6,6,15,18)).difference(rect(6,21,15,24))
prism(LOW,2.58,.08,'v_ceiling',0,'videoCeiling')
for z in np.arange(.2,24,.38):
 for x,w in [(0,6),(15,6)]:
  B(x,z,2.47,w,.065,.12,'v_rib','videoCeiling')
  if int(round(z/.38))%4==0:B(x+.20,z-.01,2.449,w-.40,.035,.020,'v_light','videoLights')
for z in list(np.arange(.1,6,.38))+list(np.arange(18.1,21,.38)):
 B(6,z,2.47,9,.065,.12,'v_rib','videoCeiling')
 if int(z/.38)%4==0:B(6.2,z-.01,2.449,8.6,.035,.020,'v_light','videoLights')
# Detailed, bounded bookcases: pale oak with multicoloured spines and a few blank spaces.
book_palette=['v_books0']*6+['v_books1','v_books2','v_books3','v_books4','v_books5','v_books6','v_books7']
def bookshelf(x,z,w,axis='x',height=2.32,y=0,layer='videoFurniture',back=True,seed=0,front=1):
 rng=random.Random(918+seed+int(x*71+z*103))
 dep=.30
 def b(u,v,yy,ww,dd,hh,m='v_oak'):
  if axis=='x':B(x+u,z+(v if front==1 else dep-v-dd),y+yy,ww,dd,hh,m,layer)
  else:B(x+(v if front==1 else dep-v-dd),z+u,y+yy,dd,ww,hh,m,layer)
 if back:b(0,0,0,w,.04,height)
 b(0,0,.03,w,dep,.10);b(0,0,height-.04,w,dep,.04)
 for u in [0,w-.035]:b(u,0,0,.035,dep,height)
 for yy in np.arange(.18,height-.15,.36):
  b(.035,.02,yy,w-.07,dep-.02,.03)
  u=.07
  while u<w-.12:
   wid=rng.uniform(.022,.055); bh=min(rng.uniform(.205,.295),height-yy-.07)
   if rng.random()>.035:
    mat=rng.choice(book_palette);b(u,.075,yy+.03,wid,.19,bh,mat)
    if rng.random()>.35:b(u+.002,.265,yy+.061,max(.008,wid-.004),.006,.017,'v_books0')
   u+=wid+rng.uniform(.002,.009)
 # small dark shelf label
 b(w*.36,.305,1.275,w*.28,.011,.052,'v_dark')
# Window-wall bookshelves and seated carrels: x0 façade seen at 1:05-1:20.
for z in [1.15,3.25,5.35,7.45,9.55,11.65,17.45,19.15]:bookshelf(.12,z,1.55,'z',seed=int(z*5))
# Window glazed infills + large integrated desk bays between shelving (video appearance).
for z in [13.35,15.30]:
 B(.14,z,.06,.28,1.62,.68,'v_oak','videoFurniture')
 B(.13,z,.73,.84,1.62,.07,'v_oak','videoFurniture')
 for zz in [z,z+1.58]:B(.10,zz,.05,.35,.04,2.33,'v_oak','videoFurniture')
 for yy in [1.37,1.85,2.31]:B(.1,z,yy,.34,1.62,.04,'v_oak','videoFurniture')
 B(.055,z+.04,.86,.025,1.54,1.42,'v_glass','videoGlass')
 B(.035,z+.78,.80,.08,.035,1.48,'v_metal','videoFurniture')
# Timber chair with curved back/arm rather than the legacy cubic seat.
def chair_v(x,z,ang=0,y=0,layer='videoFurniture'):
 # Facing local -Z; rotated globally around this chair centre.
 ca,sa=math.cos(ang),math.sin(ang)
 def p(xx,yy,zz):return [x+ca*xx+sa*zz,y+yy,z-sa*xx+ca*zz]
 def beam0(a,b,r,mat='v_woodwall'):L(p(*a),p(*b),r,mat,layer,n=8)
 for a in [-.19,.19]:
  for b in [-.18,.18]:beam0([a,.03,b],[a*.85,.45,b*.95],.022)
 # rounded cushion
 mesh=trimesh.creation.cylinder(radius=.265,height=.065,sections=20)
 mesh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]));mesh.apply_scale([1,1,.92]);mesh.apply_translation([x,y+.44,z]);add(mesh,'v_dark',0,layer)
 for a in [-.235,.235]:beam0([a,.44,.18],[a,.73,.20],.023)
 pts=[[.265*math.cos(t),.76,.265*math.sin(t)] for t in np.linspace(0,math.pi,14)]
 for a,b in zip(pts,pts[1:]):beam0(a,b,.028)
 for a in [-.255,.255]:beam0([a,.65,-.08],[a,.76,.11],.022)
# Long double-sided shared table down western corridor, black suspended desk lamp bar.
def table_v(x,z,w,d,y=0,layer='videoFurniture',lamp=False):
 # Rounded corners: softened tabletop perimeter and thin pale edge.
 poly=rect(x+.09,z+.09,x+w-.09,z+d-.09).buffer(.09,resolution=5)
 prism(poly,y+.745,.055,'v_oak',0,layer)
 for xx in [x+.12,x+w-.16]:
  for zz in [z+.14,z+d-.18]:B(xx,zz,y,.045,.045,.745,'v_white',layer)
 for zz in np.arange(z+.70,z+d-.1,1.25):
  B(x+w/2-.075,zz,y+.803,.15,.055,.011,'v_metal',layer)
  for dx in [-.045,.032]:B(x+w/2+dx,zz+.012,y+.815,.024,.020,.006,'v_dark',layer)
 if lamp:
  for zz in [z+.22,z+d-.22]:L([x+w/2,y+.8,zz],[x+w/2,y+1.25,zz],.013,'v_dark',layer)
  B(x+w/2-.026,z+.15,y+1.23,.052,d-.3,.05,'v_dark',layer)
  B(x+w/2-.017,z+.18,y+1.222,.034,d-.36,.013,'v_light',layer)
table_v(1.85,11.9,1.42,4.85,lamp=True)
for z in [12.55,13.85,15.15,16.30]:
 chair_v(1.40,z,ang=-math.pi/2);chair_v(3.70,z,ang=math.pi/2)
for z in [14.0,15.95]:chair_v(1.22,z,ang=-math.pi/2)
# Rear shelf walls with neutral metal service door, shown around 1:17-1:28.
for x,w in [(.3,1.70),(3.25,2.4)]:bookshelf(x,20.45,w,seed=int(x*17),front=-1)
W(0,21.0,6,'x',h=2.58,doors=[(2.65,1.1)])
B(2.12,20.93,.04,1.06,.055,2.1,'v_door','videoBuilt')
for x in [2.09,3.20]:B(x,20.90,.01,.045,.1,2.2,'v_metal','videoBuilt')
L([2.28,1.0,20.865],[2.43,1.0,20.865],.014,'v_metal','videoBuilt')
# Timber enclosure on west side: a full-height face, not the naked stair profile.
B(5.82,11.65,.04,.16,6.42,2.46,'v_woodwall')
for z in [12,18]:B(5.77,z-.23,.04,.46,.46,2.50,'v_woodwall')
# East aisle is opposite the western shared-table aisle. The desk runs lengthwise,
# beside the staircase; it is not placed in a fabricated rear tunnel.
for z in [6.25,8.0,9.75,11.50,13.25,15.0,16.75,18.50]:
 bookshelf(20.55,z,1.55,'z',front=-1,seed=int(z*11),back=False)
 B(20.92,z+.03,.70,.025,1.49,1.62,'v_glass','videoGlass')
 B(20.59,z,.04,.34,1.55,.57,'v_oak','videoFurniture')
# White high visitor front and lower worktop (seen from both sides in 1:30-1:42).
B(17.60,9.50,.04,.62,7.6,1.33,'v_white','videoFurniture')
B(17.57,9.48,1.37,.69,7.64,.045,'v_white','videoFurniture')
B(18.20,9.50,.76,.68,7.60,.055,'v_white','videoFurniture')
for z in [10.3,12.7,15.0]:
 B(18.27,z, .99,.035,.55,.35,'v_dark','videoFurniture')
 B(18.29,z+.235,.83,.10,.055,.18,'v_dark','videoFurniture')
 B(18.30,z+.1,.825,.22,.30,.013,'v_dark','videoFurniture')
 B(18.53,z+.09,.823,.18,.43,.020,'v_metal','videoFurniture')
 chair_v(19.28,z+.25,ang=-math.pi/2)
# Blank information board (no invented notices or personal screen contents).
B(15.30,14.4,.04,.09,3.60,2.43,'v_woodwall')
B(15.405,14.62,1.12,.027,2.00,.89,'v_white','videoFurniture')
for z in [14.72,15.36,16.00]:B(15.44,z,1.2,.009,.51,.68,'v_books0','videoFurniture')
# Public kiosk and trolley, simplified from visible casing and frame.
B(19.85,18.80,.04,.45,.40,1.5,'v_white','videoFurniture')
B(19.80,18.83,.91,.053,.33,.35,'v_dark','videoFurniture')
B(16.05,11.10,.17,.62,.88,.045,'v_white','videoFurniture')
B(16.05,11.10,.72,.62,.88,.045,'v_white','videoFurniture')
for x in [16.09,16.60]:
 for z in [11.15,11.91]:L([x,.10,z],[x,.94,z],.019,'v_white','videoFurniture')
for x in [16.1,16.59]:
 for z in [11.17,11.9]:C(x,z,.045,.055,.08,'v_dark','videoFurniture',n=10)
# Books-on-display island at rear of east aisle.
B(17.7,18.0,.04,.72,.62,.78,'v_oak','videoFurniture')
B(17.64,17.95,.82,.84,.72,.055,'v_oak','videoFurniture')
B(17.75,18.06,.88,.51,.18,.27,'v_books0','videoFurniture')
# Add black balusters / oak handrail to existing central stair core; retain original steps.
for i in range(11):
 z=15.8+i*.255;top=(i+1)*3.3/22
 L([24.02,top,z],[24.02,top+.95,z],.011,'v_dark')
 z2=18.605-i*.255;top2=1.65+(i+1)*3.3/22
 L([26.45,top2,z2],[26.45,top2+.95,z2],.011,'v_dark')
L([24.02,1,15.8],[24.02,2.65,18.6],.034,'v_woodwall')
L([26.45,2.65,18.6],[26.45,4.3,15.8],.034,'v_woodwall')
# The latter reading room's exact identity cannot be proved from the edited video.
# Fit its visible furnishings within an existing café room, explicitly marked provisional.
# Do NOT remove a structural wall or combine rooms merely to match the image.
for z in [14.95,16.70,18.45,20.20]:bookshelf(31.62,z,1.55,'z',front=1,height=2.36,seed=int(z*9))
table_v(33.10,16.30,1.3,3.70)
for z in [16.92,18.00,19.05]:chair_v(32.7,z,ang=-math.pi/2);chair_v(34.85,z,ang=math.pi/2)
for x in [32.05,33.55,35.05]:
 C(x,21.04,.73,.40,.065,'v_oak','videoFurniture',n=20)
 C(x,21.04,0,.04,.73,'v_dark','videoFurniture',n=10)
 chair_v(x,20.38,ang=math.pi)
B(31.75,21.80,.85,4.00,.025,1.60,'v_glass','videoGlass')
for x in [31.72,33.71,35.75]:B(x,21.64,.03,.16,.28,2.64,'v_woodwall')
B(31.55,14.65,2.70,4.40,7.35,.07,'v_white','videoCeiling')
B(32.40,14.80,2.63,.04,6.10,.04,'v_dark','videoLights')
for z in [15.1,16.5,17.9,19.3,20.6]:
 C(32.42,z,2.43,.045,.2,'v_dark','videoLights');C(32.42,z,2.42,.034,.012,'v_light','videoLights')
# Top landing backdrop encloses the room glimpsed above the book stairs.
W(6,23.55,9,'x',y=3.30,h=2.9,mat='v_limewall',th=.10,layer='videoUpper')
B(6,18.1,5.83,9,5.45,.10,'v_white','videoCeiling')
for x in [6.25,8.9,11.2,13.75]:
 B(x,22.90,4.10,1.0,.035,1.35,'v_glass','videoGlass')
 B(x,22.93,4.08,1,.025,.038,'v_dark','videoUpper')
B(9.85,20.27,3.34,1.20,.035,2.32,'v_glass','videoGlass')
for x in [9.80,11.08]:B(x,20.20,3.30,.055,.11,2.45,'v_dark','videoUpper')
B(9.80,20.20,5.71,1.335,.11,.05,'v_dark','videoUpper')
for x in [7.,12.9]:
 for z in [18.75,21.8]:C(x,z,5.80,.056,.018,'v_light','videoLights')
# Small air conditioner / circular ceiling fixtures actually visible in the western zone.
for x,z in [(3.25,17.0),(9.0,19.0)]:
 B(x-.31,z-.31,2.41,.62,.62,.055,'v_white','videoBuilt')
 B(x-.20,z-.20,2.397,.40,.40,.013,'v_rib','videoBuilt')
 for k in [-.26,.25]:B(x-.26,z+k,2.395,.52,.012,.009,'v_dark','videoBuilt')
for x,z in [(2.9,13.0),(3.,18.7),(11.6,19.2)]:
 C(x,z,2.425,.09,.036,'v_white','videoBuilt',n=18)
# Indoor plants observed alongside the book stair. Decorative approximate leaf geometry.
def pot(x,z):
 C(x,z,.025,.21,.43,'v_white','videoFurniture',n=18)
 C(x,z,.43,.18,.02,'soil','videoFurniture')
 for k in range(13):
  ang=k*2.399;yy=.6+k*.06
  end=[x+.24*math.cos(ang),yy,z+.24*math.sin(ang)]
  L([x,.38,z],end,.008,'v_woodwall','videoFurniture',n=6)
  m=trimesh.creation.icosphere(subdivisions=1,radius=1);m.apply_scale([.13,.035,.065]);
  m.apply_transform(trimesh.transformations.rotation_matrix(ang,[0,1,0]));m.apply_translation(end);add(m,'green',0,'videoFurniture')
pot(5.28,9.78);pot(15.47,10.04)
# Upper level visible furniture silhouette (shelving through the glazing in 0:47).
for x in [6.5,8.15,11.0,12.65]:bookshelf(x,22.80,1.5,height=2.10,y=3.3,layer='videoUpper',seed=55,front=-1)
# Upper full-width glazed partition visible beyond the top tier.
for x in np.arange(6.10,15,.74):
 B(x,20.32,3.30,.030,.065,2.45,'v_dark','videoUpper')
 B(x+.032,20.35,3.35,.705,.020,2.32,'v_glass','videoGlass')
for y in [3.30,4.42,5.72]:B(6.10,20.32,y,8.85,.065,.035,'v_dark','videoUpper')
# Reference route room labels: keep all original room ids; correct only their video-covered extent.
for r in rooms:
 if r['id']=='102':
  r.update(name='책누리터 · 계단형 열람석',polygon=[[6.16,10.4],[14.85,10.4],[14.85,18],[6.16,18],[6.16,10.4]],center=[10.5,.08,9.2],area=8.69*7.6,source='영상 00:20–00:52 + 건축 단면 79쪽',note='목재 계단·밝은 좌석띠·옆계단·천장 리브를 영상에 맞춰 재구성. 8단 분할 및 상세 치수는 추정.')
 if r['id']=='103':r.update(name='안내데스크 · 서가 통로',center=[17,.08,9.0],polygon=[[15,9],[21,9],[21,18],[15,18],[15,9]],area=54,source='영상 01:25–01:48 · 도면 축척으로 정합',note='흰색 안내데스크·모니터·목재 벽을 재구성. 실제 회로 또는 개인정보 화면은 재현하지 않음.')
 if r['id']=='101':r.update(note='영상에서 확인된 서측 창가 서가·장방형 공용 책상·붙박이 열람석 반영. 미촬영 동측은 기존 모델 유지.')
 if r['id']=='1S':r.update(note='영상 01:50–02:10의 연녹색 벽·검정 난간·목재 손잡이 재구성. 촬영되지 않은 반대편 계단은 기존 도면에 따른 단순화.')
 if r['id']=='105':r.update(source='기존 북카페 구획 + 영상 02:12 이후 가구 외형(위치 미확정)',note='후반 열람공간의 실명·정확한 위치를 영상만으로 확정하지 못하여 기존 구획 안에 임시 배치했습니다. 실제 배치 확인 필요.')
# Rebuild the five previously delivered conceptual systems. Their paths were not measured or traced.
# Do NOT claim these generic connections as observed installation locations.
MEP={'power':('power_orange',(9.25,12),2.95,.035),'comm':('comm_purple',(9.25,16.75),2.75,.03),'plumbing':('plumbing_blue',(18,12),2.45,.04),'hvacpipe':('hvac_teal',(18,18.5),2.65,.045),'fire':('fire_red',(24,18.6),2.95,.03)}
for layer,(mat,(rx,rz),off,rad) in MEP.items():
 for f in [-1,0,1,2,3]:
  yy=BASE[f]+min(off,H[f]-.25)
  # Separate the vertical run by floor, so selecting/exploding floors stays correct.
  beam([rx,BASE[f],rz],[rx,BASE[f]+H[f],rz],.10,mat,f,layer,n=10)
  if f<0:continue
  cz=18.3 if layer=='plumbing' else 13.3
  beam([rx,yy,rz],[rx,yy,cz],rad*1.5,mat,f,layer)
  beam([rx,yy,cz],[43 if layer=='plumbing' else 52,yy,cz],rad*1.5,mat,f,layer)
  for r in rooms:
   if r['level']!=f or r['kind']=='terrace' or '계단실' in r['name']:continue
   n=r['name']
   if layer=='plumbing' and not any(k in n for k in ['화장실','북카페','수유실','휴게실','미화원실','어르신건강교실']):continue
   if layer=='comm' and ('화장실' in n or '방풍실' in n or r['area']<10):continue
   if layer=='fire' and ('화장실' in n or r['area']<15):continue
   x,z=r['center'][0],r['center'][2]
   beam([x,yy,cz],[x,yy,z],rad,mat,f,layer,n=6)
# Metadata preserves observed / inferred / legacy distinction per region.
observations=[
 {'id':'tiers','name':'목재 계단형 열람석','source':VIDEO,'time_range':[20,52],'verified':'목재 단·밝은 연속 좌석띠·한쪽 좁은 계단·금속 손잡이','inferred':'8단 분할, 단별 깊이와 세부 소켓 위치. 층간 높이는 기존 3.3m 기준.','bounds':[6,6,15.2,18.1]},
 {'id':'ceiling','name':'리브 천장과 선형 조명','source':VIDEO,'time_range':[22,52],'verified':'반복 리브·선형 조명·쌍 다운라이트·프로젝터·검정 스피커','inferred':'간격·기구 수·설치높이. 광각 렌즈의 휨은 실제 구조 곡률로 해석하지 않음.','bounds':[6,6,15,18]},
 {'id':'shelves','name':'서측 창가 서가와 공용 책상','source':VIDEO,'time_range':[52,83],'verified':'밝은 붙박이 서가·창가 1인석·긴 양면 테이블·검정 책상 조명·목재 의자','inferred':'각 모듈 치수·책 권수·가구 간 거리. 동측 미촬영 공간은 기존 표현.','bounds':[0,10,6,21]},
 {'id':'desk','name':'안내데스크와 서가 통로','source':VIDEO,'time_range':[84,109],'verified':'흰색 데스크·모니터·정보판·기기함·책 전시대·목재 가림벽','inferred':'촬영 동선과 계단 기준으로 배치 정합. 정확한 장비 모델과 회로는 미확인.','bounds':[15,9,21,21]},
 {'id':'stairwell','name':'연녹색 계단실','source':VIDEO,'time_range':[110,131],'verified':'연녹색 벽·검정 세로 난간·목재 손잡이·유리문','inferred':'반대편 미촬영 계단 제외. 단수·구획 위치는 도면과 촬영 이동 기준의 근사.','bounds':[21,15.7,27,21.5]},
 {'id':'reading','name':'후반 열람공간 · 위치 추정','source':VIDEO,'time_range':[132,150.55],'verified':'목재 서가·긴 독서 테이블·창가 좌석·레일 조명·외부 녹지','inferred':'영상 후반 공간의 정확한 실명을 확인할 수 없어 기존 북카페 구획에 가구 외형을 임시 배치. 실제 실명·위치 확인 필요.','bounds':[31.5,14.6,36,22]},
]
landmarks=[
 {'id':'tiers','label':'계단형 열람석','eye':[10.65,2.05,5.9],'target':[10.35,3.40,17.0],'timestamp':'00:47','source':'video-tiers','obs':'tiers'},
 {'id':'shelves','label':'창가 서가·책상','eye':[3.70,1.65,10.50],'target':[2.15,1.3,17.7],'timestamp':'00:58','source':'video-shelves','obs':'shelves'},
 {'id':'carrels','label':'붙박이 1인 열람석','eye':[3.15,1.6,15.0],'target':[.15,1.25,15.0],'timestamp':'01:12','source':'video-carrels','obs':'shelves'},
 {'id':'desk','label':'안내데스크','eye':[16.65,1.95,8.80],'target':[18.1,1.35,17.50],'timestamp':'01:37','source':'video-desk','obs':'desk'},
 {'id':'stairwell','label':'연녹색 계단실','eye':[24.58,1.65,15.12],'target':[24.58,2.3,18.6],'timestamp':'01:58','source':'video-stairwell','obs':'stairwell'},
 {'id':'reading','label':'열람공간(위치 추정)','eye':[35.1,1.85,15.4],'target':[32.7,1.2,21.2],'timestamp':'02:27','source':'video-reading','obs':'reading'},
]
materials=[]
for name,(hexval,rough,metal,pattern) in MATS.items():
 c=[int(hexval[i:i+2],16)/255 for i in [1,3,5]]
 materials.append({'name':name,'color':c,'roughness':rough,'metallic':metal,'pattern':pattern,'alpha':.28 if name in ['glass','v_glass'] else 1,'emissive':.80 if name=='v_light' else 0})
matindex={m['name']:i for i,m in enumerate(materials)}
scene=trimesh.Scene();meshes=[];triangles=0
for (lv,layer,mat),items in sorted(parts.items()):
 if not items:continue
 combined=trimesh.util.concatenate(items)
 p=np.asarray(combined.vertices,dtype=np.float32)[combined.faces].reshape(-1,3)
 n=np.repeat(np.asarray(combined.face_normals,dtype=np.float32),3,axis=0)
 buf=np.concatenate([p,n],axis=1).astype('<f4')
 name=f'{lv:02d}_{layer}_{mat}';cfg=materials[matindex[mat]]
 meshes.append({'name':name,'level':lv,'layer':layer,'mat':matindex[mat],'count':len(buf),'data':base64.b64encode(buf.tobytes()).decode(),'bounds':combined.bounds.tolist()})
 status='video appearance, dimensions estimated' if layer.startswith('video') else ('inherited conceptual route, NOT as-built' if layer in MEP else 'legacy drawing reconstruction')
 pbr=trimesh.visual.material.PBRMaterial(name=mat,baseColorFactor=[round(c*255) for c in cfg['color']]+[round(cfg['alpha']*255)],metallicFactor=cfg['metallic'],roughnessFactor=cfg['roughness'],alphaMode='BLEND' if cfg['alpha']<1 else 'OPAQUE',doubleSided=True,emissiveFactor=[.8,.76,.68] if mat=='v_light' else [0,0,0])
 combined.visual=trimesh.visual.TextureVisuals(material=pbr);combined.metadata={'level':lv,'layer':layer,'status':status,'source':VIDEO if layer.startswith('video') else 'previous model'}
 scene.add_geometry(combined,node_name=name,geom_name=name);triangles+=len(combined.faces)
scene.metadata={'title':'Gayang Library video-guided 1F + complete previous building','version':'2.0-video','units':'metres','y_up':True,'video':VIDEO,'notice':'Manually reconstructed visible appearance, NOT scan/BIM; MEP routes conceptual.'}
scene.export(str(ROOT/'Gayang_Library_Video.glb'))
DATA={'title':'강서도서관 가양관','version':'2.0-video','units':'m','origin':'X4/Y7 grid intersection, Y up; Z follows drawing downward','materials':materials,'meshes':meshes,'rooms':rooms,'bases':BASE,'heights':H,'voids':{str(k):[list(p.bounds) for p in v] for k,v in VOID.items()},'stats':{'triangles':triangles,'meshes':len(meshes),'objectsBeforeMerge':object_count,'spaces':len(rooms)},'sources':[{'file':VIDEO,'use':'1F visible interior appearance, fixed view 1080x1080, 150.5504s; not full spherical video'},{'file':'01 설계변경도면_건축.pdf','pages':[40,43,79],'use':'coordinate frame, floor heights and central stair section'}],'observations':observations,'landmarks':landmarks,'limitations':['측량·자동 스캔·준공 BIM이 아닌 도면 및 영상 기반 수동 재구성입니다.','영상 밖의 구조·치수는 추정이며, 광각 왜곡을 건물 곡률로 재현하지 않았습니다.','MEP 표시 경로는 이전 개념배관을 유지한 것으로, 실제 위치가 아닐 수 있습니다.','후반 열람공간은 기존 북카페 구획에 임시 배치했으며 실제 위치·실명 확인이 필요합니다.','실내 이동은 벽 충돌 판정 없이 이동하며 W/A/S/D, R/F로 높이를 조정합니다.'],'merge_log':dict(removed)}
(ROOT/'model.json').write_text(json.dumps(DATA,ensure_ascii=False,separators=(',',':')))
(ROOT/'observations.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2))
print(json.dumps(DATA['stats'],ensure_ascii=False));print('Removed legacy components',dict(removed));print('GLB', (ROOT/'Gayang_Library_Video.glb').stat().st_size)
