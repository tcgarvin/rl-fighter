// Linear HDR photography pipeline. The scene is drawn once into a half-float target;
// a small pyramid of it gives the halation (a tight warm halo with a long soft tail)
// and the anamorphic streak, and one lens/output pass adds them back with shockwave
// refraction, a trace of chromatic aberration, the teal shadow grade, vignette, tone
// mapping and grain.
//
// Beyond the treatment contract (init, materials, render, onResize) the live page uses:
//   setSun(side, rimTint)   the screen side the scenery's main body hangs on (-1 left,
//                           1 right): the key light comes from the other side, the
//                           rim from this one, leaning toward rimTint (the planet's air)
//   ripple({x, y, z, radius, life, strength, width, wait, inward})
//                           a ring of refraction on the battle plane, world metres
//   enableShadows(renderer) the key light casts shadows; fitShadows(camera) each frame
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { noiseTexture } from '../noise.js';

const TEAM = [0x369bd9, 0xe77832];
const KEY_COLOR = 0xffc58a, RIM_COLOR = 0x69cde5;
// The key light: this far round from the screen's side axis toward the viewer, and this
// high above the battle plane (radians). Its side flips with the match's scenery.
const KEY_AZIMUTH = .66, KEY_ELEVATION = .59;
const RIM_AZIMUTH = 1.0, RIM_ELEVATION = .27;
const BLOOM_LEVELS = 5, STREAK_LEVELS = 3, RIPPLES = 6;
// Each wider level of the halation pyramid adds this much of itself to the one below.
const WIDE_GAIN = .55;
// Shadows: the map follows the part of the battle plane on screen. Past
// SHADOW_FADE_TEXEL metres a texel they say nothing and are faded out and not drawn.
const SHADOW_MAP = 2048, SHADOW_FADE_TEXEL = [.17, .3], SHADOW_MIN_RADIUS = 40;
const cache = new Map();
let source, halo, quad, postScene, postCamera, prefilter, down, up, streakDown, finish, activeRenderer;
let key, rim, sunSide = 1, shadows = false;
const levels = [], streaks = [];
const bufferSize = new THREE.Vector2();
const rimBase = new THREE.Color(RIM_COLOR);
const vertexShader = `varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}`;
function pass(fragmentShader, uniforms, additive = false) {
  return new THREE.ShaderMaterial({
    vertexShader, fragmentShader, uniforms, depthTest: false, depthWrite: false,
    ...(additive ? { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor } : { blending: THREE.NoBlending }),
  });
}
// Half-float targets on iOS can hold Inf/NaN from hot specular; one bad texel spreads
// through the blur pyramid into black blocks, so every HDR read is made finite.
const SAFE = `vec3 safe(vec3 c){return (any(isnan(c))||any(isinf(c)))?vec3(0.):clamp(c,0.,64.);}`;
function target(depthBuffer = false) {
  return new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
}
function draw(renderer, material, destination, keep = false) {
  quad.material = material;
  renderer.setRenderTarget(destination);
  if (keep) { renderer.autoClear = false; renderer.render(postScene, postCamera); renderer.autoClear = true; }
  else renderer.render(postScene, postCamera);
}

