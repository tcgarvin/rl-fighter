// Canonical, texture-free fleet kit. Geometry caches are bounded to the twelve
// role/team combinations; returned scene graphs are recycled between matches.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mountToLocal } from './hulls.js';

const SLOTS = ['paint', 'trim', 'machinery', 'glow', 'marking'];
const kits = new Map();
const pools = new Map();
const transform = new THREE.Object3D();

function plate(points, y, depth, bevel = .1) {
  const shape = new THREE.Shape();
  points.forEach(([x,z], i) => i ? shape.lineTo(x,-z) : shape.moveTo(x,-z));
  shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape, {
    depth, bevelEnabled: bevel > 0, bevelSize: bevel,
    bevelThickness: bevel * .65, bevelSegments: 1, steps: 1, curveSegments: 1,
  });
  g.rotateX(-Math.PI / 2);
  g.translate(0,y,0);
  return g;
}
function clipped(x,z,l,w,c=.2) {
  c = Math.min(c,l*.25,w*.25);
  return [[x+l/2-c,z+w/2],[x-l/2+c,z+w/2],[x-l/2,z+w/2-c],
    [x-l/2,z-w/2+c],[x-l/2+c,z-w/2],[x+l/2-c,z-w/2],
    [x+l/2,z-w/2+c],[x+l/2,z+w/2-c]];
}
function batch() {
  const bins = Object.fromEntries(SLOTS.map(s => [s,[]]));
  return {
    add(slot,g,x=0,y=0,z=0,angle=0) {
      transform.position.set(x,y,z); transform.rotation.set(0,angle,0);
      transform.scale.set(1,1,1); transform.updateMatrix();
      g.applyMatrix4(transform.matrix);
      if (g.index) { const old=g; g=g.toNonIndexed(); old.dispose(); }
      g.deleteAttribute('uv');
      bins[slot].push(g);
    },
    panel(slot,x,z,l,w,y,d=.16,b=.09) {
      this.add(slot,plate(clipped(x,z,l,w),y,d,b));
    },
    finish() {
      const out=[];
      for (const slot of SLOTS) if (bins[slot].length) {
        const g=mergeGeometries(bins[slot],false);
        g.computeBoundingSphere();
        bins[slot].forEach(p=>p.dispose());
        out.push([slot,g]);
      }
      return out;
    },
  };
}
function cylinder(r1,r2,length) {
  const g=new THREE.CylinderGeometry(r1,r2,length,10,1);
  g.rotateZ(-Math.PI/2); // cylinder top faces exhaust, +X
  return g;
}
function fighter(b) {
  const outline=[[5,0],[2.15,1.55],[-2.8,2.55],[-4.25,1.55],[-3.6,.85],[-2.9,0],[-3.6,-.85],[-4.25,-1.55],[-2.8,-2.55],[2.15,-1.55]];
  b.add('machinery',plate(outline,-.48,.66,.13));
  for (const s of [-1,1]) {
    b.add('paint',plate([[4.55,s*.12],[1.9,s*1.38],[-2.75,s*2.33],[-3.95,s*1.58],[-2.7,s*.8],[-.6,s*.35]],.29,.27,.12));
    b.add('trim',plate([[3.3,s*.18],[.7,s*.63],[-2.65,s*.8],[-2.1,s*.25]],.63,.2,.07));
    b.panel('machinery',-2.95,s*1.55,1.25,.42,.65,.08,.035);
    b.panel('glow',-2.85,s*2.05,.65,.14,.65,.04,.02);
  }
  b.panel('machinery',-.45,0,2.55,.84,.87,.18);
  b.panel('glow',.55,0,.65,.48,1.08,.035,.025);
  b.panel('trim',-3.65,0,1.4,1.3,-.18,.8,.13);
  return [[-3,1,0],[-2,.8,1.8],[-2,.8,-1.8],[0,1.2,0],[1.8,.8,.7],[1.8,.8,-.7]];
}
function strafer(b) {
  b.add('machinery',plate([[4.5,0],[3.25,1.1],[-3.65,1.1],[-4.05,0],[-3.65,-1.1],[3.25,-1.1]],-.4,.75,.12));
  // Two separate motor banks: genuine negative space between the arms.
  for (const x of [-2.4,2.4]) {
    b.panel('machinery',x,0,1.45,9.35,-.35,.7,.13);
    for (const s of [-1,1]) {
      b.add('paint',plate(clipped(x,s*2.95,1.3,3.4,.28),.43,.28,.12));
      b.panel('trim',x,s*4.15,1.1,.65,.78,.12,.055);
      b.panel('glow',x,s*3.65,.65,.18,.81,.035,.02);
    }
  }
  b.panel('trim',-.3,0,6.5,1.65,.44,.22,.12);
  b.panel('paint',-.8,0,3.6,1.2,.78,.18,.09);
  b.panel('machinery',.5,0,1.1,.65,1.01,.07,.04);
  for (const s of [-1,1]) b.panel('machinery',0,s*4.05,3.4,.3,-.22,.32,.04);
  return [[-2.4,1,3],[-2.4,1,-3],[2.4,1,3],[2.4,1,-3],[-1,1.2,0],[1.5,.8,0]];
}
function gunship(b) {
  const outline=[[7.4,0],[5.2,3.75],[-4.5,4.85],[-7.15,3.2],[-7.15,-3.2],[-4.5,-4.85],[5.2,-3.75]];
  b.add('machinery',plate(outline,-.65,1.1,.19));
  // Port and starboard armour are separate plates, divided by the keel.
  for (const s of [-1,1]) {
    b.add('paint',plate([[6.8,s*.35],[4.95,s*3.48],[-4.3,s*4.55],[-6.8,s*3],[-6.6,s*.7]],.58,.23,.15));
    b.add('trim',plate([[5.6,s*.3],[4.2,s*1.25],[-4.6,s*1.25],[-5.65,s*.3]],.92,.14,.08));
    b.panel('machinery',-5.8,s*2,2.5,1.8,-.25,1.25,.16);
    b.panel('trim',-5.8,s*2,1.9,1.45,1.08,.14,.08);
    for (let i=0;i<3;i++) b.panel('machinery',-6.3+i*.5,s*2,.18,1.1,1.28,.06,.02);
    b.panel('glow',.8,s*3.95,1.55,.17,.99,.05,.025);
    b.panel('trim',3.6,s*3.1,1.4,.7,.94,.12,.07);
  }
  b.panel('paint',-.5,0,3.5,1.65,1.12,.22,.12);
  b.panel('machinery',-.4,0,1.75,.86,1.43,.09,.05);
  b.panel('glow',.1,0,.7,.5,1.55,.04,.025);
  return [[-5,1.45,2],[-5,1.45,-2],[-2,1.15,3.7],[-2,1.15,-3.7],[1,1.5,0],[4.8,1,2],[4.8,1,-2],[0,1.15,3.5]];
}

