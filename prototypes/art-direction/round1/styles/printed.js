import * as THREE from 'three';
import { mountToLocal } from '../hulls.js';

const PAPER = 0xe8e1cf, INK = 0x252b2d, TEAMS = [0xb83c2e, 0x17666b];
const mat = color => new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide });
const ink = mat(INK), paper = mat(PAPER), violet = mat(0x67418b), paints = TEAMS.map(mat);
const box = new THREE.BoxGeometry(1, 1, 1);
const disc = new THREE.CylinderGeometry(1, 1, 1, 24);
const dummy = new THREE.Object3D(), color = new THREE.Color();
let scene, fxMesh, cursor = 0;
const FX_COUNT = 1800;
const effects = Array.from({ length: FX_COUNT }, () => ({ life: 0, max: 1, x: 0, z: 0, vx: 0, vz: 0, angle: 0, spin: 0, length: 1, width: 1, color: INK }));
function mesh(parent, geo, material, x, y, z, sx=1, sy=1, sz=1) {
  const m = new THREE.Mesh(geo, material); m.position.set(x,y,z); m.scale.set(sx,sy,sz); parent.add(m); return m;
}
function polygon(points, depth) {
  const s = new THREE.Shape(); points.forEach(([x,y],i) => i ? s.lineTo(x,y) : s.moveTo(x,y)); s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled:false, steps:1 });
  g.rotateX(-Math.PI/2); return g;
}
function stroke(x,z,angle,length,width,life,c=INK,vx=0,vz=0,spin=0) {
  const f=effects[cursor]; cursor=(cursor+1)%FX_COUNT;
  Object.assign(f,{x,z,angle,length,width,life,max:life,color:c,vx,vz,spin});
}
function lines(points, c, opacity=1) {
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
  const o=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:c,transparent:opacity<1,opacity,depthWrite:false}));scene.add(o);return o;
}
function label(text,x,z,size=6) {
  const canvas=document.createElement('canvas');canvas.width=512;canvas.height=64;
  const c=canvas.getContext('2d');c.fillStyle='#929181';c.font='24px Georgia';c.textAlign='center';c.fillText(text,256,40);
  const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;
  const m=new THREE.Mesh(new THREE.PlaneGeometry(size*8,size),new THREE.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false}));
  m.rotation.x=-Math.PI/2;m.position.set(x,-1.8,z);scene.add(m);
}
function environment() {
  const pts=[], major=[], ticks=[];
  for(let n=-1000;n<=1000;n+=25) {
    const p=n%100===0?major:pts;p.push(n,-2,-1000,n,-2,1000,-1000,-2,n,1000,-2,n);
  }
  lines(pts,0xcac5b4,.20);lines(major,0xb8b5a5,.28);
  for(let i=0;i<240;i++) {
    const a=i*Math.PI*2/240,b=(i+.64)*Math.PI*2/240;
    ticks.push(520*Math.cos(a),-1.7,520*Math.sin(a),520*Math.cos(b),-1.7,520*Math.sin(b));
    const r=i%10===0?530:524;
    ticks.push(520*Math.cos(a),-1.7,520*Math.sin(a),r*Math.cos(a),-1.7,r*Math.sin(a));
  }
  lines(ticks,0x929586,.7);
  let seed=87;const rand=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  const stars=[];
  for(let i=0;i<170;i++){const x=(rand()-.5)*1700,z=(rand()-.5)*1700,s=.5+rand()*.8;stars.push(x-s,-1.6,z,x+s,-1.6,z,x,-1.6,z-s,x,-1.6,z+s);}
  lines(stars,0x9e9f91,.55);
  for(let n=-400;n<=400;n+=100){label(`${n<0?'−':'+'}${Math.abs(n).toString().padStart(3,'0')}`,n,12,3.5);}
  label('O R B I T A L   T E S T   F I E L D',0,-480,8);
  label('R = 520 m   /   LIMIT OF OBSERVATION',0,480,5);
  // Static, sparse paper fibres: deterministic and deliberately below grid contrast.
  const fibres=[];for(let i=0;i<2400;i++){const x=(rand()-.5)*2200,z=(rand()-.5)*2200;fibres.push(x,-2.5,z,x+rand()*1.5+.2,-2.5,z+.15);}
  lines(fibres,0xbdb39c,.13);
}

