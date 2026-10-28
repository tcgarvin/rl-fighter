import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mountToLocal } from '../hulls.js';

const PAINT = [0xf2be43, 0x929eff];
const mat = (color, roughness = .48) => new T.MeshStandardMaterial({ color, roughness, metalness: .12, flatShading: true });
const M = { ivory: mat(0xddd9cb), dark: mat(0x303a40,.7), metal: mat(0x77858a), paint: PAINT.map(c=>mat(c)), ink: new T.MeshBasicMaterial({color:0x192126}), mint: new T.MeshBasicMaterial({color:0xb6ffe0,transparent:true,opacity:.45,depthWrite:false,side:T.DoubleSide}), white: new T.MeshBasicMaterial({color:0xf4fff9}), band: new T.MeshBasicMaterial({color:0xb6ffe0}) };
const box = new T.BoxGeometry(1,1,1);
const disc = new T.CylinderGeometry(1,1,1,12);
// Exhaust begins at the mount and tapers along +X in its own frame.
const wedge = new T.BufferGeometry();
wedge.setAttribute('position',new T.Float32BufferAttribute([0,0,-.65,0,0,.65,1,0,0, 0,-.25,0,1,0,0,0,.25,0],3));
wedge.computeVertexNormals();
let scene, camera, effects, ringFX, cursor=0;
const slots = Array.from({length:768},()=>({life:0,max:1,x:0,z:0,vx:0,vz:0,size:1,angle:0,spin:0,kind:0,color:0xffffff}));
const dummy=new T.Object3D(), color=new T.Color();
const edgeShips=new Set();
let edge;
function plate(points, depth, y) {
  const shape=new T.Shape(); points.forEach((p,i)=>i?shape.lineTo(p[0],p[1]):shape.moveTo(p[0],p[1])); shape.closePath();
  const g=new T.ExtrudeGeometry(shape,{depth,bevelEnabled:true,bevelSegments:1,steps:1,bevelSize:.09,bevelThickness:.07});
  g.rotateX(-Math.PI/2); g.translate(0,y,0); return g;
}
function put(parent,geo,material,x=0,y=0,z=0,sx=1,sy=1,sz=1) {
  const o=new T.Mesh(geo,material); o.position.set(x,y,z);o.scale.set(sx,sy,sz);parent.add(o);return o;
}
function flash(x,y,size,life,kind=0,c=0xfff2c4,vx=0,vz=0) {
  const s=slots[cursor];cursor=(cursor+1)%slots.length;
  Object.assign(s,{x,z:-y,size,life,max:life,kind,color:c,vx,vz,angle:Math.random()*6.28,spin:(Math.random()-.5)*10});
}
function burst(e) {
  const death=e.kind==='death', r=e.radius;
  flash(e.x,e.y,r*.28,death?.18:.1,0,0xfff6d8);
  flash(e.x,e.y,r,death?.7:.35,2,death?0xddd9cb:0xf2be43);
  const n=death?15:7;
  for(let i=0;i<n;i++) {const a=i/n*Math.PI*2+Math.random()*.3, v=(death?13:20)*( .4+Math.random());flash(e.x,e.y,death?1.2:.45,death?.6+Math.random()*.35:.25+Math.random()*.2,1,i%3===0?PAINT[e.team]:0xddd9cb,Math.cos(a)*v,Math.sin(a)*v);}
}
function makeInstances(geo,material,n) {const m=new T.InstancedMesh(geo,material,n);m.instanceMatrix.setUsage(T.DynamicDrawUsage);m.frustumCulled=false;m.count=0;scene.add(m);return m;}