// ---- Shockwave refraction ----
const ripples = Array.from({ length: RIPPLES }, () => ({ life: 0, max: 1, wait: 0, x: 0, y: 0, z: 0, radius: 1, strength: 0, width: .25, inward: false }));
const rippleA = new Float32Array(RIPPLES * 4), rippleB = new Float32Array(RIPPLES * 4);
const centre = new THREE.Vector3(), probe = new THREE.Vector3(), axisX = new THREE.Vector3(), axisZ = new THREE.Vector3();
let rippleNext = 0;
function updateRipples(camera, dt) {
  let n = 0;
  for (const r of ripples) {
    if (r.life <= 0) continue;
    if (r.wait > 0) { r.wait -= dt; continue; }
    r.life -= dt;
    if (r.life <= 0) continue;
    const t = 1 - r.life / r.max;
    // A blast front leaves fast and slows as it thins; a collapse runs the other way.
    const grow = r.inward ? 1 - t * t : .12 + .88 * (1 - (1 - t) ** 3);
    const radius = r.radius * grow;
    // The ring lies on the battle plane: an ellipse on screen, measured by two probes.
    centre.set(r.x, r.y, r.z).project(camera);
    probe.set(r.x, r.y, r.z).addScaledVector(axisX, radius).project(camera);
    const rx = Math.hypot(probe.x - centre.x, probe.y - centre.y) * .5;
    probe.set(r.x, r.y, r.z).addScaledVector(axisZ, radius).project(camera);
    const ry = Math.hypot(probe.x - centre.x, probe.y - centre.y) * .5;
    if (!(rx > 1e-5 && ry > 1e-5)) continue;
    const j = n * 4;
    rippleA[j] = centre.x * .5 + .5; rippleA[j + 1] = centre.y * .5 + .5; rippleA[j + 2] = rx; rippleA[j + 3] = ry;
    rippleB[j] = r.strength * (r.inward ? t * (1 - t) * 4 : (1 - t) ** 1.5); rippleB[j + 1] = r.width;
    n++;
  }
  finish.uniforms.rippleCount.value = n;
}

// ---- Hull surface detail ----
// Plating on the flat hull kit: rows of plates with thin seams and their own tone, each
// cut once more by a fainter line; broad scuffing and fine grit in the roughness, so
// the clearcoat catches the lights unevenly. Lines fade out before they would alias;
// from far off only the broad variation is left. Where the key light is shadowed the
// sky's fill is cut back too, so a turret's shadow reads on any paint.
// style = (plate length m, plate width m, seam darkness, tone range).
//
// Every hull material also caps what it writes (BOUNDED). A flat plate under a flash
// light can reflect it into the camera all at once, and a smooth plate's highlight can
// then run past what a half-float target holds. Some GPUs saturate there; one that
// stores infinity instead would hand the lens pass a pixel it can only turn black (the
// iOS failure this file already guards its reads against). It has not been seen to
// happen; the plating's roughness floor and this cap (well past white) rule it out.
const HULL_MAX = 24, PLATE_ROUGHNESS_MIN = .18;
const BOUNDED = `#include <opaque_fragment>\n\tgl_FragColor.rgb=clamp(gl_FragColor.rgb,0.,${HULL_MAX.toFixed(1)});`;
/** A hull material without plating (markings, lit trim): only the cap on its output. */
function bounded(material) {
  material.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace('#include <opaque_fragment>', BOUNDED);
  };
  return material;
}
const SHADOWED = THREE.ShaderChunk.lights_fragment_begin.replace(
  /directLight\.color \*= (\( directLight\.visible && receiveShadow \) \? getShadow\( directionalShadowMap\[ i \][^;]*);/,
  'float hullLit = $1; directLight.color *= hullLit; hullShade = min( hullShade, hullLit );');
if (SHADOWED === THREE.ShaderChunk.lights_fragment_begin) throw new Error('cinematic: three\'s directional shadow line has moved; update the hull shader patch');
function detailed(material, style) {
  const uniforms = { hullNoise: { value: noiseTexture() }, hullStyle: { value: new THREE.Vector4(...style) } };
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vHullPos; varying vec3 vHullNormal;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvHullPos=position; vHullNormal=normal;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform sampler2D hullNoise; uniform vec4 hullStyle; varying vec3 vHullPos; varying vec3 vHullNormal;
        float hullHash(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
        {
          vec2 q=vHullPos.xz, plate=hullStyle.xy;
          float top=smoothstep(.55,.85,abs(normalize(vHullNormal).y));
          float px=max(length(dFdx(vHullPos)),length(dFdy(vHullPos)));
          float near=1.-smoothstep(.12,.42,px), close=1.-smoothstep(.05,.17,px);
          // Rows of plates, each row slid by its own amount.
          vec2 cell=q/plate; cell.x+=hullHash(vec2(floor(cell.y),7.));
          vec2 id=floor(cell), f=fract(cell);
          vec2 edge=min(f,1.-f)*plate;
          float seam=(1.-smoothstep(.02,.028+px*1.4,min(edge.x,edge.y)))*near;
          // One fainter cut through each plate, along it or across.
          float cut=hullHash(id+3.1);
          float off=cut<.5?abs(f.x-(.32+.36*hullHash(id+5.7)))*plate.x:abs(f.y-.5)*plate.y;
          float fine=(1.-smoothstep(.012,.018+px*1.4,off))*close;
          float tone=hullHash(id);
          float wear=texture2D(hullNoise,q*.043+vHullPos.y*.09).r;
          float grit=texture2D(hullNoise,q*.37+vec2(vHullPos.y*.21,0.)).g;
          // Sides: soot streaks running down from the deck edge.
          float streak=texture2D(hullNoise,vec2((q.x+q.y)*.31,vHullPos.y*.045)).g;
          diffuseColor.rgb*=1.-(seam+fine*.45)*hullStyle.z*top;
          diffuseColor.rgb*=mix(1.,1.-hullStyle.w*.5+hullStyle.w*tone,top*(.35+.65*near));
          diffuseColor.rgb*=mix(.76+.36*streak,.93+.14*wear,top);
          roughnessFactor=clamp(roughnessFactor+(wear-.5)*.34+(tone-.5)*.12*top+(grit-.5)*.16*close,${PLATE_ROUGHNESS_MIN},1.);
        }`)
      .replace('#include <opaque_fragment>', BOUNDED)
      .replace('#include <lights_fragment_begin>', `float hullShade=1.;\n${SHADOWED}`)
      .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        reflectedLight.indirectDiffuse*=mix(.42,1.,hullShade);
        reflectedLight.indirectSpecular*=mix(.3,1.,hullShade);`);
  };
  return material;
}

