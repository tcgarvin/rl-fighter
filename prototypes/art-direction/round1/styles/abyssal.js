import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mountToLocal } from '../hulls.js';

// All geometry uses +Y dorsal, +X nose. No post processing is required.
const COLORS = [0xff806b, 0x69dceb];
const pearl = 0xfff5df, acid = 0xe5ff87;
let scene, cursor = 0, dust;
const effects = [];
const sphere = new THREE.IcosahedronGeometry(1, 1);
const seedGeo = new THREE.SphereGeometry(1, 7, 5);
const jetGeo = new THREE.ConeGeometry(1, 1, 7);
jetGeo.rotateZ(Math.PI);
jetGeo.translate(0, -0.5, 0);
const ringGeo = new THREE.RingGeometry(0.93, 1, 36, 1, 0, Math.PI * 1.86);
ringGeo.rotateX(-Math.PI / 2);
const transform = new THREE.Object3D();
let glow;
const shell = new THREE.MeshStandardMaterial({ color: 0x304450, roughness: 0.72, metalness: 0.28, flatShading: true });
const underside = new THREE.MeshStandardMaterial({ color: 0x101f2a, roughness: 0.9, flatShading: true });
const ivory = new THREE.MeshStandardMaterial({ color: 0x92b7bd, roughness: 0.5, metalness: 0.25, flatShading: true });
const seams = COLORS.map(c => new THREE.MeshBasicMaterial({ color: c }));
const skins = COLORS.map(c => new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: 0.16, roughness: 0.6, metalness: 0.25, flatShading: true }));
const jetMat = new THREE.MeshBasicMaterial({ color: acid, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending });
const coreMat = new THREE.MeshBasicMaterial({ color: 0xf4ffd1 });

function makeGlow() {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 64;
  const ctx = canvas.getContext('2d');
  const g = ctx.createRadialGradient(32,32,0,32,32,32);
  g.addColorStop(0,'rgba(255,255,255,1)'); g.addColorStop(0.16,'rgba(255,255,255,.65)');
  g.addColorStop(0.46,'rgba(255,255,255,.12)'); g.addColorStop(1,'rgba(255,255,255,0)');
  ctx.fillStyle=g; ctx.fillRect(0,0,64,64);
  return new THREE.CanvasTexture(canvas);
}
function ellipsoid(x,y,z,sx,sy,sz) {
  const g = sphere.clone(); g.scale(sx,sy,sz); g.translate(x,y,z); return g;
}
function plate(points, thickness) {
  const shape = new THREE.Shape();
  points.forEach(([x,z],i) => i ? shape.lineTo(x,-z) : shape.moveTo(x,-z)); shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape,{depth:thickness,bevelEnabled:true,bevelSize:0.22,bevelThickness:0.18,bevelSegments:1,steps:1,curveSegments:1});
  g.rotateX(-Math.PI/2); g.translate(0,-thickness/2,0); return g;
}
function merged(root, geometries, material) {
  const g=mergeGeometries(geometries,false); geometries.forEach(g=>g.dispose());
  const m=new THREE.Mesh(g,material); root.add(m); return m;
}
function lineTube(points, radius=0.14) {
  return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p))),12,radius,4,false);
}
function spawn(x,y,r,life,c,kind=0,angle=0) {
  const f=effects[cursor++ % effects.length];
  f.life=f.max=life; f.radius=r; f.kind=kind; f.angle=angle;
  f.root.position.set(x,1.3,-y); f.root.visible=true;
  f.halo.material.color.set(c); f.ring.material.color.set(c);
}

