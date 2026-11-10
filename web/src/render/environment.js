// Seeded celestial scenery. Each match paints its sky and the surfaces of up to three
// bodies once (the bakes), into fixed-size textures that are reused. The sky is painted
// at once; the bodies over the next few frames, a strip at a time, each appearing when
// its surface is done, so a new match costs no long frame. Every frame the
// bodies are then lit as spheres, so they stay crisp at any zoom: a soft terminator,
// relief, an atmosphere at the limb, drifting cloud, night-side lights and glowing
// rifts, rings that shadow the planet and are shadowed by it, and a slow spin.
import { noiseTexture } from './noise.js';

// The quads carry a planet's disc and its halo (planet radii from the centre).
const BODY_EXTENT = 1.1;
const RING_INNER = 1.14, RING_OUTER = 1.78;
// Spin of the main body and the moons, rad/s, and the cloud deck's extra drift, turns/s.
const SPIN = [.0035, .0022, .0018], CLOUD_DRIFT = .0007;
const STARS = 26000, HERO_STARS = 36, DUST = 260;
// How strongly the faint star field is drawn (1 = as sown). Below 1 it sits back behind
// the fight: at full strength its sparkle competed with tracers and small hulls for the eye.
// The few bright stars with spikes are left alone; they are landmarks, not texture.
const STAR_FIELD_GAIN = .62;
// The low-res copy of the sky's density that the star field is sown from.
const DENSITY_W = 96, DENSITY_H = 48;

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
  vec3 hash3(vec3 p){p=fract(p*vec3(.1031,.1030,.0973));p+=dot(p,p.yxz+33.33);return fract((p.xxy+p.yxx)*p.zyx);}
  float n(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1)),f.x),f.y),f.z);}
  float fb(vec3 p){float v=0.,a=.52;for(int i=0;i<5;i++){v+=a*n(p);p=p*2.07+vec3(3.1,7.2,1.7);a*=.48;}return v;}
  `;
  const ringDensity = `
  uniform float ringSeed;
  float ringDensity(float rr){
    float band=smoothstep(1.16,1.21,rr)*(1.-smoothstep(1.69,1.76,rr));
    float d=.52+.24*sin(rr*195.+ringSeed)+.18*sin(rr*69.+ringSeed*1.7)+.1*sin(rr*431.+ringSeed*.3);
    d*=1.-.85*exp(-pow((rr-1.43)*100.,2.));
    d*=1.-.5*exp(-pow((rr-1.58)*160.,2.));
    return band*clamp(d,0.,1.);
  }
  // The rings' shadow on the planet: their broad bands only (the fine ones would shimmer).
  float ringShade(float rr){
    float band=smoothstep(1.16,1.25,rr)*(1.-smoothstep(1.64,1.76,rr));
    return band*(.58+.2*sin(rr*69.+ringSeed*1.7))*(1.-.7*exp(-pow((rr-1.43)*40.,2.)));
  }`;

  // ---- Bakes ----
  // The sky: a dim galactic lane with dust, and two colours of emission cloud in
  // patches. With density > 0 it writes the star field's density instead.
  const skyBake = new T.ShaderMaterial({ vertexShader: vertex, depthTest: false, depthWrite: false,
    uniforms: { seed: { value: 0 }, air: { value: new T.Color() }, warm: { value: new T.Color() }, density: { value: 0 } },
    fragmentShader: `varying vec2 vUv; uniform float seed,density;uniform vec3 air,warm;${noise}
    void main(){
      vec2 uv=vUv-.5;vec3 q=vec3(uv*4.,seed);
      float warp=fb(q*1.8);float lane=uv.y+uv.x*.35+(warp-.5)*.20;
      float band=exp(-lane*lane*35.);float cloud=fb(q*2.+warp*2.);
      float dark=smoothstep(.35,.65,fb(q*5.+12.));
      if(density>.5){gl_FragColor=vec4(vec3(band*(.25+cloud)*(1.-dark*.8)),1.);return;}
      float fine=fb(q*6.5+cloud*1.6+4.);
      vec3 sky=mix(vec3(.008,.013,.025),air*.05,cloud)*band*(.25+cloud)*(1.-dark*.75);
      float patchA=smoothstep(.5,.78,fb(q*1.25+7.+warp)),patchB=smoothstep(.55,.82,fb(q*1.05-9.));
      vec3 glow=air*patchA*(.25+fine*fine*1.6)*.017+warm*patchB*(.2+fine*fine*1.7)*.011;
      glow*=(.3+.7*band)*(1.-dark*.85);
      // Thin filaments where the cloud folds.
      float fold=pow(1.-abs(fb(q*3.1+warp*3.)*2.-1.),9.);
      glow+=mix(air,warm,patchB)*fold*(patchA+patchB)*.004*(1.-dark);
      gl_FragColor=vec4(sky*.34+glow+vec3(.0005,.0008,.0015),1.);
    }` });
  // A body's surface in longitude and latitude: colour (square-root encoded), and with
  // it height, a mask (water, glowing rifts or veins by kind), cloud and night lights.
  const bodyBake = new T.ShaderMaterial({ vertexShader: vertex, depthTest: false, depthWrite: false, glslVersion: T.GLSL3,
    uniforms: { seed: { value: 0 }, kind: { value: 0 }, low: { value: new T.Color() }, high: { value: new T.Color() }, air: { value: new T.Color() }, texels: { value: new T.Vector2() } },
    fragmentShader: `layout(location=0) out highp vec4 oColor; layout(location=1) out highp vec4 oAux;
    varying vec2 vUv; uniform float seed,kind;uniform vec3 low,high,air;uniform vec2 texels;${noise}
    // Bowls with raised rims, one in some cells of a 3D lattice cut by the sphere.
    float craters(vec3 p){
      vec3 i=floor(p),f=fract(p);float h=0.;
      for(int z=-1;z<=1;z++)for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
        vec3 g=vec3(x,y,z),o=hash3(i+g+seed);
        if(o.z<.42)continue;
        float rad=.16+.3*fract(o.z*7.3),d=length(g+o*vec3(1.,1.,.999)-f)/rad;
        h+=d<1.?-.55*(1.-d*d)+.5*exp(-pow((d-1.)/.14,2.)):.5*exp(-pow((d-1.)/.14,2.));
      }
      return h;
    }
    void main(){
      float lon=vUv.x*6.2831853,lat=(vUv.y-.5)*3.14159265;
      vec3 o=vec3(cos(lat)*cos(lon),sin(lat),cos(lat)*sin(lon));
      vec3 q=o*3.1+seed;
      vec3 warp=vec3(fb(q),fb(q+12.7),fb(q-8.4));vec3 w=q+warp*1.9;
      float f=fb(w*2.1),detail=fb(w*9.);vec3 paint;float height=.5,mask=0.,cloud=0.,lights=0.;
      if(kind<.5){
        float bands=sin(o.y*34.+fb(w)*8.+f*9.);float fine=sin(o.y*125.+f*20.);
        float b=smoothstep(-.8,.9,bands*.6+f*.8+fine*.13);
        paint=mix(low,high,b);paint*=.77+detail*.45;
        // One long-lived storm: an oval in the southern belts.
        vec3 s0=normalize(vec3(.72,-.3,.62)),east=normalize(cross(vec3(0.,1.,0.),s0)),north=cross(s0,east),d=o-s0;
        float storm=exp(-length(vec2(dot(d,east)*4.,dot(d,north)*9.))*2.2)*step(0.,dot(o,s0));
        paint=mix(paint,high*.75,storm*(.4+.35*sin(f*40.)));
        height=b;
      }else if(kind<1.5){
        float land=smoothstep(.47,.54,f);paint=mix(low,high,land);
        paint=mix(paint,high*.7,smoothstep(.64,.76,f)*.5);paint*=.72+detail*.6;
        float ice=smoothstep(.75,.96,abs(o.y)+(detail-.5)*.12);
        paint=mix(paint,vec3(.35,.43,.46),ice*.75);
        float deck=fb(q*2.6+warp*.9+31.);
        cloud=smoothstep(.5,.72,deck)*(.55+.75*fb(q*8.+warp*2.+3.));
        mask=(1.-land)*(1.-ice);
        height=smoothstep(.47,.85,f)*land;
        // Settlements: specks along the coasts and lowlands, in clusters.
        float cluster=smoothstep(.56,.74,fb(q*6.+41.))*land*(1.-ice)*(1.-smoothstep(.6,.72,f));
        lights=cluster*step(.78,hash(vec3(floor(vUv*texels*.75),seed)));
      }else if(kind<2.5){
        float veins=pow(1.-abs(sin(f*29.+detail*3.)),12.);paint=mix(low,high,f)*(.72+detail*.55);paint+=air*veins*.18;
        paint=mix(paint,high,smoothstep(.6,.85,fb(q*5.))*.45);
        mask=veins;height=f*.55+detail*.45-veins*.15;
      }else if(kind<3.5){
        float cracks=1.-smoothstep(.008,.027,abs(f-.52));paint=mix(low,high,detail*.65);paint=mix(paint,vec3(.32,.065,.01),cracks*.65);
        mask=1.-smoothstep(.006,.04,abs(f-.52));height=detail*.45+f*.55-mask*.3;
      }else{
        float c=craters(o*4.6)+.45*craters(o*11.3+7.)+.2*craters(o*27.+3.);
        paint=mix(low,high,smoothstep(.2,.8,f))*(.55+detail*.8);float cr=pow(abs(sin(detail*35.)),18.);paint*=1.-cr*.19;
        paint*=1.+clamp(c,-.6,.6)*.3;
        height=.5+c*.42+f*.12+detail*.1;
      }
      oColor=vec4(sqrt(clamp(paint,0.,1.)),1.);
      oAux=vec4(clamp(height,0.,1.),mask,cloud,lights);
    }` });
  const quad = new T.PlaneGeometry(1, 1);
  const bakeScene = new T.Scene(), bakeCamera = new T.OrthographicCamera(-.5, .5, .5, -.5, 0, 2);
  const bakeMesh = new T.Mesh(quad, skyBake);
  bakeCamera.position.z = 1; bakeScene.add(bakeMesh);
  const skyTarget = new T.WebGLRenderTarget(1024, 512, { type: T.HalfFloatType, depthBuffer: false, stencilBuffer: false });
  const densityTarget = new T.WebGLRenderTarget(DENSITY_W, DENSITY_H, { depthBuffer: false, stencilBuffer: false });
  const densityPixels = new Uint8Array(DENSITY_W * DENSITY_H * 4);
  const skyMat = new T.MeshBasicMaterial({ map: skyTarget.texture, depthWrite: false, depthTest: false, toneMapped: false, dithering: true });
  const sky = new T.Mesh(quad, skyMat); sky.frustumCulled = false; sky.renderOrder = -110; backdrop.add(sky);

  // ---- Bodies ----
  const anisotropy = Math.min(2, renderer.capabilities.getMaxAnisotropy());
  const bodyVertex = `varying vec2 vP; void main(){vP=position.xy;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
  const bodyFragment = `varying vec2 vP;
    uniform sampler2D map,aux,detail; uniform mat3 rot; uniform vec3 sunDir,air,sunTint;
    uniform float kind,ringOn,cloudShift,time,atmosphere; uniform vec3 ringNormal;
    ${ringDensity}
    void main(){
      vec2 p=vP;float r2=dot(p,p),r=sqrt(r2),aa=fwidth(r)+1e-5;
      float disc=1.-smoothstep(1.-aa,1.+aa,r);
      vec3 col=vec3(0.);
      if(disc>0.){
        vec3 n=r<1.?vec3(p,sqrt(1.-r2)):vec3(p/r,0.);
        vec3 o=rot*n;
        float v=asin(clamp(o.y,-1.,1.))/3.14159265+.5;
        // Two longitudes a seam apart: whichever is continuous here picks the mip.
        float ua=atan(o.z,o.x)/6.2831853,ub=fract(ua);
        float u=fwidth(ua)<fwidth(ub)+1e-6?ua:ub;
        vec2 uv=vec2(u,v);
        vec3 albedo=texture2D(map,uv).rgb;albedo*=albedo;
        vec4 ax=texture2D(aux,uv);
        // Past the bake's own resolution a tiling grain carries the surface.
        float mag=smoothstep(260.,900.,1./aa);
        if(mag>0.){
          vec3 w3=pow(abs(o),vec3(4.));w3/=w3.x+w3.y+w3.z;
          // One tap a plane: broad mottling from one channel, grit from another.
          vec2 d=w3.x*texture2D(detail,o.yz*9.).rg+w3.y*texture2D(detail,o.zx*9.).rg+w3.z*texture2D(detail,o.xy*9.).rg;
          albedo*=1.+((d.x-.5)*.55+(d.y-.5)*.4)*mag;
        }
        float sun0=dot(n,sunDir),day=smoothstep(-.16,.25,sun0);
        // Relief: the baked height's slope across the screen tips the normal (no more
        // taps: the slope is the height's own screen derivative, held in near the limb).
        vec3 nl=n;
        if(kind>.5){
          vec2 slope=clamp(vec2(dFdx(ax.r),dFdy(ax.r))/aa,-9.,9.);
          float relief=kind<1.5?.012:kind<2.5?.016:kind<3.5?.009:.05;
          nl=normalize(n-vec3(slope,0.)*relief*n.z);
        }
        float sun=dot(nl,sunDir);
        // The relief only modulates the light the sphere itself would get.
        float lambert=max(sun0,0.)*clamp(1.+(sun-sun0)*2.2,.25,1.9);
        vec3 lit=albedo*(.035+day*(.23+.65*lambert));
        // Deep air darkens toward the limb; rock much less.
        lit*=mix(1.,.42+.58*n.z,kind<.5?.85:.25);
        float shade=1.;
        if(ringOn>.5&&sun0>0.){
          float dn=dot(sunDir,ringNormal);dn=abs(dn)<1e-4?1e-4:dn;
          float t=-dot(n,ringNormal)/dn;
          if(t>0.)shade=1.-.8*ringShade(length(n+sunDir*t));
        }
        if(kind>.5&&kind<1.5){
          vec3 so=rot*sunDir;float c=max(sqrt(max(1.-o.y*o.y,0.)),.05);
          vec3 east=vec3(-o.z,0.,o.x)/c,north=cross(east,o);
          vec2 cuv=vec2(u+cloudShift,v);
          float deck=texture2D(aux,cuv).b;
          // The deck's shadow falls a little down-sun of it.
          float under=texture2D(aux,cuv+vec2(dot(so,east)/(6.2831853*c),dot(so,north)/3.14159265)*.012).b;
          float glint=pow(max(dot(reflect(-sunDir,nl),vec3(0.,0.,1.)),0.),42.)*ax.g*(1.-deck);
          lit*=1.-.5*under*day;
          lit+=sunTint*glint*.55*day;
          lit=mix(lit,vec3(.7,.74,.78)*(.03+day*(.26+.7*max(sun0,0.))),deck*.88);
          lit+=vec3(1.,.6,.26)*ax.a*(1.-day)*(1.-deck)*.42;
        }else if(kind>2.5&&kind<3.5){
          // Molten rifts: dull by day, glowing on the night side, slowly breathing.
          lit+=vec3(1.,.2,.025)*ax.g*(.05+.36*(1.-day))*(.78+.22*sin(time*.6+ax.r*23.));
        }else if(kind>1.5&&kind<2.5){
          lit+=air*ax.g*.05*(1.-day);
        }
        lit*=shade;
        // Air at the limb, reddening toward the terminator.
        float rim=pow(1.-n.z,3.5);
        vec3 scatter=mix(air,vec3(1.,.48,.22),.5*smoothstep(.32,-.06,sun0));
        lit+=scatter*rim*day*.36*atmosphere*shade;
        col=lit;
      }
      float halo=exp(-max(r-1.,0.)*65.)*.19*atmosphere*max(.12,dot(normalize(vec3(p,.1)),sunDir));
      // Premultiplied: the disc covers what is behind it, the halo adds to it.
      gl_FragColor=vec4(col*disc+air*halo*(1.-disc),disc+(1.-disc)*min(1.,halo*1.5));
    }`;
  const ringVertex = `varying vec3 vQ; varying float vRho; uniform mat3 ringRot;
    void main(){vec3 q=ringRot*position;vQ=q;vRho=length(position.xy);gl_Position=projectionMatrix*modelViewMatrix*vec4(q.xy,0.,1.);}`;
  const ringFragment = `varying vec3 vQ; varying float vRho; uniform vec3 sunDir,tintA,tintB;
    ${ringDensity}
    void main(){
      float dens=ringDensity(vRho);
      float rp=length(vQ.xy),aa=fwidth(rp)+1e-5;
      // The far half passes behind the planet.
      float hidden=vQ.z<0.?1.-smoothstep(1.-aa,1.+aa,rp):0.;
      // The planet's shadow across the rings.
      float s=dot(vQ,sunDir),d=length(vQ-s*sunDir);
      float lit=s<0.?smoothstep(.97,1.04,d):1.;
      vec3 c=mix(tintA,tintB,.5+.5*sin(vRho*37.+ringSeed))*(.2+.34*(.5+.5*dot(normalize(vQ),sunDir)))*(.07+.93*lit);
      float a=dens*.72*(1.-hidden);
      gl_FragColor=vec4(c*a,a);
    }`;
  const premultiplied = { transparent: true, depthWrite: false, depthTest: true, blending: T.CustomBlending, blendEquation: T.AddEquation, blendSrc: T.OneFactor, blendDst: T.OneMinusSrcAlphaFactor, blendSrcAlpha: T.OneFactor, blendDstAlpha: T.OneMinusSrcAlphaFactor };
  const bodyGeo = new T.PlaneGeometry(2 * BODY_EXTENT, 2 * BODY_EXTENT);
  const ringGeo = new T.RingGeometry(RING_INNER, RING_OUTER, 128, 1);
  const bodies = [];
  for (let i = 0; i < 3; i++) {
    const w = i === 0 ? 2048 : 1024;
    const target = new T.WebGLRenderTarget(w, w / 2, { count: 2, depthBuffer: false, stencilBuffer: false, generateMipmaps: true,
      minFilter: T.LinearMipmapLinearFilter, magFilter: T.LinearFilter, wrapS: T.RepeatWrapping, wrapT: T.ClampToEdgeWrapping, anisotropy });
    // Transparent objects draw after the opaque ships, so the far-off bodies must depth
    // test or they paint over any ship in front of them.
    const material = new T.ShaderMaterial({ ...premultiplied, vertexShader: bodyVertex, fragmentShader: bodyFragment,
      uniforms: { map: { value: target.textures[0] }, aux: { value: target.textures[1] }, detail: { value: noiseTexture() }, rot: { value: new T.Matrix3() },
        sunDir: { value: new T.Vector3(0, 0, 1) }, air: { value: new T.Color() }, sunTint: { value: new T.Color(0xffe2bd) }, kind: { value: 0 }, ringOn: { value: 0 },
        ringNormal: { value: new T.Vector3(0, 1, 0) }, ringSeed: { value: 0 }, cloudShift: { value: 0 }, time: { value: 0 }, atmosphere: { value: 1 } } });
    const mesh = new T.Mesh(bodyGeo, material); mesh.renderOrder = -20 + i; backdrop.add(mesh);
    const ringMaterial = new T.ShaderMaterial({ ...premultiplied, side: T.DoubleSide, vertexShader: ringVertex, fragmentShader: ringFragment,
      uniforms: { ringRot: { value: new T.Matrix3() }, sunDir: material.uniforms.sunDir, tintA: { value: new T.Color() }, tintB: { value: new T.Color() }, ringSeed: material.uniforms.ringSeed } });
    const ring = new T.Mesh(ringGeo, ringMaterial); ring.renderOrder = -19.5 + i; ring.frustumCulled = false; backdrop.add(ring);
    bodies.push({ target, material, mesh, ring, ringMaterial, pole: new T.Vector3(0, 1, 0), x0: new T.Vector3(1, 0, 0), z0: new T.Vector3(0, 0, 1), spin: 0, clouds: 0 });
  }

  // ---- Stars ----
  // Temperature-varied points sown from the sky's own density, so the lane is thick
  // with faint stars and its dust lanes are thin of them; and a few bright ones with
  // diffraction spikes.
  const starGeo = new T.BufferGeometry();
  const sp = new Float32Array(STARS * 3), sc = new Float32Array(STARS * 3), ss = new Float32Array(STARS);
  starGeo.setAttribute('position', new T.BufferAttribute(sp, 3)); starGeo.setAttribute('color', new T.BufferAttribute(sc, 3)); starGeo.setAttribute('size', new T.BufferAttribute(ss, 1));
  const starMat = new T.ShaderMaterial({ transparent: true, depthWrite: false, depthTest: true, vertexColors: true,
    uniforms: { pixelScale: { value: 1 } },
    vertexShader: `attribute float size;uniform float pixelScale;varying vec3 tint;void main(){tint=color;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);gl_PointSize=size*pixelScale;}`,
    fragmentShader: `varying vec3 tint;void main(){float d=length(gl_PointCoord-.5)*2.;float a=exp(-d*d*3.5)*(1.-smoothstep(.65,1.,d))*${STAR_FIELD_GAIN.toFixed(2)};gl_FragColor=vec4(tint,a);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }` });
  const stars = new T.Points(starGeo, starMat); stars.frustumCulled = false; stars.renderOrder = -100; backdrop.add(stars);
  const heroGeo = new T.BufferGeometry();
  const hp = new Float32Array(HERO_STARS * 3), hc = new Float32Array(HERO_STARS * 3), hs = new Float32Array(HERO_STARS);
  heroGeo.setAttribute('position', new T.BufferAttribute(hp, 3)); heroGeo.setAttribute('color', new T.BufferAttribute(hc, 3)); heroGeo.setAttribute('size', new T.BufferAttribute(hs, 1));
  const heroMat = new T.ShaderMaterial({ transparent: true, depthWrite: false, depthTest: true, vertexColors: true, blending: T.AdditiveBlending,
    uniforms: { pixelScale: { value: 1 } },
    vertexShader: `attribute float size;uniform float pixelScale;varying vec3 tint;void main(){tint=color;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);gl_PointSize=size*pixelScale;}`,
    fragmentShader: `varying vec3 tint;void main(){
      vec2 p=gl_PointCoord*2.-1.;p=vec2(p.x*.94-p.y*.34,p.x*.34+p.y*.94);float r=length(p);
      float core=exp(-r*r*140.),veil=exp(-r*9.)*.07;
      float spikes=(exp(-abs(p.x)*46.)+exp(-abs(p.y)*46.))*exp(-r*4.5)*.42;
      gl_FragColor=vec4(tint*(core*3.2+veil+spikes)*(1.-smoothstep(.7,1.,r)),1.);
    }` });
  const heroes = new T.Points(heroGeo, heroMat); heroes.frustumCulled = false; heroes.renderOrder = -99; backdrop.add(heroes);

  // ---- Foreground dust ----
  const dg = new T.BufferGeometry(), dp = new Float32Array(DUST * 3), orig = new Float32Array(DUST * 3), dk = new Float32Array(DUST);
  dg.setAttribute('position', new T.BufferAttribute(dp, 3)); dg.setAttribute('mote', new T.BufferAttribute(dk, 1));
  const dm = new T.ShaderMaterial({ transparent: true, depthWrite: false,
    uniforms: { pixelRatio: { value: renderer.getPixelRatio() } },
    vertexShader: `uniform float pixelRatio;attribute float mote;varying float vMote;void main(){vMote=mote;vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;gl_PointSize=clamp(1100./max(200.,-p.z),1.2,2.4)*pixelRatio*(.7+.9*mote);}`,
    fragmentShader: `varying float vMote;void main(){float r=length(gl_PointCoord-.5)*2.;float a=exp(-r*r*4.)*(1.-smoothstep(.5,1.,r));gl_FragColor=vec4(vec3(.34,.36,.38),a*(.12+.2*vMote));}` });
  const dust = new T.Points(dg, dm); dust.frustumCulled = false; foreground.add(dust);

  const palettes = [['#342b25','#b4a082','#518bad'],['#102936','#547c64','#4c9bb2'],['#263b4b','#a8bac0','#7bafd2'],['#15171d','#52413b','#b45324'],['#2e2333','#8c718c','#776695'],['#1c3438','#73a19a','#6bb3bb'],['#3c2521','#b37a51','#a8926e'],['#272c38','#778396','#7d94bd'],['#263044','#b89ba9','#8cadd6'],['#193b47','#78c5d0','#a6dcf0'],['#453325','#d6b978','#c1aa83'],['#302b48','#a799ce','#829bce']];
  // How much air a kind of body holds at its limb.
  const ATMOSPHERE = [1, 1.15, .55, .5, .1];
  const tint = new T.Color(), sunView = new T.Vector3(), tmp = new T.Vector3();
  let side = 1, radius = 1700, clock = 0;
  let layoutAspect = 0, layoutZoom = 0;

  function bake(material, target) {
    bakeMesh.material = material;
    renderer.setRenderTarget(target); renderer.clear(); renderer.render(bakeScene, bakeCamera);
  }
  // Body surfaces still to paint: {body, strips, done, show ring, and the bake's uniforms}.
  const jobs = [];
  const clearColor = new T.Color();
  /** Run `draw` with the renderer aimed at bake targets, then put its state back. */
  function baking(draw) {
    const target = renderer.getRenderTarget(), alpha = renderer.getClearAlpha(), auto = renderer.autoClear;
    renderer.getClearColor(clearColor);
    renderer.autoClear = true; renderer.setClearColor(0x000000, 0);
    draw();
    renderer.setRenderTarget(target); renderer.setClearColor(clearColor, alpha); renderer.autoClear = auto;
  }
  /** Paint the next strip of the next body; show the body once its last strip is in. */
  function paintStrip() {
    const job = jobs[0], b = job.body, u = bodyBake.uniforms, t = b.target;
    u.seed.value = job.seed; u.kind.value = job.kind; u.low.value.copy(job.low); u.high.value.copy(job.high); u.air.value.copy(job.air);
    u.texels.value.set(t.width, t.height);
    const rows = Math.ceil(t.height / job.strips);
    t.scissorTest = true; t.scissor.set(0, job.done * rows, t.width, rows);
    bakeMesh.material = bodyBake;
    renderer.autoClear = false;
    renderer.setRenderTarget(t); renderer.render(bakeScene, bakeCamera);
    t.scissorTest = false;
    if (++job.done < job.strips) return;
    b.mesh.visible = true; b.ring.visible = job.ringed;
    jobs.shift();
  }

  /** Paint a new sky and bodies. Returns the side the main body hangs on and its air's colour. */
  function newMatch(seed) {
    layoutAspect = 0;
    // The first stream keeps the draws (and so each seed's bodies) of the first backdrop;
    // everything added since draws from the second.
    const rng = random(seed), range = (a, b) => a + (b - a) * rng();
    const rng2 = random(seed ^ 0x9e3779b9), range2 = (a, b) => a + (b - a) * rng2();
    side = rng() < .5 ? -1 : 1;
    rng();
    radius = range(1250, 1900);
    sunView.set(-side * range(.35, .8), range(.15, .7), range(.2, .8)).normalize();
    const su = skyBake.uniforms;
    su.seed.value = range(0, 100); su.air.value.set(palettes[Math.floor(rng() * palettes.length)][2]);
    su.warm.value.set(palettes[[3, 6, 10][Math.floor(rng2() * 3)]][1]);
    baking(() => {
      su.density.value = 0; bake(skyBake, skyTarget);
      su.density.value = 1; bake(skyBake, densityTarget);
      renderer.readRenderTargetPixels(densityTarget, 0, 0, DENSITY_W, DENSITY_H, densityPixels);
    });
    jobs.length = 0;
    for (let i = 0; i < 3; i++) {
      const b = bodies[i], m = b.material.uniforms, shown = i === 0 || rng() < .68;
      const kind = i === 0 ? Math.floor(range(0, 5)) : Math.floor(range(2, 5)); const p = palettes[Math.floor(range(0, palettes.length))];
      const surface = { body: b, seed: range(1, 400), kind, low: new T.Color(p[0]), high: new T.Color(p[1]), air: new T.Color(p[2]), strips: i === 0 ? 4 : 1, done: 0, ringed: false };
      if (kind === 3) { surface.low.set('#17151b'); surface.high.set('#62534b'); surface.air.set('#a34d25'); }
      const tilt = range(-1.3, 1.3), ringed = i === 0 && rng() < .56;
      surface.ringed = ringed;
      // Hidden until painted (a few frames from now).
      b.mesh.visible = b.ring.visible = false;
      if (shown) jobs.push(surface);
      m.kind.value = kind; m.air.value.copy(surface.air); m.atmosphere.value = ATMOSPHERE[kind]; m.sunDir.value.copy(sunView);
      m.ringOn.value = ringed ? 1 : 0; m.ringSeed.value = surface.seed;
      // The pole leans `tilt` in the screen plane and tips toward the viewer, so rings
      // are seen as an ellipse this open.
      const open = Math.asin(.12 + .36 * ((surface.seed * .317) % 1));
      b.pole.set(Math.sin(tilt) * Math.cos(open), Math.cos(tilt) * Math.cos(open), Math.sin(open));
      b.x0.set(b.pole.y, -b.pole.x, 0).normalize(); b.z0.crossVectors(b.x0, b.pole);
      m.ringNormal.value.copy(b.pole);
      b.ringMaterial.uniforms.ringRot.value.set(b.x0.x, b.z0.x, b.pole.x, b.x0.y, b.z0.y, b.pole.y, b.x0.z, b.z0.z, b.pole.z);
      b.ringMaterial.uniforms.tintA.value.copy(surface.low).lerp(surface.high, .45);
      b.ringMaterial.uniforms.tintB.value.copy(surface.low).lerp(surface.high, .75);
      b.spin = range2(0, 6.283); b.clouds = range2(0, 1);
      b.mesh.userData.dx = i === 0 ? range(-.35, .35) : range(-.65, .65);
      b.mesh.userData.dy = i === 0 ? side : (i === 1 ? -side : side);
      // Rings extend to 1.76 planet radii; reserve their entire silhouette.
      b.mesh.userData.edge = ringed ? 1.80 : 1.04;
      b.mesh.userData.radius = i === 0 ? radius : range(160, 410);
      if (i === 0) tint.copy(surface.air);
    }
    // Stars: up to four tries each at a spot the sky's density accepts.
    for (let i = 0; i < STARS; i++) {
      let x = 0, y = 0, dense = 0;
      for (let k = 0; k < 4; k++) {
        x = range2(-1.2, 1.2); y = range2(-1.2, 1.2);
        const px = Math.min(DENSITY_W - 1, Math.floor((x / 2.4 + .5) * DENSITY_W)), py = Math.min(DENSITY_H - 1, Math.floor((y / 2.4 + .5) * DENSITY_H));
        dense = densityPixels[(py * DENSITY_W + px) * 4] / 255;
        if (rng2() < .2 + dense * 2.4) break;
      }
      sp.set([x, y, 0], i * 3);
      // Most are faint; the lane's crowd is fainter and finer still.
      const temp = rng2(), crowd = Math.min(1, dense * 2.2);
      const bright = range2(.1, .62) * (rng2() < .04 ? 1.5 : 1) * (1 - .35 * crowd * rng2());
      sc.set([bright * (temp < .3 ? 1 : .73), bright * .86, bright * (temp > .65 ? 1 : .7)], i * 3);
      ss[i] = range2(.6, 1.6) * (rng2() < .025 ? 1.8 : 1);
    }
    for (let i = 0; i < HERO_STARS; i++) {
      hp.set([range2(-1.15, 1.15), range2(-1.15, 1.15), 0], i * 3);
      const temp = rng2(), bright = range2(.35, 1) ** 2;
      hc.set([bright * (temp < .35 ? 1 : .72), bright * .88, bright * (temp > .6 ? 1 : .66)], i * 3);
      hs[i] = range2(14, 30) * (.6 + .4 * bright);
    }
    for (let i = 0; i < DUST; i++) { orig.set([range(-1800, 1800), range(-60, 40), range(-1800, 1800)], i * 3); dk[i] = rng2() ** 2; }
    for (const g of [starGeo, heroGeo]) for (const name of ['position', 'color', 'size']) g.attributes[name].needsUpdate = true;
    dg.attributes.mote.needsUpdate = true;
    return { side, tint };
  }

  // Everything celestial shares this one camera-space transform, built from the fixed
  // camera's own projection (`view.projection`, before the harness's digital zoom and
  // pan), so the painting is cropped and scaled with the ships, never re-fitted to the
  // screen. Without one, the camera's projection (HUD view offset included) is used.
  // `view.layoutZoom` (default 1) is the zoom the scenery is composed for: the bodies
  // are laid out in the centre 1/layoutZoom of the frame, so a typical crop of the
  // action shows them as a fitted view would; stars cover the whole frame.
  const right = new T.Vector3(), up = new T.Vector3(), forward = new T.Vector3();
  function update(dt, view) {
    clock += dt;
    if (jobs.length) baking(paintStrip);
    const depth = 10000, projection = (view.projection ?? camera.projectionMatrix).elements;
    const half = depth / projection[5], aspect = projection[5] / projection[0];
    right.setFromMatrixColumn(camera.matrixWorld, 0);
    up.setFromMatrixColumn(camera.matrixWorld, 1);
    forward.setFromMatrixColumn(camera.matrixWorld, 2).negate();
    backdrop.position.copy(camera.position).addScaledVector(forward, depth)
      .addScaledVector(right, depth * projection[8] / projection[0])
      .addScaledVector(up, depth * projection[9] / projection[5]);
    backdrop.quaternion.copy(camera.quaternion); backdrop.scale.setScalar(half);
    const k = view.layoutZoom ?? 1;
    if (aspect !== layoutAspect || k !== layoutZoom) {
      layoutAspect = aspect; layoutZoom = k;
      sky.scale.set(2.4 * aspect, 2.4, 1); sky.position.z = -.02;
      stars.scale.set(aspect, 1, 1); stars.position.z = -.01;
      heroes.scale.set(aspect, 1, 1); heroes.position.z = -.008;
      const portrait = aspect < 1, short = Math.min(aspect, 1);
      for (let i = 0; i < bodies.length; i++) {
        const b = bodies[i], d = b.mesh.userData;
        const r = .48 * d.radius / 1600 * short;
        const silhouette = r * d.edge;
        const sign = d.dy;
        // Keep the full silhouette beyond the central battle/arrival band. The
        // harness turns the camera in portrait so the fleets face off along the
        // screen's long axis; scenery then hangs mostly off the side edges.
        if (portrait) {
          b.mesh.position.set(sign * (aspect - silhouette * .28) / k, d.dx * .9 / k, 0);
        } else {
          b.mesh.position.set(sign * (aspect - silhouette * .40) / k, d.dx * short / k, 0);
        }
        b.mesh.scale.setScalar(r / k);
        b.ring.position.copy(b.mesh.position); b.ring.scale.copy(b.mesh.scale);
      }
    }
    for (let i = 0; i < bodies.length; i++) {
      const b = bodies[i], m = b.material.uniforms;
      b.spin += dt * SPIN[i]; b.clouds += dt * CLOUD_DRIFT;
      // Object space from view space: the pole is its y axis, turned by the spin.
      const c = Math.cos(b.spin), s = Math.sin(b.spin);
      right.copy(b.x0).multiplyScalar(c).addScaledVector(b.z0, s);
      tmp.copy(b.z0).multiplyScalar(c).addScaledVector(b.x0, -s);
      m.rot.value.set(right.x, right.y, right.z, b.pole.x, b.pole.y, b.pole.z, tmp.x, tmp.y, tmp.z);
      m.cloudShift.value = b.clouds % 1; m.time.value = clock;
    }
    const ratio = renderer.getPixelRatio();
    dm.uniforms.pixelRatio.value = ratio;
    starMat.uniforms.pixelScale.value = heroMat.uniforms.pixelScale.value = 1 + (ratio - 1) * .6;
    for (let i = 0; i < DUST; i++) { const j = i * 3; dp[j] = ((orig[j] - view.centerX + 5400) % 3600) - 1800 + view.centerX; dp[j + 1] = orig[j + 1]; dp[j + 2] = ((orig[j + 2] + view.centerY + 5400) % 3600) - 1800 - view.centerY; }
    dg.attributes.position.needsUpdate = true;
  }
  return {
    newMatch, update,
    dispose() {
      scene.remove(root); if (scene.background?.getHex() === 0x02040a) scene.background = oldBackground;
      quad.dispose(); bodyGeo.dispose(); ringGeo.dispose(); skyBake.dispose(); bodyBake.dispose(); skyTarget.dispose(); densityTarget.dispose(); skyMat.dispose();
      for (const b of bodies) { b.target.dispose(); b.material.dispose(); b.ringMaterial.dispose(); }
      starGeo.dispose(); starMat.dispose(); heroGeo.dispose(); heroMat.dispose(); dg.dispose(); dm.dispose();
    },
  };
}
