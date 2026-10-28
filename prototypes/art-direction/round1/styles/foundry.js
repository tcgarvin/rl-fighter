import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mountToLocal } from '../hulls.js';

// Signal Foundry: shared, merged industrial part kit; all coordinates are Y-up.
const COLORS = [0xd1ea49, 0xef77b7];
const box = new THREE.BoxGeometry(1, 1, 1);
const disc = new THREE.CylinderGeometry(1, 1, 1, 12);
const dummy = new THREE.Object3D();
const tint = new THREE.Color();
const materials = {
  steel: new THREE.MeshStandardMaterial({ color: 0x657078, roughness: .78, metalness: .35 }),
  dark: new THREE.MeshStandardMaterial({ color: 0x22282c, roughness: .86, metalness: .25 }),
  black: new THREE.MeshBasicMaterial({ color: 0x101416 }),
  white: new THREE.MeshBasicMaterial({ color: 0xf7faef }),
  amber: new THREE.MeshBasicMaterial({ color: 0xffb454 }),
  core: new THREE.MeshBasicMaterial({ color: 0xffe5a3 }),
  paint0: new THREE.MeshStandardMaterial({ color: COLORS[0], emissive: COLORS[0], emissiveIntensity: .22, roughness: .72 }),
  paint1: new THREE.MeshStandardMaterial({ color: COLORS[1], emissive: COLORS[1], emissiveIntensity: .22, roughness: .72 }),
};
let scene, camera, heightPixels = 720;
const hullCache = new Map();
const FX_COUNT = 1400, RING_COUNT = 96;
let shards, rings, cursor = 0, ringCursor = 0;
const effects = Array.from({ length: FX_COUNT }, () => ({ life: 0 }));
const waves = Array.from({ length: RING_COUNT }, () => ({ life: 0 }));

function instance(geometry, material, count) {
  const m = new THREE.InstancedMesh(geometry, material, count);
  m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); m.frustumCulled = false; m.count = 0;
  scene.add(m); return m;
}
function place(mesh, index, x, y, z, sx, sy, sz, angle = 0) {
  dummy.position.set(x, y, z); dummy.rotation.set(0, angle, 0); dummy.scale.set(sx, sy, sz);
  dummy.updateMatrix(); mesh.setMatrixAt(index, dummy.matrix);
}
function plate(points, depth) {
  const shape = new THREE.Shape(); points.forEach(([x,y], i) => i ? shape.lineTo(x,y) : shape.moveTo(x,y)); shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false });
  g.rotateX(-Math.PI / 2); g.translate(0, -depth / 2, 0); return g;
}
function buildStatic(ship) {
  const key = ship.hullName + ship.team;
  if (hullCache.has(key)) return hullCache.get(key);
  const bins = {};
  function part(mat, x,y,z, sx,sy,sz, geometry = box, angle = 0) {
    const g = geometry.index ? geometry.toNonIndexed() : geometry.clone(); const m = new THREE.Matrix4();
    dummy.position.set(x,y,z); dummy.rotation.set(0,angle,0); dummy.scale.set(sx,sy,sz); dummy.updateMatrix(); m.copy(dummy.matrix); g.applyMatrix4(m);
    (bins[mat] ||= []).push(g);
  }
  const paint = 'paint' + ship.team;
  const L = ship.hull.length, B = ship.hull.beam;
  if (ship.hullName === 'fighter') {
    const g = plate([[5,0],[2.5,1.25],[-2.7,2.3],[-4.2,1.3],[-4.2,-1.3],[-2.7,-2.3],[2.5,-1.25]], .9);
    part('dark',0,0,0,1,1,1,g); g.dispose();
    part('steel',-.1,.65,0,5.8,.55,1.2);
    for (const z of [-1.35,1.35]) part(paint,-.65,.49,z,4.9,.16,1.1,box, z < 0 ? -.17 : .17);
    part('dark',-3.15,.1,0,2.7,1.3,1.6);
    part('steel',-2.5,.8,0,.3,.15,1.5);
  } else if (ship.hullName === 'strafer') {
    const g = plate([[4.5,0],[3.5,1.25],[-3.8,1.25],[-3.8,-1.25],[3.5,-1.25]], .8);
    part('dark',0,0,0,1,1,1,g); g.dispose();
    part('steel',-.3,.52,0,6.8,.35,1.25);
    for (const x of [-2.4,2.4]) {
      part('steel',x,0,0,1.1,.85,B-1);
      for (const z of [-3,3]) part(paint,x,.52,z,1.15,.2,2.5);
    }
    for (const z of [-4.25,4.25]) part('dark',0,-.1,z,6.2,.6,.65);
  } else {
    const g = plate([[7.5,0],[5,4],[-4.5,5],[-7.5,3],[-7.5,-3],[-4.5,-5],[5,-4]], 1.4);
    part('dark',0,0,0,1,1,1,g); g.dispose();
    for (const z of [-3.6,3.6]) part(paint,-.9,.76,z,9.2,.18,1.15);
    part('steel',-.5,.77,0,10.6,.22,4.9);
    part('dark',.1,.92,0,2.4,.15,4.8);
    for (const z of [-2,2]) part('steel',-5.8,.1,z,2.5,1.65,2.1);
    for (const x of [-5,0,5]) part('black',x,.9,0,.24,.08,5.4);
  }
  // Painted identification: A one broad band; B two separated narrow bands.
  const markerX = ship.hullName === 'gunship' ? .3 : -.5;
  const top = ship.hullName === 'gunship' ? 1.03 : .98;
  for (let i=0; i<(ship.team ? 2 : 1); i++) {
    part(paint,markerX + (ship.team ? (i-.5)*.75 : 0),top,0,ship.team ? .4 : 1.05,.1,ship.hullName === 'gunship' ? 5.7 : 2.7);
  }
  // Small standardized nozzle blocks are centered on the authoritative mount.
  for (const t of ship.hull.thrusters) {
    const [x,y,z] = mountToLocal(t.pos,0); const a = Math.atan2(-t.dir[1],t.dir[0]);
    part('steel',x,y,z,.85*t.size,.9*t.size,1.35*t.size,box,a);
    part('black',x-t.dir[0]*.45*t.size,.05,z+t.dir[1]*.45*t.size,.16,.7*t.size,1.05*t.size,box,a);
  }
  const result = Object.entries(bins).map(([name,gs]) => { const g = mergeGeometries(gs); gs.forEach(g=>g.dispose()); return [g,materials[name]]; });
  hullCache.set(key,result); return result;
}
function spark(x,y,angle,speed,life,size,color) {
  const p=effects[cursor]; cursor=(cursor+1)%FX_COUNT;
  Object.assign(p,{x,z:-y,vx:Math.cos(angle)*speed,vz:-Math.sin(angle)*speed,life,max:life,size,angle,color});
}
function wave(e) {
  const p=waves[ringCursor]; ringCursor=(ringCursor+1)%RING_COUNT;
  Object.assign(p,{x:e.x,z:-e.y,life:e.kind==='death'?.65:.23,max:e.kind==='death'?.65:.23,r:e.radius});
}

