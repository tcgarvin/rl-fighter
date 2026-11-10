// Shared combat effects. Fixed-capacity CPU pools feed bounded instanced draws, with no
// per-frame object creation. Smoke, fire and flames are shaded from one small tiling
// noise texture (render/noise.js); a fixed pool of four point lights is lent to
// blasts, hits, jumps and launches so they light the hulls near them.
//
// Coordinates: every event takes sim metres (x, y; +y is the sim's "up", drawn at
// three.js z = -y) and headings in radians CCW from +x, as the sim reports them.
// Teams are 0 / 1; -1 is neutral (white) where noted. Pools are fixed: past capacity
// the oldest entry is reused, so nothing grows and nothing throws.
//
// const fx = createEffects({ THREE, scene, renderer, palette, sun?, lens? });
//   sun: {direction, color, shade}, the key light that smoke is lit by (read live);
//   lens: {ripple({x, z, radius, life, strength, width, wait})} for shockwave refraction.
//   Both are the cinematic treatment's; without them smoke takes a default light and
//   nothing refracts.
// Per frame:
//   fx.updateProjectiles(projectiles, beams, alpha)  shots in flight (current tick)
//   fx.update(dt)                                     ages and draws everything else
// fx.drawOrders(orders) sets the commander overlay; it is drawn every frame until the
// next call (pass [] to clear). The array is read, never copied or changed.
// Fire-and-forget events:
//   fx.muzzle({x, y, angle, team, weapon})
//   fx.hit({x, y, team})                     team = shooter (-1: neutral)
//   fx.shieldHit({x, y, nx, ny, team, depleted, radius, object?})  team = shooter. A
//       patch of the bubble (radius round the ship centre, x - nx*radius, y - ny*radius)
//       lights up round the impact: field cells, uneven ripples, a ragged ~0.7 s decay.
//       depleted: the whole bubble strobes and shatters outward (1 s). Pass the hull's
//       THREE.Object3D as `object` so the response rides with a moving ship; at most
//       SHIELD_LAYERS responses per shield are live, and quick repeats feed the last.
//   fx.explosion({x, y, radius, team, kind})  kind 'death' | 'flak' | 'collision' | 'major'
//       'major' is a destroyed hull blowing up big (radius ~2.5 collision radii): flash,
//       shockwave to ~2.9 radius, fireball with secondary pops, debris, embers and hot
//       smoke that lingers ~4 s.
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
//   fx.trail({team, width}) -> {head(x, y, z, level), lay(), cut(), dispose()}  an engine
//       trail: a ribbon in the team's colour, as bright as the throttle when each point
//       was laid, fading over ~1.25 s. head() each frame, lay() once a sim tick.
//   fx.beacons(model, team) -> {show(on), dispose()}  running lights at model.strobes
//   fx.attachDamage(model) -> {update(hpFraction, visible, dt), smoulder(dt, heat), dispose()}
//       smoulder: a burnt-out hulk's hot spots instead of smoke and fire, a few glowing
//       points fixed on the hull where it burned; heat 0..1, call every frame to keep them
//
// drawOrders(orders): each order is {kind, team, x2, y2, radius?, x1?, y1?, progress?}.
//   kind 'attack' | 'defend' | 'goto' | 'jump'. With x1, y1 a faint dashed line crawls
//   from the squad (x1, y1) toward the target (x2, y2) and stops at its marker:
//   attack = four corner brackets, defend = a thin ring round the ward, goto = a ring
//   with inward ticks, jump = a slowly turning dashed ring with a brighter arc for
//   `progress` (0..1, e.g. the jump charge). radius is the marker's (metres).
import { noiseTexture } from './noise.js';

export const JUMP_OUT_DISTANCE = 900;
export const JUMP_OUT_DURATION = 0.09;
const JUMP_OUT_TAIL = 0.16, QUICK_OUT_TAIL = 0.10;
/** Metres a departing hull has moved forward `age` seconds into jumpOut (ease-in). */
export function jumpOutOffset(age, duration = JUMP_OUT_DURATION) {
  const t = Math.max(0, Math.min(1, age / duration));
  return JUMP_OUT_DISTANCE * t * t * t;
}

// Shield responses: one pooled, instanced dome (a sphere flattened to 0.75 in height)
// per live response, lit only where and while it is struck. Per instance: tint (rgb,
// peak strength), hit (impact direction in the unit sphere's frame, age s), mode
// (depleted 0/1, seed, radius m, life s). The fragment shader does all of the look.
const SHIELD_CAP = 48;
// Live responses per shield: a gunship under sustained fire reuses its oldest layer
// instead of stacking more additive shells over the hull.
const SHIELD_LAYERS = 3;
// Peak strength of a fresh response, and the most a shield's live responses may sum to.
const SHIELD_STRENGTH = .85, SHIELD_BUDGET = 1.15;
const SHIELD_LIFE = .7, SHIELD_DEPLETED_LIFE = 1.0, SHIELD_FLATTEN = .75;
const SHIELD_VERTEX = `
  attribute vec4 tint; attribute vec4 hit; attribute vec4 mode;
  varying vec4 vTint; varying vec4 vHit; varying vec4 vMode;
  varying vec3 vSphere; varying vec3 vNormal; varying vec3 vView;
  void main(){
    vTint=tint; vHit=hit; vMode=mode;
    vec3 n=normalize(vec3(position.x,position.y/${SHIELD_FLATTEN},position.z)); vSphere=n;
    // A collapsing shield swells as it lets go.
    float u=clamp(hit.w/max(mode.w,.001),0.,1.);
    float grow=mode.x>.5?1.+.05*u*u:1.;
    vec4 world=modelMatrix*instanceMatrix*vec4(position*grow,1.);
    vNormal=normalize(mat3(modelMatrix*instanceMatrix)*vec3(n.x,n.y/${SHIELD_FLATTEN},n.z));
    vView=normalize(cameraPosition-world.xyz);
    gl_Position=projectionMatrix*viewMatrix*world;
  }`;