function bomber(b) {
  // Broad haunches and a blunt, low nose leave the forward rack exposed.
  const outline=[[6,1.45],[3.5,3.05],[-3.6,3.8],[-5.7,2.65],[-5.7,-2.65],[-3.6,-3.8],[3.5,-3.05],[6,-1.45]];
  b.add('machinery',plate(outline,-.65,1.05,.16));
  for (const s of [-1,1]) {
    b.add('paint',plate([[4.2,s*1.15],[3.25,s*2.85],[-3.45,s*3.55],[-5.35,s*2.5],[-5.1,s*.65],[-.7,s*.65]],.55,.38,.14));
    b.panel('machinery',-4.6,s*1.6,2.35,1.65,-.2,1.2,.13);
    b.panel('trim',-4.5,s*1.6,1.85,1.3,1.12,.16,.08);
    for (let i=0;i<3;i++) b.panel('machinery',-5+i*.48,s*1.6,.19,1.03,1.33,.06,.02);
    b.panel('trim',-.65,s*2.65,3.3,.55,1.04,.14,.07);
    b.panel('glow',2.6,s*2.5,.75,.16,1.04,.045,.02);
    // External torpedoes in dark saddles: long pale bodies, pointed warheads.
    b.panel('machinery',.85,s*1.65,4.3,1.15,.92,.22,.1);
    b.add('trim',plate([[3.15,s*1.65],[2.35,s*2.04],[-.95,s*2.04],[-1.3,s*1.65],[-.95,s*1.26],[2.35,s*1.26]],1.18,.38,.09));
    for (const x of [-.55,1.35]) b.panel('machinery',x,s*1.65,.25,.98,1.6,.08,.025);
    b.panel('paint',2.25,s*1.65,.65,.67,1.6,.07,.035);
  }
  b.panel('trim',-1.3,0,5.6,1.25,.65,.5,.12);
  b.panel('paint',-1.35,0,2.3,1.05,1.25,.22,.09);
  b.panel('machinery',.6,0,1.3,.8,1.22,.14,.05);
  b.panel('glow',.9,0,.48,.6,1.4,.04,.02);
  // The rack is lower than the dorsal armour, with clear space ahead of it.
  b.panel('machinery',4.3,0,2.4,2.05,.38,.2,.1);
  return [[-4.4,1.4,1.6],[-4.4,1.4,-1.6],[-2.5,1.1,3],[-2.5,1.1,-3],[-1.3,1.6,0],[1.3,1.7,1.65],[1.3,1.7,-1.65],[3.6,.95,0]];
}

