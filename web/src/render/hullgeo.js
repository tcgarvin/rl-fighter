// Canonical, texture-free fleet kit. A spec's look is `model` when it names one, else
// its role, so one role can have several looks (the transport role's freighter today,
// a medical frigate later). Geometry caches are bounded to the look/team combinations
// (seven looks x two teams = fourteen); returned scene graphs are recycled between matches.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mountToLocal } from './hulls.js';

// `scorch` is burnt metal (destroyed hardpoints); a treatment without it uses machinery.
const SLOTS = ['paint', 'trim', 'machinery', 'glow', 'marking', 'scorch'];
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

function freighter(b) {
  // Four exposed containers flank a painted spine, rather than an armoured deck.
  b.panel('machinery',-.5,0,24.6,2.1,-.65,1.05,.12);
  b.panel('paint',-.8,0,17.2,1.35,.42,.95,.08);
  for (const x of [-4.6,3]) for (const s of [-1,1]) {
    const z=s*2.55;
    b.panel('machinery',x,z,7.15,3.75,-.25,.8,.08);
    // Painted ends and broad side rims keep both teams legible around pale lids.
    b.panel('paint',x,z,6.8,3.65,.5,1.25,.1);
    b.panel('trim',x,z,5.3,2.65,1.81,.2,.06);
    // A dark strap crosses each lid and folds down over the painted sides.
    b.panel('machinery',x+.25,z,.45,3.72,1.79,.34,.025);
  }
  // A low crossmember anchors the heading puffers beneath a distinctly narrow cab.
  b.panel('machinery',9,0,1.25,8.2,-.45,.9,.08);
  b.panel('machinery',9.4,0,6.3,4.5,-.6,1.15,.12);
  b.panel('paint',9.45,0,6.1,4.1,.6,1,.12);
  // This flat roof carries the badge and stripes; the windshield faces forward.
  b.panel('paint',9.2,0,4.8,3.8,1.65,.4,.1);
  b.panel('machinery',11.77,0,.38,3.1,1.65,.48,.045);
  b.panel('glow',11.98,0,.12,2.65,1.75,.23,.015);
  // The squat engine block encloses the mains and meets the aft RCS at its edge.
  b.panel('machinery',-10.25,0,5.3,8.6,-.8,1.45,.16);
  b.panel('paint',-10.25,0,5.1,8.35,.8,.65,.1);
  for (const s of [-1,1]) {
    b.panel('trim',-10.5,s*2,3,1.5,1.52,.12,.06);
    for (const x of [-11.3,-10.5,-9.7])
      b.panel('machinery',x,s*2,.28,1.1,1.7,.06,.025);
  }
  return [[-11,1.8,2],[-11,1.8,-2],[-4.6,2.16,2.55],[-4.6,2.16,-2.55],
    [0,1.45,0],[3,2.16,2.55],[3,2.16,-2.55],[8.2,2.5,0]];
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

const CITADEL_BAY={depth:8,width:7.2,y:-.64};
function citadel(b,h) {
  // The rim stops at each launch cutout: a solid core plate would roof the wells.
  const hub=Array.from({length:12},(_,i)=>radial(14,i*Math.PI/6));
  b.add('machinery',plate(hub,-1.2,3,.24));
  for (let i=0;i<12;i++) {
    const a=i*Math.PI/6;
    if ([1,5,7,11].includes(i)) continue;
    b.add('machinery',plate(ringSector(13,20,a,Math.PI/12),-1.2,3,.18));
    b.add('paint',plate(ringSector(13.6,19.5,a,Math.PI/12-.025),2.08,.45,.13));
    b.add('trim',plate(ringSector(18.7,19.65,a,Math.PI/12-.04),2.7,.18,.07));
    b.add('glow',plate(ringSector(17.9,18.15,a,.14),2.7,.045,.02));
  }
  for (const bay of h.bays) {
    const a=Math.atan2(bay.dir[1],bay.dir[0]);
    const add=(slot,g)=>b.add(slot,g,0,0,0,a);
    add('machinery',plate(clipped(18,0,CITADEL_BAY.depth,CITADEL_BAY.width,.3),-1,.25,.1));
    add('machinery',plate(clipped(14.1,0,.8,7.2,.15),-.8,2.8,.1));
    for (const s of [-1,1]) {
      add('machinery',plate([[13.2,s*3.6],[13.2,s*3.9],[19.32,s*5.18],[22,s*4.65],[22,s*3.65]],-1.1,3,.12));
      add('paint',plate([[14.5,s*3.95],[19,s*4.8],[21.6,s*4.4],[21.6,s*3.9]],2.1,.4,.1));
      add('trim',plate(clipped(18.2,s*3.85,7.5,.45,.1),2.55,.18,.055));
      add('glow',plate(clipped(18.3,s*3.61,6.8,.16,.04),2.53,.07,.02));
      add('trim',plate(clipped(18,s*2.25,6.3,.22,.06),-.62,.08,.025));
      add('glow',plate(clipped(21.25,s*2.25,.9,.35,.06),-.49,.04,.02));
    }
  }
  // Six narrow bridges only on module bearings; the inter-module annulus stays empty.
  const damage=[[0,4.95,0],[9,3.8,4],[-9,3.8,-4],[0,2.9,-16]];
  for (let k=0;k<6;k++) {
    const a=k*Math.PI/3, [x,z]=radial(38,a);
    const add=(slot,g)=>b.add(slot,g,x,0,z,-a);
    b.add('machinery',plate(clipped(24,0,12,3.6,.5),-.8,1.7,.14),0,0,0,-a);
    b.add('trim',plate(clipped(24,0,10,1.7,.3),1.1,.22,.08),0,0,0,-a);
    const hex=Array.from({length:6},(_,i)=>radial(11,i*Math.PI/3));
    add('machinery',plate(hex,-1.1,2.8,.2));
    // Separated armour leaves dark seams and a pale perimeter, as on the v9 station.
    for (let j=0;j<6;j++) {
      const q=j*Math.PI/3+Math.PI/6, half=Math.PI/6-.035;
      add('paint',plate([radial(2.9,q-half),radial(10.4,q-half),radial(9.08,q),
        radial(10.4,q+half),radial(2.9,q+half)],1.96,.4,.12));
      add('trim',plate([radial(9.6,q-half+.02),radial(10.4,q-half+.02),radial(9.08,q),
        radial(10.4,q+half-.02),radial(9.6,q+half-.02),radial(8.4,q)],2.52,.16,.065));
    }
    add('paint',plate(clipped(-3,0,7.4,6.6,.9),2.42,.34,.12));
    add('machinery',plate(clipped(-6.2,0,2.4,3.5,.3),2.88,.12,.06));
    for (const s of [-1,1]) {
      add('glow',plate(clipped(-3.2,s*7,3.1,.22,.05),2.57,.05,.02));
      add('trim',plate(clipped(-5,s*4.5,2.5,.65,.15),2.56,.14,.06));
    }
    damage.push([x,3,z]);
  }
  for (const t of h.turrets) {
    const heavy=t.weapon==='lance', l=heavy?7.6:5.2, w=heavy?7.2:4.9;
    const x=t.pos[0], z=-t.pos[1], a=(t.rest??0)*Math.PI/180;
    b.add('machinery',plate(clipped(0,0,l,w,.7),2.25,t.height-2.7,.14),x,0,z,a);
    b.add('trim',plate(clipped(0,0,l-.45,w-.45,.6),t.height-.53,.23,.1),x,0,z,a);
  }
  b.add('trim',plate(hub.map(([x,z])=>[x*.85,z*.85]),2.12,.55,.17));
  b.add('paint',plate(hub.map(([x,z])=>[x*.76,z*.76]),2.93,.58,.16));
  b.panel('trim',0,0,13,13,3.72,.4,.18);
  return damage;
}
function dreadnought(b,h) {
  // A deep arrowhead belt thins into exposed engineering aft, never a flight deck.
  const outline=[[27,0],[22,7],[8,9.6],[-17,8.6],[-23,7.5],[-31,7],[-31,-7],[-23,-7.5],[-17,-8.6],[8,-9.6],[22,-7]];
  b.add('machinery',plate(outline,-1.25,2.5,.24));
  for (const s of [-1,1]) {
    b.add('trim',plate([[26,s*.35],[21.6,s*6.7],[8,s*9.15],[-17,s*8.15],[-18,s*6.2],[9,s*6.6],[21,s*4.4]],1.38,.35,.16));
    b.add('paint',plate([[25.6,s*.55],[21.3,s*6.25],[8,s*8.65],[-17,s*7.65],[-17,s*3.5],[10,s*3.4],[20.5,s*2.8]],1.96,.46,.15));
    // Overlapping bow cheeks make the armoured end readable even at phone scale.
    b.add('machinery',plate([[24.8,s*.7],[21,s*5.6],[10,s*7.7],[5.6,s*5.9],[10,s*3.65],[21,s*2.4]],2.58,.3,.12));
    b.add('paint',plate([[24.2,s*.9],[20.6,s*5.05],[10.4,s*7.15],[7.2,s*5.8],[11,s*4],[20.8,s*2.6]],3.03,.42,.14));
    b.add('trim',plate([[22.8,s*1.6],[20.4,s*4.7],[11.5,s*6.6],[12.5,s*5.7],[20.1,s*3.8]],3.64,.16,.065));
    b.panel('glow',-7,s*7.45,3.3,.2,2.56,.05,.025);
    // Low flak sponsons project from the belt, below the rail barbettes.
    b.add('machinery',plate(clipped(0,s*8.6,6.1,4.6,.8),.4,1.05,.13));
    b.panel('trim',0,s*9,4.6,4,1.72,.28,.1);
    b.panel('machinery',-23.8,s*5,10.2,3.5,.7,.7,.15);
    b.panel('trim',-24,s*5,7.6,2.7,1.62,.18,.08);
    for (let i=0;i<5;i++) b.panel('machinery',-27+i*1.35,s*5,.62,2.3,1.88,.22,.04);
    b.panel('paint',-20,s*6.8,2.6,1.5,1.72,.3,.1);
  }
  b.panel('machinery',0,0,35,6.8,1.35,1,.2);
  b.panel('trim',0,0,34,5.8,2.58,.25,.12);
  b.panel('paint',0,0,32.8,4.8,2.99,.18,.09);
  for (const t of h.turrets.filter(t=>t.weapon==='rail')) {
    b.add('machinery',new THREE.CylinderGeometry(3.35,3.8,.62,12),t.pos[0],2.65,0);
    b.add('trim',new THREE.CylinderGeometry(3.25,3.35,.22,12),t.pos[0],3.05,0);
  }
  // The tiny bow gun overhangs a low nose deck; it must not bury in the bow cheeks.
  b.add('trim',plate([[27,0],[25.2,2.3],[23.5,1.5],[23.5,-1.5],[25.2,-2.3]],1.42,.3,.1));
  b.panel('machinery',-2,0,7.5,4.6,3.27,.6,.17);
  b.panel('trim',-2.5,0,5.5,4.1,4.1,.45,.14);
  b.panel('paint',-2.8,0,4.7,3.6,4.75,.45,.12);
  b.panel('machinery',1.05,0,.5,3.5,3.9,.9,.06);
  b.panel('glow',1.33,0,.12,2.9,4.22,.25,.025);
  // Three independent engine blocks leave the stern visibly less armoured.
  for (const z of [-5,0,5]) {
    b.panel('machinery',-28.7,z,4.6,4.2,-1.4,2.7,.18);
    b.panel('trim',-28.6,z,2.1,3.7,1.55,.22,.09);
    b.panel('machinery',-28.6,z,.65,3.2,1.87,.12,.035);
  }
  b.panel('paint',-22.6,0,6.1,5.2,1.5,.45,.13);
  return [[21,3.9,4],[21,3.9,-4],[10,3.6,6],[10,3.6,-6],[-2.8,5.75,0],
    [-14,2.8,6],[-23,2.3,5],[-23,2.3,-5],[-28.6,2.1,0]];
}

// Capital turret kits by weapon (body frame: barrel along +X; y up from the base ring).
// Each fills the batch and returns where its muzzle is: {tip, muzzleHeight}.
const TURRET_KITS={
  lance(tb,r) {
    // A single coil-wrapped accelerator, much heavier than the point-defence guns.
    tb.panel('machinery',-.35,0,r*1.95,r*1.6,.02,.65,.2);
    tb.panel('trim',-.4,0,r*1.7,r*1.45,.81,.65,.18);
    tb.panel('paint',-.85,0,r*1.12,r*1.25,1.63,.3,.12);
    const y=1.18, tip=11.8;
    tb.add('machinery',cylinder(.48,.62,10.2),6.5,y,0);
    for (const x of [2.2,4.15,6.1,8.05,10]) {
      tb.add('trim',cylinder(.81,.81,.42),x,y,0);
      tb.add('machinery',cylinder(.88,.88,.14),x-.16,y,0);
    }
    for (const s of [-1,1]) {
      tb.panel('machinery',3.2,s*.88,4.1,.38,.9,.62,.07);
      tb.panel('glow',1.9,s*r*.61,1.2,.15,1.62,.06,.02);
    }
    tb.add('trim',cylinder(.72,.72,.65),11.35,y,0);
    tb.add('machinery',cylinder(.57,.57,.11),11.72,y,0);
    tb.add('glow',cylinder(.4,.4,.07),tip,y,0);
    return {tip:tip+.04,muzzleHeight:y};
  },
  rail(tb,r) {
    // Two broad rails keep a visible dark slot; there is no tube joining their tips.
    tb.panel('machinery',-.45,0,r*1.95,r*1.65,.03,.6,.18);
    tb.panel('trim',-.7,0,r*1.65,r*1.46,.79,.85,.2);
    tb.panel('paint',-1.05,0,r*1.16,r*1.2,1.85,.23,.1);
    for (const s of [-1,1]) {
      tb.panel('machinery',5.15,s*.95,8.1,.95,.77,.63,.08);
      tb.panel('trim',5.05,s*1.15,7.8,.5,1.55,.24,.055);
      tb.panel('glow',6.6,s*.51,4.4,.12,1.44,.07,.02);
      for (const x of [2.3,4.4,6.5]) tb.panel('paint',x,s*1.13,.42,.62,1.86,.12,.04);
      tb.panel('trim',8.98,s*.96,.4,1.08,.74,.75,.08);
    }
    return {tip:9.22,muzzleHeight:1.17};
  },
};

/**
 * A destroyed turret's stump on a base ring of radius r (hull-local, centred on the
 * mount, y from the base ring's top): scorched, torn plate and a snapped barrel root.
 */
function stump(sb,r,weapon) {
  // Separate teeth leave the centre hollow; a dark solid disc reads as a live cap.
  sb.add('scorch',new THREE.CylinderGeometry(r*.55,r*.65,.13,9),0,.04,0);
  for (let i=0;i<9;i++) {
    const a=i*TAU9, outer=r*(i%3===0?1.04:.87), half=TAU9*.42;
    sb.add('scorch',plate([radial(r*.52,a-half),radial(outer,a-half),radial(outer*.78,a),
      radial(outer,a+half),radial(r*.46,a+half)],.02,.18+(i%3)*.06,.035));
  }
  const heavy=weapon==='lance'||weapon==='rail';
  sb.add('scorch',plate([[-r*.15,-r*.22],[r*.85,-r*.22],[r*.61,0],[r*.92,r*.13],[-r*.15,r*.25]],.16,heavy?.36:.22,.035));
  sb.add('machinery',plate([[r*.6,-r*.2],[r*.84,-r*.21],[r*.63,-r*.06],[r*.8,r*.12],[r*.57,r*.17]],heavy?.54:.4,.045,.015));
  for (const s of [-1,1]) {
    const g=plate([[-r*.65,0],[-r*.2,-s*r*.14],[r*.12,s*r*.16],[-r*.42,s*r*.29]],0,.08,.02);
    g.rotateX(s*.42);g.rotateZ(-s*.18);
    sb.add('scorch',g,0,.25,s*r*.62);
    sb.add('trim',plate([[-r*.63,s*r*.63],[-r*.18,s*r*.56],[-r*.31,s*r*.65]],.39,.035,.01));
  }
}
const TAU9=Math.PI*2/9;

/**
 * Where a bay's mouth is drawn on look `name`: hull-local centre (x, z), the angle of
 * its long axis (rad about +Y), deck height y, and its size [length, width] in metres.
 */
function bayFrame(name,h,bay) {
  if (name==='carrier') {
    // The carrier's open launch wells run fore and aft from the bay mount (see carrier()).
    const s=Math.sign(-bay.pos[1]), outer=Math.abs(bay.pos[1]), inner=3.35;
    return {x:bay.pos[0],z:s*(inner+outer)/2,angle:0,y:-.76,size:[10.7,outer-inner]};
  }
  const a=Math.atan2(bay.dir[1],bay.dir[0]), depth=name==='citadel'?CITADEL_BAY.depth:3;
  return {x:bay.pos[0]-bay.dir[0]*depth/2,z:-(bay.pos[1]-bay.dir[1]*depth/2),angle:a,
    y:name==='citadel'?CITADEL_BAY.y:1.3,size:[depth,name==='citadel'?CITADEL_BAY.width:5]};
}
/** A destroyed bay: a dark, burnt-out mouth of length l (along the launch) and width w. */
function bayHole(hb,l,w) {
  hb.panel('scorch',0,0,l,w,.02,.25,.04);
  for (const s of [-1,1]) {
    hb.add('scorch',plate([[-l*.5,s*w*.54],[-l*.29,s*w*.52],[-l*.18,s*w*.3],
      [-l*.04,s*w*.49],[l*.16,s*w*.36],[l*.33,s*w*.51],[l*.5,s*w*.46],
      [l*.5,s*w*.61],[-l*.5,s*w*.61]],.17,.23,.035));
    // Wreck caps cover the permanent edge lights: these bays have no live node to hide.
    const citadel=Math.abs(l-CITADEL_BAY.depth)<.01, y=citadel?3.35:2.43;
    if (citadel) hb.panel('scorch',0,s*(w/2+.12),l-.65,.54,y,.12,.04);
    else hb.panel('scorch',s*(l/2-.35),0,.55,w-.2,y,.12,.04);
    hb.panel('scorch',0,s*(w/2-.08),l-.4,.46,citadel?3.15:2.4,.12,.04);
    const g=plate([[-l*.5,-w*.3],[-l*.35,-w*.28],[-l*.4,w*.04],[-l*.3,w*.18],[-l*.5,w*.28]],0,.12,.025);
    g.rotateZ(s*.2);
    hb.add('scorch',g,s*l*.03,.55,s*w*.09,s<0?Math.PI:0);
    hb.add('machinery',plate([[s*l*.42,-w*.26],[s*l*.35,-w*.23],[s*l*.39,w*.02]],.81,.045,.015));
  }
}

// Keyed by look (spec.model ?? spec.role). `transport` is the role's default look.
const BUILDERS={fighter,skirmisher:strafer,anchor:gunship,bomber,carrier,freighter,transport:freighter,station,citadel,dreadnought};
/** The look a spec is built with: its explicit model, else its role. */
function look(h) { return h.model ?? h.role; }
// Roles drawn at capital scale: big turret kits, hardpoint stumps, large markings.
const CAPITAL_ROLES=new Set(['carrier','station','line']);
// Dimensions are explicit per role; capital-ship weapons cannot inherit darts.
const TURRETS={
  fighter:{r:.46,base:.5,len:1.45}, skirmisher:{r:.46,base:.5,len:1.45},
  anchor:{r:1,base:1.25,len:2.5}, bomber:{r:.55,base:.7,len:1.25},
  carrier:{r:1.35,base:1.65,len:3.1}, station:{r:1.6,base:1.95,len:3.6},
  line:{r:1.45,base:1.75,len:3.3},
};
// Capital guns heavier than their hull's standard turret: a base radius of their own.
const HEAVY_BASE={lance:3.1,rail:2.9};
/** The radius of the base ring `weapon` sits on, on hull `h`. */
function turretBase(h,weapon) {
  return CAPITAL_ROLES.has(h.role) && HEAVY_BASE[weapon] ? HEAVY_BASE[weapon] : TURRETS[h.role].base;
}

function insignia(b,team,x,z,y,scale) {
  b.panel('machinery',x,z,1.75*scale,1.65*scale,y,.06,.08*scale);
  // Clear the backing's scaled bevel as well as its extrusion depth.
  const top=y+.06+.08*scale*.65+.025;
  if (!team) b.add('marking',plate([[x+.65*scale,z],[x,z+.65*scale],[x-.65*scale,z],[x,z-.65*scale]],top,.04,.015));
  else for (const s of [-1,1]) b.panel('marking',x,z+s*.38*scale,1.25*scale,.5*scale,top,.04,.015);
}
function largeMarkings(b,kind,team) {
  const stripe=(x,z,y,span,scale)=>{
    for (let i=0;i<(team?2:1);i++) b.panel('marking',x+(team?(i-.5)*.68*scale:0),z,(team?.27:.85)*scale,span,y,.045,.015);
  };
  if (kind==='bomber') {
    stripe(-2.8,0,1.06,6.1,1.2);
    insignia(b,team,-1.4,0,1.56,.95);
  } else if (kind==='carrier') {
    // Split across the aft deck; stripes never bridge an open launch bay.
    for (const s of [-1,1]) stripe(-12.7,s*5.7,1.91,4.1,2.8);
    insignia(b,team,-10.6,0,3.12,2.35);
  } else if (kind==='freighter' || kind==='transport') {
    // Contact planes include the roof's top bevel and the markings' bottom bevel.
    const cabTop=1.65+.4+.1*.65, engineTop=.8+.65+.1*.65;
    stripe(10.45,0,cabTop+.015*.65,3.1,1);
    stripe(-8.35,0,engineTop+.015*.65,7.1,.9);
    insignia(b,team,8.25,0,cabTop+.08*1.05*.65,1.05);
  } else if (kind==='citadel') {
    for (const s of [-1,1]) stripe(s*35,0,2.87,5.3,2.5);
    for (const s of [-1,1]) stripe(0,s*9,3.65,2.6,2.7);
    insignia(b,team,0,0,4.28,6);
  } else if (kind==='dreadnought') {
    for (const s of [-1,1]) stripe(-9,s*5.65,2.56,3.5,2);
    stripe(-20.5,0,2.08,4.1,1.2);
    // Keep the badge on the bridge, clear of the aft gun's long rest-bearing rails.
    insignia(b,team,-2.8,0,5.3,1.95);
  } else {
    for (const s of [-1,1]) stripe(0,s*17.2,1.99,6.6,3);
    insignia(b,team,0,0,2.72,3.6);
  }
}

function createKit(h,team) {
  const b=batch(), heavy=h.role==='anchor', ray=h.role==='skirmisher';
  const build=BUILDERS[look(h)];
  if (!build) throw new Error(`hullgeo: no builder for look "${look(h)}" (role ${h.role})`);
  const damage=build(b,h,team);
  const capital=CAPITAL_ROLES.has(h.role);
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
  } else largeMarkings(b,look(h),team);

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
  // Unarmed hulls (the freighter) have no turret kit at all.
  if (!h.turrets.length) {
    return {body:b.finish(),turrets:new Map(),stumps:new Map(),hole:[],damagePoints:damage.map(p=>new THREE.Vector3(...p))};
  }
  const weapon=TURRETS[h.role];
  if (!weapon) throw new Error(`hullgeo: no turret dimensions for role ${h.role}`);
  for (const t of h.turrets) {
    const r=turretBase(h,t.weapon);
    const g=new THREE.CylinderGeometry(r,r*1.12,.23,12);
    b.add('machinery',g,t.pos[0],t.height-.12,-t.pos[1]);
  }
  // One turret kit per weapon the hull mounts (most hulls: one look for all of them).
  const turrets=new Map();
  for (const name of new Set(h.turrets.map(t=>t.weapon))) {
    const special=TURRET_KITS[name];
    if (capital && special) {
      const tb=batch(), dims=special(tb,turretBase(h,name));
      turrets.set(name,{meshes:tb.finish(),...dims});
      continue;
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
    turrets.set(name,{meshes:tb.finish(),tip:h.role==='bomber'?1.33:len+.46,
      muzzleHeight:h.role==='bomber'?.345:capital?.19+.125*r:.315});
  }
  const damagePoints=damage.map(p=>new THREE.Vector3(...p));
  // Destroyed hardpoints (capital hulls): one stump per weapon's base size, one bay hole.
  const stumps=new Map();
  if (capital) for (const name of turrets.keys()) {
    const sb=batch(); stump(sb,turretBase(h,name),name);
    stumps.set(name,sb.finish());
  }
  let hole=[];
  if (h.bays?.length) {
    const hb=batch(); const [l,w]=bayFrame(look(h),h,h.bays[0]).size; bayHole(hb,l,w);
    hole=hb.finish();
  }
  return {body:b.finish(),turrets,stumps,hole,damagePoints};
}
// Unit plume: a soft body of revolution from the nozzle (x = 0) to its tip (x = 1),
// swelling a little before it tapers. The treatment's exhaust material shades it.
const plume=new THREE.LatheGeometry(Array.from({length:13},(_,i)=>{
  const x=i/12;
  return new THREE.Vector2(.55*(1-x)**.7*(1+.2*Math.sin(Math.PI*Math.min(1,x*1.7))),x);
}),14);
plume.rotateZ(-Math.PI/2);
// Running lights on the big hulls, by look: hull-local points (metres) that strobe.
const STROBES={
  carrier:[[19.3,1.6,4.6],[19.3,1.6,-4.6],[-18.9,1.6,6.6],[-18.9,1.6,-6.6],[-10.6,3.2,0]],
  freighter:[[12.2,2.2,0],[-12.8,1.6,4.2],[-12.8,1.6,-4.2]],
  station:[[21.4,2.2,0],[-21.4,2.2,0],[0,2.2,21.4],[0,2.2,-21.4]],
  citadel:Array.from({length:6},(_,i)=>{const [x,z]=radial(48.5,i*Math.PI/3);return [x,2.9,z];}),
  dreadnought:[[25.2,2.1,2.2],[25.2,2.1,-2.2],[10,3.7,8.8],[10,3.7,-8.8],[-30.6,1.9,6.6],[-30.6,1.9,-6.6],[-2.8,5.7,0]],
};
STROBES.transport=STROBES.freighter;

export function buildHull(hull,team,mats) {
  const key=`${look(hull)}:${team?1:0}`;
  let pool=pools.get(key);
  if (!pool) pools.set(key,pool=[]);
  let model=pool.pop();
  const material=slot=>mats[slot] ?? (slot==='scorch'?mats.machinery:undefined);
  if (model) {
    model.object.traverse(o=>{if(o.isMesh) o.material=material(o.userData.slot);});
    model.object.position.set(0,0,0);model.object.rotation.set(0,0,0);
    model.object.scale.set(1,1,1);model.object.visible=true;
    for (const t of model.thrusters) {t.level=0;t.node.visible=false;}
    for (const p of model.turrets) p.rotation.y=0;
    for (const kind of ['turret','bay']) model.hardpoints[kind].forEach((_,i)=>model.setHardpointDestroyed(kind,i,false));
    model._released=false;
    return model;
  }
  let kit=kits.get(key);
  if (!kit) kits.set(key,kit=createKit(hull,team));
  const object=new THREE.Group();object.name=`hull.${look(hull)}`;
  function meshes(parent,entries) {
    for (const [slot,g] of entries) {
      const m=new THREE.Mesh(g,material(slot));m.userData.slot=slot;
      // Lit trim (glow) throws no shadow; everything takes them (where the page casts any).
      m.castShadow=slot!=='glow';m.receiveShadow=true;parent.add(m);
    }
  }
  meshes(object,kit.body);
  const thrusters=hull.thrusters.map((t,i)=>{
    const node=new THREE.Group();node.name=t.id;
    node.position.set(...mountToLocal(t.pos));
    node.rotation.y=Math.atan2(-t.dir[1],-t.dir[0]);
    const flame=new THREE.Mesh(plume,mats.exhaust);
    flame.userData.slot='exhaust';
    flame.position.x=.055*t.size;
    // A thruster whose force pushes the ship forward is a main engine.
    const state={node,size:t.size,flame,level:0,main:t.dir[0]>.5};
    // The shared exhaust material takes this plume's throttle just before it is drawn.
    const seed=(i*7.31+hull.thrusters.length*1.7)%10;
    flame.onBeforeRender=(_renderer,_scene,_camera,_geometry,material)=>{
      const u=material.uniforms;
      if (!u || !u.level) return;
      u.level.value=state.level;u.seed.value=seed;material.uniformsNeedUpdate=true;
    };
    node.add(flame);object.add(node);node.visible=false;
    return state;
  });
  const muzzles=[];
  const hardpoints={turret:[],bay:[]};
  const turrets=hull.turrets.map(t=>{
    const gun=kit.turrets.get(t.weapon);
    const pivot=new THREE.Group();pivot.name=t.id;
    pivot.position.set(...mountToLocal(t.pos,t.height));
    meshes(pivot,gun.meshes);
    const muzzle=new THREE.Object3D();muzzle.name=`${t.id}.muzzle`;
    muzzle.position.set(gun.tip,gun.muzzleHeight,0);pivot.add(muzzle);muzzles.push(muzzle);
    object.add(pivot);
    // The stump replaces the gun where it stood, at its rest bearing (it no longer slews).
    let wreck=null;
    const stumpKit=kit.stumps.get(t.weapon);
    if (stumpKit) {
      wreck=new THREE.Group();wreck.name=`${t.id}.stump`;
      wreck.position.set(...mountToLocal(t.pos,t.height));
      wreck.rotation.y=(t.rest ?? 0)*Math.PI/180;
      meshes(wreck,stumpKit);wreck.visible=false;object.add(wreck);
    }
    hardpoints.turret.push({live:pivot,wreck,destroyed:false,size:turretBase(hull,t.weapon),
      local:new THREE.Vector3(...mountToLocal(t.pos,t.height+.4))});
    return pivot;
  });
  for (const bay of hull.bays ?? []) {
    const f=bayFrame(look(hull),hull,bay);
    const wreck=new THREE.Group();wreck.name=`${bay.id}.hole`;
    wreck.position.set(f.x,f.y,f.z);wreck.rotation.y=f.angle;
    meshes(wreck,kit.hole);wreck.visible=false;object.add(wreck);
    hardpoints.bay.push({live:null,wreck,destroyed:false,size:Math.max(...f.size)/2,
      local:new THREE.Vector3(f.x,f.y+.6,f.z)});
  }
  model={object,thrusters,turrets,muzzles,hardpoints,
    damagePoints:kit.damagePoints.map(p=>p.clone()),
    strobes:(STROBES[look(hull)] ?? []).map(p=>new THREE.Vector3(...p)),_released:false,
    /**
     * Show turret or bay `index` (the hull spec's order) destroyed or whole. A destroyed
     * turret becomes a scorched stump (its gun and muzzle hidden), a destroyed bay a
     * dark hole over its mouth. Returns whether anything changed; out-of-range indices
     * (a hull without that hardpoint) change nothing.
     */
    setHardpointDestroyed(kind,index,destroyed=true) {
      const h=hardpoints[kind]?.[index];
      if (!h || h.destroyed===destroyed) return false;
      h.destroyed=destroyed;
      // The barrel snaps where the gun last pointed.
      if (destroyed && h.live && h.wreck && kind==='turret') h.wreck.rotation.y=h.live.rotation.y;
      if (h.live) h.live.visible=!destroyed;
      if (h.wreck) h.wreck.visible=destroyed;
      return true;
    },
    /** Whether turret or bay `index` is shown destroyed. */
    hardpointDestroyed(kind,index) { return !!hardpoints[kind]?.[index]?.destroyed; },
    setThrottles(throttles,dt) {
      const k=1-Math.exp(-Math.max(0,dt)*24);
      for (let i=0;i<thrusters.length;i++) {
        const t=thrusters[i],target=Math.max(0,Math.min(1.4,throttles[i]||0)); // >1: boosted engine power
        t.level+=(target-t.level)*k;
        if (target===0 && t.level<.015) t.level=0;
        t.node.visible=t.level>.01;
        const s=t.size, v=t.level;
        // Half throttle is a short, narrow jet; full is over twice as long.
        t.flame.scale.set(s*(.3+7*v),s*(.55+.5*v),s*(.55+.5*v));
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