export default {
  id:'printed', name:'Printed Orbits',
  blurb:'An observatory chart in motion — cut-paper fleets, violet thrust and crisp ink trajectories.',
  hud:{'--bg':'#f5efdf','--fg':'#252b2d','--muted':'#696b61','--team-a':'#b83c2e','--team-b':'#17666b','--font':'Georgia, "Times New Roman", serif'},
  init(ctx) {
    scene=ctx.scene;scene.background=new THREE.Color(PAPER);environment();
    fxMesh=new THREE.InstancedMesh(box,ink,FX_COUNT);fxMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);fxMesh.frustumCulled=false;fxMesh.count=0;scene.add(fxMesh);
  },
  createShip(ship) {
    const root=new THREE.Group(), owned=[], paint=paints[ship.team], h=ship.hull;
    function plate(points,depth=.75,y=0,material=paint,scale=1) {
      const geo=polygon(points,depth);owned.push(geo);
      return mesh(root,geo,material,0,y,0,scale,1,scale);
    }
    const fighter=[[5,0],[2.5,1.25],[-2.7,2.3],[-4.2,1.3],[-4.2,-1.3],[-2.7,-2.3],[2.5,-1.25]];
    const gun=[[7.5,0],[5,4],[-4.5,5],[-7.5,3],[-7.5,-3],[-4.5,-5],[5,-4]];
    if(ship.hullName==='fighter') {
      plate(fighter,.8,-.35,ink,1.045);plate(fighter,.12,.46);
      mesh(root,box,paper,-.4,.68,0,4.6,.16,.7);
    } else if(ship.hullName==='strafer') {
      plate([[4.5,0],[2.8,1.25],[-3.8,1.25],[-3.8,-1.25],[2.8,-1.25]],.8,-.35,ink);
      for(const x of [-2.4,2.4]) {
        mesh(root,box,ink,x,.12,0,1.4,.8,9.4);
        mesh(root,box,paint,x,.55,0,.95,.12,9.4);
      }
      mesh(root,box,paint,-.5,.5,0,5.8,.12,2);
      mesh(root,box,paper,-.5,.64,0,5.3,.1,.65);
    } else {
      plate(gun,1.1,-.5,ink,1.025);plate(gun,.12,.62);
      plate(gun,.06,.76,paper,.61);
      mesh(root,box,paint,-.8,.85,0,8,.1,1.2);
    }
    // Fleet identity is redundant: stripe count and a distinct raised emblem.
    const mx=ship.hullName==='gunship'?-5: -2;
    if(ship.team===0) {
      mesh(root,box,paper,mx,.95,0,.85,.08,ship.hullName==='gunship'?6:3.1);
      const d=mesh(root,box,ink,mx,1.05,0,1.05,.08,1.05);d.rotation.y=Math.PI/4;
    } else {
      for(const x of [mx-.45,mx+.45])mesh(root,box,paper,x,.95,0,.38,.08,ship.hullName==='gunship'?6:3.1);
      for(const z of [-.45,.45])mesh(root,box,ink,mx,1.06,z,1.1,.08,.48);
    }
    const wedgeGeo=polygon([[0,-.65],[0,.65],[1,0]],.02);owned.push(wedgeGeo);
    const flames=h.thrusters.map(t=>{
      const g=new THREE.Group();g.name=t.id;g.position.set(...mountToLocal(t.pos,.4));g.rotation.y=Math.atan2(-t.dir[1],-t.dir[0]);root.add(g);
      mesh(g,box,ink,0,0,0,.65*t.size+.3,.5,1.5*t.size+.25);
      mesh(g,box,paper,.14,.28,0,.2,.04,1.15*t.size);
      const w=mesh(g,wedgeGeo,violet,.25,.12,0,1,1,t.size);
      const bars=[.38,.68].map(x=>mesh(g,box,paper,x,.18,0,.045,.04,.6*t.size));
      return {w,bars,size:t.size,level:0};
    });
    const turrets=h.turrets.map(t=>{
      const g=new THREE.Group();g.name=t.id;g.position.set(...mountToLocal(t.pos,t.height));root.add(g);
      const r=t.arc?1.05:.55;
      mesh(g,disc,paper,0,.1,0,r+.22,.12,r+.22);
      mesh(g,disc,ink,0,.25,0,r,.25,r);
      const len=t.arc?3.2:1.8;
      mesh(g,box,paper,len*.48,.35,0,len+.25,.18,.64);
      mesh(g,box,paint,len*.5,.46,0,len,.12,.32);
      mesh(g,box,ink,len,.45,0,.3,.18,.54);
      return g;
    });
    return {object:root,update(v,dt){
      root.visible=v.alive;root.position.set(v.x,0,-v.y);root.rotation.y=v.heading;
      flames.forEach((f,i)=>{const target=v.throttles[i]||0;f.level+=(target-f.level)*(1-Math.exp(-dt*24));
        f.w.visible=f.level>.025;const length=(3+5*f.size)*f.level;
        f.w.scale.x=length;f.w.scale.z=f.size*(.65+.35*f.level);
        f.bars.forEach((b,j)=>{b.visible=f.w.visible&&target>=(j===0?.5:1);b.position.x=.25+length*(j===0?.3:.58);});
      });turrets.forEach((g,i)=>g.rotation.y=v.turretAngles[i]);
    },dispose(){owned.forEach(g=>g.dispose());}};
  },
  createProjectiles(capacity) {
    const outer=new THREE.InstancedMesh(box,paper,capacity+128),inner=new THREE.InstancedMesh(box,ink,capacity+128);
    for(const m of [outer,inner]){m.frustumCulled=false;m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);scene.add(m);}
    function dash(i,x,z,a,len,w,c) {
      dummy.position.set(x,1.9,z);dummy.rotation.set(0,a,0);dummy.scale.set(len+.55,.1,w+.55);dummy.updateMatrix();outer.setMatrixAt(i,dummy.matrix);
      dummy.position.y=2.02;dummy.scale.set(len,.1,w);dummy.updateMatrix();inner.setMatrixAt(i,dummy.matrix);inner.setColorAt(i,color.set(c));
    }
    return {update(ps,bs,alpha){let n=0;
      for(let i=0;i<Math.min(ps.length,capacity);i++){const p=ps[i],flak=p.kind==='flak';dash(n++,p.x+p.vx*alpha/30,-p.y-p.vy*alpha/30,Math.atan2(p.vy,p.vx),flak?3.2:4.2,flak?1.25:.65,INK);}
      for(let i=0;i<Math.min(bs.length,128);i++){const b=bs[i],dx=b.x2-b.x1,dy=b.y2-b.y1;dash(n++,(b.x1+b.x2)/2,-(b.y1+b.y2)/2,Math.atan2(dy,dx),Math.hypot(dx,dy),.65,0xa65b12);}
      outer.count=inner.count=n;outer.instanceMatrix.needsUpdate=inner.instanceMatrix.needsUpdate=true;if(inner.instanceColor)inner.instanceColor.needsUpdate=true;
    }};
  },
  onMuzzle(e) {
    for(let i=-1;i<=1;i++) {const a=e.angle+i*.65;stroke(e.x+Math.cos(a)*2,-e.y-Math.sin(a)*2,a,2,.4,.085,0xa65b12);}
  },
  onHit(e) {
    for(let i=0;i<7;i++){const a=i*Math.PI*2/7;stroke(e.x+Math.cos(a)*1.6,-e.y-Math.sin(a)*1.6,a,2.4,.4,.19,INK,Math.cos(a)*6,-Math.sin(a)*6);}
  },
  onExplosion(e) {
    const death=e.kind==='death',r=e.radius,life=death?.85:.35;
    for(let i=0;i<22;i++) {if(i%4===0)continue;const a=i*Math.PI*2/22;stroke(e.x+Math.cos(a)*r*.25,-e.y-Math.sin(a)*r*.25,a+Math.PI/2,r*.14,.45,life,INK,Math.cos(a)*r*.95,-Math.sin(a)*r*.95);}
    for(let i=0;i<(death?13:5);i++){const a=i*2.39996;stroke(e.x,-e.y,a,death?2.5:1.3,death?1:.5,life*(.65+(i%3)*.1),TEAMS[e.team],Math.cos(a)*r*1.5,-Math.sin(a)*r*1.5,(i%2?1:-1)*2);}
  },
  update(dt) {
    let n=0;for(const f of effects){if(f.life<=0)continue;f.life-=dt;if(f.life<=0)continue;
      f.x+=f.vx*dt;f.z+=f.vz*dt;f.angle+=f.spin*dt;
      dummy.position.set(f.x,2.3,f.z);dummy.rotation.set(0,f.angle,0);dummy.scale.set(f.length,.08,f.width*Math.min(1,f.life/f.max*3));dummy.updateMatrix();
      fxMesh.setMatrixAt(n,dummy.matrix);fxMesh.setColorAt(n++,color.set(f.color));
    }fxMesh.count=n;fxMesh.instanceMatrix.needsUpdate=true;if(fxMesh.instanceColor)fxMesh.instanceColor.needsUpdate=true;
  },
  render(renderer,s,camera){renderer.render(s,camera);}
};
