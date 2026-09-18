/* Self-contained native WebGL2 viewer. No CDN, network, install or account needed. */
'use strict';
(()=>{
const DATA=JSON.parse(document.getElementById('model-data').textContent);
const ASSETS=JSON.parse(document.getElementById('asset-data').textContent);
const $=id=>document.getElementById(id);
const canvas=$('viewport'), host=$('stage');
const state={mode:'floor',floor:0,cut:true,wallHeight:1.45,exterior:true,roof:false,furniture:true,mep:false,power:false,comm:false,fire:false,plumbing:false,hvacpipe:false,videoCeiling:true,focus:true,reference:false,landmark:'tiers',landscape:true,site:false,context:false,labels:false,shadows:true,clay:false,explode:5.5,axis:'x',slice:60,auto:false,selected:null,walk:false};
const orbit={target:[25,1.2,14],yaw:-.75,pitch:.88,distance:65};
const walk={eye:[10,4.95,20],yaw:Math.PI,pitch:0};
let gl,program,shadowProgram,depthTex,shadowFBO,shadowSize=2048,shadowDirty=true,dirty=true,ready=false,meshes=[],width=1,height=1,last=0,keys=new Set(),selectionMesh=null,viewProjection,viewInv,viewMat,eye=[0,0,0],lightMatrix;
const floors=[[-1,'B1','지하 · 기계실'],[0,'1F','로비 · 책누리터'],[1,'2F','자료실 · 열람실'],[2,'3F','청소년 · 사무공간'],[3,'4F','서진홀 · 강의실'],[4,'RF','옥상 · 설비']];
const layerNames={slab:'바닥',roomfloor:'공간별 바닥',exterior:'외벽·창호',interior:'내벽',doors:'문',furniture:'가구',mep:'기계설비',stairs:'계단',structure:'기둥',fixtures:'시설물',ceiling:'천장',landscape:'조경',rail:'난간',site:'부지',context:'주변 건물'};
const materials=DATA.materials;
const v={add:(a,b)=>a.map((x,i)=>x+b[i]),sub:(a,b)=>a.map((x,i)=>x-b[i]),scale:(a,s)=>a.map(x=>x*s),dot:(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),cross:(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],norm:a=>{let n=Math.hypot(...a);return a.map(x=>x/(n||1));}};
const M={
 mul(a,b){let o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o;},
 perspective(fov,asp,n,f){let t=1/Math.tan(fov/2);return new Float32Array([t/asp,0,0,0,0,t,0,0,0,0,(f+n)/(n-f),-1,0,0,2*f*n/(n-f),0]);},
 ortho(l,r,b,t,n,f){return new Float32Array([2/(r-l),0,0,0,0,2/(t-b),0,0,0,0,-2/(f-n),0,-(r+l)/(r-l),-(t+b)/(t-b),-(f+n)/(f-n),1]);},
 lookAt(e,t,up=[0,1,0]){const z=v.norm(v.sub(e,t)),x=v.norm(v.cross(up,z)),y=v.cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-v.dot(x,e),-v.dot(y,e),-v.dot(z,e),1]);},
 transform(a,b){return [0,1,2,3].map(r=>a[r]*b[0]+a[4+r]*b[1]+a[8+r]*b[2]+a[12+r]*b[3]);},
 inverse(a){let rows=[0,1,2,3].map(r=>[a[r],a[4+r],a[8+r],a[12+r],...(Array.from({length:4},(_,c)=>+(r===c)))]);for(let c=0;c<4;c++){let k=c;for(let r=c+1;r<4;r++)if(Math.abs(rows[r][c])>Math.abs(rows[k][c]))k=r;[rows[c],rows[k]]=[rows[k],rows[c]];let d=rows[c][c];if(Math.abs(d)<1e-15)return null;rows[c]=rows[c].map(x=>x/d);for(let r=0;r<4;r++)if(r!==c){let s=rows[r][c];rows[r]=rows[r].map((x,i)=>x-s*rows[c][i]);}}let o=new Float32Array(16);for(let r=0;r<4;r++)for(let c=0;c<4;c++)o[c*4+r]=rows[r][4+c];return o;}
};
const vert=`#version 300 es
precision highp float;
layout(location=0) in vec3 position; layout(location=1) in vec3 normal;
uniform mat4 vp,lightVP; uniform float offsetY;
out vec3 wp,norm; out vec4 lightCoord;
void main(){wp=position+vec3(0.,offsetY,0.);norm=normal;lightCoord=lightVP*vec4(wp,1.);gl_Position=vp*vec4(wp,1.);}`;
const frag=`#version 300 es
precision highp float;
in vec3 wp,norm;in vec4 lightCoord;out vec4 outColor;
uniform vec4 color; uniform vec3 eye;uniform sampler2D shadowMap;
uniform float cutY,cutAxis,cutVal,pattern,metallic,alpha,clay,shadowOn,highlight,emissive,interiorLight;
float noise(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,45.164)))*43758.5453);}
void main(){
 if(wp.y>cutY)discard;
 if(cutAxis>0.5){float q=cutAxis<1.5?wp.x:cutAxis<2.5?wp.y:wp.z;if(q>cutVal)discard;}
 vec3 n=normalize(norm);if(!gl_FrontFacing)n=-n;
 vec3 base=clay>.5?vec3(.87,.86,.83):color.rgb;
 if(clay<.5){
 if(pattern>.5&&pattern<1.5){float u=abs(n.x)>.5?wp.z:wp.x;float row=floor(wp.y/.09);float a=fract((u+mod(row,2.)*.12)/.24),b=fract(wp.y/.09);float mortar=(1.-smoothstep(.035,.075,min(a,1.-a)))*(1.-step(.15,abs(n.y)));mortar=max(mortar,1.-smoothstep(.035,.10,min(b,1.-b)));base=mix(base,vec3(.58,.51,.44),mortar*.46);base*=.97+.045*noise(floor(vec3(u/.24,row,0.)));}
 if(pattern>1.5&&pattern<2.5&&abs(n.y)>.7){vec2 q=fract(wp.xz/1.2);float seam=1.-smoothstep(.008,.020,min(min(q.x,1.-q.x),min(q.y,1.-q.y)));base*=1.-seam*.10;}
 if(pattern>2.5&&pattern<3.5){float u=abs(n.y)>.6?wp.z:wp.x;float grain=sin(u*67.+sin(wp.y*9.+u*3.)*.65);base*=.987+.008*grain+.005*sin(u*219.);}
 if(pattern>4.5&&pattern<5.5){float q=abs(n.y)>.6?wp.z:wp.y;float g=sin(q*85.+sin(wp.x*1.7)+sin(wp.x*.37)*2.);base*=.982+.012*g+.006*sin(q*267.+sin(wp.x*4.)*.4);}
 if(pattern>5.5&&pattern<6.5){float q=abs(n.x)>.5?wp.z:wp.x;float g=sin(q*42.+sin(wp.y*1.5)*.8);base*=.990+.010*g;}
 if(pattern>3.5&&pattern<4.5){vec2 q=fract(wp.xz/.6);float seam=1.-smoothstep(.0018,.005,min(min(q.x,1.-q.x),min(q.y,1.-q.y)));base*=1.-seam*.13;base*=.996+.004*noise(floor(wp*60.));}
 }
 vec3 light=normalize(vec3(-.48,.84,-.36));float nd=max(dot(n,light),0.);
 float sha=1.;vec3 sc=lightCoord.xyz/lightCoord.w*.5+.5;
 if(shadowOn>.5&&alpha>.95&&sc.x>0.&&sc.x<1.&&sc.y>0.&&sc.y<1.&&sc.z<1.){
 float b=max(.00045*(1.-nd),.00014);float sum=0.;
 for(int i=-1;i<=1;i++)for(int j=-1;j<=1;j++){float depth=texture(shadowMap,sc.xy+vec2(float(i),float(j))/2048.).r;sum+=sc.z-b<=depth?1.:0.;}sha=.52+.48*sum/9.;}
 float hemi=mix(.56,.76,interiorLight)+.08*n.y;float sun=nd*mix(.47,.29,interiorLight)*sha;
 vec3 lit=base*(hemi+sun);
 vec3 dir=normalize(eye-wp),halfDir=normalize(dir+light);
 float spec=pow(max(dot(n,halfDir),0.),alpha<.95?48.:36.)*(metallic*.19+(alpha<.95?.2:.025));lit+=spec;
 if(emissive>.01)lit=mix(lit,vec3(1.,.97,.88),emissive);
 if(highlight>.5)lit=mix(lit,vec3(.04,.58,.63),.55);
 float dist=distance(eye,wp);float fog=smoothstep(125.,260.,dist)*.55;lit=mix(lit,vec3(.94,.96,.97),fog);
 outColor=vec4(lit,alpha);
}`;
const shVert=`#version 300 es
precision highp float;layout(location=0) in vec3 position;uniform mat4 vp;uniform float offsetY;out vec3 wp;void main(){wp=position+vec3(0.,offsetY,0.);gl_Position=vp*vec4(wp,1.);}`;
const shFrag=`#version 300 es
precision highp float;in vec3 wp;uniform float cutY,cutAxis,cutVal;void main(){if(wp.y>cutY)discard;if(cutAxis>.5){float q=cutAxis<1.5?wp.x:cutAxis<2.5?wp.y:wp.z;if(q>cutVal)discard;}}`;
function shader(type,s){const sh=gl.createShader(type);gl.shaderSource(sh,s);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(sh));return sh;}
function prog(vs,fs){let p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,vs));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));let names=['vp','lightVP','offsetY','color','eye','shadowMap','cutY','cutAxis','cutVal','pattern','metallic','alpha','clay','shadowOn','highlight','emissive','interiorLight'];return {p,u:Object.fromEntries(names.map(n=>[n,gl.getUniformLocation(p,n)]))};}
function floats64(b64){let str=atob(b64),b=new Uint8Array(str.length);for(let i=0;i<str.length;i++)b[i]=str.charCodeAt(i);return new Float32Array(b.buffer);}
function bufferMesh(a){let vao=gl.createVertexArray();gl.bindVertexArray(vao);let b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,a,gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,3,gl.FLOAT,false,24,12);return {vao,b,count:a.length/6};}
function setup(){
 gl=canvas.getContext('webgl2',{antialias:true,alpha:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});
 if(!gl)throw Error('WebGL 2를 사용할 수 없습니다. Chrome/Edge의 그래픽 가속을 켠 뒤 다시 열어주세요.');
 program=prog(vert,frag);shadowProgram=prog(shVert,shFrag);
 gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);
 depthTex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,depthTex);gl.texImage2D(gl.TEXTURE_2D,0,gl.DEPTH_COMPONENT24,shadowSize,shadowSize,0,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
 shadowFBO=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,shadowFBO);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,depthTex,0);gl.drawBuffers([gl.NONE]);gl.readBuffer(gl.NONE);if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)state.shadows=false;gl.bindFramebuffer(gl.FRAMEBUFFER,null);
 for(let m of DATA.meshes){let a=floats64(m.data);meshes.push({...m,...bufferMesh(a)});delete m.data;}
 lightMatrix=M.mul(M.ortho(-72,72,-65,78,1,220),M.lookAt([-45,100,-38],[20,0,4]));
 resize();ready=true;window.__viewerReady=true;updateUI();fit();goVideo('tiers');$('loading').classList.add('gone');requestAnimationFrame(frame);
}
function offset(m){return state.mode==='explode'&&m.level!==9?(m.level+1)*state.explode:0;}
function visible(m){
 if(m.layer==='context')return state.context&&state.mode==='overview';
 if(m.level===9){if(m.layer==='landscape')return state.site&&state.landscape;return state.site;}
 if(state.mode==='floor'&&m.level!==state.floor)return false;
 if(['overview','section'].includes(state.mode)&&m.level===-1)return false;
 if(m.level===4&&!(state.mode==='floor'&&state.floor===4)&&!state.roof)return false;
 if(m.layer==='ceiling')return state.walk;
 if(['videoCeiling','videoLights'].includes(m.layer))return state.walk&&state.videoCeiling;
 if(m.layer==='videoUpper'&&!state.walk&&['floor','explode'].includes(state.mode))return false;
 if(m.layer==='videoFurniture'&&!state.furniture)return false;
 if(['power','comm','fire','plumbing','hvacpipe'].includes(m.layer)&&!state[m.layer])return false;
 if(m.layer==='exterior'&&!state.exterior)return false;
 if(m.layer==='furniture'&&!state.furniture)return false;
 if(m.layer==='mep'&&!state.mep)return false;
 if(m.layer==='landscape'&&!state.landscape)return false;
 return true;
}
function clip(m){
 let y=1e5,axis=0,val=1e5;
 if(!state.walk&&state.cut&&['floor','explode'].includes(state.mode)&&m.level!==9&&m.level!==4&&['interior','exterior','structure','videoWall','videoGlass','doors'].includes(m.layer))y=DATA.bases[m.level]+state.wallHeight+offset(m);
 if(state.mode==='section'){
  axis={x:1,y:2,z:3}[state.axis];val=state.axis==='x'?(-.4+state.slice/100*56):state.axis==='y'?(state.slice/100*19.5):(-1+state.slice/100*33);
 }
 return [y,axis,val];
}
function uniformClip(p,m){let c=clip(m);gl.uniform1f(p.u.cutY,c[0]);gl.uniform1f(p.u.cutAxis,c[1]);gl.uniform1f(p.u.cutVal,c[2]);gl.uniform1f(p.u.offsetY,offset(m));}
function doShadow(list){
 if(!state.shadows)return;
 gl.bindFramebuffer(gl.FRAMEBUFFER,shadowFBO);gl.viewport(0,0,shadowSize,shadowSize);gl.clear(gl.DEPTH_BUFFER_BIT);gl.useProgram(shadowProgram.p);gl.uniformMatrix4fv(shadowProgram.u.vp,false,lightMatrix);gl.disable(gl.BLEND);
 for(let m of list){if(materials[m.mat].alpha<.95)continue;uniformClip(shadowProgram,m);gl.bindVertexArray(m.vao);gl.drawArrays(gl.TRIANGLES,0,m.count);}
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);
}
function getCamera(){
 let target;
 if(state.walk){eye=[...walk.eye];target=v.add(eye,[Math.sin(walk.yaw)*Math.cos(walk.pitch),Math.sin(walk.pitch),Math.cos(walk.yaw)*Math.cos(walk.pitch)]);}
 else{let cp=Math.cos(orbit.pitch);eye=v.add(orbit.target,[Math.sin(orbit.yaw)*cp*orbit.distance,Math.sin(orbit.pitch)*orbit.distance,Math.cos(orbit.yaw)*cp*orbit.distance]);target=orbit.target;}
 viewMat=M.lookAt(eye,target);viewProjection=M.mul(M.perspective((state.walk?72:42)*Math.PI/180,width/height,.08,450),viewMat);viewInv=M.inverse(viewProjection);
}
function draw(){
 getCamera();let list=meshes.filter(visible);
 if(shadowDirty){doShadow(list);shadowDirty=false;}
 gl.viewport(0,0,canvas.width,canvas.height);gl.clearColor(.946,.961,.970,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(program.p);
 let u=program.u;gl.uniformMatrix4fv(u.vp,false,viewProjection);gl.uniformMatrix4fv(u.lightVP,false,lightMatrix);gl.uniform3fv(u.eye,eye);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,depthTex);gl.uniform1i(u.shadowMap,0);gl.uniform1f(u.clay,state.clay?1:0);gl.uniform1f(u.shadowOn,state.shadows?1:0);gl.uniform1f(u.highlight,0);gl.uniform1f(u.interiorLight,state.walk?1:0);
 let opaques=list.filter(m=>materials[m.mat].alpha>.95),transparent=list.filter(m=>materials[m.mat].alpha<.95);
 function one(m){let mat=materials[m.mat];uniformClip(program,m);gl.uniform4fv(u.color,[...mat.color,1]);gl.uniform1f(u.pattern,mat.pattern);gl.uniform1f(u.metallic,mat.metallic);gl.uniform1f(u.alpha,mat.alpha);gl.uniform1f(u.emissive,mat.emissive||0);gl.bindVertexArray(m.vao);gl.drawArrays(gl.TRIANGLES,0,m.count);}
 gl.disable(gl.BLEND);gl.depthMask(true);for(let m of opaques)one(m);
 transparent.sort((a,b)=>distanceTo(b)-distanceTo(a));gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);for(let m of transparent)one(m);gl.depthMask(true);
 if(selectionMesh&&state.selected&&!state.walk){let r=DATA.rooms.find(r=>r.id===state.selected);let meta={level:r.level};gl.uniform1f(u.cutY,1e5);gl.uniform1f(u.cutAxis,0);gl.uniform1f(u.offsetY,offset(meta));gl.uniform4fv(u.color,[.05,.67,.71,1]);gl.uniform1f(u.alpha,.42);gl.uniform1f(u.highlight,1);gl.uniform1f(u.emissive,0);gl.uniform1f(u.pattern,0);gl.bindVertexArray(selectionMesh.vao);gl.drawArrays(gl.TRIANGLES,0,selectionMesh.count);gl.uniform1f(u.highlight,0);}
 gl.disable(gl.BLEND);drawLabels();drawMiniMap();
 $('render-status').textContent=`${floors.find(f=>f[0]===state.floor)?.[1]||''} · ${list.length}개 메시 표시`;
 window.__lastVisible=list.map(m=>({level:m.level,layer:m.layer}));window.__frameCount=(window.__frameCount||0)+1;
}
function distanceTo(m){let b=m.bounds,c=[(b[0][0]+b[1][0])/2,(b[0][1]+b[1][1])/2+offset(m),(b[0][2]+b[1][2])/2];return Math.hypot(...v.sub(c,eye));}
function frame(ts){let dt=Math.min(.05,(ts-last)/1000||.016);last=ts;let moving=false;
 if(state.auto&&!state.walk){orbit.yaw+=dt*.14;moving=true;}
 if(state.walk&&keys.size){let speed=(keys.has('shift')?5:1.8)*dt;let dir=[Math.sin(walk.yaw),0,Math.cos(walk.yaw)],right=[-dir[2],0,dir[0]];
 for(let [test,vec,s] of [[['w','arrowup'],dir,1],[['s','arrowdown'],dir,-1],[['d','arrowright'],right,1],[['a','arrowleft'],right,-1],[['r'],[0,1,0],1],[['f'],[0,1,0],-1]])if(test.some(k=>keys.has(k))){walk.eye=v.add(walk.eye,v.scale(vec,s*speed));moving=true;}}
 if(dirty||moving){draw();dirty=false;}
 requestAnimationFrame(frame);
}
function resize(){let r=host.getBoundingClientRect();width=Math.max(r.width,1);height=Math.max(r.height,1);let dpr=Math.min(window.devicePixelRatio||1,1.8);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);canvas.style.width=width+'px';canvas.style.height=height+'px';dirty=true;}
new ResizeObserver(resize).observe(host);
function invalidate(shadow=true){dirty=true;if(shadow)shadowDirty=true;}
function fit(){state.walk=false;keys.clear();if(state.mode==='overview'){orbit.target=[17,4,-1];orbit.distance=125;orbit.pitch=.73;orbit.yaw=-.78;}
 else if(state.mode==='explode'){orbit.target=[25,16,15];orbit.distance=96;orbit.pitch=.59;orbit.yaw=-.65;}
 else if(state.floor===-1&&state.mode==='floor'){orbit.target=[13.5,-2.7,15.5];orbit.distance=28;orbit.pitch=.94;orbit.yaw=-.65;}
 else if(state.floor===0&&state.focus&&state.mode==='floor'){orbit.target=[10.5,1.45,13.4];orbit.distance=38;orbit.pitch=.80;orbit.yaw=-.66;}
 else{orbit.target=[27,DATA.bases[state.floor]+1,14.5];orbit.distance=70;orbit.pitch=.93;orbit.yaw=-.62;}
 let a=width/height;if(a<1.25)orbit.distance*=1.25/a;
 updateUI();invalidate();}