function carrier(b,h) {
  // A continuous keel joins the aft engineering deck and the two forward tines.
  // Nothing roofs the bays: their floors sit two metres below the armour.
  b.panel('machinery',-.1,0,39.2,6.2,-1.1,1.9,.3);
  for (const s of [-1,1]) {
    b.add('machinery',plate([[-19.2,s*.4],[-19.2,s*6.8],[-16.5,s*8.5],[-1.4,s*8.5],[-1.4,s*.4]],-1.1,2,.24));
    b.add('paint',plate([[-18.8,s*.7],[-18.8,s*6.5],[-16.1,s*8.1],[-2,s*8.1],[-2,s*3.45],[-7,s*3.45],[-7,s*.7]],1.05,.38,.2));
    b.add('machinery',plate([[9.6,s*.4],[9.6,s*8.45],[15.8,s*8.05],[19.7,s*4.9],[19.7,s*.4]],-1.1,2,.24));
    b.add('paint',plate([[10.1,s*3.45],[10.1,s*8.05],[15.5,s*7.65],[19.2,s*4.65],[19.2,s*.8],[15.8,s*.8],[15.8,s*3.45]],1.05,.38,.17));
    b.panel('trim',13.7,s*5.5,4.3,1.35,1.57,.2,.12);
    b.panel('trim',-10.5,s*5.7,6.5,1.8,1.57,.2,.12);
    b.panel('machinery',-17.2,s*4.5,4,4,-.4,1.9,.22);
    b.panel('trim',-17,s*4.5,2.6,3.25,1.65,.2,.12);
    for (let i=0;i<4;i++) b.panel('machinery',-18+i*.67,s*4.5,.28,2.7,1.91,.08,.03);
  }
  b.panel('paint',3.5,0,29.8,5.65,1.05,.4,.2);
  for (const s of [-1,1]) b.panel('trim',3.2,s*2.6,28,.4,1.6,.12,.05);
  for (const bay of h.bays) {
    const x=bay.pos[0], s=Math.sign(-bay.pos[1]);
    const outer=Math.abs(bay.pos[1]), inner=3.35, center=s*(inner+outer)/2;
    b.panel('machinery',x,center,10.7,outer-inner,-1.03,.25,.12);
    // Fore/aft walls and the inboard sill form an open-sided launch well.
    for (const end of [-1,1]) {
      b.panel('trim',x+end*5.35,center,.65,outer-inner,.1,1.35,.1);
      b.panel('glow',x+end*5,center,.17,outer-inner-.4,1.53,.05,.02);
    }
    b.panel('glow',x,s*(inner+.1),9.6,.17,1.54,.045,.02);
    // Low guidance rails stop at the mouth and leave its centre dark.
    for (const dx of [-2.1,2.1]) {
      b.panel('trim',x+dx,center,.22,outer-inner-1,-.69,.07,.03);
      b.panel('glow',x+dx,s*(outer-.45),.35,.65,-.57,.045,.02);
    }
  }
  // A raised aft command island carries the large fleet badge.
  b.panel('machinery',-10,0,8.4,4.8,1.4,.6,.18);
  b.panel('trim',-10,0,7.5,4.1,2.16,.35,.16);
  b.panel('paint',-10.6,0,4.9,3.5,2.65,.35,.13);
  b.panel('machinery',-6.6,0,1.25,3.4,2.2,.5,.1);
  b.panel('glow',-5.93,0,.16,2.8,2.75,.1,.025);
  b.panel('machinery',-17.9,0,3.6,3.8,-.35,1.8,.2);
  b.panel('trim',-17.6,0,2.8,3.2,1.65,.2,.12);
  for (const t of h.turrets) b.panel('trim',t.pos[0],-t.pos[1],3.8,3.4,1.65,.3,.16);
  return [[-17,2,4.5],[-17,2,-4.5],[-10.6,3.2,0],[-6,1.6,5],[-6,1.6,-5],[2,1.65,0],[13.5,1.9,5.5],[13.5,1.9,-5.5],[18,1.7,2],[18,1.7,-2]];
}

