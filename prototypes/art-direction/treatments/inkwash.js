// Ink on warm rag paper: stepped gouache hulls and a single full-resolution
// depth/colour pass. No extra scene render, blur buffers, or per-frame objects.
import * as THREE from 'three';

const TEAM = [0x65c9e5, 0xf49a63];
const cache = new Map();
let target, quad, postScene, postCamera, rendererRef;
let inkTime = 0;
const size = new THREE.Vector2();
const ramp = new THREE.DataTexture(new Uint8Array([70, 158, 245]), 3, 1, THREE.RedFormat);
ramp.minFilter = ramp.magFilter = THREE.NearestFilter;
ramp.generateMipmaps = false;
ramp.needsUpdate = true;

function painted(color) {
  const material = new THREE.MeshToonMaterial({ color, gradientMap: ramp });
  material.onBeforeCompile = shader => {
    shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 inkPosition;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\ninkPosition = position;');
    shader.fragmentShader = shader.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 inkPosition;')
      .replace('#include <color_fragment>', `#include <color_fragment>
      float wash = sin(inkPosition.x * .72 + sin(inkPosition.z * .9)) * sin(inkPosition.z * 1.4 + inkPosition.x * .21);
      diffuseColor.rgb *= .89 + .14 * wash;`);
  };
  material.customProgramCacheKey = () => 'inkwash-gouache-v2';
  return material;
}

