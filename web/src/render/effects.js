// Shared combat effects. Fixed-capacity CPU pools feed bounded instanced draws;
// no textures, lights, post-processing dependencies, or per-frame object creation.
//
// Coordinates: every event takes sim metres (x, y; +y is the sim's "up", drawn at
// three.js z = -y) and headings in radians CCW from +x, as the sim reports them.
// Teams are 0 / 1; -1 is neutral (white) where noted. Pools are fixed: past capacity
// the oldest entry is reused, so nothing grows and nothing throws.
//
// const fx = createEffects({ THREE, scene, renderer, palette });
// Per frame:
//   fx.updateProjectiles(projectiles, beams, alpha)  shots in flight (current tick)
//   fx.update(dt)                                     ages and draws everything else
// fx.drawOrders(orders) sets the commander overlay; it is drawn every frame until the
// next call (pass [] to clear). The array is read, never copied or changed.
// Fire-and-forget events:
//   fx.muzzle({x, y, angle, team, weapon})
//   fx.hit({x, y, team})                     team = shooter (-1: neutral)
//   fx.shieldHit({x, y, nx, ny, team, depleted, radius})  team = shooter
//   fx.explosion({x, y, radius, team, kind})  kind 'death' | 'flak' | 'collision'
//   fx.arrival({x, y, heading, team, size, duration})  jump-in streak; size = hull length
//   fx.bayLaunch({x, y, heading, team, size, speed})   ship leaving a carrier bay: x, y is
//       the bay mouth, heading/speed the launch velocity (m/s), size the launched hull's
//       length. A flash at the mouth, an afterglow inside the bay and a short trail that
//       follows the ship out for 0.6 s (it assumes the launch's straight, locked coast).
//   fx.jumpCharge({object, team, size, duration}) -> {cancel()}  a transport spooling
//       its jump drive: contracting rings, a growing core glow, inward sparks and, at the
//       end, a forward aperture line. It follows `object` (the hull's THREE.Object3D, so
//       a moving ship carries it); pass {x, y, heading} instead for a fixed spot.
//       duration defaults to 2 s; it stops at completion so it cannot follow the jumping
//       hull. Call cancel() to fade it out early (ship destroyed).
//   fx.jumpOut({x, y, heading, team, size})  the departure: a flash and a collapse at
//       the ship, then a streak whose tail clears the origin as it fades. Move the
//       hull model with jumpOutOffset() (below) and hide it after JUMP_OUT_DURATION.
//   fx.jumpOutQuick({x, y, heading, team, size})  the cheap variant (no charge, no ring,
//       thinner streak) for a whole wing leaving at the end of a match; stagger the calls.
//   fx.attachDamage(model) -> {update(hpFraction, visible, dt), dispose()}
//
// drawOrders(orders): each order is {kind, team, x2, y2, radius?, x1?, y1?, progress?}.
//   kind 'attack' | 'guard' | 'hold' | 'jump'. With x1, y1 a faint dashed line crawls
//   from the squad (x1, y1) toward the target (x2, y2) and stops at its marker:
//   attack = four corner brackets, guard = a thin ring round the ward, hold = a ring
//   with inward ticks, jump = a slowly turning dashed ring with a brighter arc for
//   `progress` (0..1, e.g. the escort's hold time). radius is the marker's (metres).
export const JUMP_OUT_DISTANCE = 900;
export const JUMP_OUT_DURATION = 0.09;
const JUMP_OUT_TAIL = 0.16, QUICK_OUT_TAIL = 0.10;
/** Metres a departing hull has moved forward `age` seconds into jumpOut (ease-in). */
export function jumpOutOffset(age, duration = JUMP_OUT_DURATION) {
  const t = Math.max(0, Math.min(1, age / duration));
  return JUMP_OUT_DISTANCE * t * t * t;
}

