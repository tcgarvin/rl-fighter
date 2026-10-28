// Shared combat effects. Fixed-capacity CPU pools feed bounded instanced draws;
// no textures, lights, post-processing dependencies, or per-frame object creation.
export function createEffects({ THREE: T, scene, renderer, palette }) {
  const team = palette.team.map(c => new T.Color(c));
  const shot = palette.projectile.map(c => new T.Color(c));
  const pellet = shot.map(c => c.clone().lerp(new T.Color(0xffad63), .48));
  const shield = palette.shield.map(c => new T.Color(c));
  const white = new T.Color(0xfff5df), amber = new T.Color(palette.exhaust);
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
  // Velocity-aligned ribbons expand across the view, so they cannot turn edge-on.
  // Soft analytic profiles replace solid box faces; both layers remain additive.
  const tracers = batch(new T.PlaneGeometry(1, 1), 1200, false, false, true, false, 1);
  const cores = batch(new T.PlaneGeometry(1, 1), 1200, false, false, true, false, 2);
  const bolts = batch(new T.BoxGeometry(1, 1, 1), 512);

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
  const jumps = Array.from({ length: 32 }, () => ({ life: 0, max: 1, x: 0, z: 0,
    angle: 0, size: 1, color: white, landed: false }));
  let pc = 0, wc = 0, jc = 0;
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
  const api = {
    // Jump-in shockwave speed multiplier; 0 hides it.
    jumpRing: 1,
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
      p.color=team[e.team] || white; p.landed=false;
    },
    attachDamage(model) {
      let smokeClock=0, fireClock=0, arcClock=0, index=0, disposed=false;
      const points=model.damagePoints || [];
      // Damage mounts span the hull: derive a scale once, without geometry traversal.
      let extent=0;
      for(const p of points) extent=Math.max(extent,Math.abs(p.x),Math.abs(p.z));
      const scale=Math.max(.85,extent/3);
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
      glow.n=flames.n=smoke.n=chips.n=rings.n=ripples.n=bolts.n=0;
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
        } else {
          const r=w.radius*(w.kind===2?1-t*.55:.15+t);
          put(rings,w.x,1.1,w.z,r,1,r,w.angle+t*.7,w.color,fade*(w.kind===2?.9:.6));
        }
      }
      for(const p of jumps) {
        if(p.life<=0)continue;
        p.life-=dt;if(p.life<=0)continue;
        const age=p.max+.7-p.life, travel=Math.min(1,age/p.max);
        const dx=Math.cos(p.angle), dz=-Math.sin(p.angle);
        const back=900*(1-travel)**3;
        const tail=travel<1?Math.min(900-back,430):350*Math.max(0,1-(age-p.max)/.38);
        const x=p.x-dx*back,z=p.z-dz*back, fade=travel<1?1:Math.max(0,1-(age-p.max)/.38);
        segment(bolts,x-dx*tail,1.4,z-dz*tail,x,1.4,z,p.size*.65,p.color,.42*fade);
        segment(bolts,x-dx*tail*.85,1.5,z-dz*tail*.85,x,1.5,z,Math.max(1.8,p.size*.1),white,fade);
        if(travel===1) {
          const after=Math.max(0,1-(age-p.max)/.7);
          segment(bolts,p.x-dx*p.size*.65,2,p.z-dz*p.size*.65,
            p.x+dx*p.size*.65,2,p.z+dz*p.size*.65,p.size*.35,p.color,after*.6);
        }
        if(travel===1 && !p.landed) {
          p.landed=true;particle(p.x,2,p.z,p.size*5,.38,p.color);
          particle(p.x,2,p.z,p.size*2,.18,white);
          if(api.jumpRing>0) wave(p.x,p.z,p.size*2.4,.65/api.jumpRing,p.color);
        }
      }
      finish(glow);finish(flames);finish(smoke);finish(chips);finish(rings);finish(ripples);finish(bolts);
    },
    // Optional lifecycle hook for embeds; normal harness keeps one Effects for its lifetime.
    dispose() {
      for(const b of resources) { scene.remove(b.mesh);b.mesh.geometry.dispose();b.mesh.material.dispose(); }
    },
  };
  return api;
}
