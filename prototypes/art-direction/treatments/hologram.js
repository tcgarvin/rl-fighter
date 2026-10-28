// Projected volumes over a tactical table. All buffers and uniforms are reused.
import * as THREE from 'three';
const TEAM = [0x37ddff, 0xffa448];
const time = { value: 0 }, cache = new Map();
const size = new THREE.Vector2();
let source, ping, pong, postScene, postCamera, quad, blur, finish;
const vertex = `varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}`;
function shell(team, strength, opacity) {
  const m = new THREE.ShaderMaterial({
    uniforms: { clock: time, hue: { value: new THREE.Color(TEAM[team]) }, strength: { value: strength }, alpha: { value: opacity } },
    vertexShader: `varying vec3 vN; varying vec3 vV; varying vec3 vP;
      void main(){vec4 p=modelViewMatrix*vec4(position,1.);vN=normalize(normalMatrix*normal);vV=-p.xyz;vP=position;gl_Position=projectionMatrix*p;}`,
    fragmentShader: `uniform float clock,strength,alpha;uniform vec3 hue;varying vec3 vN,vV,vP;
      void main(){float rim=pow(1.-abs(dot(normalize(vN),normalize(vV))),1.6);
      float scan=.87+.13*sin(vP.y*19.+vP.z*2.4-clock*3.);
      float band=pow(max(0.,sin(vP.z*.13+vP.x*.07-clock*.75)),48.);
      float pulse=1.-.065*pow(max(0.,sin(clock*2.7)),18.);
      vec3 c=hue*(strength+rim*1.25+band*.23)*scan*pulse;
      gl_FragColor=vec4(c,alpha+rim*.2);}`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    side: THREE.FrontSide,
  });
  m.userData.hologram = true;
  return m;
}
const outlined = new WeakSet(), edges = new WeakMap();
const edgeMaterials = TEAM.map(c => new THREE.LineBasicMaterial({ color:c, transparent:true, opacity:.35, blending:THREE.AdditiveBlending, depthWrite:false }));
function outline(object) {
  if (!object.isMesh || !object.material.userData.hologram || outlined.has(object)) return;
  outlined.add(object);
  let geometry=edges.get(object.geometry);
  if (!geometry) { geometry=new THREE.EdgesGeometry(object.geometry,24); edges.set(object.geometry,geometry); }
  const team=object.material.uniforms.hue.value.b > .5 ? 0 : 1;
  object.add(new THREE.LineSegments(geometry,edgeMaterials[team]));
}
export default {
  id:'hologram', name:'Hologram Table',
  blurb:'Projected fleets · luminous volumes above a tactical sand table.',
  hud:{'--bg':'#030b10','--fg':'#d0f6f4','--muted':'#719397','--team-a':'#37ddff','--team-b':'#ffa448','--font':'ui-monospace, SFMono-Regular, monospace'},
  fonts:[],
  palette:{team:TEAM,exhaust:0xc5fff4,projectile:[0x57e5ff,0xffb557],shield:[0x37ddff,0xffa448]},
  init({scene,renderer}) {
    renderer.toneMapping=THREE.NoToneMapping;
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    scene.add(new THREE.HemisphereLight(0x8abec9,0x051018,.65));
    // Depth-tested grid is below the ships; the distant scenery remains visible.
    const table=new THREE.Mesh(new THREE.PlaneGeometry(2200,2200),new THREE.ShaderMaterial({
      transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
      vertexShader:`varying vec2 p;void main(){p=position.xy;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
      fragmentShader:`varying vec2 p;void main(){vec2 q=abs(fract(p/40.-.5)-.5)*40.;vec2 aa=fwidth(p);float line=1.-smoothstep(.0,max(aa.x,aa.y)*1.15,min(q.x,q.y));
        vec2 r=abs(fract(p/200.-.5)-.5)*200.;float major=1.-smoothstep(0.,max(aa.x,aa.y)*1.4,min(r.x,r.y));
        float fade=1.-smoothstep(300.,1050.,length(p));float ring=1.-smoothstep(.4,2.+length(aa),abs(length(p)-520.));
        gl_FragColor=vec4(vec3(.025,.20,.22),fade*(line*.12+major*.16+ring*.20));}`,
    }));
    table.rotation.x=-Math.PI/2;table.position.y=-16;scene.add(table);
    const options={type:THREE.HalfFloatType,depthBuffer:false};
    source=new THREE.WebGLRenderTarget(1,1,{...options,depthBuffer:true});
    ping=new THREE.WebGLRenderTarget(1,1,options);pong=new THREE.WebGLRenderTarget(1,1,options);
    postScene=new THREE.Scene();postCamera=new THREE.Camera();
    blur=new THREE.ShaderMaterial({uniforms:{image:{value:null},stepSize:{value:new THREE.Vector2()},threshold:{value:0}},vertexShader:vertex,
      fragmentShader:`varying vec2 vUv;uniform sampler2D image;uniform vec2 stepSize;uniform float threshold;
      vec3 tap(vec2 uv){vec3 c=texture2D(image,uv).rgb;return c*max(0.,max(max(c.r,c.g),c.b)-threshold)/max(.001,max(max(c.r,c.g),c.b));}
      void main(){vec3 c=tap(vUv)*.227027;c+=(tap(vUv+stepSize*1.384615)+tap(vUv-stepSize*1.384615))*.316216;c+=(tap(vUv+stepSize*3.230769)+tap(vUv-stepSize*3.230769))*.070270;gl_FragColor=vec4(c,1.);}`});
    finish=new THREE.ShaderMaterial({uniforms:{image:{value:source.texture},bloom:{value:pong.texture},clock:time,resolution:{value:new THREE.Vector2()}},vertexShader:vertex,
      fragmentShader:`varying vec2 vUv;uniform sampler2D image,bloom;uniform float clock;uniform vec2 resolution;
      void main(){vec2 uv=vUv;float sweep=pow(max(0.,sin(uv.y*9.-clock*.28)),64.);uv.x+=sweep*sin(clock*11.)*.00018;
      vec3 c=texture2D(image,uv).rgb;
      float lum=dot(c,vec3(.2126,.7152,.0722));
      float scenery=1.-smoothstep(.16,.65,max(max(c.r,c.g),c.b));
      c=mix(c,mix(vec3(lum),c,.3)*vec3(.65,.92,1.),scenery*.62);
      vec2 shift=vec2(.55/resolution.x,0.);c.r=mix(c.r,texture2D(image,uv+shift).r,.18);c.b=mix(c.b,texture2D(image,uv-shift).b,.18);
      c+=texture2D(bloom,uv).rgb*.48;
      c*=.975+.025*sin(vUv.y*resolution.y*3.14159);
      c*=1.-.23*pow(length((vUv-.5)*1.3),2.);
      c=vec3(1.)-exp(-c*1.25);gl_FragColor=vec4(c,1.);
      #include <colorspace_fragment>
      }`});
    quad=new THREE.Mesh(new THREE.PlaneGeometry(2,2),blur);quad.frustumCulled=false;postScene.add(quad);
    renderer.getSize(size);this.onResize(size.x,size.y);
  },
  materials(team) {
    if(!cache.has(team)) cache.set(team,{
      paint:shell(team,.58,.49),trim:shell(team,.83,.53),machinery:shell(team,.26,.42),
      glow:new THREE.MeshBasicMaterial({color:TEAM[team],transparent:true,opacity:.95,blending:THREE.AdditiveBlending,depthWrite:false}),
      marking:new THREE.MeshBasicMaterial({color:team?0xffe4ad:0xb9faff,transparent:true,opacity:.95,blending:THREE.AdditiveBlending,depthWrite:false}),
      exhaust:new THREE.MeshBasicMaterial({color:0xbaffef,transparent:true,opacity:.9,blending:THREE.AdditiveBlending,depthWrite:false}),
    });
    return cache.get(team);
  },
  render(renderer,scene,camera,dt) {
    time.value+=Math.min(dt||0,.1);scene.traverse(outline);
    renderer.setRenderTarget(source);renderer.render(scene,camera);
    quad.material=blur;blur.uniforms.image.value=source.texture;blur.uniforms.threshold.value=.48;
    blur.uniforms.stepSize.value.set(1/source.width,0);renderer.setRenderTarget(ping);renderer.render(postScene,postCamera);
    blur.uniforms.image.value=ping.texture;blur.uniforms.threshold.value=0;
    blur.uniforms.stepSize.value.set(0,1/ping.height);renderer.setRenderTarget(pong);renderer.render(postScene,postCamera);
    quad.material=finish;renderer.setRenderTarget(null);renderer.render(postScene,postCamera);
  },
  onResize(width,height) {
    if(!source)return;
    const dpr=Math.min(window.devicePixelRatio||1,2), w=Math.max(1,Math.round(width*dpr)),h=Math.max(1,Math.round(height*dpr));
    source.setSize(w,h);ping.setSize(Math.max(1,w>>1),Math.max(1,h>>1));pong.setSize(ping.width,ping.height);
    finish.uniforms.resolution.value.set(w,h);
  },
};