export default {
  id: 'inkwash',
  name: 'Ink & Wash',
  blurb: 'Living gouache on warm rag paper: pooled washes, hatched shadows and bold hand-inked contours.',
  hud: { '--bg': '#e1d6bb', '--fg': '#202e33', '--muted': '#4e5a5a', '--team-a': '#186078', '--team-b': '#994725', '--font': 'Georgia, serif' },
  fonts: [],
  palette: { team: TEAM, exhaust: 0xffe6a0, projectile: [0xa3e8ff, 0xffc286], shield: [0x86d9ec, 0xf3b78d] },

  init({ scene, renderer }) {
    rendererRef = renderer;
    renderer.toneMapping = THREE.NoToneMapping;
    renderer.toneMappingExposure = 1;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    scene.add(new THREE.HemisphereLight(0xc4d9ee, 0x222536, 1.25));
    const key = new THREE.DirectionalLight(0xffebc7, 2.1);
    key.position.set(-350, 800, 220);
    scene.add(key);
    renderer.getDrawingBufferSize(size);
    target = new THREE.WebGLRenderTarget(size.x, size.y, {
      type: THREE.HalfFloatType, minFilter: THREE.NearestFilter,
      magFilter: THREE.NearestFilter, depthBuffer: true,
    });
    target.depthTexture = new THREE.DepthTexture(size.x, size.y, THREE.UnsignedIntType);
    quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
      depthTest: false, depthWrite: false,
      uniforms: {
        image: { value: target.texture }, depthImage: { value: target.depthTexture },
        pixel: { value: new THREE.Vector2(1 / size.x, 1 / size.y) },
        nearPlane: { value: 1 }, farPlane: { value: 60000 },
        paperScale: { value: renderer.getPixelRatio() }, boil: { value: 0 },
      },
      vertexShader: `varying vec2 vUv;
        void main() { vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }`,
      fragmentShader: `
        uniform sampler2D image, depthImage;
        uniform vec2 pixel;
        uniform float nearPlane, farPlane, paperScale, boil;
        varying vec2 vUv;
        float depthAt(vec2 uv) {
          float d = texture2D(depthImage, uv).r;
          return nearPlane * farPlane / (farPlane - d * (farPlane - nearPlane));
        }
        float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
        float inkLuma(vec3 c) { return dot(c, vec3(.2126,.7152,.0722)); }
        void main() {
          // All marks are sized in CSS pixels, including on a Retina phone.
          vec2 paper = gl_FragCoord.xy / paperScale;
          vec2 px = pixel * paperScale;
          float wobble = sin(paper.y * .13 + boil) * sin(paper.x * .09 - boil);
          vec2 nib = px * (1.0 + .25 * wobble);
          vec3 raw = texture2D(image, vUv).rgb;
          vec3 left = texture2D(image, vUv - vec2(px.x,0.)).rgb;
          vec3 right = texture2D(image, vUv + vec2(px.x,0.)).rgb;
          vec3 up = texture2D(image, vUv + vec2(0.,px.y)).rgb;
          vec3 down = texture2D(image, vUv - vec2(0.,px.y)).rgb;
          float d = depthAt(vUv);
          float wide = max(max(abs(depthAt(vUv + vec2(nib.x,0.)) - d),
                               abs(depthAt(vUv - vec2(nib.x,0.)) - d)),
                           max(abs(depthAt(vUv + vec2(0.,nib.y)) - d),
                               abs(depthAt(vUv - vec2(0.,nib.y)) - d))) / max(d,1.);
          float silhouette = smoothstep(.008, .04, wide);
          float crease = smoothstep(.035,.18, length(right-left) + length(up-down));
          float lum = inkLuma(raw);
          vec3 display = pow(raw / (1. + raw * .35), vec3(.454545));
          // Five opaque pigment values; the dilute halo below escapes their edges.
          vec3 pigment = floor(display * 5. + .5) / 5.;
          float pool = sin(vUv.x * 29. + sin(vUv.y * 17.)) * sin(vUv.y * 37. + vUv.x * 9.);
          float fibre = sin(paper.y * 2.2 + sin(paper.x * .071) * 2.);
          float grain = hash(floor(paper * 1.6)) - .5;
          float pulp = hash(floor(paper / 3.)) - .5;
          vec3 stock = vec3(.88,.84,.73) * (1. + grain * .075 + pulp * .035 + fibre * .016);
          float coverage = smoothstep(.002,.085,lum);
          float bleed = inkLuma((left + right + up + down) * .25);
          float halo = smoothstep(.008,.10,bleed) * (1. - coverage);
          vec3 c = mix(stock, stock * vec3(.56,.65,.69), halo * .28);
          c = mix(c, pigment * vec3(.79,.79,.74), coverage * (.88 + pool * .07));
          // Cross-hatched dry ink in shadow, with sparse stippling on the wash.
          float shade = coverage * (1. - smoothstep(.07,.48,lum));
          float hatch = 1. - smoothstep(.65,1.25,abs(mod(paper.x + paper.y * .64 + wobble * .35,5.) - 2.5));
          float cross = 1. - smoothstep(.5,1.,abs(mod(paper.x - paper.y * .9,7.) - 3.5));
          float stipple = step(.92,hash(floor(paper * .7))) * .3;
          c *= 1. - shade * (hatch * .26 + cross * .14 + stipple);
          float ink = max(silhouette * .95, crease * .40 * coverage);
          c = mix(c,vec3(.055,.070,.079),ink);
          c *= 1. + grain * .045 + fibre * .01;
          gl_FragColor = vec4(c,1.);
        }`,
    }));
    quad.frustumCulled = false;
    postScene = new THREE.Scene();
    postScene.add(quad);
    postCamera = new THREE.Camera();
  },

  materials(team) {
    if (!cache.has(team)) cache.set(team, {
      paint: painted(TEAM[team]),
      trim: painted(team === 0 ? 0xc8d9db : 0xf1d4ad),
      machinery: painted(0x283443),
      glow: new THREE.MeshBasicMaterial({ color: team === 0 ? 0xc6f6ff : 0xffddb0 }),
      marking: painted(0xfff0cc),
      exhaust: new THREE.MeshBasicMaterial({ color: 0xffe6a0, transparent: true, opacity: .95, depthWrite: false, blending: THREE.AdditiveBlending }),
    });
    return cache.get(team);
  },

  render(renderer, scene, camera, dt) {
    inkTime += dt || 0;
    quad.material.uniforms.boil.value = Math.floor(inkTime * 10) * .73;
    quad.material.uniforms.nearPlane.value = camera.near;
    quad.material.uniforms.farPlane.value = camera.far;
    renderer.setRenderTarget(target);
    renderer.render(scene, camera);
    renderer.setRenderTarget(null);
    renderer.render(postScene, postCamera);
  },

  onResize() {
    if (!target) return;
    rendererRef.getDrawingBufferSize(size);
    target.setSize(size.x, size.y);
    quad.material.uniforms.pixel.value.set(1 / size.x, 1 / size.y);
    quad.material.uniforms.paperScale.value = rendererRef.getPixelRatio();
  },
};