function chooseMode(mode){state.focus=false;state.labels=true;state.reference=false;state.mode=mode;state.selected=null;selectionMesh=null;state.walk=false;
 if(mode==='overview'){state.site=true;state.exterior=true;state.roof=true;state.cut=false;}
 if(mode==='floor'){state.site=false;state.roof=false;state.cut=true;state.exterior=true;}
 if(mode==='explode'){state.site=false;state.exterior=false;state.cut=true;state.roof=false;}
 if(mode==='section'){state.site=false;state.exterior=true;state.roof=true;state.cut=false;}
 fit();updateRooms();}
function chooseFloor(f){state.focus=false;state.labels=true;state.reference=false;state.floor=+f;state.mode='floor';state.site=false;state.cut=f!==4;state.exterior=true;state.selected=null;selectionMesh=null;state.roof=f===4;state.walk=false;fit();updateRooms();}
function pointIn(poly,x,z){let inside=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){let a=poly[i],b=poly[j];if((a[1]>z)!==(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])inside=!inside;}return inside;}
function earclip(poly){let ps=poly.slice(0,-1),ids=ps.map((_,i)=>i),tris=[];let area=ps.reduce((s,p,i)=>{let q=ps[(i+1)%ps.length];return s+p[0]*q[1]-q[0]*p[1]},0);if(area<0)ids.reverse();let guard=0;
 const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
 while(ids.length>2&&guard++<200){let found=false;for(let j=0;j<ids.length;j++){let ia=ids[(j+ids.length-1)%ids.length],ib=ids[j],ic=ids[(j+1)%ids.length],a=ps[ia],b=ps[ib],c=ps[ic];if(cross(a,b,c)<=1e-8)continue;let others=ids.filter(i=>![ia,ib,ic].includes(i));if(others.some(i=>{let p=ps[i];return cross(a,b,p)>=-1e-8&&cross(b,c,p)>=-1e-8&&cross(c,a,p)>=-1e-8}))continue;tris.push(a,b,c);ids.splice(j,1);found=true;break;}if(!found)break;}return tris;}