export default {
  id:'abyssal', name:'Abyssal Organisms',
  blurb:'Armored life in black water. Coral and ice hunt by luminous seams and sharp siphon jets.',
  hud:{'--bg':'#10232ce8','--fg':'#dfecec','--muted':'#88a8af','--team-a':'#ff806b','--team-b':'#69dceb','--font':'"Trebuchet MS", sans-serif'},
  fonts:[],
  init(ctx) {
    scene=ctx.scene; effects.length=0; cursor=0; glow=makeGlow();
    scene.background=new THREE.Color(0x060f18);
    scene.add(new THREE.HemisphereLight(0xa3d9e5,0x08111a,2.1));
    const light=new THREE.DirectionalLight(0xd8f7ff,3.2); light.position.set(-200,500,180); scene.add(light);
    // Broad, quiet underwater fields: a single opaque plane, no alpha overdraw.
    const field=new THREE.Mesh(new THREE.PlaneGeometry(2200,2200),new THREE.ShaderMaterial({
      vertexShader:'varying vec2 v; void main(){v=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
      fragmentShader:'varying vec2 v; void main(){vec2 p=(v-.5)*7.;float a=exp(-dot(p-vec2(-.7,.5),p-vec2(-.7,.5))*.8);float b=exp(-dot(p-vec2(1.,-1.),p-vec2(1.,-1.))*.7);gl_FragColor=vec4(vec3(.017,.037,.059)+a*vec3(.005,.025,.029)+b*vec3(.02,.005,.017),1.);}'
    })); field.rotation.x=-Math.PI/2; field.position.y=-65; scene.add(field);
    let rand=17; const random=()=>{rand=(Math.imul(rand,1664525)+1013904223)>>>0;return rand/4294967296;};
    const positions=new Float32Array(550*3);
    for(let i=0;i<550;i++){positions[i*3]=(random()-.5)*2600;positions[i*3+1]=-15-random()*40;positions[i*3+2]=(random()-.5)*2600;}
    const dg=new THREE.BufferGeometry();dg.setAttribute('position',new THREE.BufferAttribute(positions,3));
    dust=new THREE.Points(dg,new THREE.PointsMaterial({color:0x587b85,size:0.8,transparent:true,opacity:.35,depthWrite:false}));scene.add(dust);
    // The habitat limit is only a dim, broken contour at the true arena radius.
    const boundary=new THREE.Mesh(new THREE.RingGeometry(519.8,520.2,180),new THREE.MeshBasicMaterial({color:0x17313b,side:THREE.DoubleSide}));boundary.rotation.x=-Math.PI/2;boundary.position.y=-1;scene.add(boundary);
    for(let i=0;i<160;i++) {
      const root=new THREE.Group();root.visible=false;
      const halo=new THREE.Sprite(new THREE.SpriteMaterial({map:glow,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending}));root.add(halo);
      const ring=new THREE.Mesh(ringGeo,new THREE.MeshBasicMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide}));root.add(ring);
      const shards=new THREE.Group(); root.add(shards);
      for(let j=0;j<5;j++){const m=new THREE.Mesh(sphere,j%2?ivory:underside);shards.add(m);}
      scene.add(root); effects.push({root,halo,ring,shards,life:0,max:1,radius:1,kind:0,angle:0});
    }
  },
  createShip(ship) {
    const root=new THREE.Group(), h=ship.hull, team=ship.team;
    const L=h.length, B=h.beam, gun=ship.hullName==='gunship', ray=ship.hullName==='strafer';
    const parts=[], panels=[], bands=[];
    if(gun) {
      parts.push(plate([[7.5,0],[5,4],[-4.5,5],[-7.5,3],[-7.5,-3],[-4.5,-5],[5,-4]],1.35));
      parts.push(ellipsoid(-.8,.5,0,L*.43,1.15,B*.43));
      for(const t of h.turrets) parts.push(ellipsoid(t.pos[0],.7,-t.pos[1],1.65,.5,1.65));
    } else if(ray) {
      parts.push(plate([[4.5,0],[2.5,1.3],[3,4.25],[2.4,4.8],[.6,3],[-1.4,2.1],[-2.4,4.7],[-3.3,4.1],[-2.7,1],[-4.1,0],[-2.7,-1],[-3.3,-4.1],[-2.4,-4.7],[-1.4,-2.1],[.6,-3],[2.4,-4.8],[3,-4.25],[2.5,-1.3]],.65));
      parts.push(ellipsoid(0,.45,0,3.6,.9,1.35));
      for(const z of [-1,1]) panels.push(ellipsoid(-.1,.45,z*2.6,2.3,.22,1.3));
    } else {
      // Rear fork leaves the main siphon open between the two shell lobes.
      parts.push(plate([[5,0],[2.5,1.25],[-2.7,2.3],[-4.2,1.3],[-3.1,.6],[-2.7,0],[-3.1,-.6],[-4.2,-1.3],[-2.7,-2.3],[2.5,-1.25]],.8));
      parts.push(ellipsoid(-.1,.35,0,3.4,.85,1.35));
      for(const z of [-1,1]) panels.push(ellipsoid(-2.3,.22,z*1.48,1.35,.25,.55));
    }
    merged(root,parts,shell);
    // A broad tinted lip keeps the shells identifiable at the widest framing.
    if(gun) for(const z of [-1,1]) panels.push(ellipsoid(-.5,.65,z*3.8,4.4,.2,.52));
    merged(root,panels,skins[team]);
    const offsets=team===0?[0]:[-.52,.52];
    for(const z of offsets) bands.push(lineTube([[-L*.32,1,z],[-L*.12,gun?1.72:1.35,z],[L*.16,gun?1.65:1.25,z],[L*.34,.85,z]],gun?.23:.19));
    merged(root,bands,seams[team]);
    // Visible siphon mouths sit exactly on the specified mount positions.
    const flames=h.thrusters.map(t=>{
      const mount=new THREE.Group(); mount.name=t.id; mount.position.fromArray(mountToLocal(t.pos));
      const ex=new THREE.Vector3(-t.dir[0],0,t.dir[1]);
      mount.quaternion.setFromUnitVectors(new THREE.Vector3(0,-1,0),ex);root.add(mount);
      const bell=new THREE.Mesh(new THREE.CylinderGeometry(t.size*.52,t.size*.8,.65,8,1,true),ivory);bell.position.y=.25;mount.add(bell);
      const mouth=new THREE.Mesh(new THREE.CircleGeometry(t.size*.72,8),underside);mouth.rotation.x=Math.PI/2;mouth.position.y=-.09;mount.add(mouth);
      const jet=new THREE.Mesh(jetGeo,jetMat);mount.add(jet);
      const core=new THREE.Mesh(jetGeo,coreMat);mount.add(core);
      return {jet,core,size:t.size,level:0};
    });
    const turrets=h.turrets.map(t=>{
      const pivot=new THREE.Group();pivot.name=t.id;pivot.position.fromArray(mountToLocal(t.pos,t.height));root.add(pivot);
      const stalk=new THREE.Mesh(sphere,underside);stalk.scale.set(.65,.5,.65);pivot.add(stalk);
      const head=new THREE.Mesh(sphere,ivory);head.position.y=.45;head.scale.set(gun?1:.65,.45,.55);pivot.add(head);
      const spine=new THREE.Mesh(new THREE.ConeGeometry(gun?.28:.19,gun?2.6:1.3,5),seams[team]);spine.rotation.z=-Math.PI/2;spine.position.set(gun?1.3:.65,.45,0);pivot.add(spine);
      return pivot;
    });
    return {object:root,update(view,dt){
      root.visible=view.alive;root.position.set(view.x,0,-view.y);root.rotation.y=view.heading;
      for(let i=0;i<flames.length;i++) {const f=flames[i];f.level+=(view.throttles[i]-f.level)*(1-Math.exp(-dt*22));const v=f.level>.015;f.jet.visible=f.core.visible=v;
        f.jet.scale.set(f.size*.7,7*f.size*f.level,f.size*.7);f.core.scale.set(f.size*.32,3*f.size*f.level,f.size*.32);}
      for(let i=0;i<turrets.length;i++)turrets[i].rotation.y=view.turretAngles[i];
    },dispose(){root.traverse(o=>{if(o.isMesh && o.geometry!==sphere && o.geometry!==jetGeo)o.geometry.dispose();});}};
  },
  createProjectiles(capacity) {
    const seeds=new THREE.InstancedMesh(seedGeo,new THREE.MeshBasicMaterial({color:pearl}),capacity);seeds.instanceMatrix.setUsage(THREE.DynamicDrawUsage);seeds.frustumCulled=false;scene.add(seeds);
    const tails=new THREE.InstancedMesh(seedGeo,new THREE.MeshBasicMaterial({color:0xcb9bff}),capacity);tails.instanceMatrix.setUsage(THREE.DynamicDrawUsage);tails.frustumCulled=false;scene.add(tails);
    const bg=new THREE.BufferGeometry(),bp=new Float32Array(128*6);bg.setAttribute('position',new THREE.BufferAttribute(bp,3));
    const beams=new THREE.LineSegments(bg,new THREE.LineBasicMaterial({color:pearl,transparent:true,opacity:.9}));beams.frustumCulled=false;scene.add(beams);
    return {update(projectiles,beamList,alpha){
      const n=Math.min(projectiles.length,capacity);let nt=0;
      for(let i=0;i<n;i++){const p=projectiles[i],flak=p.kind==='flak';const a=Math.atan2(p.vy,p.vx);
        transform.position.set(p.x+p.vx*alpha/30,1.2,-p.y-p.vy*alpha/30);transform.rotation.set(0,a,0);transform.scale.set(flak?1.25:2.1,flak?.65:.32,flak?.65:.32);transform.updateMatrix();seeds.setMatrixAt(i,transform.matrix);
        if(flak){transform.position.x-=Math.cos(a)*1.9;transform.position.z+=Math.sin(a)*1.9;transform.scale.set(1.5,.3,.3);transform.updateMatrix();tails.setMatrixAt(nt++,transform.matrix);}}
      seeds.count=n;tails.count=nt;seeds.instanceMatrix.needsUpdate=tails.instanceMatrix.needsUpdate=true;
      const nb=Math.min(128,beamList.length);for(let i=0;i<nb;i++){const b=beamList[i],j=i*6;bp[j]=b.x1;bp[j+1]=1.3;bp[j+2]=-b.y1;bp[j+3]=b.x2;bp[j+4]=1.3;bp[j+5]=-b.y2;}
      bg.setDrawRange(0,nb*2);bg.attributes.position.needsUpdate=true;
    }};
  },
  onMuzzle(e){spawn(e.x,e.y,3,.09,pearl,0,e.angle);},
  onHit(e){spawn(e.x,e.y,3.5,.24,COLORS[e.team],1);},
  onExplosion(e){spawn(e.x,e.y,e.radius,e.kind==='death'?.95:.32,e.kind==='death'?COLORS[e.team]:pearl,e.kind==='death'?2:1);},
  update(dt,time){
    for(const f of effects){if(f.life<=0)continue;f.life-=dt;if(f.life<=0){f.root.visible=false;continue;}const t=1-f.life/f.max,r=f.radius;
      f.halo.scale.setScalar(r*(f.kind===0?2.1:3)*(1+t*.7));f.halo.material.opacity=(1-t)*(1-t)*(f.kind===2?.9:.7);
      f.ring.visible=f.kind>0;f.ring.scale.setScalar(r*(.15+t));f.ring.rotation.y=t*.7;f.ring.material.opacity=(1-t)*.65;
      f.shards.visible=f.kind>0;
      if(f.kind>0)for(let j=0;j<5;j++){const m=f.shards.children[j],a=j*2.399+f.angle,d=r*t*(.4+j*.14);m.position.set(Math.cos(a)*d,Math.sin(t*Math.PI)*r*.12,Math.sin(a)*d);m.rotation.set(t*4+j,t*3,j);m.scale.setScalar((f.kind===2?1.6:.5)*(1-t));}
    }
  },
  render(renderer,s,camera){renderer.render(s,camera);}
};