export default {
 id:'enamel',name:'Enamel Fleet',blurb:'Painted armor, exposed mechanisms, and pale mint thrust. A kinetic exhibit in warm charcoal.',
 hud:{'--bg':'#20282dee','--fg':'#ece9df','--muted':'#a9b4b8','--team-a':'#f2be43','--team-b':'#929eff','--font':'"Inter", "Helvetica Neue", sans-serif'},fonts:[],
 init(ctx) {
  scene=ctx.scene;camera=ctx.camera;scene.background=new T.Color(0x14191c);
  ctx.renderer.toneMapping=T.ACESFilmicToneMapping;ctx.renderer.toneMappingExposure=1.25;
  scene.add(new T.HemisphereLight(0xf5f1df,0x35434b,2));
  const sun=new T.DirectionalLight(0xfff1d5,3);sun.position.set(-120,320,150);scene.add(sun);
  const stars=new Float32Array(420*3);let seed=12345;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  for(let i=0;i<420;i++){stars[i*3]=(rand()-.5)*2600;stars[i*3+1]=-25-rand()*70;stars[i*3+2]=(rand()-.5)*2600;}
  const sg=new T.BufferGeometry();sg.setAttribute('position',new T.BufferAttribute(stars,3));scene.add(new T.Points(sg,new T.PointsMaterial({color:0x718080,size:.65,transparent:true,opacity:.34,sizeAttenuation:true})));
  const lines=[];for(let i=0;i<160;i++){const a=i/160*Math.PI*2;const r=i%10===0?526:522;lines.push(Math.cos(a)*520,-2,Math.sin(a)*520,Math.cos(a)*r,-2,Math.sin(a)*r);}
  const lg=new T.BufferGeometry();lg.setAttribute('position',new T.Float32BufferAttribute(lines,3));scene.add(new T.LineSegments(lg,new T.LineBasicMaterial({color:0x56636a,transparent:true,opacity:.35})));
  edge=makeInstances(new T.RingGeometry(518,519,128,1,0,.1),new T.MeshBasicMaterial({color:0xf2be43,transparent:true,opacity:.6,side:T.DoubleSide,depthWrite:false}),32);
  effects=makeInstances(box,new T.MeshBasicMaterial({vertexColors:false,transparent:true,depthWrite:false,blending:T.AdditiveBlending}),768);
  // A broken contour, not a smoke disc.
  const rg=[];for(let i=0;i<10;i++){const g=new T.RingGeometry(.94,1,4,1,i*Math.PI/5,.43);rg.push(g);}const ringGeo=mergeGeometries(rg);rg.forEach(g=>g.dispose());ringGeo.rotateX(-Math.PI/2);
  ringFX=makeInstances(ringGeo,new T.MeshBasicMaterial({side:T.DoubleSide,transparent:true,depthWrite:false,blending:T.AdditiveBlending}),768);
 },
 createShip(ship) {
  const root=new T.Group(), staticRoot=new T.Group();root.add(staticRoot);const h=ship.hull, team=ship.team, paint=M.paint[team], owned=[];
  const addPlate=(p,d,y,m)=>{const g=plate(p,d,y);owned.push(g);return put(staticRoot,g,m);};
  const L=h.length,B=h.beam;
  if(ship.hullName==='fighter') {
   const p=[[5,0],[2.5,1.25],[-2.7,2.3],[-4.2,1.3],[-4.2,-1.3],[-2.7,-2.3],[2.5,-1.25]];
   addPlate(p,.9,-.45,M.dark);addPlate(p.map(([x,z])=>[x*.94,z*.94]),.17,.48,paint);
   put(staticRoot,box,M.ivory,-.1,.81,0,5.8,.55,1.2);put(staticRoot,box,M.ink,.9,1.1,0,1.5,.08,.66);
  } else if(ship.hullName==='strafer') {
   for(const x of [-2.4,2.4]) {put(staticRoot,box,M.dark,x,0,0,1.5,.8,B-.9);put(staticRoot,box,paint,x,.49,0,1.2,.24,B-1.2);}
   addPlate([[4.5,0],[3.2,1.25],[-3.8,1.25],[-3.8,-1.25],[3.2,-1.25]],.8,-.4,M.dark);
   put(staticRoot,box,M.ivory,-.3,.5,0,6.7,.35,2);put(staticRoot,box,paint,-1.5,.72,0,2,.1,1.65);
  } else {
   const p=[[7.5,0],[5,4],[-4.5,5],[-7.5,3],[-7.5,-3],[-4.5,-5],[5,-4]];
   addPlate(p,1.4,-.7,M.dark);addPlate(p.map(([x,z])=>[x*.97,z*.97]),.15,.76,paint);
   addPlate(p.map(([x,z])=>[x*.73,z*.66]),.12,.98,M.dark);
   put(staticRoot,box,M.ivory,-.3,1.07,0,3.2,.25,1.6);
   for(const z of [-2,2])put(staticRoot,box,M.dark,-5.8,.4,z,2.4,1.3,2);
  }
  // One broad transverse stripe versus a paired stripe, visible without hue.
  const markX=ship.hullName==='gunship'?-5: -2.6, markY=ship.hullName==='gunship'?1.01:.79;
  for(let j=0;j<(team?2:1);j++)put(staticRoot,box,M.ivory,markX+j*.65,markY,0,team?.32:.85,.06,ship.hullName==='strafer'?B-1.8:B*.63);
  // Dorsal identification: a solid diamond / two separated square halves.
  if(team===0){const o=put(staticRoot,box,M.ink,-.9,1.14,0,.8,.05,.8);o.rotation.y=Math.PI/4;}
  else for(const z of [-.32,.32])put(staticRoot,box,M.ink,-.9,1.14,z,.85,.06,.42);
  const flames=h.thrusters.map(t=>{
   const g=new T.Group();g.name=t.id;g.position.set(...mountToLocal(t.pos,0));g.rotation.y=Math.atan2(-t.dir[1],-t.dir[0]);root.add(g);
   const s=t.size;
   const collar=put(g,disc,M.metal,-.18,0,0,s*.72,s*.65,s*.72);collar.rotation.z=Math.PI/2;
   const bellGeo=new T.CylinderGeometry(s*.64,s*.38,s*.65,8,1,true);owned.push(bellGeo);const bell=put(g,bellGeo,M.dark);bell.rotation.z=-Math.PI/2;
   const mouth=put(g,disc,M.ink,.34,0,0,s*.53,.06,s*.53);mouth.rotation.z=Math.PI/2;
   const throat=put(g,disc,M.ivory,.38,0,0,s*.3,.02,s*.3);throat.rotation.z=Math.PI/2;
   const jet=new T.Group();jet.position.x=.4;g.add(jet);
   const shell=put(jet,wedge,M.mint,0,0,0,1,s,s);const core=put(jet,wedge,M.white,0,.03,0,1,s*.36,s*.4);
   const band=put(jet,box,M.band,0,.05,0,.11,s*.17,s*.75);
   return {jet,shell,core,band,size:s,level:0};
  });
  const turrets=h.turrets.map(t=>{
   const base=new T.Group();base.position.set(...mountToLocal(t.pos,t.height));root.add(base);
   const r=t.arc?1.13:.58;
   put(base,disc,M.dark,0,0,0,r,.3,r);put(base,disc,M.ivory,0,.2,0,r*.8,.2,r*.8);
   const aim=new T.Group();aim.name=t.id;base.add(aim);
   put(aim,box,M.ivory,0,.42,0,t.arc?1.6:.9,.6,t.arc?1.05:.65);
   put(aim,box,paint,-.35,.75,0,.45,.08,t.arc?.9:.6);
   const len=t.arc?2.2:1.25;put(aim,box,M.dark,len*.5+.45,.43,0,len,.32,.34);
   put(aim,box,M.ivory,len+.35,.43,0,.35,.4,.44);
   return aim;
  });
  // Merge all stationary parts by material: a few draw calls per hull.
  staticRoot.updateMatrixWorld(true);const batches=new Map();for(const o of staticRoot.children){const g=o.geometry.clone();g.applyMatrix4(o.matrix);if(!batches.has(o.material))batches.set(o.material,[]);batches.get(o.material).push(g);}
  staticRoot.clear();for(const [m,gs] of batches){const normalized=gs.map(g=>g.index?g.toNonIndexed():g);const g=mergeGeometries(normalized);put(staticRoot,g,m);owned.push(g);for(const v of normalized)v.dispose();for(const v of gs)if(v.index)v.dispose();}
  const state={x:0,z:0,alive:false};edgeShips.add(state);
  return {object:root,update(v,dt){root.visible=v.alive;root.position.set(v.x,0,-v.y);root.rotation.y=v.heading;state.x=v.x;state.z=-v.y;state.alive=v.alive;
   for(let i=0;i<flames.length;i++){const f=flames[i],target=v.throttles[i]||0;f.level+=(target-f.level)*(1-Math.exp(-dt*22));f.jet.visible=f.level>.018;const pixel=camera.position.distanceTo(root.position)*.0009;const len=Math.max(f.size,pixel)*(1+6*f.level);f.shell.scale.set(len,Math.max(f.size,pixel*.7),Math.max(f.size,pixel*.7));f.core.scale.x=len*.5;f.band.position.x=len*.36;f.band.visible=target>.75;}
   for(let i=0;i<turrets.length;i++)turrets[i].rotation.y=v.turretAngles[i];
  },dispose(){edgeShips.delete(state);for(const g of owned)g.dispose();}};
 },
 createProjectiles(capacity) {
  const bullets=makeInstances(box,new T.MeshBasicMaterial({color:0xfff2c4}),capacity), trails=makeInstances(box,new T.MeshBasicMaterial({color:0xffd99b,transparent:true,opacity:.18,depthWrite:false}),capacity),beams=makeInstances(box,new T.MeshBasicMaterial({color:0xffffff}),128), beamHalo=makeInstances(box,new T.MeshBasicMaterial({color:0xb6ffe0,transparent:true,opacity:.16,depthWrite:false}),128);
  return {update(ps,bs,alpha){const n=Math.min(ps.length,capacity);for(let i=0;i<n;i++){const p=ps[i],a=Math.atan2(p.vy,p.vx);dummy.position.set(p.x+p.vx*alpha/30,1,-p.y-p.vy*alpha/30);dummy.rotation.set(0,a,0);dummy.scale.set(p.kind==='flak'?2:3.2,.35,p.kind==='flak'?.9:.48);dummy.updateMatrix();bullets.setMatrixAt(i,dummy.matrix);dummy.scale.set(p.kind==='flak'?4:8,.12,.8);dummy.position.x-=Math.cos(a)*3;dummy.position.z+=Math.sin(a)*3;dummy.updateMatrix();trails.setMatrixAt(i,dummy.matrix);}bullets.count=trails.count=n;bullets.instanceMatrix.needsUpdate=trails.instanceMatrix.needsUpdate=true;
   const nb=Math.min(bs.length,128);for(let i=0;i<nb;i++){const b=bs[i],dx=b.x2-b.x1,dy=b.y2-b.y1;dummy.position.set((b.x1+b.x2)/2,1,-(b.y1+b.y2)/2);dummy.rotation.set(0,Math.atan2(dy,dx),0);dummy.scale.set(Math.hypot(dx,dy),.16,.23);dummy.updateMatrix();beams.setMatrixAt(i,dummy.matrix);dummy.scale.z=1.5;dummy.updateMatrix();beamHalo.setMatrixAt(i,dummy.matrix);}beams.count=beamHalo.count=nb;beams.instanceMatrix.needsUpdate=beamHalo.instanceMatrix.needsUpdate=true;
  }};
 },
 onMuzzle(e){flash(e.x+Math.cos(e.angle)*1.5,e.y+Math.sin(e.angle)*1.5,e.weapon==='flak'?1.8:1,.065,0,0xf4fff9);},
 onHit(e){flash(e.x,e.y,1.4,.09,0,0xffffff);for(let i=0;i<4;i++){const a=Math.random()*6.28;flash(e.x,e.y,.35,.25,1,0xddd9cb,Math.cos(a)*12,Math.sin(a)*12);}},
 onExplosion:burst,
 update(dt,time){let n=0,nr=0;for(const s of slots){if(s.life<=0)continue;s.life-=dt;if(s.life<=0)continue;const f=s.life/s.max,t=1-f;s.x+=s.vx*dt;s.z+=s.vz*dt;s.angle+=s.spin*dt;dummy.position.set(s.x,1.5,s.z);dummy.rotation.set(s.kind===1?s.angle*.3:0,s.angle,s.kind===1?s.angle:0);let size=s.size*(s.kind===2?.3+t:s.kind===0?.6+t:1);dummy.scale.set(size,s.kind===2?1:size*.25,size);dummy.updateMatrix();const mesh=s.kind===2?ringFX:effects,idx=s.kind===2?nr++:n++;mesh.setMatrixAt(idx,dummy.matrix);color.set(s.color).multiplyScalar(f*f);mesh.setColorAt(idx,color);}effects.count=n;ringFX.count=nr;for(const m of [effects,ringFX]){m.instanceMatrix.needsUpdate=true;if(m.instanceColor)m.instanceColor.needsUpdate=true;}
  let ne=0;for(const s of edgeShips){if(!s.alive||Math.hypot(s.x,s.z)<470||ne>=32)continue;dummy.position.set(0,-1.8,0);dummy.rotation.set(-Math.PI/2,0,Math.atan2(s.z,s.x)-.05);dummy.scale.set(1,1,1);dummy.updateMatrix();edge.setMatrixAt(ne++,dummy.matrix);}edge.count=ne;edge.instanceMatrix.needsUpdate=true;
 },
 render(renderer,s,c){renderer.render(s,c);}
};