function selectRoom(id,focus=false){let r=DATA.rooms.find(r=>r.id===id);if(!r)return;
 if(state.mode!=='floor'||state.floor!==r.level)chooseFloor(r.level);
 state.selected=id;if(selectionMesh){gl.deleteBuffer(selectionMesh.b);gl.deleteVertexArray(selectionMesh.vao);}
 let tri=earclip(r.polygon),arr=[];for(let p of tri)arr.push(p[0],DATA.bases[r.level]+.06,p[1],0,1,0);selectionMesh=bufferMesh(new Float32Array(arr));
 if(focus){orbit.target=[r.center[0],DATA.bases[r.level]+.6,r.center[2]];let p=r.polygon,xs=p.map(p=>p[0]),zs=p.map(p=>p[1]);orbit.distance=Math.max(14,Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...zs)-Math.min(...zs))*2.5);orbit.pitch=.98;state.walk=false;}
 updateUI();updateRooms(false);invalidate(false);
}
function project(p){let a=M.transform(viewProjection,[...p,1]);if(a[3]<=0)return null;return [(a[0]/a[3]*.5+.5)*width,(-a[1]/a[3]*.5+.5)*height,a[2]/a[3]];}
function drawLabels(){let con=$('labels');con.replaceChildren();if(!state.labels||state.walk)return;
 let used=[];
 if(state.mode==='floor'){
 let rs=DATA.rooms.filter(r=>r.level===state.floor).sort((a,b)=>(b.id===state.selected?1:0)-(a.id===state.selected?1:0)||b.area-a.area);
 for(let r of rs){if(r.area<9&&!state.selected)continue;let p=project([r.center[0],DATA.bases[r.level]+.10,r.center[2]]);if(!p||p[0]<80||p[0]>width-82||p[1]<88||p[1]>height-65||p[2]>1)continue;
 let w=Math.min(150,38+r.name.length*10),rect=[p[0]-w/2,p[1]-11,w,22];if(used.some(b=>Math.abs((b[0]+b[2]/2)-p[0])<(b[2]+w)/2+4&&Math.abs((b[1]+11)-p[1])<26))continue;
 if(used.length>=14&&r.id!==state.selected)continue;used.push(rect);
 let btn=document.createElement('button');btn.className='room-label'+(r.id===state.selected?' active':'');btn.textContent=r.name;btn.style.left=p[0]+'px';btn.style.top=p[1]+'px';btn.onclick=()=>selectRoom(r.id);con.append(btn);
 }
 }else if(state.mode==='explode'){
 for(let [f,title] of floors){if(f===4&&!state.roof)continue;let p=project([-2,DATA.bases[f]+(f+1)*state.explode+.2,24]);if(!p)continue;let b=document.createElement('button');b.className='floor-label';b.textContent=title;b.style.left=p[0]+'px';b.style.top=p[1]+'px';b.onclick=()=>chooseFloor(f);con.append(b);}
 }
}
function rayAt(x,y){let ax=x/width*2-1,ay=1-y/height*2;let a=M.transform(viewInv,[ax,ay,-1,1]),b=M.transform(viewInv,[ax,ay,1,1]);a=a.map(x=>x/a[3]).slice(0,3);b=b.map(x=>x/b[3]).slice(0,3);return [a,v.norm(v.sub(b,a))];}
function pick(x,y){if(state.walk||state.mode!=='floor')return;let [a,d]=rayAt(x,y);if(Math.abs(d[1])<1e-5)return;let t=(DATA.bases[state.floor]+.05-a[1])/d[1];if(t<0)return;let p=v.add(a,v.scale(d,t));let hits=DATA.rooms.filter(r=>r.level===state.floor&&pointIn(r.polygon,p[0],p[2])).sort((a,b)=>a.area-b.area);if(hits.length)selectRoom(hits[0].id);}
function drawMiniMap(){let c=$('minimap'),ctx=c.getContext('2d'),cw=220,ch=132;ctx.clearRect(0,0,cw,ch);let sx=3.55,ox=10,oz=10;
 for(let r of DATA.rooms.filter(r=>r.level===state.floor)){
 ctx.beginPath();r.polygon.forEach((p,i)=>{let x=ox+p[0]*sx,y=oz+p[1]*sx;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.closePath();ctx.fillStyle=r.id===state.selected?'#258e97':({study:'#d1ddd7',service:'#cfd7dc',terrace:'#cbbb9f',kids:'#e5d6b5',culture:'#d8c7c2'}[r.kind]||'#e0e5e5');ctx.fill();ctx.strokeStyle='#87989c';ctx.lineWidth=.5;ctx.stroke();}
 if(state.walk){let x=ox+walk.eye[0]*sx,y=oz+walk.eye[2]*sx;ctx.fillStyle='#087783';ctx.beginPath();ctx.arc(x,y,3,0,7);ctx.fill();ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+Math.sin(walk.yaw)*13,y+Math.cos(walk.yaw)*13);ctx.lineWidth=2;ctx.strokeStyle='#087783';ctx.stroke();}
 $('minimap-title').textContent=`${floors.find(f=>f[0]===state.floor)[1]} 공간 위치`;
}
function updateRooms(reset=true){let search=$('room-search').value.trim();let list=$('room-list');list.replaceChildren();let rs=DATA.rooms.filter(r=>r.level===state.floor&&(!search||r.name.includes(search)||r.id.includes(search)));
 $('room-count').textContent=rs.length;
 for(let r of rs){let b=document.createElement('button');b.className='room-row'+(r.id===state.selected?' selected':'');b.innerHTML=`<span class="room-dot ${r.kind}"></span><span>${r.name}</span><span class="room-arrow">↗</span>`;b.onclick=()=>selectRoom(r.id,true);list.append(b);}
 if(!rs.length){let p=document.createElement('p');p.className='muted';p.textContent=state.floor===4?'옥상 정원 · 주요 설비를 회전해서 살펴보세요.':'일치하는 공간이 없습니다.';list.append(p);}
}
function updateUI(){
 host.classList.toggle('walking',state.walk);
 document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===state.mode));
 document.querySelectorAll('[data-floor]').forEach(b=>b.classList.toggle('active',+b.dataset.floor===state.floor&&state.mode==='floor'));
 let fl=floors.find(f=>f[0]===state.floor);$('floor-title').textContent=fl[2];$('floor-number').textContent=fl[1];
 $('canvas-title').textContent=state.walk?(state.floor===0?'1F · '+(DATA.landmarks.find(l=>l.id===state.landmark)?.label||'실내 자유 시점'):'실내 자유 시점'):({overview:'건물 전체',floor:fl[1]+' · 층별 내부',explode:'층 분리 보기',section:'건물 단면'}[state.mode]);
 $('canvas-subtitle').textContent=state.walk?'드래그로 둘러보기 · W A S D 이동 · R / F 높이 · 벽 충돌 미적용':state.mode==='floor'?'바닥의 공간을 클릭하면 실명과 위치를 확인할 수 있습니다.':'도면을 기반으로 재구성한 검토용 3D 모델입니다.';
 for(let key of ['exterior','furniture','mep','power','comm','fire','plumbing','hvacpipe','videoCeiling','landscape','site','context','labels','shadows','clay','cut','roof']){let el=$('toggle-'+key);if(el)el.checked=state[key];}
 $('wall-control').hidden=!['floor','explode'].includes(state.mode)||state.walk;
 $('explode-control').hidden=state.mode!=='explode';$('section-control').hidden=state.mode!=='section';
 $('wall-value').textContent=state.wallHeight.toFixed(2)+' m';$('explode-value').textContent=state.explode.toFixed(1)+' m';
 $('rotate-auto').classList.toggle('on',state.auto);$('walk-exit').hidden=!state.walk;$('walk-pad').hidden=!state.walk;
 let r=DATA.rooms.find(r=>r.id===state.selected);$('room-detail').hidden=!r||state.walk;
 if(r){$('selected-name').textContent=r.name;$('selected-source').textContent=r.source;$('selected-area').textContent=`모델상 약 ${r.area.toFixed(1)} m² · 실측 면적 아님`;}
 $('walk-btn').textContent=state.walk?'조감도로 돌아가기':'실내 시점';
 document.querySelectorAll('[data-landmark]').forEach(b=>b.classList.toggle('active',state.walk&&state.floor===0&&b.dataset.landmark===state.landmark));
 $('reference-panel').hidden=!state.reference;
 $('compare-open').classList.toggle('teal',state.reference);
 $('system-warning').hidden=!['power','comm','fire','plumbing','hvacpipe'].some(k=>state[k]);
 $('video-ceiling-row').hidden=!state.walk;
 updateReference();
}
function setProp(k,val){state[k]=val;updateUI();invalidate();}
function startWalk(){if(state.walk){fit();return;}if(state.floor===0&&(!state.selected||['101','102','103','1S','105'].includes(state.selected))){goVideo(({101:'shelves',102:'tiers',103:'desk','1S':'stairwell',105:'reading'})[state.selected]||'tiers');return;}if(state.mode!=='floor')chooseFloor(state.floor);let r=DATA.rooms.find(r=>r.id===state.selected)||DATA.rooms.find(r=>r.level===state.floor&&r.kind==='study')||DATA.rooms.find(r=>r.level===state.floor);
 if(!r){toast('공간을 선택한 뒤 실내 시점을 사용하세요.');return;}
 walk.eye=[r.center[0],DATA.bases[state.floor]+1.65,r.center[2]];walk.yaw=Math.PI;walk.pitch=-.02;state.walk=true;state.auto=false;updateUI();invalidate();toast('W A S D로 이동하고, 드래그로 둘러보세요. 벽 충돌은 적용하지 않았습니다.');}
