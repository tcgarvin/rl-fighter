// Canonical, texture-free fleet kit. Geometry caches are bounded to the six
// hull/team combinations; returned scene graphs are recycled between matches.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mountToLocal } from '../hulls.js';

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
function createKit(h,team) {
  const b=batch(), heavy=h.role==='anchor', ray=h.role==='skirmisher';
  if (!heavy && !ray) {
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
  } else if (ray) {
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
  } else {
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
  }
  // Raised, high-contrast fleet insignia. The split square has a real gap.
  const mx=heavy?-4.45:ray?-2.4:-2.25;
  const my=heavy?1.02:ray?1.02:.79;
  const span=heavy?6.2:ray?7.7:3.55;
  for (let i=0;i<(team?2:1);i++)
    b.panel('marking',mx+(team?(i-.5)*.68:0),0,team?.27:.85,span,my,.045,.015);
  const ex=heavy?-.65:ray?-.8:-.6, ey=heavy?1.56:ray?1.03:1.08;
  b.panel('machinery',ex,0,1.75,1.65,ey,.06,.08);
  if (!team) b.add('marking',plate([[ex+.65,0],[ex,.65],[ex-.65,0],[ex,-.65]],ey+.08,.04,.015));
  else for (const s of [-1,1]) b.panel('marking',ex,s*.38,1.25,.5,ey+.08,.04,.015);

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
  for (const t of h.turrets) {
    const r=heavy?1.25:.5;
    const g=new THREE.CylinderGeometry(r,r*1.12,.23,12);
    b.add('machinery',g,t.pos[0],t.height-.12,-t.pos[1]);
  }
  const tb=batch(), r=heavy?1:.46, len=heavy?2.5:1.45;
  tb.panel('trim',0,0,r*1.65,r*1.5,.08,heavy?.42:.27,.1);
  tb.panel('paint',-.22,0,r*.8,r*1.2,heavy?.58:.42,.07,.04);
  tb.panel('machinery',len*.5+.35,0,len,.3, .19,.25,.035);
  tb.panel('trim',len+.25,0,.35,.49,.14,.35,.04);
  tb.panel('glow',len+.44,0,.045,.24,.26,.1,.01);
  const damagePoints=(heavy? [[-5,1.45,2],[-5,1.45,-2],[-2,1.15,3.7],[-2,1.15,-3.7],[1,1.5,0],[4.8,1,2],[4.8,1,-2],[0,1.15,3.5]]:
    ray?[[-2.4,1,3],[-2.4,1,-3],[2.4,1,3],[2.4,1,-3],[-1,1.2,0],[1.5,.8,0]]:
    [[-3,1,0],[-2, .8,1.8],[-2,.8,-1.8],[0,1.2,0],[1.8,.8,.7],[1.8,.8,-.7]])
    .map(p=>new THREE.Vector3(...p));
  return {body:b.finish(),turret:tb.finish(),tip:len+.46,damagePoints};
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
    muzzle.position.set(kit.tip,.315,0);pivot.add(muzzle);muzzles.push(muzzle);
    object.add(pivot);return pivot;
  });
  model={object,thrusters,turrets,muzzles,
    damagePoints:kit.damagePoints.map(p=>p.clone()),_released:false,
    setThrottles(throttles,dt) {
      const k=1-Math.exp(-Math.max(0,dt)*24);
      for (let i=0;i<thrusters.length;i++) {
        const t=thrusters[i],target=Math.max(0,Math.min(1,throttles[i]||0));
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