// ---- Engine plume ----
// One soft cone per thruster (hullgeo's unit plume, +X downstream): bright where the
// view passes through the most of it, white-hot at the nozzle, with standing shock
// diamonds at high throttle. hullgeo sets `level` (throttle) and `seed` per plume.
function plumeMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 }, level: { value: 1 }, seed: { value: 0 },
      hot: { value: new THREE.Color(0xf3fbff).multiplyScalar(4.2) }, body: { value: new THREE.Color(0x8fd0ff).multiplyScalar(2.3) }, tail: { value: new THREE.Color(0x3f8fe0).multiplyScalar(1.5) } },
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
    vertexShader: `varying float vAlong; varying vec3 vNormal; varying vec3 vView;
      void main(){
        vAlong=position.x;
        vec4 world=modelMatrix*vec4(position,1.);
        // The plume's own scale is far from uniform: take the normal through the inverse transpose.
        vNormal=normalize(mat3(transpose(inverse(modelMatrix)))*normal);
        vView=cameraPosition-world.xyz;
        gl_Position=projectionMatrix*viewMatrix*world;
      }`,
    fragmentShader: `uniform float time, level, seed; uniform vec3 hot, body, tail;
      varying float vAlong; varying vec3 vNormal; varying vec3 vView;
      void main(){
        float x=clamp(vAlong,0.,1.);
        // (The tip's normal can vanish: divide by a floored length, not normalize.)
        float facing=abs(dot(vNormal/max(length(vNormal),1e-4),normalize(vView)));
        // Both faces add: thick through the middle, nothing at the silhouette.
        float depth=facing*facing*(3.-2.*facing);
        float flicker=.9+.1*sin(time*71.+seed*19.+x*11.)*sin(time*43.+seed*7.);
        float power=clamp(level,0.,1.4);
        float diamonds=1.+smoothstep(.5,1.,power)*1.1*pow(.5+.5*cos(x*44.-1.),4.)*exp(-x*6.);
        float fall=pow(1.-x,1.6)*smoothstep(0.,.02,x);
        vec3 col=mix(tail,body,smoothstep(.75,.12,x));
        col=mix(col,hot,smoothstep(.3,0.,x)*depth);
        gl_FragColor=vec4(col*depth*fall*diamonds*flicker*(.5+.55*power),1.);
      }`,
  });
}
let plume = null;

