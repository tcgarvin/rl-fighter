// Linear HDR photography pipeline: quarter-resolution halation, then one lens/output pass.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const TEAM = [0x369bd9, 0xe77832];
const cache = new Map();
let source, bright, blur, bloom, streakBuffer, anamorphic, quad, postScene, postCamera, extract, soften, finish, activeRenderer;
const bufferSize = new THREE.Vector2();
const vertexShader = `varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}`;
function pass(fragmentShader, uniforms) {
  return new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, depthTest: false, depthWrite: false });
}
// Half-float targets on iOS can hold Inf/NaN from hot specular; one bad texel spreads
// through the quarter-res blur into black blocks, so every HDR read is made finite.
const SAFE = `vec3 safe(vec3 c){return (any(isnan(c))||any(isinf(c)))?vec3(0.):clamp(c,0.,64.);}`;
function target(depthBuffer = false) {
  return new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
}
function draw(renderer, material, destination) {
  quad.material = material;
  renderer.setRenderTarget(destination);
  renderer.render(postScene, postCamera);
}

export default {
  id: 'cinematic',
  name: 'Cinematic',
  blurb: 'Dense teal shadows, amber key light, anamorphic flares and silver-grain optics.',
  hud: { '--bg': '#060a10', '--fg': '#e5e1d8', '--muted': '#8c99a8', '--team-a': '#63bfff', '--team-b': '#ffae69', '--font': '"Helvetica Neue", Arial, sans-serif' },
  fonts: [],
  palette: { team: TEAM, exhaust: 0xc4e8ff, projectile: [0x8bcfff, 0xffba73], shield: [0x65bfff, 0xff9d58] },

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
    const key = new THREE.DirectionalLight(0xffc58a, 4.6);
    key.position.set(-450, 380, 350);
    const fill = new THREE.HemisphereLight(0x659cae, 0x030813, 0.32);
    const rim = new THREE.DirectionalLight(0x69cde5, 2.4);
    rim.position.set(350, 180, -550);
    scene.add(key, fill, rim);

    source = target(true);
    // The canvas MSAA does not apply to offscreen HDR targets.
    source.samples = 2;
    bright = target(); blur = target(); bloom = target(); streakBuffer = target();
    postScene = new THREE.Scene();
    postCamera = new THREE.Camera();
    quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.MeshBasicMaterial());
    quad.frustumCulled = false;
    postScene.add(quad);
    extract = pass(`varying vec2 vUv; uniform sampler2D image; uniform vec2 texel;
      ${SAFE}
      vec3 threshold(vec2 p){vec3 c=safe(texture2D(image,p).rgb);float l=max(c.r,max(c.g,c.b));return c*max(l-.7,0.)/max(l,.001);}
      void main(){vec3 c=threshold(vUv+texel*vec2(-1.,-1.))+threshold(vUv+texel*vec2(1.,-1.))+threshold(vUv+texel*vec2(-1.,1.))+threshold(vUv+texel*vec2(1.,1.));gl_FragColor=vec4(c*.25,1.);}`,
      { image: { value: source.texture }, texel: { value: new THREE.Vector2() } });
    soften = pass(`varying vec2 vUv;uniform sampler2D image;uniform vec2 stepUv;
      void main(){vec3 c=texture2D(image,vUv).rgb*.227027;
      c+=(texture2D(image,vUv+stepUv*1.384615).rgb+texture2D(image,vUv-stepUv*1.384615).rgb)*.316216;
      c+=(texture2D(image,vUv+stepUv*3.230769).rgb+texture2D(image,vUv-stepUv*3.230769).rgb)*.070270;
      gl_FragColor=vec4(c,1.);}`, { image: { value: null }, stepUv: { value: new THREE.Vector2() } });
    // Wide lens flare stays at quarter resolution: one lookup in the output pass.
    anamorphic = pass(`varying vec2 vUv; uniform sampler2D image; uniform vec2 span;
      void main(){
        vec3 c=texture2D(image,vUv).rgb*.12;
        for(int i=1;i<=32;i++){
          float f=float(i)/32.; vec2 d=span*f*f;
          c+=(texture2D(image,vUv+d).rgb+texture2D(image,vUv-d).rgb)*exp(-f*3.)*.06;
        }
        gl_FragColor=vec4(c,1.);
      }`, { image: { value: bloom.texture }, span: { value: new THREE.Vector2() } });
    finish = pass(`varying vec2 vUv;uniform sampler2D image;${SAFE}uniform sampler2D bloom;uniform sampler2D flare;uniform vec2 pixel;uniform float time;
      void main(){
        vec2 p=vUv-.5;float edge=dot(p,p);vec2 ca=p*edge*.0018;
        vec3 c=safe(vec3(texture2D(image,vUv+ca).r,texture2D(image,vUv).g,texture2D(image,vUv-ca).b));
        vec3 halo=safe(texture2D(bloom,vUv).rgb);
        vec3 streak=safe(texture2D(flare,vUv).rgb);
        // Warm local halation and a cool, long anamorphic ghost.
        c+=halo*vec3(.48,.24,.15)+streak*vec3(.4,.85,1.25);
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
      }`, { image: { value: source.texture }, bloom: { value: bloom.texture }, flare: { value: streakBuffer.texture }, pixel: { value: new THREE.Vector2() }, time: { value: 0 } });
    this.onResize();
  },

  materials(team) {
    if (!cache.has(team)) cache.set(team, {
      paint: new THREE.MeshPhysicalMaterial({ color: TEAM[team], metalness: .48, roughness: .32, clearcoat: .65, clearcoatRoughness: .27 }),
      trim: new THREE.MeshStandardMaterial({ color: team === 0 ? 0xbacbd2 : 0xe0c7a6, metalness: .72, roughness: .29 }),
      machinery: new THREE.MeshStandardMaterial({ color: 0x26313f, metalness: .8, roughness: .42 }),
      marking: new THREE.MeshStandardMaterial({ color: 0xf1ede0, metalness: .2, roughness: .43 }),
      glow: new THREE.MeshStandardMaterial({ color: 0xa4dfff, emissive: team === 0 ? 0x6bc6ff : 0xffa15a, emissiveIntensity: 3.2, roughness: .3 }),
      exhaust: new THREE.MeshBasicMaterial({ color: new THREE.Color(0xa9dcff).multiplyScalar(3.0), transparent: true, opacity: .9, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }),
    });
    return cache.get(team);
  },

  render(renderer, scene, camera, dt) {
    renderer.setRenderTarget(source);
    renderer.render(scene, camera);
    draw(renderer, extract, bright);
    soften.uniforms.image.value = bright.texture;
    soften.uniforms.stepUv.value.set(1 / bright.width, 0);
    draw(renderer, soften, blur);
    soften.uniforms.image.value = blur.texture;
    soften.uniforms.stepUv.value.set(0, 1 / bright.height);
    draw(renderer, soften, bloom);
    draw(renderer, anamorphic, streakBuffer);
    finish.uniforms.time.value += dt;
    draw(renderer, finish, null);
  },

  onResize() {
    if (!activeRenderer) return;
    activeRenderer.getDrawingBufferSize(bufferSize);
    const w = bufferSize.x, h = bufferSize.y;
    source.setSize(w, h);
    const bw = Math.max(1, Math.ceil(w / 4)), bh = Math.max(1, Math.ceil(h / 4));
    bright.setSize(bw, bh); blur.setSize(bw, bh); bloom.setSize(bw, bh); streakBuffer.setSize(bw, bh);
    anamorphic.uniforms.span.value.set(.16, 0);
    extract.uniforms.texel.value.set(1 / w, 1 / h);
    finish.uniforms.pixel.value.set(1 / w, 1 / h);
  },
};