function toast(s){$('toast').textContent=s;$('toast').classList.add('show');clearTimeout(window.__toastT);window.__toastT=setTimeout(()=>$('toast').classList.remove('show'),4200);}
// Pointer/touch orbit: one finger rotation, two-finger pan+pinch. No third-party dependencies.
let pointers=new Map(),lastPt=null,startPt=null,dragged=false,pinch=null;
canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);startPt=[e.clientX,e.clientY];lastPt=[e.clientX,e.clientY,e.button];dragged=false;if(pointers.size===2){let [a,b]=[...pointers.values()];pinch={d:Math.hypot(a[0]-b[0],a[1]-b[1]),c:[(a[0]+b[0])/2,(a[1]+b[1])/2]};}canvas.classList.add('dragging');});
function pan(dx,dy){let s=orbit.distance*.0012;let right=[Math.cos(orbit.yaw),0,-Math.sin(orbit.yaw)],fwd=[Math.sin(orbit.yaw),0,Math.cos(orbit.yaw)];orbit.target=v.add(orbit.target,v.add(v.scale(right,-dx*s),v.scale(fwd,dy*s)));}
canvas.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,[e.clientX,e.clientY]);let dx=e.clientX-lastPt[0],dy=e.clientY-lastPt[1];if(Math.hypot(e.clientX-startPt[0],e.clientY-startPt[1])>4)dragged=true;
 if(pointers.size===2&&!state.walk){let [a,b]=[...pointers.values()],d=Math.hypot(a[0]-b[0],a[1]-b[1]),c=[(a[0]+b[0])/2,(a[1]+b[1])/2];if(pinch){orbit.distance=Math.max(4,Math.min(270,orbit.distance*pinch.d/d));pan(c[0]-pinch.c[0],c[1]-pinch.c[1]);}pinch={d,c};}
 else if(state.walk){walk.yaw-=dx*.004;walk.pitch=Math.max(-1.45,Math.min(1.45,walk.pitch-dy*.004));}
 else if(lastPt[2]===2||e.shiftKey||e.ctrlKey||e.metaKey)pan(dx,dy);
 else{orbit.yaw-=dx*.005;orbit.pitch=Math.max(.02,Math.min(1.56,orbit.pitch+dy*.005));}
 lastPt=[e.clientX,e.clientY,lastPt[2]];invalidate(false);
});
canvas.addEventListener('pointerup',e=>{pointers.delete(e.pointerId);if(!dragged&&!state.walk){let r=canvas.getBoundingClientRect();pick(e.clientX-r.left,e.clientY-r.top);}pinch=null;if(!pointers.size){lastPt=null;canvas.classList.remove('dragging');}});
canvas.addEventListener('pointercancel',()=>{pointers.clear();pinch=null;canvas.classList.remove('dragging');});
canvas.addEventListener('contextmenu',e=>e.preventDefault());
canvas.addEventListener('wheel',e=>{e.preventDefault();if(state.walk){walk.eye=v.add(walk.eye,[Math.sin(walk.yaw)*e.deltaY*-.012,0,Math.cos(walk.yaw)*e.deltaY*-.012]);}else orbit.distance=Math.max(4,Math.min(300,orbit.distance*Math.exp(e.deltaY*.001)));invalidate(false);},{passive:false});
window.addEventListener('keydown',e=>{if(e.key==='Escape'){keys.clear();if($('source-dialog').open)$('source-dialog').close();if($('help-dialog').open)$('help-dialog').close();if(state.walk)fit();return;}if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;if(state.walk&&['w','a','s','d','r','f','arrowup','arrowdown','arrowleft','arrowright','shift'].includes(e.key.toLowerCase())){keys.add(e.key.toLowerCase());e.preventDefault();}});
window.addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));window.addEventListener('blur',()=>keys.clear());
// Native interface bindings.
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>chooseMode(b.dataset.mode));
document.querySelectorAll('[data-floor]').forEach(b=>b.onclick=()=>chooseFloor(+b.dataset.floor));
for(let k of ['exterior','furniture','mep','power','comm','fire','plumbing','hvacpipe','videoCeiling','landscape','site','context','labels','shadows','clay','cut','roof']){let el=$('toggle-'+k);if(el)el.onchange=()=>setProp(k,el.checked);}
$('wall-height').oninput=e=>setProp('wallHeight',+e.target.value);$('explode-height').oninput=e=>setProp('explode',+e.target.value);$('slice-value').oninput=e=>setProp('slice',+e.target.value);
$('slice-axis').onchange=e=>setProp('axis',e.target.value);$('room-search').oninput=()=>updateRooms(false);
$('reset-view').onclick=()=>fit();$('rotate-auto').onclick=()=>setProp('auto',!state.auto);
$('top-view').onclick=()=>{state.walk=false;orbit.pitch=1.56;orbit.yaw=0;updateUI();invalidate(false);};
$('front-view').onclick=()=>{state.walk=false;orbit.pitch=.20;orbit.yaw=0;updateUI();invalidate(false);};
$('iso-view').onclick=()=>{state.walk=false;orbit.pitch=.88;orbit.yaw=-.65;updateUI();invalidate(false);};
$('zoom-in').onclick=()=>{orbit.distance*=.83;invalidate(false);};$('zoom-out').onclick=()=>{orbit.distance*=1.2;invalidate(false);};
$('walk-btn').onclick=startWalk;$('walk-room').onclick=startWalk;$('walk-exit').onclick=()=>fit();
$('minimap').onclick=e=>{let r=e.target.getBoundingClientRect(),x=((e.clientX-r.left)*220/r.width-10)/3.55,z=((e.clientY-r.top)*132/r.height-10)/3.55;let hit=DATA.rooms.filter(s=>s.level===state.floor&&pointIn(s.polygon,x,z)).sort((a,b)=>a.area-b.area)[0];if(hit)selectRoom(hit.id,true);};
$('menu-toggle').onclick=()=>$('sidebar').classList.toggle('mobile-open');
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{toast('브라우저 메뉴에서 전체화면을 사용하세요.');}};
function download(blob,name){let a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),15000);}
$('save-image').onclick=()=>{draw();canvas.toBlob(b=>download(b,'Gayang_3D_view.png'));};
$('download-glb').onclick=()=>{let s=atob($('glb-data').textContent.trim()),b=new Uint8Array(s.length);for(let i=0;i<s.length;i++)b[i]=s.charCodeAt(i);download(new Blob([b],{type:'model/gltf-binary'}),'Gayang_Library_Video.glb');toast('층·레이어 이름이 포함된 실제 3D 모델 파일입니다.');};
function showSource(){let opt=$('source-select');opt.replaceChildren();for(let [key,a] of Object.entries(ASSETS)){let o=document.createElement('option');o.value=key;o.textContent=a.title;opt.append(o);}opt.value=String(state.floor);if(!ASSETS[opt.value])opt.value='1';loadSource();$('source-dialog').showModal();}
function loadSource(){let a=ASSETS[$('source-select').value];$('source-img').src=a.data;$('source-caption').textContent=a.caption;$('source-zoom').value=100;$('source-img').style.width='100%';}
$('source-open').onclick=showSource;$('mini-source').onclick=showSource;$('source-select').onchange=loadSource;$('source-zoom').oninput=e=>$('source-img').style.width=e.target.value+'%';
$('help-open').onclick=()=>$('help-dialog').showModal();document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());
$('detail-close').onclick=()=>{state.selected=null;selectionMesh=null;updateUI();updateRooms(false);invalidate(false);};
for(let b of document.querySelectorAll('[data-key]')){b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);keys.add(b.dataset.key)};b.onpointerup=b.onpointercancel=()=>keys.delete(b.dataset.key);}