export function createEffects({ THREE: T, scene, renderer, palette }) {
  const team = palette.team.map(c => new T.Color(c));
  const shot = palette.projectile.map(c => new T.Color(c));
  const pellet = shot.map(c => c.clone().lerp(new T.Color(0xffad63), .48));
  const shield = palette.shield.map(c => new T.Color(c));
  const white = new T.Color(0xfff5df), warmWhite = new T.Color(0xffd9a8), amber = new T.Color(palette.exhaust);
  const fireColor = new T.Color(0xff6514);
  const smokeColor = new T.Color(0x887b6b), shell = new T.Color(0x26333c);
  const transform = new T.Object3D(), point = new T.Vector3(), end = new T.Vector3();
  const resources = [];
  function batch(geo, cap, billboard = false, smoke = false, additive = true, flame = false, trace = 0) {
    const rgba = new T.InstancedBufferAttribute(new Float32Array(cap * 4), 4).setUsage(T.DynamicDrawUsage);
    geo.setAttribute('tint', rgba);
    const mat = new T.ShaderMaterial({
      uniforms: { viewportHeight: { value: 720 } },
      transparent: true, depthWrite: false, side: T.DoubleSide,
      blending: additive ? T.AdditiveBlending : T.NormalBlending,
      vertexShader: `uniform float viewportHeight; attribute vec4 tint; varying vec4 vTint; varying vec2 vUv;
        void main(){ vTint=tint; vUv=uv;
        ${trace ? `vec4 center=modelViewMatrix*instanceMatrix*vec4(0.,0.,0.,1.);
        vec3 axis=(modelViewMatrix*vec4(instanceMatrix[0].xyz,0.)).xyz;
        vec2 along=axis.xy/max(length(axis.xy),.0001);
        vec2 across=vec2(-along.y,along.x);
        float width=length(instanceMatrix[1].xyz);
        float pixelWorld=2.*max(1.,-center.z)/(projectionMatrix[1][1]*viewportHeight);
        width=max(width,pixelWorld*${trace === 1 ? '2.8' : '.95'});
        center.xy+=axis.xy*position.x+across*position.y*width;
        gl_Position=projectionMatrix*center;` : billboard ? `vec4 center=modelViewMatrix*instanceMatrix*vec4(0.,0.,0.,1.);
        vec2 size=vec2(length(instanceMatrix[0].xyz),length(instanceMatrix[1].xyz));
        center.xy+=position.xy*size; gl_Position=projectionMatrix*center;` :
        'gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.);'} }`,
      fragmentShader: `varying vec4 vTint; varying vec2 vUv;
        void main(){float a=vTint.a;
        ${trace ? `float crossSection=abs(vUv.y*2.-1.);
          ${trace === 1 ? `float taper=mix(.08,1.,vUv.x);
          a*=exp(-4.*crossSection*crossSection/(taper*taper))*pow(vUv.x,.7);
          a*=smoothstep(0.,.12,vUv.x)*smoothstep(1.,.83,vUv.x);` :
          `a*=exp(-5.*crossSection*crossSection)*smoothstep(0.,.14,vUv.x)*smoothstep(1.,.86,vUv.x);`}` : ''}
        ${billboard ? `vec2 p=vUv*2.-1.; float r=dot(p,p);
          ${smoke ? `float cloud=0.78+0.12*sin(p.x*13.+sin(p.y*9.))+0.10*cos(p.y*17.+p.x*6.);
          a*=smoothstep(1.,0.1,r)*cloud;` : 'a*=max(0.,exp(-r*5.)-0.0067);'}
          ${flame ? `float taper=max(.16,.62-p.y*.40);
          a*=smoothstep(1.,.05,abs(p.x)/taper);
          a*=smoothstep(-1.,-.5,p.y)*smoothstep(1.,.35,p.y);` : ''}
          if(r>1.) discard;` : ''}
        gl_FragColor=vec4(vTint.rgb,a);
        ${trace ? '' : '#include <tonemapping_fragment>'}
        #include <colorspace_fragment>
        }`,
    });
    const mesh = new T.InstancedMesh(geo, mat, cap);
    mesh.instanceMatrix.setUsage(T.DynamicDrawUsage); mesh.frustumCulled = false; mesh.count = 0;
    mesh.renderOrder = smoke ? 1 : 2; scene.add(mesh);
    const b = { mesh, rgba, n: 0, cap };
    resources.push(b); return b;
  }
  const glow = batch(new T.PlaneGeometry(1, 1), 1400, true);
  const flames = batch(new T.PlaneGeometry(1, 1), 512, true, false, true, true);
  const smoke = batch(new T.PlaneGeometry(1, 1), 1200, true, true, false);
  const chips = batch(new T.IcosahedronGeometry(1, 0), 256, false, false, false);
  const ringGeo = new T.RingGeometry(.89, 1, 48, 1, 0, Math.PI * 1.86);
  ringGeo.rotateX(-Math.PI / 2);
  const rings = batch(ringGeo, 160);
  // A curved sliver on the actual shield radius, oriented toward the hit normal.
  const arcGeo = new T.RingGeometry(.92, 1, 28, 1, -.62, 1.24);
  arcGeo.rotateX(-Math.PI / 2);
  const ripples = batch(arcGeo, 160);
  // Closed hairline rings for the jump drive: energy, not a HUD arc with a gap.
  const thinGeo = new T.RingGeometry(.978, 1, 64, 1);
  thinGeo.rotateX(-Math.PI / 2);
  const thin = batch(thinGeo, 128);
  // Velocity-aligned ribbons expand across the view, so they cannot turn edge-on.
  // Soft analytic profiles replace solid box faces; both layers remain additive.
  const tracers = batch(new T.PlaneGeometry(1, 1), 1200, false, false, true, false, 1);
  const cores = batch(new T.PlaneGeometry(1, 1), 1200, false, false, true, false, 2);
  const bolts = batch(new T.BoxGeometry(1, 1, 1), 512);
  // Launch trails (tapered, like tracers) and the commander overlay's hairlines; both
  // keep a minimum pixel width, so they read on a phone at any zoom.
  const trails = batch(new T.PlaneGeometry(1, 1), 256, false, false, true, false, 1);
  const lines = batch(new T.PlaneGeometry(1, 1), 1024, false, false, true, false, 2);

  function put(b, x, y, z, sx, sy, sz, angle, c, opacity, tumble = 0) {
    if (b.n >= b.cap) return;
    const i = b.n++;
    transform.position.set(x, y, z); transform.rotation.set(tumble, angle, tumble * .73);
    transform.scale.set(sx, sy, sz); transform.updateMatrix(); b.mesh.setMatrixAt(i, transform.matrix);
    const j = i * 4, a = b.rgba.array;
    a[j] = c.r; a[j+1] = c.g; a[j+2] = c.b; a[j+3] = opacity;
  }
  function finish(b) {
    b.mesh.count = b.n;
    if (b.n) { b.mesh.instanceMatrix.needsUpdate = true; b.rgba.needsUpdate = true; }
  }
  function segment(b, x, y, z, ex, ey, ez, width, c, opacity) {
    // All weapon traces lie in the battle plane; electric bolts use slight height offsets.
    const dx = ex-x, dz = ez-z;
    put(b, (x+ex)*.5, (y+ey)*.5, (z+ez)*.5, Math.hypot(dx,dz), width, width,
      Math.atan2(-dz,dx), c, opacity);
  }
  const particles = Array.from({ length: 3200 }, () => ({ life: 0, max: 1, x: 0, y: 0, z: 0,
    vx: 0, vy: 0, vz: 0, size: 1, kind: 0, color: white, angle: 0 }));
  const waves = Array.from({ length: 160 }, () => ({ life: 0, max: 1, x: 0, z: 0,
    radius: 1, angle: 0, color: white, kind: 0 }));
  // Arrivals and departures share one pool (`out` marks a departure).
  const jumps = Array.from({ length: 48 }, () => ({ life: 0, max: 1, x: 0, z: 0,
    angle: 0, size: 1, color: white, landed: false, out: false, quick: false }));
  const launches = Array.from({ length: 24 }, () => ({ life: 0, max: 1, x: 0, z: 0,
    dx: 1, dz: 0, speed: 0, size: 1, color: white }));
  const charges = Array.from({ length: 16 }, () => ({ active: false, age: 0, duration: 2,
    object: null, x: 0, z: 0, heading: 0, size: 1, color: white, fade: 1, cancelled: false,
    phase: 0, sparkClock: 0, gen: 0 }));
  let pc = 0, wc = 0, jc = 0, lc = 0, cc = 0, clock = 0, orders = [];
  // kind: glow, smoke, shell fragment, spark, tapered flame.
  function particle(x, y, z, size, life, color, kind = 0, vx = 0, vy = 0, vz = 0) {
    const p = particles[pc++]; if (pc === particles.length) pc = 0;
    p.x=x; p.y=y; p.z=z; p.size=size; p.life=p.max=life; p.color=color; p.kind=kind;
    p.vx=vx; p.vy=vy; p.vz=vz; p.angle=Math.random()*6.283;
  }
  function wave(x, z, radius, life, color, kind=0, angle=0) {
    const p=waves[wc++]; if(wc===waves.length)wc=0;
    p.model=null; p.x=x; p.z=z; p.radius=radius; p.life=p.max=life; p.color=color; p.kind=kind; p.angle=angle;
  }
  function sparks(x, z, n, radius, color) {
    for(let j=0;j<n;j++) {
      const a=j*2.399+Math.random()*.35, speed=radius*(1+Math.random());
      particle(x,1.6,z,Math.max(.9,radius*.08)+Math.random()*.7,.25+Math.random()*.35,color,3,
        Math.cos(a)*speed,2+Math.random()*4,Math.sin(a)*speed);
    }
  }
  function explosion(e) {
    const death=e.kind==='death', r=e.radius, c=(death?team:pellet)[e.team] || white;
    particle(e.x,1.5,-e.y,r*(death?4:1.8),death?1.05:.3,c);
    particle(e.x,2,-e.y,r*1.5,death?.28:.14,white);
    wave(e.x,-e.y,r,death?1.1:.38,death?c:white);
    if (death) {
      // Abyssal's five dark shell shards, golden-angle spread and rising tumble.
      for(let j=0;j<5;j++) {
        const a=j*2.399, speed=r*(.4+j*.14);
        particle(e.x,1.3,-e.y,r*.12,1.1+Math.random()*.35,j%2?shell:smokeColor,2,
          Math.cos(a)*speed,r*.26,Math.sin(a)*speed);
      }
      for(let j=0;j<8;j++) {
        const a=j*2.399, d=r*.3*Math.random();
        particle(e.x+Math.cos(a)*d,1,-e.y+Math.sin(a)*d,r*(.42+Math.random()*.3),
          1.6+Math.random(),smokeColor,1,Math.cos(a)*r*.15,2,Math.sin(a)*r*.15);
      }
    }
    sparks(e.x,-e.y,death?16:5,r*.9,death?c:white);
  }
  function depart(e, quick) {
    const p=jumps[jc++]; if(jc===jumps.length)jc=0;
    const c=team[e.team] || white, size=e.size || 10;
    p.x=e.x; p.z=-e.y; p.size=size; p.angle=e.heading; p.color=c;
    p.max=JUMP_OUT_DURATION; p.life=p.max+(quick?QUICK_OUT_TAIL:JUMP_OUT_TAIL); p.out=true; p.quick=quick; p.landed=false;
    // The drive lets go: a hot flash where the ship was, and (full jump) a collapse ring.
    particle(p.x,2,p.z,size*(quick?.5:1.45),quick?.12:.24,c);
    particle(p.x,2.2,p.z,size*(quick?.24:.6),quick?.055:.11,quick?warmWhite:white);
    if(!quick) { wave(p.x,p.z,size*.72,.26,c,4); sparks(p.x,p.z,8,size*.5,c); }
  }
  // Hairline arc of `radius` round (x, z) from angle a0 to a1 (radians, three.js plane).
  function arc(x, z, radius, a0, a1, c, opacity, steps) {
    const n=Math.max(1,steps|0), da=(a1-a0)/n, closed=Math.abs(a1-a0)>=TAU-.0001;
    // Trace ends fade; a small overlap keeps adjoining pieces from looking dotted.
    for(let i=0;i<n;i++) {
      const u=a0+i*da-(i || closed?da*.1:0), v=a0+(i+1)*da+(i<n-1 || closed?da*.1:0);
      segment(lines,x+Math.cos(u)*radius,1.2,z+Math.sin(u)*radius,x+Math.cos(v)*radius,1.2,z+Math.sin(v)*radius,.5,c,opacity);
    }
  }
  const TAU=Math.PI*2;
  function order(o) {
    const c=team[o.team] || white, x=o.x2, z=-o.y2, r=o.radius ?? (o.kind==='attack'?10:o.kind==='guard'?24:40);
    if(o.x1!==undefined && o.y1!==undefined) {
      const sx=o.x1, sz=-o.y1, dx=x-sx, dz=z-sz, d=Math.hypot(dx,dz);
      const from=8, to=d-r-3;
      if(to>from) {
        const ux=dx/d, uz=dz/d;
        // Dashes crawl toward the target, so the line says which way the order points.
        let dash=7, gap=6;
        if((to-from)/(dash+gap)>60) { const k=(to-from)/(60*(dash+gap)); dash*=k; gap*=k; }
        const period=dash+gap;
        for(let s=from-period+(clock*14)%period;s<to;s+=period) {
          const a=Math.max(from,s), b=Math.min(to,s+dash);
          if(b<=a) continue;
          // Fade in from the squad and out at the marker.
          const m=(a+b)*.5, fade=Math.min(1,(m-from)/30)*Math.min(1,(to-m)/20+.35);
          segment(lines,sx+ux*a,1.2,sz+uz*a,sx+ux*b,1.2,sz+uz*b,.5,c,.22*fade);
        }
      }
    }
    if(o.kind==='attack') {
      // Corner brackets: four short arcs at the diagonals.
      for(let i=0;i<4;i++) { const a=Math.PI/4+i*Math.PI/2; arc(x,z,r,a-.32,a+.32,c,.6,4); }
    } else if(o.kind==='guard') {
      arc(x,z,r,0,TAU,c,.38,40);
    } else if(o.kind==='hold') {
      arc(x,z,r,0,TAU,c,.4,48);
      for(let i=0;i<4;i++) {
        const a=i*Math.PI/2+Math.PI/4, ca=Math.cos(a), sa=Math.sin(a);
        segment(lines,x+ca*r,1.2,z+sa*r,x+ca*r*.84,1.2,z+sa*r*.84,.5,c,.5);
      }
    } else if(o.kind==='jump') {
      // Dashed outer ring turns slowly; the progress arc runs clockwise from the top.
      const spin=clock*.12;
      for(let i=0;i<24;i++) { const a=spin+i*TAU/24; arc(x,z,r,a,a+TAU/48,c,.4,2); }
      const progress=Math.max(0,Math.min(1,o.progress ?? 0));
      if(progress>0) arc(x,z,r*.9,-Math.PI/2,-Math.PI/2+progress*TAU,white,.72,Math.ceil(48*progress));
      arc(x,z,r*.9,0,TAU,c,.08,36);
    }
  }
  // The mirror of an arrival's streak: it grows forward from where the ship was as the
  // hull accelerates away (jumpOutOffset), then its rear end immediately chases the
  // front off the screen. A lingering line at the origin reads as a weapon beam.
  function departure(p) {
    const total=p.max+(p.quick?QUICK_OUT_TAIL:JUMP_OUT_TAIL), age=total-p.life, travel=Math.min(1,age/p.max);
    const dx=Math.cos(p.angle), dz=-Math.sin(p.angle);
    const front=JUMP_OUT_DISTANCE*travel**3;
    let start=0, fade=1;
    if(travel===1) { const after=(age-p.max)/(total-p.max); fade=Math.max(0,1-after)**1.5; start=front*(p.quick?Math.sqrt(after):after); }
    if(front-start<1) return;
    // Soft, tapered profiles (not the arrival's boxes): a box as wide as a 26 m hull
    // read as a solid beam. Narrow where the ship was, full width far ahead.
    const w=p.quick?.16:.28, core=Math.max(p.quick?.6:.9,p.size*(p.quick?.035:.045));
    segment(trails,p.x+dx*start,1.4,p.z+dz*start,p.x+dx*front,1.4,p.z+dz*front,p.size*w,p.color,(p.quick?.65:.9)*fade);
    segment(lines,p.x+dx*start,1.5,p.z+dz*start,p.x+dx*front,1.5,p.z+dz*front,core,p.quick?warmWhite:white,(p.quick?.6:.85)*fade);
  }
  function updateLaunches() {
    for(const p of launches) {
      if(p.life<=0) continue;
      const age=p.max-p.life, head=p.speed*age, fade=(p.life/p.max)**.85;
      // A short jet straddles the mouth immediately, even before the tail has cleared.
      // It then follows the tail, capped at 2.2 hulls, through the locked launch coast.
      const end=Math.max(p.size*.3,head-p.size*.42), start=Math.max(-p.size*.2,end-p.size*2.2);
      if(end-start<.5) continue;
      segment(trails,p.x+p.dx*start,2.4,p.z+p.dz*start,p.x+p.dx*end,2.4,p.z+p.dz*end,p.size*.3,p.color,.8*fade);
      segment(lines,p.x+p.dx*(start+end)*.5,2.45,p.z+p.dz*(start+end)*.5,p.x+p.dx*end,2.45,p.z+p.dz*end,.75,white,.65*fade);
    }
  }
  function updateCharges(dt) {
    for(const c of charges) {
      if(!c.active) continue;
      c.age+=dt;
      // Only the departure owns the jump movement and flash after charge completion.
      if(!c.cancelled && c.age>=c.duration) { c.active=false; c.object=null; continue; }
      if(c.object) {
        point.setFromMatrixPosition(c.object.matrixWorld); c.x=point.x; c.z=point.z; c.heading=c.object.rotation.y;
      }
      if(c.cancelled) c.fade-=dt*6;
      if(c.fade<=0) { c.active=false; c.object=null; continue; }
      const k=Math.min(1,c.age/c.duration), e=k*k, f=c.fade, s=c.size;
      c.phase+=dt*(.55+2.2*k);
      // Two hairline rings contract onto the hull out of step (unequal phase, unequal
      // brightness), so they read as the drive's field rather than a target reticle.
      for(let i=0;i<2;i++) {
        const u=(c.phase+i*.37)%1, r=s*(.76-.42*u)*(1-.12*e);
        put(thin,c.x,1.3,c.z,r,1,r,0,c.color,f*(.24+.46*e)*Math.sin(Math.PI*u)*(i?.5:1));
      }
      // A broad, low field reads on a phone; only the last 0.3 s gets a hot core.
      put(glow,c.x,2.6,c.z,s*(.45+.35*e),s*(.45+.35*e),1,0,c.color,f*(.1+.32*e));
      const late=Math.max(0,Math.min(1,(c.age-(c.duration-.3))/.3));
      const flare=late*late*(3-2*late);
      if(late>0) {
        put(glow,c.x,2.7,c.z,s*(.65+.45*flare),s*(.65+.45*flare),1,0,c.color,f*.75*flare);
        put(glow,c.x,2.8,c.z,s*.32*flare,s*.32*flare,1,0,white,f*.8*flare*flare);
      }
      c.sparkClock+=dt*(5+23*k);
      while(c.sparkClock>=1) {
        c.sparkClock--;
        const a=Math.random()*TAU, r=s*(.8+Math.random()*.3), life=.24+Math.random()*.1;
        particle(c.x+Math.cos(a)*r,1.6,c.z+Math.sin(a)*r,1+Math.random()*.6,life,Math.random()<.2?white:c.color,3,
          -Math.cos(a)*r/life*.85,0,-Math.sin(a)*r/life*.85);
      }
      // The last 0.25 s: a short aperture line opens ahead, along the coming streak.
      const open=Math.max(0,Math.min(1,(c.age-(c.duration-.25))/.25));
      if(open>0) {
        const dx=Math.cos(c.heading), dz=-Math.sin(c.heading), reach=s*(.55+.85*open*open);
        segment(trails,c.x+dx*s*.5,1.55,c.z+dz*s*.5,c.x+dx*reach,1.55,c.z+dz*reach,s*.1,c.color,f*open*.35);
        segment(lines,c.x+dx*s*.55,1.6,c.z+dz*s*.55,c.x+dx*reach,1.6,c.z+dz*reach,.65,white,f*open*.65);
      }
    }
  }
  return {
    updateProjectiles(projectiles, beams, alpha) {
      tracers.n=cores.n=0;
      // CSS pixels keep the minimum width stable at phone DPR 1–2 and desktop.
      const height=Math.max(1,renderer.domElement.clientHeight || renderer.domElement.height);
      tracers.mesh.material.uniforms.viewportHeight.value=height;
      cores.mesh.material.uniforms.viewportHeight.value=height;
      for(let i=0;i<Math.min(projectiles.length,1024);i++) {
        const p=projectiles[i], flak=p.kind==='flak';
        const c=(flak?pellet:shot)[p.team] || white, a=Math.atan2(p.vy,p.vx);
        const x=p.x+p.vx*alpha/30, z=-p.y-p.vy*alpha/30;
        if(p.kind==='torpedo') {
          // Slow, fat and smoking, so a torpedo run reads as different from gunfire.
          const dx=Math.cos(a), dz=-Math.sin(a);
          put(tracers,x-dx*7,1.4,z-dz*7,16,3.2,1,a,pellet[p.team] || white,.5);
          put(cores,x,1.4,z,4.2,1.1,1,a,white,1);
          if(Math.random()<.35) particle(x-dx*3,1.2,z-dz*3,2.4,.9,smokeColor,1,0,1.5,0);
          continue;
        }
        const len=flak?3.2:6.5, dx=Math.cos(a), dz=-Math.sin(a);
        put(tracers,x-dx*len*.43,1.4,z-dz*len*.43,len,flak?.75:1.25,1,a,c,flak?.32:.62);
        put(cores,x,1.4,z,flak?1.1:2.2,flak?.22:.3,1,a,flak?c:white,flak?.72:1);
      }
      for(let i=0;i<Math.min(beams.length,128);i++) {
        const b=beams[i], c=shot[b.team] || white, fade=Math.min(1,(b.ttl ?? .06)/.035);
        segment(tracers,b.x1,1.6,-b.y1,b.x2,1.6,-b.y2,1.25,c,.42*fade);
        segment(cores,b.x1,1.6,-b.y1,b.x2,1.6,-b.y2,.22,white,.95*fade);
      }
      finish(tracers);finish(cores);
    },
    muzzle(e) {
      const c=shot[e.team] || white, dx=Math.cos(e.angle), dz=-Math.sin(e.angle);
      particle(e.x,1.5,-e.y,e.weapon==='flak'?5:3.8,.085,c);
      particle(e.x+dx,1.5,-e.y+dz,2,.055,white);
    },
    hit(e) {
      particle(e.x,1.5,-e.y,6,.18,shot[e.team] || white);
      particle(e.x,1.8,-e.y,2.5,.08,white);
      sparks(e.x,-e.y,5,12,amber);
      particle(e.x,1.2,-e.y,2,.7,smokeColor,1,0,2,0);
    },
    shieldHit(e) {
      // The event team is the shooter; the defending shield belongs to the other team.
      const c=shield[e.team===0?1:0] || white, a=Math.atan2(e.ny,e.nx), r=e.radius;
      const cx=e.x-e.nx*r, cz=-e.y+e.ny*r;
      wave(cx,cz,r,.55,c,1,a);
      particle(e.x,1.8,-e.y,Math.max(9,r*.65),.25,c);
      particle(e.x,2,-e.y,4,.12,white);
      if(e.depleted) {
        wave(cx,cz,r,.6,c,2,a);
        particle(cx,1,cz,r*2.4,.22,c);
        sparks(cx,cz,12,r,c);
      }
    },
    explosion,
    arrival(e) {
      const p=jumps[jc++]; if(jc===jumps.length)jc=0;
      p.x=e.x; p.z=-e.y; p.size=e.size; p.angle=e.heading;
      p.max=Math.max(.03,e.duration); p.life=p.max+.7;
      p.color=team[e.team] || white; p.landed=false; p.out=false; p.quick=false;
    },
    bayLaunch(e) {
      const c=team[e.team] || white, size=e.size || 10, dx=Math.cos(e.heading), dz=-Math.sin(e.heading);
      const p=launches[lc++]; if(lc===launches.length)lc=0;
      p.x=e.x; p.z=-e.y; p.dx=dx; p.dz=dz; p.speed=e.speed ?? 60; p.size=size;
      p.life=p.max=.6; p.color=c;
      // A tight catapult flash at the mouth, and an afterglow back inside the bay well.
      particle(p.x,2.4,p.z,size*1.45,.2,c);
      particle(p.x,2.5,p.z,size*.65,.12,white);
      particle(p.x-dx*size*.55,.6,p.z-dz*size*.55,size*1.1,.32,c);
      for(let j=0;j<4;j++) {
        const a=e.heading+(Math.random()-.5)*.5, v=p.speed*(.6+Math.random()*.25);
        particle(p.x,1.4,p.z,.8+Math.random()*.6,.12+Math.random()*.12,j%2?white:c,3,
          Math.cos(a)*v,1+Math.random()*2,-Math.sin(a)*v);
      }
    },
    jumpCharge(e) {
      const c=charges[cc++]; if(cc===charges.length)cc=0;
      c.active=true; c.age=0; c.duration=Math.max(.2,e.duration ?? 2); c.object=e.object || null;
      c.x=e.x ?? 0; c.z=-(e.y ?? 0); c.heading=e.heading ?? 0; c.size=e.size || 20;
      c.color=team[e.team] || white; c.fade=1; c.cancelled=false; c.phase=0; c.sparkClock=0;
      // A handle outliving its pooled slot must not cancel the slot's next charge.
      const gen=++c.gen;
      return { cancel() { if(c.active && c.gen===gen) c.cancelled=true; } };
    },
    jumpOut(e) { depart(e,false); },
    jumpOutQuick(e) { depart(e,true); },
    drawOrders(list) { orders=list || []; },
    attachDamage(model) {
      let smokeClock=0, fireClock=0, arcClock=0, index=0, disposed=false;
      const points=model.damagePoints || [];
      // Damage mounts span the hull: derive a scale once, without geometry traversal.
      let extent=0;
      for(const p of points) extent=Math.max(extent,Math.abs(p.x),Math.abs(p.z));
      // Small craft stay unchanged; large hulls burn at local vent scale, not hull scale.
      // Even square-root growth engulfed the freighter's cargo and command cab.
      const scale=Math.max(.85,Math.min(1.8,extent/3));
      const electric=new T.Color(0x99ddff);
      return {
        update(hp, alive, dt) {
          if(disposed || !alive || hp>=.7 || !points.length) {
            smokeClock=fireClock=arcClock=0; return;
          }
          dt=Math.min(dt,.1);
          smokeClock+=dt*(hp<.4?14:9);
          // The matrix is read at emission only. Detached particles never follow the hull.
          while(smokeClock>=1) {
            smokeClock--; point.copy(points[index++%points.length]).applyMatrix4(model.object.matrixWorld);
            particle(point.x,point.y+.3,point.z,(3.2+Math.random()*1.6)*scale,1.8+Math.random()*.8,smokeColor,5,
              (Math.random()-.5)*2,2.2,(Math.random()-.5)*2);
          }
          if(hp<.4) {
            fireClock+=dt*30;
            while(fireClock>=1) {
              fireClock--; point.copy(points[index++%Math.min(3,points.length)]).applyMatrix4(model.object.matrixWorld);
              particle(point.x,point.y+.4,point.z,(5+Math.random()*4)*scale,.3+Math.random()*.25,fireColor,4,
                (Math.random()-.5)*3,9*scale,(Math.random()-.5)*3);
              particle(point.x,point.y+.5,point.z,3*scale,.16,white);
            }
          }
          if(hp<.2) {
            arcClock+=dt;
            if(arcClock>.18) {
              arcClock%=.18;
              point.copy(points[index++%points.length]).applyMatrix4(model.object.matrixWorld);
              end.copy(points[index%points.length]).applyMatrix4(model.object.matrixWorld);
              // Short-lived jagged electrical filaments, cached in the same bounded wave pool.
              const w=waves[wc++]; if(wc===waves.length)wc=0;
              w.x=point.x;w.z=point.z;w.y=point.y+.6;w.ex=end.x;w.ez=end.z;w.ey=end.y+.6;
              w.model=model;w.from=(index-1)%points.length;w.to=index%points.length;
              w.life=w.max=.14;w.kind=3;w.color=electric;w.width=.65*scale;w.angle=Math.random()*6.28;
              if(Math.random()<.35) sparks(point.x,point.z,6,12*scale,electric);
            }
          }
        },
        dispose() { disposed=true; },
      };
    },
    update(dt) {
      dt=Math.max(0,Math.min(dt,.1));
      glow.n=flames.n=smoke.n=chips.n=rings.n=ripples.n=bolts.n=trails.n=lines.n=thin.n=0;
      clock+=dt;
      const height=Math.max(1,renderer.domElement.clientHeight || renderer.domElement.height);
      trails.mesh.material.uniforms.viewportHeight.value=height;
      lines.mesh.material.uniforms.viewportHeight.value=height;
      for(const o of orders) order(o);
      for(const p of launches) if(p.life>0) p.life-=dt;
      updateLaunches();
      // Charges run before the particle pass so their sparks are drawn this frame.
      updateCharges(dt);
      for(const p of particles) {
        if(p.life<=0)continue;
        p.life-=dt; if(p.life<=0)continue;
        const t=1-p.life/p.max, fade=1-t;
        p.x+=p.vx*dt;p.y+=p.vy*dt;p.z+=p.vz*dt;
        if(p.kind===1) {
          const size=p.size*(1+t*2.3);
          put(smoke,p.x,p.y,p.z,size,size,1,0,p.color,.7*Math.min(1,(1-t)*4));
        } else if(p.kind===5) {
          // Damage trail: faint over the hull so a slow ship stays visible, fuller once it has drifted off.
          const size=p.size*(1+t*2.6);
          put(smoke,p.x,p.y,p.z,size,size,1,0,p.color,.38*(.25+.75*Math.min(1,t*4))*Math.min(1,(1-t)*3));
        } else if(p.kind===2) {
          p.vy-=dt*7;
          const size=p.size*(1-t*.65);
          put(chips,p.x,p.y,p.z,size,size*.4,size*.7,p.angle+t*3,p.color,fade,t*4+p.angle);
        } else {
          const size=p.size*(p.kind===4?(1-t*.65)*(1+.18*Math.sin(t*35+p.angle)):p.kind===3?1-t*.65:1+t*.7);
          put(p.kind===4?flames:glow,p.x,p.y,p.z,size,size*(p.kind===4?1.8:1),1,0,p.color,fade*fade*(p.kind===3?1:.9));
        }
      }
      for(const w of waves) {
        if(w.life<=0)continue;
        w.life-=dt;if(w.life<=0)continue;
        const t=1-w.life/w.max, fade=1-t;
        if(w.kind===3) {
          // Keep the crawling filament on a moving hull; only smoke/fire detach.
          point.copy(w.model.damagePoints[w.from]).applyMatrix4(w.model.object.matrixWorld);
          end.copy(w.model.damagePoints[w.to]).applyMatrix4(w.model.object.matrixWorld);
          w.x=point.x;w.y=point.y+.6;w.z=point.z;
          w.ex=end.x;w.ey=end.y+.6;w.ez=end.z;
          let x=w.x,y=w.y,z=w.z;
          for(let j=1;j<=5;j++) {
            const f=j/5, jitter=j===5?0:Math.sin(j*17+w.angle+t*12)*w.width*1.5;
            const ex=w.x+(w.ex-w.x)*f+jitter, ez=w.z+(w.ez-w.z)*f-jitter;
            const ey=w.y+(w.ey-w.y)*f+Math.sin(f*Math.PI);
            segment(bolts,x,y,z,ex,ey,ez,w.width*2.8,w.color,fade*.3);
            segment(bolts,x,y,z,ex,ey,ez,w.width,white,fade);x=ex;y=ey;z=ez;
          }
        } else if(w.kind===1) {
          // Concentric wave fronts spread tangentially over just the struck shield sector.
          for(let j=0;j<2;j++) {
            const r=w.radius*(1+t*.18-j*.10);
            put(ripples,w.x,1.1+j*.15,w.z,r,1,r,w.angle,j?white:w.color,fade*fade*(j?.65:1));
          }
        } else if(w.kind===4) {
          const r=w.radius*(1-.92*t*t*(3-2*t));
          put(thin,w.x,1.3,w.z,r,1,r,0,w.color,fade**1.5*.75);
        } else {
          const r=w.radius*(w.kind===2?1-t*.55:.15+t);
          put(rings,w.x,1.1,w.z,r,1,r,w.angle+t*.7,w.color,fade*(w.kind===2?.9:.6));
        }
      }
      for(const p of jumps) {
        if(p.life<=0)continue;
        p.life-=dt;if(p.life<=0)continue;
        if(p.out) { departure(p); continue; }
        const age=p.max+.7-p.life, travel=Math.min(1,age/p.max);
        const dx=Math.cos(p.angle), dz=-Math.sin(p.angle);
        const back=900*(1-travel)**3;
        const tail=travel<1?Math.min(900-back,430):350*Math.max(0,1-(age-p.max)/.38);
        const x=p.x-dx*back,z=p.z-dz*back, fade=travel<1?1:Math.max(0,1-(age-p.max)/.38);
        segment(bolts,x-dx*tail,1.4,z-dz*tail,x,1.4,z,p.size*.65,p.color,.42*fade);
        segment(bolts,x-dx*tail*.85,1.5,z-dz*tail*.85,x,1.5,z,Math.max(1.8,p.size*.1),white,fade);
        if(travel===1 && !p.landed) {
          p.landed=true;particle(p.x,2,p.z,p.size*5,.38,p.color);
          particle(p.x,2,p.z,p.size*2,.18,white);
        }
      }
      finish(glow);finish(flames);finish(smoke);finish(chips);finish(rings);finish(ripples);finish(bolts);
      finish(trails);finish(lines);finish(thin);
    },
    // Optional lifecycle hook for embeds; normal harness keeps one Effects for its lifetime.
    dispose() {
      for(const b of resources) { scene.remove(b.mesh);b.mesh.geometry.dispose();b.mesh.material.dispose(); }
    },
  };
}