export default {
  id: 'cinematic',
  name: 'Cinematic',
  blurb: 'Dense teal shadows, amber key light, anamorphic flares and silver-grain optics.',
  hud: { '--bg': '#060a10', '--fg': '#e5e1d8', '--muted': '#8c99a8', '--team-a': '#63bfff', '--team-b': '#ffae69', '--font': '"Helvetica Neue", Arial, sans-serif' },
  fonts: [],
  palette: { team: TEAM, exhaust: 0xc4e8ff, projectile: [0x8bcfff, 0xffba73], shield: [0x65bfff, 0xff9d58] },
  /** World-space unit vector toward the key light, and its colour (linear). */
  sun: { direction: new THREE.Vector3(-.657, .555, .511), color: new THREE.Color(KEY_COLOR), shade: new THREE.Color(0x2b4f63) },

  init({ scene, renderer }) {
    activeRenderer = renderer;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    const room = new RoomEnvironment();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const environment = pmrem.fromScene(room, 0.06);
    scene.environment = environment.texture;
    scene.environmentIntensity = 0.18;
    room.dispose();
    pmrem.dispose();
    key = new THREE.DirectionalLight(KEY_COLOR, 4.6);
    key.position.set(-450, 380, 350);
    const fill = new THREE.HemisphereLight(0x659cae, 0x030813, 0.32);
    rim = new THREE.DirectionalLight(RIM_COLOR, 2.4);
    rim.position.set(350, 180, -550);
    scene.add(key, key.target, fill, rim, rim.target);

    source = target(true);
    // The canvas MSAA does not apply to offscreen HDR targets.
    source.samples = 2;
    halo = target();
    for (let i = 0; i < BLOOM_LEVELS; i++) levels.push(target());
    for (let i = 0; i < STREAK_LEVELS; i++) streaks.push(target());
    postScene = new THREE.Scene();
    postCamera = new THREE.Camera();
    quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.MeshBasicMaterial());
    quad.frustumCulled = false;
    postScene.add(quad);
    // Quarter resolution: what is brighter than the film's shoulder, box-filtered.
    prefilter = pass(`varying vec2 vUv; uniform sampler2D image; uniform vec2 texel;
      ${SAFE}
      vec3 threshold(vec2 p){vec3 c=safe(texture2D(image,p).rgb);float l=max(c.r,max(c.g,c.b));return c*max(l-.7,0.)/max(l,.001);}
      void main(){vec3 c=threshold(vUv+texel*vec2(-1.,-1.))+threshold(vUv+texel*vec2(1.,-1.))+threshold(vUv+texel*vec2(-1.,1.))+threshold(vUv+texel*vec2(1.,1.));gl_FragColor=vec4(c*.25,1.);}`,
      { image: { value: source.texture }, texel: { value: new THREE.Vector2() } });
    // The pyramid: each level halves the last (five taps), then they are added back up
    // through a tent filter, the wide levels fainter, into one smooth quarter-res halo.
    down = pass(`varying vec2 vUv;uniform sampler2D image;uniform vec2 texel;
      void main(){vec3 c=texture2D(image,vUv).rgb*4.;
      c+=texture2D(image,vUv+texel).rgb+texture2D(image,vUv-texel).rgb;
      c+=texture2D(image,vUv+vec2(texel.x,-texel.y)).rgb+texture2D(image,vUv-vec2(texel.x,-texel.y)).rgb;
      gl_FragColor=vec4(c*.125,1.);}`, { image: { value: null }, texel: { value: new THREE.Vector2() } });
    const tent = `varying vec2 vUv;uniform sampler2D image;uniform vec2 texel;uniform float gain;
      void main(){vec3 c=texture2D(image,vUv+vec2(-2.*texel.x,0.)).rgb+texture2D(image,vUv+vec2(2.*texel.x,0.)).rgb
        +texture2D(image,vUv+vec2(0.,2.*texel.y)).rgb+texture2D(image,vUv+vec2(0.,-2.*texel.y)).rgb;
      c+=2.*(texture2D(image,vUv+texel).rgb+texture2D(image,vUv-texel).rgb
        +texture2D(image,vUv+vec2(texel.x,-texel.y)).rgb+texture2D(image,vUv-vec2(texel.x,-texel.y)).rgb);
      gl_FragColor=vec4(c*gain/12.,1.);}`;
    up = pass(tent, { image: { value: null }, texel: { value: new THREE.Vector2() }, gain: { value: 1 } }, true);
    // The anamorphic streak: the quarter-res highlights squeezed 4:1 sideways, three
    // times over, each level read directly (and so stretched) by the output pass.
    streakDown = pass(`varying vec2 vUv;uniform sampler2D image;uniform vec2 texel;
      void main(){gl_FragColor=vec4((texture2D(image,vUv-texel).rgb+texture2D(image,vUv+texel).rgb
        +texture2D(image,vUv-vec2(texel.x,-texel.y)).rgb+texture2D(image,vUv+vec2(texel.x,-texel.y)).rgb)*.25,1.);}`,
      { image: { value: null }, texel: { value: new THREE.Vector2() } });
    finish = pass(`varying vec2 vUv;uniform sampler2D image;${SAFE}uniform sampler2D bloom;uniform sampler2D streak0;uniform sampler2D streak1;uniform sampler2D streak2;uniform float time;
      uniform vec4 rippleA[${RIPPLES}];uniform vec4 rippleB[${RIPPLES}];uniform int rippleCount;
      void main(){
        vec2 uv=vUv;
        // Shockwaves bend the picture: each is a ring where the image is pushed outward
        // ahead of the front and pulled back behind it.
        for(int i=0;i<rippleCount;i++){
          vec2 d=(vUv-rippleA[i].xy)/rippleA[i].zw;float r=length(d);
          float x=(r-1.)/rippleB[i].y;
          uv+=d/max(r,.001)*rippleA[i].zw*x*exp(-x*x)*rippleB[i].x;
        }
        vec2 p=vUv-.5;float edge=dot(p,p);
        vec3 c=texture2D(image,uv).rgb;
        // Lateral colour only where it reaches a visible fraction of a pixel.
        if(edge>.09){vec2 ca=p*edge*.0018;c.r=texture2D(image,uv+ca).r;c.b=texture2D(image,uv-ca).b;}
        c=safe(c);
        vec3 glow=safe(texture2D(bloom,vUv).rgb);
        vec3 flare=safe(texture2D(streak0,vUv).rgb*.34+texture2D(streak1,vUv).rgb*.4+texture2D(streak2,vUv).rgb*.26);
        // Warm local halation and a cool, long anamorphic ghost.
        c+=glow*vec3(.50,.27,.18)+flare*vec3(.4,.85,1.25);
        float l=dot(c,vec3(.2126,.7152,.0722));
        float shadow=1.-smoothstep(.015,.55,l);
        c=mix(vec3(l),c,1.08);
        c*=mix(vec3(1.09,1.015,.88),vec3(.66,1.02,1.12),shadow*.8);
        c+=vec3(.001,.006,.009)*shadow;
        // Soft aperture falloff evokes a wide film gate without hiding the HUD.
        float gate=smoothstep(.25,.5,abs(p.y));
        c*=1.-.38*smoothstep(.045,.46,edge);
        c*=1.-.38*gate;
        gl_FragColor=vec4(c,1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        float grain=fract(sin(dot(gl_FragCoord.xy+mod(time,100.)*vec2(37.,17.),vec2(12.9898,78.233)))*43758.5453)-.5;
        gl_FragColor.rgb+=grain*.014;
      }`, { image: { value: source.texture }, bloom: { value: halo.texture }, streak0: { value: streaks[0].texture }, streak1: { value: streaks[1].texture }, streak2: { value: streaks[2].texture },
      time: { value: 0 }, rippleA: { value: rippleA }, rippleB: { value: rippleB }, rippleCount: { value: 0 } });
    this.setSun(1, null);
    this.onResize();
  },

  materials(team) {
    if (!cache.has(team)) cache.set(team, {
      paint: detailed(new THREE.MeshPhysicalMaterial({ color: TEAM[team], metalness: .48, roughness: .32, clearcoat: .65, clearcoatRoughness: .27 }), [4.2, 2.1, .3, .1]),
      trim: detailed(new THREE.MeshStandardMaterial({ color: team === 0 ? 0xbacbd2 : 0xe0c7a6, metalness: .72, roughness: .29 }), [3.4, 1.7, .2, .07]),
      machinery: detailed(new THREE.MeshStandardMaterial({ color: 0x26313f, metalness: .8, roughness: .42 }), [1.1, .7, .45, .26]),
      marking: bounded(new THREE.MeshStandardMaterial({ color: 0xf1ede0, metalness: .2, roughness: .43 })),
      glow: bounded(new THREE.MeshStandardMaterial({ color: 0xa4dfff, emissive: team === 0 ? 0x6bc6ff : 0xffa15a, emissiveIntensity: 3.2, roughness: .3 })),
      exhaust: plume ??= plumeMaterial(),
    });
    return cache.get(team);
  },

  /**
   * Aim the lights for a match whose main body hangs on screen side `side` (-1 left, 1
   * right): the key comes from the other side and behind the viewer (the sun that
   * lights the planet's near face), the rim from the planet's side, leaning toward
   * `rimTint` (the light off it). fitShadows() turns this into world directions.
   */
  setSun(side, rimTint) {
    sunSide = side < 0 ? -1 : 1;
    if (rim) rim.color.copy(rimBase).lerp(rimTint ?? rimBase, rimTint ? .3 : 0);
  },

  ripple(e) {
    const r = ripples[rippleNext++]; if (rippleNext === RIPPLES) rippleNext = 0;
    r.x = e.x; r.y = e.y ?? 0; r.z = e.z; r.radius = e.radius; r.life = r.max = e.life ?? .6; r.wait = e.wait ?? 0;
    r.strength = e.strength ?? .05; r.width = e.width ?? .25; r.inward = !!e.inward;
  },

  /** The key light casts shadows from now on (the live page; the hull cards do without). */
  enableShadows(renderer) {
    shadows = true;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    key.castShadow = true;
    key.shadow.mapSize.set(SHADOW_MAP, SHADOW_MAP);
    key.shadow.normalBias = .03;
    key.shadow.autoUpdate = false;
  },

  /**
   * Light the scene from the camera's point of view and fit the shadow map to the part
   * of the battle plane on screen (snapped to its texels, so shadows don't swim).
   */
  fitShadows(camera) {
    // Screen-right and toward-the-viewer along the ground.
    axisX.setFromMatrixColumn(camera.matrixWorld, 0); axisX.y = 0; axisX.normalize();
    axisZ.setFromMatrixColumn(camera.matrixWorld, 2); axisZ.y = 0; axisZ.normalize();
    const sun = this.sun.direction, ce = Math.cos(KEY_ELEVATION);
    sun.set(0, Math.sin(KEY_ELEVATION), 0).addScaledVector(axisX, -sunSide * Math.cos(KEY_AZIMUTH) * ce).addScaledVector(axisZ, Math.sin(KEY_AZIMUTH) * ce);
    // Where the screen's corners meet the battle plane.
    let cx = 0, cz = 0, radius = 0;
    const corners = [];
    for (const [u, v] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      probe.set(u, v, .5).unproject(camera).sub(camera.position);
      const t = probe.y < -1e-6 ? -camera.position.y / probe.y : 1e5;
      const x = camera.position.x + probe.x * t, z = camera.position.z + probe.z * t;
      corners.push(x, z); cx += x / 4; cz += z / 4;
    }
    for (let i = 0; i < 8; i += 2) radius = Math.max(radius, Math.hypot(corners[i] - cx, corners[i + 1] - cz));
    key.target.position.set(cx, 0, cz);
    key.position.copy(key.target.position).addScaledVector(sun, 600);
    rim.target.position.copy(key.target.position);
    const cr = Math.cos(RIM_ELEVATION);
    rim.position.set(0, Math.sin(RIM_ELEVATION), 0).addScaledVector(axisX, sunSide * Math.cos(RIM_AZIMUTH) * cr).addScaledVector(axisZ, -Math.sin(RIM_AZIMUTH) * cr).multiplyScalar(600).add(rim.target.position);
    if (!shadows) return;
    // The map's span steps in ratios of 1.25, so easing zooms don't rescale it each frame.
    const span = SHADOW_MIN_RADIUS * 1.25 ** Math.ceil(Math.log(Math.max(radius, SHADOW_MIN_RADIUS) / SHADOW_MIN_RADIUS) / Math.log(1.25));
    const texel = (2 * span) / SHADOW_MAP;
    const strength = 1 - THREE.MathUtils.smoothstep(texel, SHADOW_FADE_TEXEL[0], SHADOW_FADE_TEXEL[1]);
    const shadow = key.shadow;
    shadow.intensity = strength;
    shadow.needsUpdate = strength > 0;
    if (strength <= 0) return;
    // Snap the map's centre to whole texels in the light's own frame.
    const lightX = probe.crossVectors(sun, THREE.Object3D.DEFAULT_UP).normalize();
    const lightY = centre.crossVectors(lightX, sun).normalize();
    const px = key.target.position.dot(lightX), py = key.target.position.dot(lightY), pz = key.target.position.dot(sun);
    key.target.position.set(0, 0, 0).addScaledVector(lightX, Math.round(px / texel) * texel).addScaledVector(lightY, Math.round(py / texel) * texel).addScaledVector(sun, pz);
    const dist = span + 120;
    key.position.copy(key.target.position).addScaledVector(sun, dist);
    const c = shadow.camera;
    if (c.right !== span) { c.left = -span; c.right = span; c.top = span; c.bottom = -span; c.near = 20; c.far = dist + span + 100; c.updateProjectionMatrix(); }
    // Depth bias in metres (a texel's worth of slope, and a little), as a fraction of the depth range.
    shadow.bias = -(texel * .7 + .02) / (c.far - c.near);
    key.target.updateMatrixWorld();
    key.updateMatrixWorld();
  },

  render(renderer, scene, camera, dt) {
    if (plume) plume.uniforms.time.value += dt;
    updateRipples(camera, dt);
    renderer.setRenderTarget(source);
    renderer.render(scene, camera);
    draw(renderer, prefilter, levels[0]);
    for (let i = 1; i < BLOOM_LEVELS; i++) {
      down.uniforms.image.value = levels[i - 1].texture;
      down.uniforms.texel.value.set(1 / levels[i - 1].width, 1 / levels[i - 1].height);
      draw(renderer, down, levels[i]);
    }
    for (let i = BLOOM_LEVELS - 1; i > 1; i--) {
      up.uniforms.image.value = levels[i].texture;
      up.uniforms.texel.value.set(.5 / levels[i].width, .5 / levels[i].height);
      up.uniforms.gain.value = WIDE_GAIN;
      draw(renderer, up, levels[i - 1], true);
    }
    up.uniforms.image.value = levels[1].texture;
    up.uniforms.texel.value.set(.5 / levels[1].width, .5 / levels[1].height);
    up.uniforms.gain.value = 1;
    draw(renderer, up, halo);
    for (let i = 0; i < STREAK_LEVELS; i++) {
      // The first level softens the quarter-res highlights a little up and down as well.
      const from = i ? streaks[i - 1] : levels[0];
      streakDown.uniforms.image.value = from.texture;
      streakDown.uniforms.texel.value.set(1 / from.width, i ? 0 : .75 / from.height);
      draw(renderer, streakDown, streaks[i]);
    }
    finish.uniforms.time.value += dt;
    draw(renderer, finish, null);
  },

  onResize() {
    if (!activeRenderer) return;
    activeRenderer.getDrawingBufferSize(bufferSize);
    const w = bufferSize.x, h = bufferSize.y;
    source.setSize(w, h);
    let bw = Math.max(1, Math.ceil(w / 4)), bh = Math.max(1, Math.ceil(h / 4));
    halo.setSize(bw, bh);
    let sw = bw;
    for (const s of streaks) { sw = Math.max(1, Math.ceil(sw / 4)); s.setSize(sw, bh); }
    for (const level of levels) { level.setSize(bw, bh); bw = Math.max(1, Math.ceil(bw / 2)); bh = Math.max(1, Math.ceil(bh / 2)); }
    prefilter.uniforms.texel.value.set(1 / w, 1 / h);
  },
};