const SHIELD_FRAGMENT = `
  uniform float time;
  varying vec4 vTint; varying vec4 vHit; varying vec4 vMode;
  varying vec3 vSphere; varying vec3 vNormal; varying vec3 vView;
  float hash(vec3 p){ p=fract(p*vec3(.1031,.1030,.0973)); p+=dot(p,p.yxz+33.33); return fract((p.x+p.y)*p.z); }
  float vnoise(vec3 p){
    vec3 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
    return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
               mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);
  }
  // Cells of the field (3D Voronoi on the sphere): x = distance to the cell border,
  // y = the cell's own random value.
  vec2 cells(vec3 p){
    vec3 i=floor(p), f=fract(p); float d1=8., d2=8.; vec3 id=vec3(0);
    for(int z=-1;z<=1;z++) for(int y=-1;y<=1;y++) for(int x=-1;x<=1;x++){
      vec3 g=vec3(x,y,z), o=vec3(hash(i+g),hash(i+g+19.1),hash(i+g+47.7));
      vec3 r=g+o-f; float d=dot(r,r);
      if(d<d1){ d2=d1; d1=d; id=i+g; } else if(d<d2) d2=d;
    }
    return vec2(sqrt(d2)-sqrt(d1), hash(id+3.7));
  }
  void main(){
    float age=vHit.w, life=vMode.w, u=clamp(age/life,0.,1.), seed=vMode.y, radius=vMode.z;
    bool depleted=vMode.x>.5;
    vec3 n=normalize(vSphere), impact=normalize(vHit.xyz);
    float theta=acos(clamp(dot(n,impact),-1.,1.));
    // Stationary, low-frequency warp: wave fronts run unevenly over the surface.
    float warped=theta+(vnoise(n*2.6+seed)-.5)*.34;
    // Cells about 2.6 m across, never fewer than a few over the bubble.
    float scale=clamp(radius/2.6,3.,10.);
    vec2 cell=cells(n*scale+seed*7.);
    // Hairline cell borders, antialiased; once the cells shrink toward a few pixels
    // (a small ship on a phone) the lines melt into a faint even shimmer.
    float aa=fwidth(cell.x), w=.04;
    float edge=1.-smoothstep(w-aa*.5,w+aa*.5+.001,cell.x);
    edge=mix(edge,.14,clamp(aa/w-1.,0.,1.));
    // Each cell breathes on its own, smoothly (no stepped strobing under sustained fire).
    float flicker=.6+.4*vnoise(vec3(cell.y*31.,time*7.,seed));
    float facing=abs(dot(normalize(vNormal),normalize(vView)));
    float rim=pow(1.-facing,3.);
    // Refraction-like glints: a fast, short-lived noise band across the struck patch.
    float glint=pow(vnoise(n*7.+vec3(0.,time*9.,seed)),3.)*exp(-age*7.);
    float a, white, lift=0.;
    if(!depleted){
      float width=mix(.3,.6,smoothstep(0.,.2,age));
      float spot=exp(-pow(warped/width,2.));
      float halo=exp(-pow(warped/(width*1.35),2.));
      float front=exp(-pow((warped-age*3.)/.13,2.))*.55+exp(-pow((warped-max(0.,age-.08)*2.4)/.1,2.))*.25*step(.08,age);
      front*=exp(-theta*.9);
      // Fast attack, then a ragged decay: noise blobs eat the patch as it fades.
      float env=smoothstep(0.,.02,age)*exp(-age/.24);
      float ragged=smoothstep(u-.25,u+.1,vnoise(n*5.+seed+vec3(0.,time*.8,0.)));
      // A few cells flare at a time; the outline is broken by slow gaps, so the patch
      // reads as energy on a dome, not a lit surface or a HUD arc.
      // A few cells at a time light a soft node at their heart, each on its own clock.
      float k=time*6.+cell.y*5.;
      float lit=step(.93,hash(vec3(floor(cell.y*97.),floor(k),seed)))*sin(3.1416*fract(k))*smoothstep(.12,.4,cell.x);
      float gaps=smoothstep(.3,.6,vnoise(n*3.+seed+vec3(time*.5)));
      float body=(spot*(.02+.3*edge*flicker+.6*lit)+halo*rim*.12*gaps)*ragged;
      lift=spot*(.35*lit+.2*edge);
      // Only a patch of the dome answers: nothing past ~70 degrees from the impact.
      a=1.4*env*(body+front*(.1+.4*edge)+glint*spot*1.25)*(1.-smoothstep(.65,1.25,theta));
      white=exp(-pow(theta/.15,2.))*exp(-age/.07);
      a+=white*1.2;
    } else {
      // The whole bubble: a hard flash with two unequal dropouts, then the cells
      // shatter from the impact outward, each flaring as it goes.
      float strobe=1.-.85*step(.05,age)*step(age,.08)-.6*step(.12,age)*step(age,.15);
      float d=smoothstep(.08,.65,u)*1.15;
      float key=.6*cell.y+.4*theta/3.1416;
      float alive=smoothstep(d,d+.06,key);
      float dying=exp(-pow((key-d)/.05,2.))*step(.001,d);
      float env=smoothstep(0.,.02,age);
      float front=exp(-pow((warped-age*5.)/.12,2.));
      float body=.05+.6*edge*flicker+.9*rim;
      a=env*strobe*(body*alive+dying*(.25+edge)*1.2+front*(.15+.6*edge)*exp(-age*3.))*.7;
      white=exp(-pow(theta/.25,2.))*exp(-age/.06);
      a+=white*1.2;
    }
    // The far side of the bubble (seen through it) stays faint.
    if(!gl_FrontFacing) a*=.3;
    a*=vTint.a;
    // Contrast: the dim cell network drops away (an orange field at low light reads as
    // brown crust), the bright cells, fronts and glints keep their strength.
    a=a*a/(a+.08);
    if(a<.003) discard;
    // Bright structure runs hotter (toward white) than the field's own colour.
    vec3 col=mix(vTint.rgb,vec3(.9,.98,1.),clamp(white+glint*.5+lift,0.,1.));
    gl_FragColor=vec4(col,min(a,1.4));
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;
function shieldBatch(T, scene, cap) {
  const geo = new T.SphereGeometry(1, 40, 20);
  geo.scale(1, SHIELD_FLATTEN, 1);
  const attr = (name) => {
    const a = new T.InstancedBufferAttribute(new Float32Array(cap * 4), 4).setUsage(T.DynamicDrawUsage);
    geo.setAttribute(name, a); return a;
  };
  const rgba = attr('tint'), hit = attr('hit'), mode = attr('mode');
  const mat = new T.ShaderMaterial({
    uniforms: { time: { value: 0 } },
    transparent: true, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending,
    vertexShader: SHIELD_VERTEX, fragmentShader: SHIELD_FRAGMENT,
  });
  const mesh = new T.InstancedMesh(geo, mat, cap);
  mesh.instanceMatrix.setUsage(T.DynamicDrawUsage); mesh.frustumCulled = false; mesh.count = 0;
  mesh.renderOrder = 2; scene.add(mesh);
  return { mesh, rgba, hit, mode, n: 0, cap };
}

// Lights thrown by blasts, flashes and jumps: a fixed pool of point lights (the hull
// shaders are compiled for exactly this many), each lent to the brightest events.
const FLASH_LIGHTS = 4;
// Engine trails: ribbons of TRAIL_NODES points laid one a sim tick behind each main
// engine, fading over TRAIL_LIFE seconds.
const TRAIL_CAP = 48, TRAIL_NODES = 40, TRAIL_LIFE = 1.25;

/**
 * @param {{ THREE: any, scene: any, renderer: any, palette: any, sun?: any, lens?: any, flashLights?: boolean }} options
 * `sun` is the key light smoke is lit by ({direction, color, shade}, read live) and `lens`
 * an object with ripple({x, z, radius, life, strength, width, wait}) for shockwave
 * refraction; both are the cinematic treatment's, and both are optional. `flashLights`
 * false leaves the point lights dark (a switch for telling a lighting fault apart).
 */
export function createEffects({ THREE: T, scene, renderer, palette, sun: sunIn, lens = null, flashLights = true }) {
  // The key light the smoke is lit by (the treatment's, live: it turns with the scenery).
  const sun = sunIn ?? { direction: new T.Vector3(-.657, .555, .511), color: new T.Color(0xffc58a), shade: new T.Color(0x2b4f63) };
  const team = palette.team.map(c => new T.Color(c));
  const shot = palette.projectile.map(c => new T.Color(c));
  const pellet = shot.map(c => c.clone().lerp(new T.Color(0xffad63), .48));
  const shield = palette.shield.map(c => new T.Color(c));
  const white = new T.Color(0xfff5df), warmWhite = new T.Color(0xffd9a8), amber = new T.Color(palette.exhaust);
  const fireColor = new T.Color(0xff6514);
  const smokeColor = new T.Color(0x77726c), shell = new T.Color(0x26333c);
  const transform = new T.Object3D(), point = new T.Vector3(), end = new T.Vector3();
  const resources = [];
  // opts (billboards): minPx keeps a sprite at least that many CSS pixels across; fire
  // is a rolling fire cloud; aux adds a second per-instance vec4 (seed, age 0..1, heat, -)
  // that the smoke, fire and flame looks are shaded from.
  function batch(geo, cap, billboard = false, smoke = false, additive = true, flame = false, trace = 0, ringWidth = 0, ringMin = .022, opts = {}) {
    const { minPx = 0, fire = false } = opts;
    const shaded = smoke || fire || flame;
    const rgba = new T.InstancedBufferAttribute(new Float32Array(cap * 4), 4).setUsage(T.DynamicDrawUsage);
    geo.setAttribute('tint', rgba);
    const aux = shaded ? new T.InstancedBufferAttribute(new Float32Array(cap * 4), 4).setUsage(T.DynamicDrawUsage) : null;
    if (aux) geo.setAttribute('aux', aux);
    const mat = new T.ShaderMaterial({
      uniforms: { viewportHeight: { value: 720 }, time: { value: 0 }, noise: { value: noiseTexture() },
        sunDir: { value: sun.direction }, sunColor: { value: sun.color }, shadeColor: { value: sun.shade } },
      transparent: true, depthWrite: false, side: T.DoubleSide,
      blending: additive ? T.AdditiveBlending : T.NormalBlending,
      vertexShader: `uniform float viewportHeight; uniform vec3 sunDir; attribute vec4 tint; varying vec4 vTint; varying vec2 vUv; varying float vSeed;
        ${shaded ? 'attribute vec4 aux; varying vec4 vAux; varying vec3 vSun;' : ''}
        void main(){ vTint=tint; vUv=uv; vSeed=length(instanceMatrix[2].xyz);
        ${shaded ? 'vAux=aux; vSun=normalize(mat3(viewMatrix)*sunDir);' : ''}
        ${trace ? `vec4 center=modelViewMatrix*instanceMatrix*vec4(0.,0.,0.,1.);
        vec3 axis=(modelViewMatrix*vec4(instanceMatrix[0].xyz,0.)).xyz;
        vec2 along=axis.xy/max(length(axis.xy),.0001);
        vec2 across=vec2(-along.y,along.x);
        float width=length(instanceMatrix[1].xyz);
        float pixelWorld=2.*max(1.,-center.z)/(projectionMatrix[1][1]*viewportHeight);
        width=max(width,pixelWorld*${trace === 1 ? '2.8' : '.95'});
        center.xy+=axis.xy*position.x+across*position.y*width;
        gl_Position=projectionMatrix*center;` : ringWidth ? `float radius=length(position.xz);
        vec3 rim=position/max(radius,.0001);
        vec4 center=modelViewMatrix*instanceMatrix*vec4(0.,0.,0.,1.);
        vec4 edge=modelViewMatrix*instanceMatrix*vec4(rim,1.);
        float pixelWorld=2.*max(1.,-center.z)/(projectionMatrix[1][1]*viewportHeight);
        float inset=max(${ringMin},pixelWorld*${ringWidth}/max(length(edge.xy-center.xy),.0001));
        float radial=radius<.99?max(0.,1.-inset):1.;
        gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(rim*radial,1.);` : billboard ? `vec4 center=modelViewMatrix*instanceMatrix*vec4(0.,0.,0.,1.);
        vec2 size=vec2(length(instanceMatrix[0].xyz),length(instanceMatrix[1].xyz));
        ${minPx ? `size=max(size,vec2(2.*max(1.,-center.z)/(projectionMatrix[1][1]*viewportHeight)*${minPx.toFixed(2)}));` : ''}
        center.xy+=position.xy*size; gl_Position=projectionMatrix*center;` :
        'gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.);'} }`,
      fragmentShader: `uniform float time; uniform sampler2D noise; uniform vec3 sunColor, shadeColor; varying vec4 vTint; varying vec2 vUv; varying float vSeed;
        ${shaded ? 'varying vec4 vAux; varying vec3 vSun;' : ''}
        void main(){float a=vTint.a; vec3 col=vTint.rgb;
        ${trace ? `float crossSection=abs(vUv.y*2.-1.);
          ${trace === 1 ? `float taper=mix(.08,1.,vUv.x);
          a*=exp(-4.*crossSection*crossSection/(taper*taper))*pow(vUv.x,.7);
          a*=smoothstep(0.,.12,vUv.x)*smoothstep(1.,.83,vUv.x);` :
          `a*=exp(-5.*crossSection*crossSection)*smoothstep(0.,.14,vUv.x)*smoothstep(1.,.86,vUv.x);`}` : ''}
        ${fire ? `vec2 p=vUv*2.-1.; float seed=vAux.x, age=vAux.y;
          // A fire cloud: billows shape its edge and roll outward as it ages; it burns
          // yellow-white at the heart, through orange and red, and dies to soot from
          // the outside in. Filaments keep a few veins alight.
          vec2 q=p*.19*(1.-age*.25)+vec2(seed*.371,seed*.613);
          float lump=texture2D(noise,q).b, vein=texture2D(noise,q*2.3+vec2(seed,-time*.07)).a;
          float rd=length(p)*(1.32-.62*lump);
          if(rd>1.) discard;
          float core=1.-rd;
          float temp=(core*1.25+vein*.55-.2)*(1.+vAux.z*.5)*(1.-smoothstep(.2,1.,age*(1.25-vAux.z*.45)));
          vec3 ember=mix(vec3(.035,.028,.024),vec3(.85,.1,.012),smoothstep(.05,.38,temp));
          ember=mix(ember,vec3(2.6,.78,.1),smoothstep(.32,.62,temp));
          ember=mix(ember,vec3(4.4,3.,1.5),smoothstep(.6,.98,temp));
          col=ember;
          a*=smoothstep(0.,.22,core)*(.55+.6*lump);` : smoke ? `vec2 p=vUv*2.-1.; float r2=dot(p,p);
          if(r2>1.) discard;
          float seed=vAux.x, age=vAux.y;
          // A puff: rounded billows with finer breakup, eroding into wisps as it ages,
          // lit as a soft ball by the key light with the shadows going teal.
          vec2 q=p*.2+vec2(seed*.731,seed*.419);
          float lump=texture2D(noise,q+vec2(0.,age*.04)).b, wisp=texture2D(noise,q*2.6+vec2(seed,-age*.1)).r;
          float body=(1.-r2)*(.45+.8*lump)*(.6+.7*wisp);
          float erode=mix(.03,.33,age);
          float dens=smoothstep(erode,erode+.62,body);
          vec3 nrm=normalize(vec3(p+(vec2(lump,wisp)-.5)*1.2,.7*sqrt(1.-r2)+.12));
          float lit=dot(nrm,vSun)*.5+.5; lit*=lit;
          col=vTint.rgb*(shadeColor*1.2+mix(sunColor,vec3(1.),.5)*lit*1.05);
          // Heat: a glowing pocket deep inside a fresh, hot puff.
          col+=vec3(2.2,.55,.08)*vAux.z*smoothstep(.5,1.,body)*lump;
          a*=dens;` : flame ? `vec2 p=vUv*2.-1.; float seed=vAux.x;
          // Tongues of flame: rising filaments, a wavering taper, hot at the root.
          float rise=time*(1.1+.3*fract(seed*3.7));
          float n1=texture2D(noise,vec2(p.x*.16+seed*.61,p.y*.13-rise)).a;
          float n2=texture2D(noise,vec2(p.x*.31-seed*.37,p.y*.2-rise*1.7)).r;
          float lift=(p.y+1.)*.5;
          float x=(p.x+(n2-.5)*.75*lift)/max(.14,.62-p.y*.42);
          float shape=(1.-smoothstep(.15,1.,abs(x)))*smoothstep(-1.,-.6,p.y)*(1.-smoothstep(-.1,1.,p.y+(.5-n1)*1.3));
          shape*=(1.-smoothstep(.72,1.,abs(p.x)))*(1.-smoothstep(.8,1.,p.y));
          if(shape<.004) discard;
          a*=shape*(.55+1.1*n1);
          col=mix(col,vec3(2.,1.15,.38),shape*shape*(1.-lift)*.7);` : billboard ? `vec2 p=vUv*2.-1.; float r=dot(p,p);
          a*=max(0.,exp(-r*5.)-0.0067);
          if(r>1.) discard;` : ''}
        gl_FragColor=vec4(col,a);
        ${trace ? '' : '#include <tonemapping_fragment>'}
        #include <colorspace_fragment>
        }`,
    });
    const mesh = new T.InstancedMesh(geo, mat, cap);
    mesh.instanceMatrix.setUsage(T.DynamicDrawUsage); mesh.frustumCulled = false; mesh.count = 0;
    mesh.renderOrder = smoke || fire ? 1 : 2; scene.add(mesh);
    const b = { mesh, rgba, aux, n: 0, cap };
    resources.push(b); return b;
  }
  const glow = batch(new T.PlaneGeometry(1, 1), 1400, true);
  const flames = batch(new T.PlaneGeometry(1, 1), 512, true, false, true, true);
  const smoke = batch(new T.PlaneGeometry(1, 1), 1200, true, true, false);
  const chips = batch(new T.IcosahedronGeometry(1, 0), 256, false, false, false);
  const ringGeo = new T.RingGeometry(.89, 1, 48, 1, 0, Math.PI * 1.86);
  ringGeo.rotateX(-Math.PI / 2);
  const rings = batch(ringGeo, 160);
  // Closed hairline rings for the jump drive: energy, not a HUD arc with a gap.
  const thinGeo = new T.RingGeometry(.978, 1, 64, 1);
  thinGeo.rotateX(-Math.PI / 2);
  const thin = batch(thinGeo, 128);
  // Charge rings alone get a CSS-pixel floor; collapse rings retain their fine edge.
  const chargeRings = batch(thinGeo.clone(), 32, false, false, true, false, 0, .85);
  // Velocity-aligned ribbons expand across the view, so they cannot turn edge-on.
  // Soft analytic profiles replace solid box faces; both layers remain additive.
  const tracers = batch(new T.PlaneGeometry(1, 1), 1200, false, false, true, false, 1);
  const cores = batch(new T.PlaneGeometry(1, 1), 1200, false, false, true, false, 2);
  const bolts = batch(new T.BoxGeometry(1, 1, 1), 512);
  // Launch trails (tapered, like tracers) and the commander overlay's hairlines; both
  // keep a minimum pixel width, so they read on a phone at any zoom.
  const trails = batch(new T.PlaneGeometry(1, 1), 256, false, false, true, false, 1);
  const lines = batch(new T.PlaneGeometry(1, 1), 1024, false, false, true, false, 2);
  // Sparks: short streaks along their own velocity.
  const streaks = batch(new T.PlaneGeometry(1, 1), 1024, false, false, true, false, 2);
  // Major explosions' shockwave: a closed ring with a CSS-pixel floor on its width.
  const shockGeo = new T.RingGeometry(.9, 1, 96, 1);
  shockGeo.rotateX(-Math.PI / 2);
  const shocks = batch(shockGeo, 32, false, false, true, false, 0, 1.6, .007);
  // Major explosions: turbulent fire clouds (normal blending), hot points that keep a
  // pixel floor so they read on a phone, and the collapsing shield's flat fragments.
  const fires = batch(new T.PlaneGeometry(1, 1), 256, true, false, false, false, 0, 0, .022, { fire: true });
  const embers = batch(new T.PlaneGeometry(1, 1), 512, true, false, true, false, 0, 0, .022, { minPx: 3.5 });
  const emberHalos = batch(new T.PlaneGeometry(1, 1), 512, true, false, true, false, 0, 0, .022, { minPx: 8 });
  const shardGeo = new T.IcosahedronGeometry(1, 0);
  shardGeo.scale(1, .18, .7);
  const shards = batch(shardGeo, 128);
  const shieldFx = shieldBatch(T, scene, SHIELD_CAP);
  resources.push(shieldFx);

  function put(b, x, y, z, sx, sy, sz, angle, c, opacity, tumble = 0, seed = 0, age = 0, heat = 0) {
    if (b.n >= b.cap) return;
    const i = b.n++;
    transform.position.set(x, y, z); transform.rotation.set(tumble, angle, tumble * .73);
    transform.scale.set(sx, sy, sz); transform.updateMatrix(); b.mesh.setMatrixAt(i, transform.matrix);
    const j = i * 4, a = b.rgba.array;
    a[j] = c.r; a[j+1] = c.g; a[j+2] = c.b; a[j+3] = opacity;
    if (b.aux) { const x4 = b.aux.array; x4[j] = seed; x4[j+1] = age; x4[j+2] = heat; }
  }
  // Send the GPU only the part of an attribute that is in use this frame.
  function upload(attribute, count) {
    attribute.clearUpdateRanges(); attribute.addUpdateRange(0, count * attribute.itemSize); attribute.needsUpdate = true;
  }
  function finish(b) {
    b.mesh.count = b.n;
    if (b.n) { upload(b.mesh.instanceMatrix, b.n); upload(b.rgba, b.n); if (b.aux) upload(b.aux, b.n); }
  }
  function segment(b, x, y, z, ex, ey, ez, width, c, opacity) {
    // All weapon traces lie in the battle plane; electric bolts use slight height offsets.
    const dx = ex-x, dz = ez-z;
    put(b, (x+ex)*.5, (y+ey)*.5, (z+ez)*.5, Math.hypot(dx,dz), width, width,
      Math.atan2(-dz,dx), c, opacity);
  }
  const particles = Array.from({ length: 3200 }, () => ({ life: 0, max: 1, x: 0, y: 0, z: 0,
    vx: 0, vy: 0, vz: 0, size: 1, kind: 0, color: white, angle: 0, wait: 0, hot: false, gain: 1 }));
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
  const shields = Array.from({ length: SHIELD_CAP }, () => ({ age: 0, max: 0, object: null,
    x: 0, z: 0, dx: 1, dz: 0, radius: 1, color: white, depleted: false, seed: 0, strength: 1, born: 0 }));
  let pc = 0, wc = 0, jc = 0, lc = 0, cc = 0, sc = 0, clock = 0, orders = [];
  // kind: 0 glow, 1 smoke, 2 shell fragment, 3 spark, 4 tapered flame, 5 damage smoke,
  // 6 ember (a flickering hot point), 7 explosion smoke (`hot`: with a glowing pocket),
  // 8 fire cloud (yellow, red, then soot), 9 shield fragment. `wait` delays the
  // particle (s): it is invisible and still until then.
  function particle(x, y, z, size, life, color, kind = 0, vx = 0, vy = 0, vz = 0, wait = 0) {
    const p = particles[pc++]; if (pc === particles.length) pc = 0;
    p.x=x; p.y=y; p.z=z; p.size=size; p.life=p.max=life; p.color=color; p.kind=kind;
    p.vx=vx; p.vy=vy; p.vz=vz; p.angle=Math.random()*6.283; p.wait=wait; p.hot=false; p.gain=1;
    return p;
  }
  const scratch = new T.Color();
  // ---- Flash lights ----
  const flashes = Array.from({ length: FLASH_LIGHTS }, () => {
    const light = new T.PointLight(0xffffff, 0, 60, 2); scene.add(light);
    return { light, life: 0, max: 1, wait: 0, peak: 0 };
  });
  /** Lend a light to a flash of `intensity` (candela) unless brighter ones hold them all. */
  function flash(x, y, z, color, intensity, range, life, wait = 0) {
    if (!flashLights) return;
    let free = null, least = Infinity;
    for (const f of flashes) {
      const level = f.life > 0 ? f.peak * (f.life / f.max) ** 2 : 0;
      if (level < least) { least = level; free = f; }
    }
    if (least >= intensity) return;
    free.light.position.set(x, y, z); free.light.color.copy(color); free.light.distance = range;
    free.light.intensity = 0; free.peak = intensity; free.life = free.max = life; free.wait = wait;
  }
  function updateFlashes(dt) {
    for (const f of flashes) {
      if (f.life <= 0) continue;
      if (f.wait > 0) { f.wait -= dt; continue; }
      f.life -= dt;
      f.light.intensity = f.life > 0 ? f.peak * (f.life / f.max) ** 2 : 0;
    }
  }
  const ripple = lens ? (x, z, radius, life, strength, width = .25, wait = 0) => lens.ripple({ x, z, radius, life, strength, width, wait }) : () => {};
  // ---- Engine trails ----
  // One mesh for every ribbon: two vertices a node, widened to face the view in the
  // vertex shader (never thinner than a pixel), brightest down the middle.
  const trailGeo = new T.BufferGeometry();
  const trailPos = new Float32Array(TRAIL_CAP * TRAIL_NODES * 2 * 3), trailSide = new Float32Array(TRAIL_CAP * TRAIL_NODES * 2 * 3), trailTint = new Float32Array(TRAIL_CAP * TRAIL_NODES * 2 * 4);
  {
    const index = new Uint16Array(TRAIL_CAP * (TRAIL_NODES - 1) * 6);
    for (let r = 0, k = 0; r < TRAIL_CAP; r++) for (let n = 0; n < TRAIL_NODES - 1; n++) {
      const v = (r * TRAIL_NODES + n) * 2;
      index[k++] = v; index[k++] = v + 1; index[k++] = v + 2; index[k++] = v + 1; index[k++] = v + 3; index[k++] = v + 2;
    }
    trailGeo.setIndex(new T.BufferAttribute(index, 1));
    trailGeo.setAttribute('position', new T.BufferAttribute(trailPos, 3).setUsage(T.DynamicDrawUsage));
    trailGeo.setAttribute('side', new T.BufferAttribute(trailSide, 3).setUsage(T.DynamicDrawUsage));
    trailGeo.setAttribute('tint', new T.BufferAttribute(trailTint, 4).setUsage(T.DynamicDrawUsage));
  }
  const trailMat = new T.ShaderMaterial({
    uniforms: { viewportHeight: { value: 720 } },
    transparent: true, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending,
    vertexShader: `uniform float viewportHeight; attribute vec3 side; attribute vec4 tint; varying vec4 vTint; varying float vAcross;
      void main(){ vTint=tint; vAcross=sign(side.z);
        vec4 center=modelViewMatrix*vec4(position,1.);
        float pixelWorld=2.*max(1.,-center.z)/(projectionMatrix[1][1]*viewportHeight);
        float reach=max(abs(side.z),pixelWorld*.9);
        gl_Position=projectionMatrix*modelViewMatrix*vec4(position+vec3(side.x,0.,side.y)*reach*vAcross,1.); }`,
    fragmentShader: `varying vec4 vTint; varying float vAcross;
      void main(){ gl_FragColor=vec4(vTint.rgb,vTint.a*exp(-3.6*vAcross*vAcross));
        #include <colorspace_fragment>
      }`,
  });
  const trailMesh = new T.Mesh(trailGeo, trailMat);
  trailMesh.frustumCulled = false; trailMesh.renderOrder = 1.5; trailGeo.setDrawRange(0, 0); scene.add(trailMesh);
  const ribbons = Array.from({ length: TRAIL_CAP }, (_, slot) => ({ slot, used: false, color: white, width: .5, n: 0, start: 0,
    x: new Float32Array(TRAIL_NODES), z: new Float32Array(TRAIL_NODES), level: new Float32Array(TRAIL_NODES), born: new Float64Array(TRAIL_NODES),
    hx: 0, hz: 0, hy: 1, hlevel: 0, live: false, fresh: false, drawn: false }));
  const trailColor = team.map(c => c.clone().lerp(new T.Color(palette.exhaust), .22).multiplyScalar(1.25));
  function updateTrails() {
    let top = 0;
    for (const r of ribbons) {
      const base = r.slot * TRAIL_NODES * 2;
      if (!r.used || (!r.live && r.n === 0)) {
        // Collapse an idle ribbon to nothing (once is enough; it stays that way).
        if (r.drawn) { trailTint.fill(0, base * 4, (base + TRAIL_NODES * 2) * 4); trailSide.fill(0, base * 3, (base + TRAIL_NODES * 2) * 3); r.drawn = false; top = r.slot + 1; }
        continue;
      }
      // Drop nodes that have faded out.
      while (r.n > 0 && clock - r.born[r.start] > TRAIL_LIFE) { r.start = (r.start + 1) % TRAIL_NODES; r.n--; }
      // Newest first: the live head at the nozzle, then the laid nodes back in time.
      const count = Math.min(TRAIL_NODES, r.n + (r.live ? 1 : 0));
      let px = 0, pz = 0, lastX = 0, lastZ = 0, sideX = 0, sideZ = 1;
      for (let k = 0; k < TRAIL_NODES; k++) {
        let x, z, level, age;
        if (k < count) {
          if (r.live && k === 0) { x = r.hx; z = r.hz; level = r.hlevel; age = 0; }
          else { const i = (r.start + r.n - 1 - (k - (r.live ? 1 : 0)) + TRAIL_NODES * 2) % TRAIL_NODES; x = r.x[i]; z = r.z[i]; level = r.level[i]; age = clock - r.born[i]; }
          if (k > 0) { const dx = px - x, dz = pz - z, d = Math.hypot(dx, dz); if (d > 1e-4) { sideX = -dz / d; sideZ = dx / d; } }
          px = x; pz = z; lastX = x; lastZ = z;
        } else { x = lastX; z = lastZ; level = 0; age = TRAIL_LIFE; }
        const t = Math.min(1, age / TRAIL_LIFE), fade = (1 - t) ** 1.7;
        // The plume owns the first metres; the trail comes up behind it.
        const alpha = level * fade * Math.min(1, .25 + age * 9) * .7, half = r.width * (.55 + 1.5 * t);
        for (let e = 0; e < 2; e++) {
          const v = base + k * 2 + e, s3 = v * 3, s4 = v * 4;
          trailPos[s3] = x; trailPos[s3 + 1] = r.hy; trailPos[s3 + 2] = z;
          trailSide[s3] = sideX; trailSide[s3 + 1] = sideZ; trailSide[s3 + 2] = e ? half : -half;
          trailTint[s4] = r.color.r; trailTint[s4 + 1] = r.color.g; trailTint[s4 + 2] = r.color.b; trailTint[s4 + 3] = alpha;
        }
        // The first segment takes its direction from the second node.
        if (k === 1) for (let e = 0; e < 2; e++) { const s3 = (base + e) * 3; trailSide[s3] = sideX; trailSide[s3 + 1] = sideZ; }
      }
      r.drawn = true; r.live = false; top = r.slot + 1;
    }
    trailGeo.setDrawRange(0, top * (TRAIL_NODES - 1) * 6);
    if (top) for (const name of ['position', 'side', 'tint']) upload(trailGeo.attributes[name], top * TRAIL_NODES * 2);
  }
  // Capital ships' running lights (see beacons()).
  const beaconSets = new Set();
  const beaconColor = team.map(c => c.clone().lerp(white, .7).multiplyScalar(1.6));
  // Hulks' hot spots, drawn each frame from their hull's transform (see smoulder).
  const hulks = new Set();
  const goldWhite = new T.Color(0xfff3cf), orange = new T.Color(0xff952f), deepFire = new T.Color(0xff5218);
  const emberColor = new T.Color(0xffab4a), emberDim = new T.Color(0xff6a24), emberHot = new T.Color(0xffab4a).multiplyScalar(2), soot = new T.Color(0x3a3029);
  const fireLight = new T.Color(0xff7a2a).multiplyScalar(.2), shockColor = new T.Color(0xffd9a0);
  // Fireball puffs are additive and overlap: dimmed so their sum stays fire, not white.
  const puffA = orange.clone().multiplyScalar(.3), puffB = deepFire.clone().multiplyScalar(.35);
  const hitLight = new T.Color(0xffc48a);
  const shocksLive = Array.from({ length: 32 }, () => ({ life: 0, max: 1, wait: 0, x: 0, z: 0, radius: 1, color: white, alpha: 1 }));
  let shc = 0;
  function shock(x, z, radius, life, color, alpha, wait) {
    const s=shocksLive[shc++]; if(shc===shocksLive.length)shc=0;
    s.x=x; s.z=z; s.radius=radius; s.life=s.max=life; s.wait=wait; s.color=color; s.alpha=alpha;
  }
  // A destroyed ship blowing up big (R = the event radius, ~2.5 collision radii): core
  // flash, a shockwave out to ~2.4 R, a turbulent fireball with secondary detonations,
  // debris and embers, and smoke with hot pockets that lingers for a few seconds.
  function majorExplosion(e) {
    const R=e.radius, x=e.x, z=-e.y, c=team[e.team] || white;
    particle(x,2.4,z,R*1.4,.16,goldWhite);
    particle(x,2.3,z,R*2.6,.4,puffA);
    particle(x,2.2,z,R*.9,.12,white);
    flash(x,7+R*.3,z,warmWhite,Math.min(60*R*R,70000),Math.min(R*9,420),.95);
    ripple(x,z,R*3.1,.85,.34,.2);
    // Light thrown on the surroundings, and a faint team-coloured breath of the reactor.
    particle(x,.6,z,R*4.5,.7,fireLight);
    particle(x,.8,z,R*2.4,.35,c);
    shock(x,z,R*2.4,.65,shockColor,.55,.02);
    shock(x,z,R*1.8,.45,orange,.12,.06);
    // Fireball: turbulent fire clouds rolling outward, staggered over the first 0.15 s,
    // and a few additive puffs inside them for heat.
    particle(x,1.65,z,R*.9,.55,soot,8,0,R*.1,0,.03);
    for(let j=0;j<9;j++) {
      const a=j*2.399+Math.random()*.6, d=R*(.15+.45*Math.random()), v=R*(.35+.5*Math.random());
      particle(x+Math.cos(a)*d,1.7+j*.02,z+Math.sin(a)*d,R*(.35+.35*Math.random()),1+.7*Math.random(),
        soot,8,Math.cos(a)*v,R*.1,Math.sin(a)*v,j*.017);
      // Four lobes keep burning through the middle of the blast.
      particles[(pc+particles.length-1)%particles.length].hot=j<4;
    }
    for(let j=0;j<4;j++) {
      const a=j*1.7+Math.random(), d=R*.3*Math.random(), v=R*.4;
      particle(x+Math.cos(a)*d,2.6,z+Math.sin(a)*d,R*(.8+.4*Math.random()),.5+.3*Math.random(),
        j%2?puffA:puffB,0,Math.cos(a)*v,0,Math.sin(a)*v,j*.03);
    }
    // Secondary detonations through the first second, some out at the hull's edge: a
    // compact white core, then an orange lobe and a few sparks, each at its own height.
    const pops=Math.min(7,3+Math.floor(R/12));
    for(let j=0;j<pops;j++) {
      const at=.18+j*(.67/pops)+Math.random()*.08, a=Math.random()*TAU, d=R*(j%2?.65+.35*Math.random():.25+.4*Math.random());
      const px=x+Math.cos(a)*d, pz=z+Math.sin(a)*d, py=2.2+R*(.05+.1*Math.random()), s=R*(.4+.2*Math.random());
      particle(px,py+.2,pz,R*(.12+.08*Math.random()),.05+.03*Math.random(),white,0,0,0,0,at);
      particle(px,py,pz,s,.25+.15*Math.random(),puffA,0,0,0,0,at);
      particle(px,py-.3,pz,s*.7,.45+.2*Math.random(),soot,8,0,R*.1,0,at+.03);
      for(let k=0;k<3;k++) {
        const b=Math.random()*TAU, v=R*(.8+Math.random());
        particle(px,py,pz,Math.max(.8,R*.04),.3+.25*Math.random(),emberColor,3,Math.cos(b)*v,1,Math.sin(b)*v,at);
      }
    }
    // Debris: dark tumbling chips (four of them big), each lit by a brief amber glow
    // moving with it.
    for(let j=0;j<14;j++) {
      const big=j<4, a=j*2.399+Math.random()*.4, v=R*(big?1.1+.7*Math.random():.7+.9*Math.random());
      const life=1.2+1.2*Math.random(), vx=Math.cos(a)*v, vz=Math.sin(a)*v;
      const s=big ? Math.min(4,Math.max(.8,R*(.045+.025*Math.random()))) : Math.min(2.2,Math.max(.5,R*(.02+.025*Math.random())));
      particle(x,1.4,z,s,life,j%2?shell:smokeColor,2,vx,R*.15,vz);
      particle(x,1.6,z,s*2.2,.2+.15*Math.random(),emberColor,0,vx,0,vz);
    }
    // Fast sparks out of the core.
    for(let j=0;j<22;j++) {
      const a=Math.random()*TAU, v=R*(1.4+1.8*Math.random());
      particle(x,1.8,z,Math.max(.8,R*.035),.35+.45*Math.random(),j%4?emberColor:goldWhite,3,Math.cos(a)*v,2,Math.sin(a)*v,Math.random()*.05);
    }
    // Embers that drift out slowly; a third of them start late and last 3-4 s.
    for(let j=0;j<18;j++) {
      const late=j%3===0, a=Math.random()*TAU, d=R*.6*Math.random(), v=R*(.08+.25*Math.random());
      particle(x+Math.cos(a)*d,1.6,z+Math.sin(a)*d,Math.max(.4,R*(.02+.02*Math.random())),late?3+Math.random():1.5+1.5*Math.random(),
        emberHot,6,Math.cos(a)*v,.5,Math.sin(a)*v,late?.4+.5*Math.random():.1+.3*Math.random());
    }
    // Smoke: soot that rises and spreads; four puffs carry a hot pocket for a while.
    for(let j=0;j<12;j++) {
      const a=j*2.399+Math.random()*.5, d=R*.5*Math.random(), v=R*(.1+.15*Math.random());
      particle(x+Math.cos(a)*d,1,z+Math.sin(a)*d,R*(.45+.25*Math.random()),2.5+1.5*Math.random(),
        soot,7,Math.cos(a)*v,R*.25,Math.sin(a)*v,.12+.55*Math.random());
      particles[(pc+particles.length-1)%particles.length].hot=j<4;
    }
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
    if (e.kind==='major') { majorExplosion(e); return; }
    const death=e.kind==='death', r=e.radius, c=(death?team:pellet)[e.team] || white;
    particle(e.x,1.5,-e.y,r*(death?4:1.8),death?1.05:.3,c);
    particle(e.x,2,-e.y,r*1.5,death?.28:.14,white);
    wave(e.x,-e.y,r,death?1.1:.38,death?c:white);
    if (death) { flash(e.x,6,-e.y,scratch.copy(c).lerp(white,.45),55*r*r,r*9,.5); ripple(e.x,-e.y,r*3.4,.6,.2,.28); }
    else if (e.kind==='collision') { flash(e.x,5,-e.y,white,500*r,40,.2); ripple(e.x,-e.y,r*4,.32,.1,.3); }
    else flash(e.x,5,-e.y,c,6*r*r,r*7,.16);
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
    if(!quick) {
      wave(p.x,p.z,size*.72,.26,c,4); sparks(p.x,p.z,8,size*.5,c);
      flash(p.x,6,p.z,c,20*size*size,size*7,.25); ripple(p.x,p.z,size*1.8,.4,.28,.3);
    }
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
    const c=team[o.team] || white, x=o.x2, z=-o.y2, r=o.radius ?? (o.kind==='attack'?10:o.kind==='defend'?24:40);
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
    } else if(o.kind==='defend') {
      arc(x,z,r,0,TAU,c,.38,40);
    } else if(o.kind==='goto') {
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
      const end=Math.max(p.size*.12,head-p.size*.55), start=Math.max(-p.size*.2,end-p.size*2.2);
      if(end-start<.5) continue;
      segment(trails,p.x+p.dx*start,2.4,p.z+p.dz*start,p.x+p.dx*end,2.4,p.z+p.dz*end,p.size*.3,p.color,.8*fade);
      segment(lines,p.x+p.dx*(start+end)*.5,2.45,p.z+p.dz*(start+end)*.5,p.x+p.dx*end,2.45,p.z+p.dz*end,.75,white,.65*fade);
    }
  }
  function updateShields(dt) {
    for(const s of shields) {
      if(s.age>=s.max) continue;
      s.age+=dt; if(s.age>=s.max) { s.object=null; continue; }
      // A hull object carries its bubble; without one the response stays where it was.
      if(s.object) { point.setFromMatrixPosition(s.object.matrixWorld); s.x=point.x; s.z=point.z; }
      const b=shieldFx; if(b.n>=b.cap) break;
      const i=b.n;
      put(b,s.x,1.2,s.z,s.radius,s.radius,s.radius,0,s.color,s.strength);
      const h=b.hit.array, m=b.mode.array, j=i*4;
      h[j]=s.dx; h[j+1]=0; h[j+2]=s.dz; h[j+3]=s.age;
      m[j]=s.depleted?1:0; m[j+1]=s.seed; m[j+2]=s.radius; m[j+3]=s.max;
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
        put(chargeRings,c.x,1.3,c.z,r,1,r,0,c.color,f*(.42+.3*e)*Math.sin(Math.PI*u)*(i?.6:1));
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
      // A lick of flame out of the barrel.
      particle(e.x+dx*.5,1.5,-e.y+dz*.5,1.3,.07,c,3,dx*70,0,dz*70);
    },
    hit(e) {
      particle(e.x,1.5,-e.y,6,.18,shot[e.team] || white);
      particle(e.x,1.8,-e.y,2.5,.08,white);
      sparks(e.x,-e.y,5,12,amber);
      particle(e.x,1.2,-e.y,2,.7,smokeColor,1,0,2,0);
      flash(e.x,5,-e.y,hitLight,70,24,.12);
    },
    shieldHit(e) {
      // The event team is the shooter; the defending shield belongs to the other team.
      const c=shield[e.team===0?1:0] || white, r=e.radius, object=e.object || null;
      const nl=Math.hypot(e.nx,e.ny) || 1, nx=e.nx/nl, ny=e.ny/nl;
      const cx=e.x-nx*r, cz=-e.y+ny*r;
      // Responses already live on this shield (same hull object, or same centre).
      let count=0, total=0, oldest=null, latest=null;
      for(const s of shields) {
        if(s.age>=s.max) continue;
        const same=object ? s.object===object : s.object===null && Math.hypot(s.x-cx,s.z-cz)<r*.15 && Math.abs(s.radius-r)<.01;
        if(!same) continue;
        if(e.depleted) { s.age=s.max; continue; }
        count++; total+=s.strength;
        if(!oldest || s.born<oldest.born) oldest=s;
        if(!latest || s.born>latest.born) latest=s;
      }
      // A hit landing right after another, close by, feeds that response instead of
      // starting a new one: sustained fire glows a little harder without restarting
      // the flash, and the shield's summed strength stays within SHIELD_BUDGET.
      if(latest && clock-latest.born<.16 && latest.dx*nx-latest.dz*ny>.85) {
        latest.strength=Math.min(SHIELD_BUDGET-(total-latest.strength),latest.strength+.2);
        return;
      }
      if(!e.depleted) {
        const others=total-(count>=SHIELD_LAYERS?oldest.strength:0), room=SHIELD_BUDGET-SHIELD_STRENGTH;
        if(others>room) for(const q of shields) {
          if(q.age<q.max && q!==oldest && (object ? q.object===object : q.object===null && Math.hypot(q.x-cx,q.z-cz)<r*.15)) q.strength*=room/others;
        }
      }
      let s=null;
      if(count>=SHIELD_LAYERS) s=oldest;
      else {
        // Prefer a free slot; past capacity the round-robin slot is reused.
        for(let i=0;i<shields.length && !s;i++) { const q=shields[(sc+i)%shields.length]; if(q.age>=q.max) { s=q; sc=(sc+i+1)%shields.length; } }
        if(!s) { s=shields[sc++]; if(sc===shields.length)sc=0; }
      }
      s.age=0; s.max=e.depleted?SHIELD_DEPLETED_LIFE:SHIELD_LIFE; s.object=object; s.x=cx; s.z=cz;
      s.dx=nx; s.dz=-ny; s.radius=r; s.color=c; s.depleted=!!e.depleted;
      // One field pattern per hull, so repeated hits light up the same cells.
      s.seed=object ? (object.id*12.9898)%50 : Math.random()*50;
      s.strength=e.depleted?1:SHIELD_STRENGTH; s.born=clock;
      // A pinpoint at the impact, so the strike reads even when the dome is a few pixels.
      particle(e.x,1.8,-e.y,Math.max(3,r*.3),.09,white);
      if(e.depleted) {
        particle(cx,1.2,cz,r*2.6,.3,c);
        flash(cx,5,cz,c,2600,r*6,.3); ripple(cx,cz,r*2.2,.45,.2,.3);
        // The field breaks into flat glowing fragments that fly off the bubble's
        // surface, mostly from the struck side, plus a few sparks.
        for(let j=0;j<18;j++) {
          const a=Math.atan2(-ny,nx)+(Math.random()-.5)*(j<11?2.2:6.28), up=Math.random()*.7;
          const ox=Math.cos(a)*Math.cos(up), oz=Math.sin(a)*Math.cos(up), oy=Math.sin(up)*SHIELD_FLATTEN;
          const v=r*(.8+.6*Math.random()), wait=.1+Math.random()*.3;
          particle(cx+ox*r,1.2+oy*r,cz+oz*r,r*(.06+.06*Math.random()),.25+.3*Math.random(),c,9,ox*v,oy*v,oz*v,wait);
          if(j%3===0) particle(cx+ox*r,1.2+oy*r,cz+oz*r,Math.max(.8,r*.05),.4+.3*Math.random(),white,3,ox*v*1.3,oy*v,oz*v*1.3,wait);
        }
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
      particle(p.x,2.4,p.z,size*2,.28,c);
      particle(p.x,2.5,p.z,size*.85,.18,white);
      particle(p.x-dx*size*.55,.6,p.z-dz*size*.55,size*1.1,.32,c);
      flash(p.x,5,p.z,c,1400,40,.25);
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
      let smokeClock=0, fireClock=0, arcClock=0, index=0, disposed=false, hot=null;
      // The hull's speed, from where it was drawn last frame: a slow ship's smoke stays
      // over it, so it is laid thinner (it never hides the hull it comes from).
      let lastX=NaN, lastZ=NaN, thin=1;
      const points=model.damagePoints || [];
      // Damage mounts span the hull: derive a scale once, without geometry traversal.
      let extent=0;
      for(const p of points) extent=Math.max(extent,Math.abs(p.x),Math.abs(p.z));
      // Small craft stay unchanged; large hulls burn at local vent scale, not hull scale.
      // Even square-root growth engulfed the freighter's cargo and command cab.
      const scale=Math.max(.85,Math.min(1.8,extent/3));
      const freight=model.object.name==='hull.freighter' || model.object.name==='hull.transport';
      const fireScale=scale*(freight?.7:1);
      const electric=new T.Color(0x99ddff);
      return {
        update(hp, alive, dt) {
          if(disposed || !alive || hp>=.7 || !points.length) {
            smokeClock=fireClock=arcClock=0; lastX=NaN; return;
          }
          dt=Math.min(dt,.1);
          point.setFromMatrixPosition(model.object.matrixWorld);
          if(dt>0) {
            const speed=Number.isNaN(lastX)?40:Math.hypot(point.x-lastX,point.z-lastZ)/dt;
            thin+=(Math.max(.34,Math.min(1,speed/38))-thin)*Math.min(1,dt*4);
            lastX=point.x; lastZ=point.z;
          }
          smokeClock+=dt*(hp<.4?14:9);
          // The matrix is read at emission only. Detached particles never follow the hull.
          while(smokeClock>=1) {
            smokeClock--; point.copy(points[index++%points.length]).applyMatrix4(model.object.matrixWorld);
            particle(point.x,point.y+.3,point.z,(3.2+Math.random()*1.6)*scale,1.8+Math.random()*.8,smokeColor,5,
              (Math.random()-.5)*2,2.2,(Math.random()-.5)*2).gain=thin;
          }
          if(hp<.4) {
            fireClock+=dt*(freight?20:30);
            while(fireClock>=1) {
              fireClock--; point.copy(points[index++%Math.min(3,points.length)]).applyMatrix4(model.object.matrixWorld);
              particle(point.x,point.y+.4,point.z,(5+Math.random()*4)*fireScale,.3+Math.random()*.25,fireColor,4,
                (Math.random()-.5)*3,9*scale,(Math.random()-.5)*3);
              particle(point.x,point.y+.5,point.z,(freight?1.8:3)*scale,freight?.12:.16,white);
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
        smoulder(dt, heat) {
          if(disposed || !points.length) return;
          if(!hot) {
            // Fixed on the hull near its damage mounts, each with its own size and pulse.
            hot={model,heat:0,spots:Array.from({length:Math.min(7,3+points.length)},(_,i)=>{
              const p=points[i%points.length];
              return {local:new T.Vector3(p.x+(Math.random()-.5)*.9*scale,p.y+.25,p.z+(Math.random()-.5)*.9*scale),
                size:(.3+Math.random()*.35)*scale,phase:Math.random()*6.283,rate:.6+Math.random()*1.2};
            })};
            hulks.add(hot);
          }
          hot.heat=Math.max(0,Math.min(1,heat));
        },
        dispose() { disposed=true; if(hot) hulks.delete(hot); },
      };
    },
    /**
     * An engine trail in `team`'s colour, `width` metres across at the nozzle. head()
     * every frame the engine is drawn (three.js world position, throttle 0..1); lay()
     * once a sim tick to leave a point behind; cut() when the ship jumps; dispose()
     * frees the ribbon. With every ribbon in use the handle does nothing.
     */
    trail(e) {
      const r=ribbons.find(q=>!q.used);
      if(!r) return { head() {}, lay() {}, cut() {}, dispose() {} };
      r.used=true; r.n=0; r.start=0; r.live=false; r.fresh=false; r.color=trailColor[e.team] || white; r.width=e.width ?? .5;
      return {
        head(x,y,z,level) { r.hx=x; r.hy=y; r.hz=z; r.hlevel=level; r.live=true; r.fresh=true; },
        lay() {
          if(!r.fresh) return;
          r.fresh=false;
          if(r.n>0) {
            const last=(r.start+r.n-1)%TRAIL_NODES, d=Math.hypot(r.hx-r.x[last],r.hz-r.z[last]);
            // Hardly moved: nothing to add. A leap (a jump, a fast-forward): start afresh.
            if(d<.35) return;
            if(d>90) r.n=0;
          }
          if(r.n>=TRAIL_NODES-1) { r.start=(r.start+1)%TRAIL_NODES; r.n--; }
          const i=(r.start+r.n)%TRAIL_NODES;
          r.x[i]=r.hx; r.z[i]=r.hz; r.level[i]=r.hlevel; r.born[i]=clock; r.n++;
        },
        cut() { r.n=0; r.live=false; r.fresh=false; },
        dispose() { r.used=false; r.n=0; r.live=false; r.fresh=false; },
      };
    },
    /**
     * Running lights at the hull model's `strobes`: show(true) every frame the hull is
     * on the field keeps them flashing.
     */
    beacons(model, teamIndex) {
      const set={ model, color: beaconColor[teamIndex] || white, phase: Math.random()*2.4, on: false };
      if(model.strobes && model.strobes.length) beaconSets.add(set);
      return { show(on) { set.on=on; }, dispose() { beaconSets.delete(set); } };
    },
    update(dt) {
      dt=Math.max(0,Math.min(dt,.1));
      fires.n=embers.n=emberHalos.n=shards.n=glow.n=flames.n=smoke.n=chips.n=rings.n=bolts.n=trails.n=lines.n=streaks.n=thin.n=chargeRings.n=shocks.n=shieldFx.n=0;
      clock+=dt;
      updateFlashes(dt);
      const height=Math.max(1,renderer.domElement.clientHeight || renderer.domElement.height);
      trails.mesh.material.uniforms.viewportHeight.value=height;
      lines.mesh.material.uniforms.viewportHeight.value=height;
      streaks.mesh.material.uniforms.viewportHeight.value=height;
      trailMat.uniforms.viewportHeight.value=height;
      flames.mesh.material.uniforms.time.value=clock;
      chargeRings.mesh.material.uniforms.viewportHeight.value=height;
      shocks.mesh.material.uniforms.viewportHeight.value=height;
      embers.mesh.material.uniforms.viewportHeight.value=height;
      emberHalos.mesh.material.uniforms.viewportHeight.value=height;
      fires.mesh.material.uniforms.time.value=clock;
      shieldFx.mesh.material.uniforms.time.value=clock;
      for(const o of orders) order(o);
      updateShields(dt);
      for(const s of shocksLive) {
        if(s.life<=0)continue;
        if(s.wait>0) { s.wait-=dt; continue; }
        s.life-=dt; if(s.life<=0)continue;
        // Cubic ease-out: the front leaves fast and slows as it thins.
        const t=1-s.life/s.max, r=s.radius*(.1+.9*(1-(1-t)**3));
        put(shocks,s.x,1.1,s.z,r,1,r,0,s.color,s.alpha*(1-t)**2);
      }
      for(const p of launches) if(p.life>0) p.life-=dt;
      updateLaunches();
      // Charges run before the particle pass so their sparks are drawn this frame.
      updateCharges(dt);
      for(const p of particles) {
        if(p.life<=0)continue;
        if(p.wait>0) { p.wait-=dt; continue; }
        p.life-=dt; if(p.life<=0)continue;
        const t=1-p.life/p.max, fade=1-t;
        p.x+=p.vx*dt;p.y+=p.vy*dt;p.z+=p.vz*dt;
        if(p.kind===1) {
          const size=p.size*(1.15+t*2.5);
          put(smoke,p.x,p.y,p.z,size,size,1,0,p.color,.82*Math.min(1,(1-t)*3),0,p.angle,t,0);
        } else if(p.kind===5) {
          // Damage trail: faint over the hull so a slow ship stays visible, fuller once it has drifted off.
          const size=p.size*(1.15+t*2.8);
          put(smoke,p.x,p.y,p.z,size,size,1,0,p.color,.5*p.gain*(.25+.75*Math.min(1,t*4))*Math.min(1,(1-t)*3),0,p.angle,t,0);
        } else if(p.kind===7) {
          // Hot smoke: lit orange from within, cooling to soot as it rises and spreads.
          const size=p.size*(1.1+t*1.8), heat=Math.max(0,1-t*1.8);
          p.vx*=1-dt*.6; p.vz*=1-dt*.6;
          put(smoke,p.x,p.y,p.z,size,size,1,0,p.color,.5*Math.min(1,t*8)*(1-t)**1.3,0,p.angle,t,p.hot?heat*heat:heat*heat*.3);
        } else if(p.kind===8) {
          // Fire cloud (shaded from its age): it billows out and slows.
          p.vx*=1-dt*1.5; p.vz*=1-dt*1.5;
          const size=p.size*(.62+1.6*(1-(1-t)**2)), aspect=.8+.4*p.angle/6.283;
          put(fires,p.x,p.y,p.z,size*aspect,size/aspect,1,0,p.color,.92*Math.min(1,t*14)*(1-t)**.6,0,p.angle,t,p.hot?1:0);
        } else if(p.kind===6) {
          // Ember: a hot point that slows, flickers and dims.
          p.vx*=1-dt*.9; p.vz*=1-dt*.9;
          const flick=.65+.35*Math.sin(clock*31+p.angle*7)*Math.sin(clock*17+p.angle);
          const size=p.size*(1-t*.5);
          put(embers,p.x,p.y,p.z,size,size,1,0,p.color,fade**1.2*flick);
          put(emberHalos,p.x,p.y,p.z,size*2.5,size*2.5,1,0,p.color,.18*fade**1.2*flick);
        } else if(p.kind===9) {
          // A fragment of a collapsed shield: flat, tumbling, shrinking.
          const size=p.size*(1-t*.6);
          put(shards,p.x,p.y,p.z,size,size,size,p.angle+t*4,p.color,fade*fade*.8,t*3+p.angle);
        } else if(p.kind===2) {
          p.vy-=dt*7;
          const size=p.size*(1-t*.65);
          put(chips,p.x,p.y,p.z,size,size*.4,size*.7,p.angle+t*3,p.color,fade,t*4+p.angle);
        } else if(p.kind===3) {
          // Spark: a streak along its own velocity, slowing and shortening.
          p.vx*=1-dt*2.4; p.vz*=1-dt*2.4;
          const speed=Math.hypot(p.vx,p.vz) || 1, len=Math.max(.8,speed*.065);
          segment(streaks,p.x-p.vx/speed*len,p.y,p.z-p.vz/speed*len,p.x,p.y,p.z,Math.max(.1,p.size*.14),p.color,fade*1.5);
        } else if(p.kind===4) {
          const size=p.size*(.85-t*.4);
          put(flames,p.x,p.y+size*.45,p.z,size,size*1.9,1,0,p.color,fade*.6,0,p.angle,t,0);
        } else {
          const size=p.size*(1+t*.7);
          put(glow,p.x,p.y,p.z,size,size,1,0,p.color,fade*fade*.9);
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
        // The mirror of the departure: a soft sheath and a hot core, wide at the ship.
        segment(trails,x-dx*tail,1.4,z-dz*tail,x,1.4,z,p.size*.5,p.color,.9*fade);
        segment(lines,x-dx*tail*.85,1.5,z-dz*tail*.85,x,1.5,z,Math.max(.9,p.size*.07),white,fade);
        if(travel===1 && !p.landed) {
          p.landed=true;particle(p.x,2,p.z,p.size*5,.38,p.color);
          particle(p.x,2,p.z,p.size*2,.18,white);
          flash(p.x,6,p.z,p.color,26*p.size*p.size,p.size*8,.35); ripple(p.x,p.z,p.size*2.4,.45,.24,.3);
        }
      }
      finish(glow);finish(flames);finish(smoke);finish(chips);finish(rings);finish(bolts);
      finish(trails);finish(lines);finish(streaks);finish(thin);finish(chargeRings);finish(shocks);
      updateTrails();
      // Running lights: a double flash every 2.4 s, each hull on its own beat.
      for(const set of beaconSets) {
        if(!set.on || !set.model.object.visible) { set.on=false; continue; }
        set.on=false;
        const beat=(clock+set.phase)%2.4;
        if(!(beat<.07 || (beat>.2 && beat<.27))) continue;
        for(const s of set.model.strobes) {
          point.copy(s).applyMatrix4(set.model.object.matrixWorld);
          put(embers,point.x,point.y+.3,point.z,.45,.45,1,0,set.color,1);
          put(emberHalos,point.x,point.y+.3,point.z,2.2,2.2,1,0,set.color,.4);
        }
      }
      for(const h of hulks) {
        if(h.heat<=0 || !h.model.object.visible) continue;
        for(const s of h.spots) {
          point.copy(s.local).applyMatrix4(h.model.object.matrixWorld);
          const glowing=h.heat*(.7+.3*Math.sin(clock*s.rate+s.phase));
          put(embers,point.x,point.y,point.z,s.size,s.size,1,0,emberDim,glowing);
          put(emberHalos,point.x,point.y,point.z,s.size*3,s.size*3,1,0,emberDim,.22*glowing);
        }
        h.heat=0;
      }
      finish(fires);finish(embers);finish(emberHalos);finish(shards);
      finish(shieldFx);
      if(shieldFx.n) { upload(shieldFx.hit,shieldFx.n); upload(shieldFx.mode,shieldFx.n); }
    },
    // Optional lifecycle hook for embeds; normal harness keeps one Effects for its lifetime.
    dispose() {
      for(const b of resources) { scene.remove(b.mesh);b.mesh.geometry.dispose();b.mesh.material.dispose(); }
      for(const f of flashes) scene.remove(f.light);
      scene.remove(trailMesh);trailGeo.dispose();trailMat.dispose();
    },
  };
}
