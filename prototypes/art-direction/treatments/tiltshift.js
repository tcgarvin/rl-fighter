import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const TEAM = [0x249cde, 0xf16a29];
const cache = new Map();
let activeRenderer, full, reduced, soft, prefilter, quad, postScene, postCamera, gather, finish;
const size = new THREE.Vector2();
const direction = new THREE.Vector3();
const focal = new THREE.Vector3();
const vertexShader = `varying vec2 vUv;
void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}`;
const lens = `
float coc(vec2 uv){
  float band=abs(uv.y-focus.y + (uv.x-focus.x)*0.105);
  float edge=smoothstep(.065,.36,band);
  return edge;
}`;

export default {
  id: 'tiltshift', name: 'Tilt-shift',
  blurb: 'Glossy resin miniatures photographed through a tilted macro lens.',
  hud: { '--bg':'#0b1019', '--fg':'#fff1db', '--muted':'#9babbc', '--team-a':'#46baff', '--team-b':'#ff9255', '--font':'"Trebuchet MS", sans-serif' },
  fonts: [],
  palette: { team: TEAM, exhaust:0xffe4a0, projectile:[0x8cddff,0xffbe78], shield:[0x68cfff,0xffa65f] },
  init({ scene, renderer, camera }) {
    activeRenderer=renderer;
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure=1.06;
    const pmrem=new THREE.PMREMGenerator(renderer);
    const room=new RoomEnvironment();
    // Large luminous cards give the clear coat a recognisable studio softbox reflection.
    const cardMaterial=new THREE.MeshBasicMaterial({color:new THREE.Color(4,3.8,3.3)});
    const card=new THREE.Mesh(new THREE.PlaneGeometry(9,5),cardMaterial);
    card.position.set(-3,7,1); card.lookAt(0,0,0); room.add(card);
    const strip=new THREE.Mesh(new THREE.PlaneGeometry(3,10),cardMaterial);
    strip.position.set(6,3,-2); strip.lookAt(0,0,0); room.add(strip);
    scene.environment=pmrem.fromScene(room,.025).texture;
    room.dispose(); pmrem.dispose();
    scene.environmentIntensity=.5;
    scene.add(new THREE.HemisphereLight(0xdbeaff,0x292333,.4));
    const key=new THREE.DirectionalLight(0xffeed5,2.2);
    key.position.set(-300,700,350); scene.add(key);
    const fill=new THREE.DirectionalLight(0xc5e2ff,.65);
    fill.position.set(400,350,-150); scene.add(fill);
    const rim=new THREE.DirectionalLight(0xffd6a2,1.7);
    rim.position.set(0,140,-650); scene.add(rim);
    full=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,depthBuffer:true});
    // Single-sample HDR avoids a costly full-resolution multisample/depth resolve.
    reduced=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,depthBuffer:false});
    soft=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,depthBuffer:false});
    const uniforms={source:{value:full.texture},focus:{value:new THREE.Vector2(.5,.5)},texel:{value:new THREE.Vector2()}};
    prefilter=new THREE.ShaderMaterial({depthTest:false,depthWrite:false,uniforms:{...uniforms,texel:{value:new THREE.Vector2()}},vertexShader,fragmentShader:`
      varying vec2 vUv; uniform sampler2D source; uniform vec2 texel;
      void main(){vec2 d=texel*.75;gl_FragColor=vec4((texture2D(source,vUv+d).rgb+texture2D(source,vUv-d).rgb+texture2D(source,vUv+vec2(d.x,-d.y)).rgb+texture2D(source,vUv+vec2(-d.x,d.y)).rgb)*.25,1.);}`});
    gather=new THREE.ShaderMaterial({depthTest:false,depthWrite:false,uniforms:{...uniforms,source:{value:reduced.texture},axis:{value:new THREE.Vector2(1,0)}},vertexShader,fragmentShader:`
      varying vec2 vUv;
      uniform sampler2D source;
      uniform vec2 focus,texel,axis;
      ${lens}
      void main(){
        float radius=.45+1.3*coc(vUv);
        vec3 sum=vec3(0.); float total=0.;
        // Two small Gaussian passes keep defocused sparks smooth, without sparse aperture ghosts.
        for(int i=-4;i<=4;i++){
          float f=float(i);
          float weight=exp(-f*f*.22);
          vec3 c=texture2D(source,clamp(vUv+axis*texel*f*radius,texel,1.-texel)).rgb;
          float peak=max(c.r,max(c.g,c.b));
          sum+=c*(1.+.04*max(0.,peak-1.)/(1.+peak))*weight;
          total+=weight;
        }
        gl_FragColor=vec4(sum/total,1.);
      }`});
    finish=new THREE.ShaderMaterial({depthTest:false,depthWrite:false,uniforms:{...uniforms,blurred:{value:reduced.texture}},vertexShader,fragmentShader:`
      varying vec2 vUv;
      uniform sampler2D source,blurred;
      uniform vec2 focus,texel;
      ${lens}
      void main(){
        vec3 sharp=texture2D(source,vUv).rgb;
        vec3 blur=texture2D(blurred,vUv).rgb;
        vec3 c=mix(sharp,blur,smoothstep(.0,.72,coc(vUv)));
        // Practical lights bloom gently even inside the focal strip.
        c+=max(blur-vec3(.7),vec3(0.))*.12;
        float l=dot(c,vec3(.2126,.7152,.0722));
        c=mix(vec3(l),c,1.32);
        c=max(c,vec3(0.));
        // Warm print grade and a coloured shadow floor make the starcloth read as a set.
        c=c*vec3(1.075,1.025,.94)+vec3(.009,.006,.012);
        c=mix(c,blur*.94+vec3(.007,.005,.012),.12*(1.-smoothstep(.015,.14,l)));
        vec2 v=(vUv-.5)*vec2(.85,1.);
        c*=1.-.27*smoothstep(.16,.65,length(v));
        gl_FragColor=vec4(c,1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`});
    postScene=new THREE.Scene(); postCamera=new THREE.Camera();
    const geometry=new THREE.BufferGeometry();
    geometry.setAttribute('position',new THREE.Float32BufferAttribute([-1,-1,0,3,-1,0,-1,3,0],3));
    geometry.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,2,0,0,2],2));
    quad=new THREE.Mesh(geometry,gather); quad.frustumCulled=false; postScene.add(quad);
    this.onResize();
  },
  materials(team) {
    if(!cache.has(team)) cache.set(team,{
      paint:new THREE.MeshPhysicalMaterial({color:TEAM[team],roughness:.23,metalness:.02,clearcoat:1,clearcoatRoughness:.065,envMapIntensity:1.2}),
      trim:new THREE.MeshPhysicalMaterial({color:0xeae6d7,roughness:.24,clearcoat:1,clearcoatRoughness:.09,metalness:.03}),
      machinery:new THREE.MeshStandardMaterial({color:0x252e3c,roughness:.42,metalness:.3}),
      glow:new THREE.MeshBasicMaterial({color:team===0?0xb5edff:0xffdb9c}),
      marking:new THREE.MeshPhysicalMaterial({color:0xfff5dc,roughness:.36,clearcoat:.65}),
      exhaust:new THREE.MeshBasicMaterial({color:0xffe4a0,transparent:true,opacity:.95,depthWrite:false,blending:THREE.AdditiveBlending})
    });
    return cache.get(team);
  },
  render(renderer,scene,camera) {
    renderer.getDrawingBufferSize(size);
    if(full.width!==size.x||full.height!==size.y) this.onResize();
    camera.getWorldDirection(direction);
    const distance=-camera.position.y/direction.y;
    focal.copy(camera.position).addScaledVector(direction,distance);
    // Project the ground-plane target, including the harness's HUD view offset.
    focal.project(camera);
    gather.uniforms.focus.value.set(focal.x*.5+.5,focal.y*.5+.5);
    const previous=renderer.getRenderTarget();
    renderer.setRenderTarget(full); renderer.render(scene,camera);
    quad.material=prefilter; renderer.setRenderTarget(reduced); renderer.render(postScene,postCamera);
    quad.material=gather;
    gather.uniforms.source.value=reduced.texture; gather.uniforms.axis.value.set(1,0);
    renderer.setRenderTarget(soft); renderer.render(postScene,postCamera);
    gather.uniforms.source.value=soft.texture; gather.uniforms.axis.value.set(0,1);
    renderer.setRenderTarget(reduced); renderer.render(postScene,postCamera);
    quad.material=finish; renderer.setRenderTarget(previous); renderer.render(postScene,postCamera);
  },
  onResize() {
    if(!full) return;
    // Use actual device pixels; CSS dimensions alone under-size iPhone render targets.
    activeRenderer.getDrawingBufferSize(size);
    const w=Math.max(1,size.x),h=Math.max(1,size.y);
    full.setSize(w,h); reduced.setSize(Math.max(1,Math.ceil(w/4)),Math.max(1,Math.ceil(h/4))); soft.setSize(Math.max(1,Math.ceil(w/4)),Math.max(1,Math.ceil(h/4)));
    // Aperture gather is quarter-resolution with two nine-tap passes, including on phones.
    gather.uniforms.texel.value.set(1/reduced.width,1/reduced.height);
    prefilter.uniforms.texel.value.set(2/w,2/h);
  }
};