function goVideo(id){
 const a=DATA.landmarks.find(x=>x.id===id);if(!a)return;
 state.mode='floor';state.floor=0;state.focus=true;state.walk=true;state.cut=false;state.exterior=true;state.site=false;state.roof=false;state.labels=false;state.furniture=true;state.auto=false;state.selected=null;state.landmark=id;keys.clear();
 walk.eye=[...a.eye];const d=v.sub(a.target,a.eye);walk.yaw=Math.atan2(d[0],d[2]);walk.pitch=Math.atan2(d[1],Math.hypot(d[0],d[2]));
 updateUI();updateRooms(false);invalidate();$('sidebar').classList.remove('mobile-open');
}
function updateReference(){
 const a=DATA.landmarks.find(x=>x.id===state.landmark)||DATA.landmarks[0],o=DATA.observations.find(x=>x.id===a.obs),im=ASSETS[a.source];
 if($('reference-title').textContent!==a.label){
  $('reference-title').textContent=a.label;$('reference-time').textContent=a.timestamp+' · 첨부 영상 프레임';
  if(im)$('reference-img').src=im.data;
  $('reference-seen').textContent=o.verified;$('reference-inferred').textContent=o.inferred;
 }
}
$('video-reset').onclick=()=>goVideo('tiers');
$('video-cutaway').onclick=()=>{state.floor=0;state.mode='floor';state.focus=true;state.walk=false;state.cut=true;state.exterior=false;state.labels=true;state.furniture=true;state.site=false;fit();updateRooms();};
for(const a of DATA.landmarks){let b=document.createElement('button');b.dataset.landmark=a.id;b.innerHTML='<span>'+a.label+'</span><small>'+a.timestamp+'</small>';b.onclick=()=>goVideo(a.id);$('video-landmarks').append(b);}
$('compare-open').onclick=()=>{state.reference=!state.reference;updateUI();};
$('reference-close').onclick=()=>{state.reference=false;updateUI();};
$('reference-original').onclick=()=>{showSource();$('source-select').value=(DATA.landmarks.find(x=>x.id===state.landmark)||DATA.landmarks[0]).source;loadSource();};
$('systems-off').onclick=()=>{for(const k of ['power','comm','fire','plumbing','hvacpipe'])state[k]=false;updateUI();invalidate();};

window.__test={goVideo,visible,clip,offset,state,orbit,walk,chooseMode,chooseFloor,setProp,selectRoom,fit,startWalk,project,rooms:DATA.rooms,materials:DATA.materials,stats:DATA.stats,getEye:()=>eye,getVisible:()=>meshes.filter(visible).map(m=>({level:m.level,layer:m.layer,name:m.name})),forceDraw:()=>{shadowDirty=true;draw();},getGL:()=>({version:gl.getParameter(gl.VERSION),error:gl.getError()})};
updateRooms();
try{setup();}catch(err){$('loading').innerHTML='<div class="load-error"><h2>3D 화면을 시작하지 못했습니다</h2><p></p><p>Chrome 또는 Edge에서 파일을 직접 열고 그래픽 가속 설정을 확인해주세요.</p></div>';$('loading').querySelector('p').textContent=err.message;console.error(err);window.__viewerError=err.message;}
})();