function radial(r,a) { return [Math.cos(a)*r,Math.sin(a)*r]; }
function ringSector(inner,outer,a,half) {
  return [radial(inner,a-half),radial(outer,a-half),radial(outer,a),radial(outer,a+half),radial(inner,a+half),radial(inner,a)];
}
function station(b,h) {
  // Twelve separated armour segments, six spokes and an open annulus.
  for (let i=0;i<12;i++) {
    const a=i*Math.PI/6;
    b.add('machinery',plate(ringSector(12.4,21.6,a,Math.PI/12-.012),-.9,2.1,.18));
    b.add('paint',plate(ringSector(13,21.15,a,Math.PI/12-.028),1.43,.45,.15));
    b.add('trim',plate(ringSector(19.9,21.1,a,Math.PI/12-.045),2.02,.16,.075));
    b.add('glow',plate(ringSector(12.95,13.17,a,.15),2.02,.05,.02));
  }
  for (const t of h.turrets) {
    const x=t.pos[0], z=-t.pos[1], a=Math.atan2(z,x);
    b.add('machinery',plate(clipped(9.5,0,12,3,.4),-.65,1.65,.16),0,0,0,-a);
    b.add('trim',plate(clipped(9.5,0,8.8,1.9,.3),1.15,.3,.1),0,0,0,-a);
    // A substantial clipped shoulder anchors every weapon to the ring.
    b.panel('machinery',x,z,6.3,5.5,1.73,.55,.2);
    b.panel('trim',x,z,5.6,4.9,2.43,.3,.16);
  }
  const hub=Array.from({length:12},(_,i)=>radial(7.6,i*Math.PI/6));
  b.add('machinery',plate(hub,-1,2.25,.22));
  b.add('paint',plate(hub.map(([x,z])=>[x*.91,z*.91]),1.53,.45,.16));
  b.panel('trim',0,0,8.8,8.8,2.16,.4,.2);
  return [[0,2.85,0],[5,2.2,2],[-5,2.2,-2],[0,2.15,19],[0,2.15,-19],[18.5,2.15,0],[-18.5,2.15,0],[12.5,2.15,12.5],[-12.5,2.15,12.5],[12.5,2.15,-12.5]];
}

const BUILDERS={fighter,skirmisher:strafer,anchor:gunship,bomber,carrier,station};
// Dimensions are explicit per role; capital-ship weapons cannot inherit darts.
const TURRETS={
  fighter:{r:.46,base:.5,len:1.45}, skirmisher:{r:.46,base:.5,len:1.45},
  anchor:{r:1,base:1.25,len:2.5}, bomber:{r:.55,base:.7,len:1.25},
  carrier:{r:1.35,base:1.65,len:3.1}, station:{r:1.6,base:1.95,len:3.6},
};