export default {
  id:'foundry', name:'Signal Foundry',
  blurb:'Heavy machinery. Visible force. A live trial on the graphite test field.',
  hud:{'--bg':'#1d2223','--fg':'#e5e9dd','--muted':'#9ca69d','--team-a':'#d1ea49','--team-b':'#ef77b7','--font':'"Barlow Condensed", "Arial Narrow", sans-serif'},
  fonts:['https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;700&display=swap'],
  init(ctx) {
    scene=ctx.scene; camera=ctx.camera; heightPixels=ctx.renderer.domElement.height / ctx.renderer.getPixelRatio();
    scene.background=new THREE.Color(0x101214);
    scene.add(new THREE.HemisphereLight(0xc8d7df,0x252321,2.2));
    const sun=new THREE.DirectionalLight(0xfff0d2,3.1); sun.position.set(-130,300,100); scene.add(sun);
    // A deliberately sparse range chart: no lines that could be mistaken for gunfire.
    const points=[];
    const line=(x,z,xx,zz)=>points.push(x,-2,z,xx,-2,zz);
    for(let x=-600;x<=600;x+=50) for(let z=-600;z<=600;z+=50) {
      if(Math.hypot(x,z)>510) continue;
      line(x-1.2,z,x+1.2,z); line(x,z-1.2,x,z+1.2);
    }
    for(let i=0;i<360;i++) { const a=i*Math.PI/180, r=i%10===0?511:517; line(Math.cos(a)*r,Math.sin(a)*r,Math.cos(a)*520,Math.sin(a)*520); }
    const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
    scene.add(new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0x303839})));
    const boundary=new THREE.Mesh(new THREE.RingGeometry(519.6,520,180),new THREE.MeshBasicMaterial({color:0x41463b,side:THREE.DoubleSide})); boundary.rotation.x=-Math.PI/2; boundary.position.y=-2; scene.add(boundary);
    // Numeric range labels are static, shared on one atlas, and stay below the action.
    const canvas=document.createElement('canvas'); canvas.width=1024; canvas.height=128;
    const c=canvas.getContext('2d'); c.font='500 44px monospace'; c.fillStyle='#59615b'; c.textAlign='center';
    for(let i=0;i<8;i++) c.fillText(String(i*45).padStart(3,'0'),i*128+64,78);
    const atlas=new THREE.CanvasTexture(canvas); atlas.colorSpace=THREE.SRGBColorSpace;
    for(let i=0;i<8;i++) {
      const geo=new THREE.PlaneGeometry(17,2.2); const uv=geo.attributes.uv;
      for(let j=0;j<uv.count;j++) uv.setX(j,(uv.getX(j)+i)/8);
      const m=new THREE.Mesh(geo,new THREE.MeshBasicMaterial({map:atlas,transparent:true,depthWrite:false,side:THREE.DoubleSide}));
      const a=i*Math.PI/4; m.rotation.x=-Math.PI/2; m.position.set(Math.cos(a)*499,-1.9,Math.sin(a)*499); scene.add(m);
    }
    shards=instance(box,new THREE.MeshBasicMaterial({vertexColors:false}),FX_COUNT);
    const ringGeo=new THREE.RingGeometry(.88,1,8); ringGeo.rotateX(-Math.PI/2);
    rings=instance(ringGeo,new THREE.MeshBasicMaterial({color:0xffb454,transparent:true,opacity:.55,depthWrite:false,side:THREE.DoubleSide}),RING_COUNT);
  },
  onResize(w,h){heightPixels=h;},
  createShip(ship) {
    const root=new THREE.Group(); for(const [g,m] of buildStatic(ship)) root.add(new THREE.Mesh(g,m));
    const turrets=ship.hull.turrets.map(t=>{
      const pivot=new THREE.Group(); pivot.name=t.id; pivot.position.set(...mountToLocal(t.pos,t.height));
      const base=new THREE.Mesh(disc,materials.steel); base.scale.set(t.arc?1.15:.58,.4,t.arc?1.15:.58); pivot.add(base);
      const cap=new THREE.Mesh(box,materials.dark); cap.scale.set(t.arc?1.65:.8,.55,t.arc?1.3:.75); cap.position.y=.35; pivot.add(cap);
      const barrel=new THREE.Mesh(box,materials.white); const length=t.arc?2.8:1.4;
      barrel.scale.set(length,.32,t.weapon==='flak'?.65:.35); barrel.position.set(length/2,.5,0); pivot.add(barrel);
      root.add(pivot); return pivot;
    });
    const flames=ship.hull.thrusters.map(t=>{
      const mount=new THREE.Group(); mount.name=t.id; mount.position.set(...mountToLocal(t.pos,.12));
      // Local -X exhaust; a positive heading maps sim +Y to world -Z.
      mount.rotation.y=Math.atan2(t.dir[1],t.dir[0]);
      const bar=new THREE.Mesh(box,materials.amber); const core=new THREE.Mesh(box,materials.core); const band=new THREE.Mesh(box,materials.white);
      mount.add(bar,core,band); root.add(mount); return {mount,bar,core,band,size:t.size,level:0};
    });
    // Identity marker: solid diamond versus split square, separate from collision hull.
    const marker=new THREE.Group(); marker.position.set(-ship.hull.length*.12,1.65,0);
    if(ship.team===0) {const m=new THREE.Mesh(box,materials.paint0);m.scale.set(1.2,.1,1.2);m.rotation.y=Math.PI/4;marker.add(m);}
    else for(const z of [-.48,.48]) {const m=new THREE.Mesh(box,materials.paint1);m.scale.set(1.6,.1,.55);m.position.z=z;marker.add(m);}
    // Marker is offset aft from the turret stations, scaled gently at long distance.
    marker.position.x=-ship.hull.length*.3; root.add(marker);
    return {object:root,update(v,dt){
      root.visible=v.alive; root.position.set(v.x,0,-v.y);root.rotation.y=v.heading;
      for(let i=0;i<turrets.length;i++) turrets[i].rotation.y=v.turretAngles[i];
      for(let i=0;i<flames.length;i++) {
        const f=flames[i];f.level+=(v.throttles[i]-f.level)*(1-Math.exp(-dt*24));
        if(v.throttles[i]===0 && f.level<.035) f.level=0;
        const l=f.size*(.6+5.6*f.level); f.mount.visible=f.level>.01;
        f.bar.position.x=-.5*f.size-l/2;f.bar.scale.set(l,.28*f.size,.85*f.size);
        f.core.position.set(-.5*f.size-l*.28,.04,0); f.core.scale.set(l*.56,.32*f.size,.38*f.size);
        f.band.visible=f.level>.74;f.band.position.set(-.5*f.size-l*.72,.05,0);f.band.scale.set(.23*f.size,.35*f.size,1.4*f.size);
      }
      const distance=root.position.distanceTo(camera.position);
      const px=ship.hull.length*heightPixels/(2*Math.tan(camera.fov*Math.PI/360)*distance);
      marker.scale.setScalar(Math.min(2.5,Math.max(1,18/Math.max(px,1))));
    },dispose(){ /* Cached hull meshes and shared kit intentionally live for the style lifetime. */ }};
  },
  createProjectiles(capacity) {
    const shots=instance(box,materials.white,capacity), flak=instance(box,materials.amber,capacity);
    const beams=instance(box,materials.white,128), halos=instance(box,new THREE.MeshBasicMaterial({color:0xffb454,transparent:true,opacity:.2,depthWrite:false}),128);
    return {update(ps,bs,alpha){
      let n=0,f=0;
      for(let i=0;i<Math.min(ps.length,capacity);i++) {const p=ps[i],a=Math.atan2(p.vy,p.vx),x=p.x+p.vx*alpha/30,z=-(p.y+p.vy*alpha/30);
        if(p.kind==='flak') place(flak,f++,x,1,z,2.5,.65,.85,a);
        else place(shots,n++,x,1,z,4.4,.35,.45,a);
      }
      shots.count=n;flak.count=f;shots.instanceMatrix.needsUpdate=true;flak.instanceMatrix.needsUpdate=true;
      const nb=Math.min(bs.length,128);
      for(let i=0;i<nb;i++){const b=bs[i],dx=b.x2-b.x1,dy=b.y2-b.y1,l=Math.hypot(dx,dy),a=Math.atan2(dy,dx);
        place(beams,i,(b.x1+b.x2)/2,1.1,-(b.y1+b.y2)/2,l,.2,.34,a);
        place(halos,i,(b.x1+b.x2)/2,1,-(b.y1+b.y2)/2,l,.12,1.7,a);
      }
      beams.count=halos.count=nb;beams.instanceMatrix.needsUpdate=true;halos.instanceMatrix.needsUpdate=true;
    }};
  },
  onMuzzle(e){
    spark(e.x,e.y,e.angle,0,.065,2.6,0xf7faef);
    for(let i=0;i<3;i++) spark(e.x,e.y,e.angle+(Math.random()-.5)*.6,25+Math.random()*25,.10+Math.random()*.06,.45,0xffb454);
  },
  onHit(e){for(let i=0;i<9;i++) spark(e.x,e.y,Math.random()*Math.PI*2,15+Math.random()*35,.12+Math.random()*.23,.55, i%3?0xffb454:0xf7faef);},
  onExplosion(e){
    wave(e);const death=e.kind==='death';
    for(let i=0;i<(death?32:12);i++) spark(e.x,e.y,Math.random()*Math.PI*2,(death?12:25)+Math.random()*35,(death?.5:.15)+Math.random()*(death?.65:.2),death?1.2+Math.random()*2:.6,i%4===0?COLORS[e.team]:i%3===0?0x657078:0xffb454);
    spark(e.x,e.y,0,0,death?.16:.08,death?e.radius*.7:3,0xffedbc);
  },
  update(dt){
    let n=0;
    for(const p of effects){if(p.life<=0)continue;p.life-=dt;if(p.life<=0)continue;
      p.x+=p.vx*dt;p.z+=p.vz*dt; const fade=p.life/p.max;
      place(shards,n,p.x,1.3,p.z,p.size*(p.vx===0?p.life/p.max:2.3)*fade,.3*fade,p.size*fade,p.angle);
      shards.setColorAt(n++,tint.setHex(p.color).multiplyScalar(.35+.65*fade));
    }
    shards.count=n;shards.instanceMatrix.needsUpdate=true;if(shards.instanceColor)shards.instanceColor.needsUpdate=true;
    n=0;for(const p of waves){if(p.life<=0)continue;p.life-=dt;if(p.life<=0)continue;const t=1-p.life/p.max,r=p.r*(.2+t);place(rings,n,p.x,.8,p.z,r,1,r,t*.3);rings.setColorAt(n++,tint.setRGB(1-t,1-t,1-t));}
    rings.count=n;rings.instanceMatrix.needsUpdate=true;if(rings.instanceColor)rings.instanceColor.needsUpdate=true;
  },
  render(renderer,s,c){renderer.render(s,c);},
};
