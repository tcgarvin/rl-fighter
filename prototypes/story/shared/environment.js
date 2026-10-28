// Seeded, baked celestial paintings. All GPU resources are fixed-size and reused.
export function createEnvironment({ THREE: T, scene, camera, renderer }) {
  const root = new T.Group(); root.name = 'Environment'; scene.add(root);
  const backdrop = new T.Group(); backdrop.name = 'Backdrop'; root.add(backdrop);
  const foreground = new T.Group(); foreground.name = 'Foreground dust'; root.add(foreground);
  const oldBackground = scene.background;
  scene.background = new T.Color(0x02040a);
  const random = seed => { let a = seed >>> 0; return () => { a += 0x6d2b79f5; let t = Math.imul(a ^ a >>> 15, a | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }; };
  const vertex = `varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
  const noise = `
  float hash(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
  float n(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1)),f.x),f.y),f.z);}
  float fb(vec3 p){float v=0.,a=.52;for(int i=0;i<5;i++){v+=a*n(p);p=p*2.07+vec3(3.1,7.2,1.7);a*=.48;}return v;}
  `;
  const bakeMat = new T.ShaderMaterial({ vertexShader: vertex, depthTest:false, depthWrite:false,
    uniforms: { seed:{value:0}, kind:{value:0}, low:{value:new T.Color()}, high:{value:new T.Color()}, air:{value:new T.Color()}, light:{value:new T.Vector3()}, tilt:{value:0}, ring:{value:0} },
    fragmentShader:`varying vec2 vUv; uniform float seed,kind,tilt,ring;uniform vec3 low,high,air,light;${noise}
    void main(){
      if(kind<-.5){
        vec2 uv=vUv-.5;vec3 q=vec3(uv*4.,seed);
        float warp=fb(q*1.8);float lane=uv.y+uv.x*.35+(warp-.5)*.20;
        float band=exp(-lane*lane*35.);float cloud=fb(q*2.+warp*2.);
        float dark=smoothstep(.35,.65,fb(q*5.+12.));
        vec3 sky=mix(vec3(.008,.013,.025),air*.045,cloud)*band*(.25+cloud)*(1.-dark*.75);
        gl_FragColor=vec4(sky*.20+vec3(.0005,.0008,.0015),1.);return;
      }
      vec2 p=(vUv-.5)*3.7;float c=cos(tilt),s=sin(tilt);p=mat2(c,-s,s,c)*p;vec3 sunDir=vec3(mat2(c,-s,s,c)*light.xy,light.z);
      float r=length(p); vec3 col=vec3(0.);float alpha=0.;
      // A tilted annulus, occluded by the near hemisphere and visible behind it.
      vec2 rp=vec2(p.x,p.y/mix(.12,.48,fract(seed*.317)));float rr=length(rp);
      float rings=smoothstep(1.14,1.19,rr)*(1.-smoothstep(1.69,1.76,rr))*ring;
      rings*=.38+.24*sin(rr*195.+seed)+.18*sin(rr*69.);rings*=1.-.8*exp(-pow((rr-1.43)*100.,2.));
      if(rings>0. && (r>1. || p.y<0.)){col=mix(low,high,.55)*(.18+.30*smoothstep(-1.5,1.5,p.x));alpha=rings*.65;}
      if(r<1.){
        vec3 normal=vec3(p,sqrt(1.-r*r));vec3 q=normal*3.1+seed;
        vec3 warp=vec3(fb(q),fb(q+12.7),fb(q-8.4));vec3 w=q+warp*1.9;
        float f=fb(w*2.1),detail=fb(w*9.);vec3 paint;
        if(kind<.5){
          float bands=sin(normal.y*34.+fb(w)*8.+f*9.);float fine=sin(normal.y*125.+f*20.);
          float b=smoothstep(-.8,.9,bands*.6+f*.8+fine*.13);
          paint=mix(low,high,b);paint*=.77+detail*.45;
          float storm=exp(-length((p-vec2(.30,-.20))*vec2(4.,9.)));paint=mix(paint,high*.75,storm*(.4+.35*sin(f*40.)));
        }else if(kind<1.5){
          float land=smoothstep(.47,.54,f);paint=mix(low,high,land);
          paint=mix(paint,high*.7,smoothstep(.64,.76,f)*.5);paint*=.72+detail*.6;
          float cloud=smoothstep(.53,.72,fb(q*2.6+warp*.9+31.));paint=mix(paint,vec3(.38,.44,.47),cloud*.65);
          paint=mix(paint,vec3(.35,.43,.46),smoothstep(.75,.96,abs(normal.y))*.75);
        }else if(kind<2.5){
          float veins=pow(1.-abs(sin(f*29.+detail*3.)),12.);paint=mix(low,high,f)*(.72+detail*.55);paint+=air*veins*.18;
          paint=mix(paint,high,smoothstep(.6,.85,fb(q*5.))* .45);
        }else if(kind<3.5){
          float cracks=1.-smoothstep(.008,.027,abs(f-.52));paint=mix(low,high,detail*.65);paint=mix(paint,vec3(.32,.065,.01),cracks*.65);
        }else{paint=mix(low,high,smoothstep(.2,.8,f))*(.55+detail*.8);float cr=pow(abs(sin(detail*35.)),18.);paint*=1.-cr*.19;}
        float sun=dot(normal,sunDir);float day=smoothstep(-.16,.25,sun);
        col=paint*(.035+day*(.23+.65*max(sun,0.)));
        float rim=pow(1.-normal.z,3.5);col+=air*rim*day*.35;
        if(kind>2.5&&kind<3.5)col+=vec3(.07,.009,.001)*(1.-day)*(1.-smoothstep(.012,.04,abs(f-.52)));
        alpha=1.;
      }else{
        float halo=exp(-(r-1.)*65.)*.19*max(.12,dot(normalize(vec3(p,.1)),sunDir));
        col+=air*halo;alpha=max(alpha,halo*2.);
      }
      // Premultiply the halo only through normal transparent compositing.
      gl_FragColor=vec4(col,alpha);
    }` });
  const quad = new T.PlaneGeometry(1,1);
  const bakeScene = new T.Scene(), bakeCamera = new T.OrthographicCamera(-.5,.5,.5,-.5,0,2);
  bakeCamera.position.z=1; bakeScene.add(new T.Mesh(quad,bakeMat));
  const skyTarget=new T.WebGLRenderTarget(768,384,{type:T.HalfFloatType,depthBuffer:false,stencilBuffer:false});
  const skyMat=new T.MeshBasicMaterial({map:skyTarget.texture,depthWrite:false,depthTest:false,toneMapped:false,dithering:true});
  const sky=new T.Mesh(quad,skyMat);sky.frustumCulled=false;sky.renderOrder=-110;backdrop.add(sky);
  const bodies=[];
  for(let i=0;i<3;i++){
    const target=new T.WebGLRenderTarget(i===0?768:384,i===0?768:384,{type:T.HalfFloatType,depthBuffer:false,stencilBuffer:false});
    const material=new T.MeshBasicMaterial({map:target.texture,transparent:true,depthWrite:false,depthTest:false,toneMapped:false,dithering:true});
    const mesh=new T.Mesh(quad,material);mesh.renderOrder=-20+i;backdrop.add(mesh);bodies.push({target,material,mesh});
  }
  // Static temperature-varied sky points, with a soft galactic concentration.
  const starCount=4200, starGeo=new T.BufferGeometry();
  const sp=new Float32Array(starCount*3), sc=new Float32Array(starCount*3), ss=new Float32Array(starCount);
  starGeo.setAttribute('position',new T.BufferAttribute(sp,3));starGeo.setAttribute('color',new T.BufferAttribute(sc,3));starGeo.setAttribute('size',new T.BufferAttribute(ss,1));
  const starMat=new T.ShaderMaterial({transparent:true,depthWrite:false,depthTest:false,vertexColors:true,
    vertexShader:`attribute float size;varying vec3 tint;void main(){tint=color;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);gl_PointSize=size;}`,
    fragmentShader:`varying vec3 tint;void main(){float d=length(gl_PointCoord-.5)*2.;float a=exp(-d*d*3.5)*(1.-smoothstep(.65,1.,d));gl_FragColor=vec4(tint,a);#include <tonemapping_fragment>\n#include <colorspace_fragment>}`.replace(';#include',';\n#include') });
  const stars=new T.Points(starGeo,starMat);stars.frustumCulled=false;stars.renderOrder=-100;backdrop.add(stars);
  const dustCount=210,dg=new T.BufferGeometry(),dp=new Float32Array(dustCount*3),orig=new Float32Array(dustCount*3);
  dg.setAttribute('position',new T.BufferAttribute(dp,3));
  const dm=new T.ShaderMaterial({transparent:true,depthWrite:false,
    uniforms:{pixelRatio:{value:renderer.getPixelRatio()}},
    vertexShader:`uniform float pixelRatio;void main(){vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;gl_PointSize=clamp(1100./max(200.,-p.z),1.2,2.4)*pixelRatio;}`,
    fragmentShader:`void main(){float r=length(gl_PointCoord-.5)*2.;float a=exp(-r*r*4.)*(1.-smoothstep(.5,1.,r));gl_FragColor=vec4(vec3(.34,.36,.38),a*.22);}`});
  const dust=new T.Points(dg,dm);dust.frustumCulled=false;foreground.add(dust);
  const palettes=[['#342b25','#b4a082','#518bad'],['#102936','#547c64','#4c9bb2'],['#263b4b','#a8bac0','#7bafd2'],['#15171d','#52413b','#b45324'],['#2e2333','#8c718c','#776695'],['#1c3438','#73a19a','#6bb3bb'],['#3c2521','#b37a51','#a8926e'],['#272c38','#778396','#7d94bd'],['#263044','#b89ba9','#8cadd6'],['#193b47','#78c5d0','#a6dcf0'],['#453325','#d6b978','#c1aa83'],['#302b48','#a799ce','#829bce']];
  let side=1, radius=1700;
  let layoutAspect=0, panX=0, panY=0;
  function newMatch(seed){
    layoutAspect=0;panX=panY=0;
    const rng=random(seed), range=(a,b)=>a+(b-a)*rng();
    side=rng()<.5?-1:1;
    rng(); // Preserve the established seed sequence for the celestial paintings.
    radius=range(1250,1900);
    const u=bakeMat.uniforms;u.light.value.set(-side*range(.35,.8),range(.15,.7),range(.2,.8)).normalize();
    const previousTarget=renderer.getRenderTarget(), clear=new T.Color();renderer.getClearColor(clear);const alpha=renderer.getClearAlpha();
    const oldAuto=renderer.autoClear;renderer.autoClear=true;renderer.setClearColor(0x000000,0);
    u.kind.value=-1;u.seed.value=range(0,100);u.air.value.set(palettes[Math.floor(rng()*palettes.length)][2]);
    renderer.setRenderTarget(skyTarget);renderer.clear();renderer.render(bakeScene,bakeCamera);
    for(let i=0;i<3;i++){
      const b=bodies[i];b.mesh.visible=i===0||rng()<.68;
      const kind=i===0?Math.floor(range(0,5)):Math.floor(range(2,5));const p=palettes[Math.floor(range(0,palettes.length))];
      u.seed.value=range(1,400);u.kind.value=kind;u.low.value.set(p[0]);u.high.value.set(p[1]);u.air.value.set(p[2]);if(kind===3){u.low.value.set("#17151b");u.high.value.set("#62534b");u.air.value.set("#a34d25");}u.tilt.value=range(-1.3,1.3);u.ring.value=i===0&&rng()<.56?1:0;
      renderer.setRenderTarget(b.target);renderer.clear();renderer.render(bakeScene,bakeCamera);
      b.mesh.userData.dx=i===0?range(-.35,.35):range(-.65,.65);
      b.mesh.userData.dy=i===0?side:(i===1?-side:side);
      // Rings extend to 1.76 planet radii; reserve their entire silhouette.
      b.mesh.userData.edge=u.ring.value?1.80:1.04;
      b.mesh.userData.radius=i===0?radius:range(160,410);
    }
    renderer.setRenderTarget(previousTarget);renderer.setClearColor(clear,alpha);renderer.autoClear=oldAuto;
    for(let i=0;i<starCount;i++){
      sp.set([range(-1.2,1.2),range(-1.2,1.2),0],i*3);
      const temp=rng(), bright=range(.16,.65)*(rng()<.04?1.5:1);sc.set([bright*(temp<.3?1:.73),bright*.86,bright*(temp>.65?1:.7)],i*3);ss[i]=range(.65,1.65)*(rng()<.025?1.8:1);
    }
    for(let i=0;i<dustCount;i++)orig.set([range(-1800,1800),range(-60,40),range(-1800,1800)],i*3);
    starGeo.attributes.position.needsUpdate=true;starGeo.attributes.color.needsUpdate=true;starGeo.attributes.size.needsUpdate=true;
  }
  // Everything celestial shares this one camera-space transform. Projection
  // coefficients account for the harness's HUD view offset as well as resize.
  const right=new T.Vector3(), up=new T.Vector3(), forward=new T.Vector3();
  function update(dt,view){
    const depth=10000, projection=camera.projectionMatrix.elements;
    const half=depth/projection[5], aspect=projection[5]/projection[0];
    right.setFromMatrixColumn(camera.matrixWorld,0);
    up.setFromMatrixColumn(camera.matrixWorld,1);
    forward.setFromMatrixColumn(camera.matrixWorld,2).negate();
    const ease=1-Math.exp(-Math.min(dt,.1)*3);
    // Bounded to four percent of the viewport in either direction. Zoom never
    // changes the painting's size or the positions of its constituent objects.
    panX+=(Math.tanh(-view.centerX/650)*.08-panX)*ease;
    panY+=(Math.tanh(view.centerY/650)*.08-panY)*ease;
    backdrop.position.copy(camera.position).addScaledVector(forward,depth)
      .addScaledVector(right,depth*projection[8]/projection[0]+panX*half*aspect)
      .addScaledVector(up,depth*projection[9]/projection[5]+panY*half);
    backdrop.quaternion.copy(camera.quaternion);backdrop.scale.setScalar(half);
    if(aspect!==layoutAspect){
      layoutAspect=aspect;
      sky.scale.set(2.4*aspect,2.4,1);sky.position.z=-.02;
      stars.scale.set(aspect,1,1);stars.position.z=-.01;
      const portrait=aspect<1, short=Math.min(aspect,1);
      for(let i=0;i<bodies.length;i++){
        const b=bodies[i], d=b.mesh.userData;
        const r=.48*d.radius/1600*short;
        const silhouette=r*d.edge;
        const sign=d.dy;
        // Keep the full silhouette beyond the central battle/arrival band. The
        // harness turns the camera in portrait so the fleets face off along the
        // screen's long axis; scenery then hangs mostly off the side edges.
        if(portrait){
          b.mesh.position.set(sign*(aspect-silhouette*.28),d.dx*.9,0);
        }else{
          b.mesh.position.set(sign*(aspect-silhouette*.40),d.dx*short,0);
        }
        b.mesh.scale.setScalar(r*3.7);
      }
    }
    dm.uniforms.pixelRatio.value=renderer.getPixelRatio();
    for(let i=0;i<dustCount;i++){const j=i*3;dp[j]=((orig[j]-view.centerX+5400)%3600)-1800+view.centerX;dp[j+1]=orig[j+1];dp[j+2]=((orig[j+2]+view.centerY+5400)%3600)-1800-view.centerY;}
    dg.attributes.position.needsUpdate=true;
  }
  return {newMatch,update,dispose(){scene.remove(root);if(scene.background?.getHex()===0x02040a)scene.background=oldBackground;quad.dispose();bakeMat.dispose();skyTarget.dispose();skyMat.dispose();for(const b of bodies){b.target.dispose();b.material.dispose();}starGeo.dispose();starMat.dispose();dg.dispose();dm.dispose();}};
}