function insignia(b,team,x,z,y,scale) {
  b.panel('machinery',x,z,1.75*scale,1.65*scale,y,.06,.08*scale);
  // Clear the backing's scaled bevel as well as its extrusion depth.
  const top=y+.06+.08*scale*.65+.025;
  if (!team) b.add('marking',plate([[x+.65*scale,z],[x,z+.65*scale],[x-.65*scale,z],[x,z-.65*scale]],top,.04,.015));
  else for (const s of [-1,1]) b.panel('marking',x,z+s*.38*scale,1.25*scale,.5*scale,top,.04,.015);
}
function largeMarkings(b,role,team) {
  const stripe=(x,z,y,span,scale)=>{
    for (let i=0;i<(team?2:1);i++) b.panel('marking',x+(team?(i-.5)*.68*scale:0),z,(team?.27:.85)*scale,span,y,.045,.015);
  };
  if (role==='bomber') {
    stripe(-2.8,0,1.06,6.1,1.2);
    insignia(b,team,-1.4,0,1.56,.95);
  } else if (role==='carrier') {
    // Split across the aft deck; stripes never bridge an open launch bay.
    for (const s of [-1,1]) stripe(-12.7,s*5.7,1.91,4.1,2.8);
    insignia(b,team,-10.6,0,3.12,2.35);
  } else {
    for (const s of [-1,1]) stripe(0,s*17.2,1.99,6.6,3);
    insignia(b,team,0,0,2.72,3.6);
  }
}

function createKit(h,team) {
  const b=batch(), heavy=h.role==='anchor', ray=h.role==='skirmisher';
  const damage=BUILDERS[h.role](b,h,team);
  const capital=h.role==='carrier'||h.role==='station';
  const legacy=h.role==='fighter'||heavy||ray;
  // Raised, high-contrast fleet insignia. The split square has a real gap.
  if (legacy) {
    const mx=heavy?-4.45:ray?-2.4:-2.25;
    const my=heavy?1.02:ray?1.02:.79;
    const span=heavy?6.2:ray?7.7:3.55;
    for (let i=0;i<(team?2:1);i++)
      b.panel('marking',mx+(team?(i-.5)*.68:0),0,team?.27:.85,span,my,.045,.015);
    const ex=heavy?-.65:ray?-.8:-.6, ey=heavy?1.56:ray?1.03:1.08;
    b.panel('machinery',ex,0,1.75,1.65,ey,.06,.08);
    if (!team) b.add('marking',plate([[ex+.65,0],[ex,.65],[ex-.65,0],[ex,-.65]],ey+.08,.04,.015));
    else for (const s of [-1,1]) b.panel('marking',ex,s*.38,1.25,.5,ey+.08,.04,.015);
  } else largeMarkings(b,h.role,team);

  for (const t of h.thrusters) {
    // +X rotated about +Y becomes (cos a,0,-sin a).
    const a=Math.atan2(-t.dir[1],-t.dir[0]);
    const x=t.pos[0], z=-t.pos[1], s=t.size;
    const g=cylinder(s*.67,s*.43,s*.75);
    g.translate(-s*.38,0,0); b.add('trim',g,x,0,z,a);
    const mouth=cylinder(s*.51,s*.51,s*.08);
    mouth.translate(-s*.025,0,0); b.add('machinery',mouth,x,0,z,a);
    const throat=cylinder(s*.26,s*.26,s*.025);
    throat.translate(s*.025,0,0); b.add('glow',throat,x,0,z,a);
  }
  const weapon=TURRETS[h.role];
  for (const t of h.turrets) {
    const r=weapon.base;
    const g=new THREE.CylinderGeometry(r,r*1.12,.23,12);
    b.add('machinery',g,t.pos[0],t.height-.12,-t.pos[1]);
  }
  const tb=batch(), r=weapon.r, len=weapon.len;
  if (h.role==='bomber') {
    // Three short launch tubes in a small fixed rack, rather than a gun barrel.
    tb.panel('machinery',.2,0,1.45,1.85,.04,.36,.08);
    for (const z of [-.6,0,.6]) {
      tb.panel('trim',.45,z,1.6,.45,.13,.42,.055);
      tb.panel('machinery',1.24,z,.1,.33,.21,.27,.025);
      tb.panel('glow',1.3,z,.025,.12,.3,.06,.01);
    }
  } else {
    const scale=capital?r:1;
    tb.panel('trim',0,0,r*1.65,r*1.5,.08,heavy||capital?.42*scale:.27,.1);
    tb.panel('paint',-.22*scale,0,r*.8,r*1.2,heavy||capital?.58*scale:.42,.07,.04);
    tb.panel('machinery',len*.5+.35,0,len,.3*scale,.19,.25*scale,.035);
    tb.panel('trim',len+.25,0,.35,.49*scale,.14,.35*scale,.04);
    tb.panel('glow',len+.44,0,.045,.24*scale,.26,.1*scale,.01);
  }
  const damagePoints=damage.map(p=>new THREE.Vector3(...p));
  return {body:b.finish(),turret:tb.finish(),tip:h.role==='bomber'?1.33:len+.46,
    muzzleHeight:h.role==='bomber'?.345:capital?.19+.125*r:.315,damagePoints};
}
// Unit plume, broad at the nozzle and tapering to +X. No textures or shaders.
const plume=new THREE.ConeGeometry(.55,1,8,1);
plume.rotateZ(-Math.PI/2); plume.translate(.5,0,0);

export function buildHull(hull,team,mats) {
  const key=`${hull.role}:${team?1:0}`;
  let pool=pools.get(key);
  if (!pool) pools.set(key,pool=[]);
  let model=pool.pop();
  if (model) {
    model.object.traverse(o=>{if(o.isMesh) o.material=mats[o.userData.slot];});
    model.object.position.set(0,0,0);model.object.rotation.set(0,0,0);
    model.object.scale.set(1,1,1);model.object.visible=true;
    for (const t of model.thrusters) {t.level=0;t.node.visible=false;}
    for (const p of model.turrets) p.rotation.y=0;
    model._released=false;
    return model;
  }
  let kit=kits.get(key);
  if (!kit) kits.set(key,kit=createKit(hull,team));
  const object=new THREE.Group();object.name=`hull.${hull.role}`;
  function meshes(parent,entries) {
    for (const [slot,g] of entries) {
      const m=new THREE.Mesh(g,mats[slot]);m.userData.slot=slot;parent.add(m);
    }
  }
  meshes(object,kit.body);
  const thrusters=hull.thrusters.map(t=>{
    const node=new THREE.Group();node.name=t.id;
    node.position.set(...mountToLocal(t.pos));
    node.rotation.y=Math.atan2(-t.dir[1],-t.dir[0]);
    const shell=new THREE.Mesh(plume,mats.exhaust);
    const core=new THREE.Mesh(plume,mats.exhaust);
    shell.userData.slot=core.userData.slot='exhaust';
    shell.position.x=core.position.x=.055*t.size;
    node.add(shell,core);object.add(node);node.visible=false;
    return {node,size:t.size,shell,core,level:0};
  });
  const muzzles=[];
  const turrets=hull.turrets.map(t=>{
    const pivot=new THREE.Group();pivot.name=t.id;
    pivot.position.set(...mountToLocal(t.pos,t.height));
    meshes(pivot,kit.turret);
    const muzzle=new THREE.Object3D();muzzle.name=`${t.id}.muzzle`;
    muzzle.position.set(kit.tip,kit.muzzleHeight,0);pivot.add(muzzle);muzzles.push(muzzle);
    object.add(pivot);return pivot;
  });
  model={object,thrusters,turrets,muzzles,
    damagePoints:kit.damagePoints.map(p=>p.clone()),_released:false,
    setThrottles(throttles,dt) {
      const k=1-Math.exp(-Math.max(0,dt)*24);
      for (let i=0;i<thrusters.length;i++) {
        const t=thrusters[i],target=Math.max(0,Math.min(1.4,throttles[i]||0)); // >1: boosted engine power
        t.level+=(target-t.level)*k;
        if (target===0 && t.level<.015) t.level=0;
        t.node.visible=t.level>.01;
        const s=t.size, v=t.level;
        // Half throttle is a short, narrow jet; full is over twice as long.
        t.shell.scale.set(s*(.2+6.8*v),s*(.5+.5*v),s*(.5+.5*v));
        t.core.scale.set(s*(.15+3.3*v),s*(.22+.2*v),s*(.22+.2*v));
      }
    },
    dispose() {
      if (model._released) return;
      model._released=true;object.removeFromParent();
      // Cap retained graphs even if a future match temporarily has a huge fleet.
      if (pool.length<24) pool.push(model);
      // Cached immutable geometries belong to the bounded fleet kit, not a ship.
      // Materials belong to the treatment and must never be disposed here.
    },
  };
  return model;
}
