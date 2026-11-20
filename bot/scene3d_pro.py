"""고품질 3D 장면 (과학 숏츠) — three.js + 빛 번짐(UnrealBloom)·그림자·금속 질감·ACES 톤, Playwright 로 프레임 녹화.

  python -m bot.scene3d_pro <장면.json> <출력.mp4>
type:
  medal        회전하는 금메달 + 반짝임 (label, year)
  photo        금속판에 빛 알갱이가 쏟아짐 (color: "blue" 면 전자가 튀어나옴 / "red" 면 안 나옴, label)
  scientist    아인슈타인풍 3D 과학자 캐릭터 (mode: "flip" 공중제비 / "think" 빛 알갱이가 주위를 돔 / "medal" 메달 들고 축하)
  photon_hit   느린 화면: 빛 알갱이 하나가 원자에 부딪혀 전자 하나가 튕겨 나감
  solar        태양전지판에 빛이 쏟아지고 전구가 켜짐
  galileo      갈릴레이풍 만화 학자(대머리 정수리·수염·가운, 눈꺼풀/입 표정) mode: "think" 물음표 / "flip" 공중제비
  tower        기울어진 흰 대리석 탑 꼭대기에 쇠공·나무공 + 물음표, 카메라가 올라감
  ancient      그리스 신전 앞, 무거운 공이 먼저 떨어지는 '옛 상식' + "약 2,000년"
  incline      경사면에 공이 굴러가며 1:3:5:7 구간 표시 (갈릴레이 홀수 법칙)
  vacuum       유리관 두 개: 공기 있음(깃털 천천히) vs 공기 없음(공·깃털 동시)
  moon_drop    달 표면·착륙선, 망치와 깃털이 동시에 떨어짐(슬로모션·먼지) — 긴 클립(라벨 label/label2, drop 초)
  ※ 모든 장면에 비네트+필름 그레인(애니메이션 키트 기법). 장면 속 글씨는 자막 자리(아래 ~21%)에 들어가면 자동으로 위로 올림. --snap 스틸엔 자막 자리 빨간 띠 표시
실존 인물 사진·초상은 쓰지 않는다 (캐릭터는 흰 머리·콧수염의 만화풍 과학자).
"""
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config

A3 = config.ROOT / "assets" / "3d"
FPS, S = 30, 1080
LIBS = ["three.min.js", "CopyShader.js", "LuminosityHighPassShader.js", "EffectComposer.js", "RenderPass.js",
        "ShaderPass.js", "UnrealBloomPass.js"]

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000;overflow:hidden}</style>
__LIBS__</head><body><script>
const CFG = __CFG__, W = __S__, H = __S__;
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setSize(W,H); renderer.setPixelRatio(1); renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.85; renderer.outputEncoding = THREE.sRGBEncoding;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); const camera = new THREE.PerspectiveCamera(35,1,.01,200);
const composer = new THREE.EffectComposer(renderer); composer.addPass(new THREE.RenderPass(scene,camera));
const bloom = new THREE.UnrealBloomPass(new THREE.Vector2(W,H), CFG.bloom||0.55, 0.5, 0.92); composer.addPass(bloom);
const rnd = (()=>{let s=CFG.seed||7; return ()=> (s=(s*16807)%2147483647)/2147483647;})();
const ease = x => x<.5 ? 2*x*x : 1-Math.pow(-2*x+2,2)/2;
function grad(top, bottom){ const c=document.createElement('canvas'); c.width=4; c.height=512; const g=c.getContext('2d'); const gr=g.createLinearGradient(0,0,0,512);
  gr.addColorStop(0,top); gr.addColorStop(1,bottom); g.fillStyle=gr; g.fillRect(0,0,4,512); const t=new THREE.CanvasTexture(c); t.encoding=THREE.sRGBEncoding; return t; }
function label(text,color,size){ const c=document.createElement('canvas'); c.width=1400; c.height=260; const g=c.getContext('2d');
  g.font=`900 ${size||110}px "Apple SD Gothic Neo","Noto Sans KR",sans-serif`; g.textAlign='center'; g.textBaseline='middle';
  g.lineWidth=22; g.strokeStyle='rgba(0,0,0,.9)'; g.strokeText(text,700,130); g.fillStyle=color||'#fff'; g.fillText(text,700,130);
  const t=new THREE.CanvasTexture(c); const s=new THREE.Sprite(new THREE.SpriteMaterial({map:t,transparent:true,depthTest:false,toneMapped:false})); s.renderOrder=20; return s; }
function hudLabel(text,color,y){ const L=label(text,color,110); L.scale.set(.58,.108,1); L.position.set(0,.228,-1); camera.add(L); return L; }  // 화면에 고정된 큰 글씨
scene.add(camera);
function stage(color){ const fl=new THREE.Mesh(new THREE.CircleGeometry(6,96), new THREE.MeshStandardMaterial({color:color||0x1a1f33, roughness:.55, metalness:.2}));
  fl.rotation.x=-Math.PI/2; fl.receiveShadow=true; scene.add(fl); return fl; }
function keyLight(x,y,z,int){ const l=new THREE.SpotLight(0xffffff,(int||2.2)*.6,30,Math.PI/5,.45,1.2); l.position.set(x,y,z); l.castShadow=true; l.shadow.mapSize.set(1024,1024); l.shadow.bias=-0.0004; scene.add(l); scene.add(l.target); return l; }
function glowBall(r,color,int){ return new THREE.Mesh(new THREE.SphereGeometry(r,20,14), new THREE.MeshBasicMaterial({color:new THREE.Color(color).multiplyScalar(Math.min(1.5,(int||2.5)*.45)), toneMapped:false})); }
let draw=()=>{};

// ── 아인슈타인풍 만화 과학자 ──
function scientist(){
  const g=new THREE.Group();
  const skin=new THREE.MeshStandardMaterial({color:0xf0c7a2, roughness:.6}), hairM=new THREE.MeshStandardMaterial({color:0xdcdce2, roughness:.9});
  const coat=new THREE.MeshStandardMaterial({color:0xcfcbbf, roughness:.75}), suit=new THREE.MeshStandardMaterial({color:0x5b4636, roughness:.8});
  const body=new THREE.Mesh(new THREE.CylinderGeometry(.42,.5,1.2,32), coat); body.position.y=.95; body.castShadow=true; g.add(body);
  const vest=new THREE.Mesh(new THREE.CylinderGeometry(.3,.36,.9,24,1,true,-.6,1.2), suit); vest.position.set(0,1.0,.08); g.add(vest);
  const tie=new THREE.Mesh(new THREE.BoxGeometry(.1,.42,.03), new THREE.MeshStandardMaterial({color:0x9b2a2a, roughness:.5})); tie.position.set(0,1.28,.47); g.add(tie);
  const head=new THREE.Mesh(new THREE.SphereGeometry(.42,48,36), skin); head.position.y=1.95; head.scale.set(1,1.05,.95); head.castShadow=true; g.add(head);
  // 흰 머리카락: 뒤·옆으로 뻗친 덩어리
  for(let i=0;i<70;i++){ const a=rnd()*Math.PI*2, b=rnd()*Math.PI*.55; const r=.42+rnd()*.12;
    const v=new THREE.Vector3(Math.sin(b)*Math.cos(a), Math.cos(b)*.9+.15, Math.sin(b)*Math.sin(a)); if (v.z>.45 && v.y<.75) continue;
    const tuft=new THREE.Mesh(new THREE.ConeGeometry(.07+rnd()*.05,.28+rnd()*.22,8), hairM); tuft.position.copy(v.clone().multiplyScalar(r)).add(new THREE.Vector3(0,1.95,0));
    tuft.lookAt(tuft.position.clone().add(v)); tuft.rotateX(Math.PI/2); tuft.castShadow=true; g.add(tuft); }
  const must=new THREE.Mesh(new THREE.SphereGeometry(.16,24,16), hairM); must.scale.set(1.5,.55,.6); must.position.set(0,1.8,.38); g.add(must);
  const nose=new THREE.Mesh(new THREE.SphereGeometry(.07,16,12), skin); nose.scale.set(1,1.2,1.3); nose.position.set(0,1.93,.42); g.add(nose);
  for(const x of [-.15,.15]){ const eye=new THREE.Mesh(new THREE.SphereGeometry(.075,20,14), new THREE.MeshStandardMaterial({color:0xffffff, roughness:.3})); eye.position.set(x,2.03,.35); g.add(eye);
    const pup=new THREE.Mesh(new THREE.SphereGeometry(.04,16,12), new THREE.MeshStandardMaterial({color:0x1a1a1a, roughness:.2})); pup.position.set(x,2.03,.42); g.add(pup);
    const brow=new THREE.Mesh(new THREE.BoxGeometry(.14,.04,.04), hairM); brow.position.set(x,2.15,.36); brow.rotation.z = x>0?-.15:.15; g.add(brow); }
  for(const x of [-.55,.55]){ const arm=new THREE.Mesh(new THREE.CylinderGeometry(.1,.11,.75,16), coat); arm.position.set(x,1.1,0); arm.rotation.z=x>0?-.35:.35; arm.castShadow=true; g.add(arm);
    const hand=new THREE.Mesh(new THREE.SphereGeometry(.1,16,12), skin); hand.position.set(x*1.25,.78,0); g.add(hand); }
  for(const x of [-.17,.17]){ const leg=new THREE.Mesh(new THREE.CylinderGeometry(.11,.11,.5,14), suit); leg.position.set(x,.25,0); leg.castShadow=true; g.add(leg); }
  return g;
}

if (CFG.type==='medal') {
  scene.background = grad('#1b1430','#05040b'); stage(0x120f1f);
  keyLight(2,5,4,3); scene.add(new THREE.AmbientLight(0x8877aa,.35));
  const env = new THREE.HemisphereLight(0xfff1c9, 0x221133, .6); scene.add(env);
  const gold = new THREE.MeshStandardMaterial({color:0xffc94a, metalness:1, roughness:.22, emissive:0x3a2600, emissiveIntensity:.3});
  const prof=[]; for(let i=0;i<=24;i++){const a=i/24*Math.PI; prof.push(new THREE.Vector2(.9+.06*Math.sin(a), .07*Math.cos(a)));} prof.unshift(new THREE.Vector2(0,.06)); prof.push(new THREE.Vector2(0,-.06));
  const medal = new THREE.Mesh(new THREE.LatheGeometry(prof,96), gold); medal.rotation.x=Math.PI/2; medal.castShadow=true;
  const face = document.createElement('canvas'); face.width=face.height=512; const fg=face.getContext('2d'); fg.fillStyle='#e8b23a'; fg.fillRect(0,0,512,512);
  fg.strokeStyle='#8a5a10'; fg.lineWidth=10; fg.beginPath(); fg.arc(256,256,215,0,7); fg.stroke(); fg.fillStyle='#7a4c0c'; fg.font='900 150px Georgia,serif'; fg.textAlign='center'; fg.textBaseline='middle'; fg.fillText(CFG.year||'1921',256,270);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(.86,96), new THREE.MeshStandardMaterial({map:new THREE.CanvasTexture(face), metalness:.9, roughness:.3}));
  const grp = new THREE.Group(); grp.add(medal); disc.position.z=.071; grp.add(disc); const back=disc.clone(); back.rotation.y=Math.PI; back.position.z=-.071; grp.add(back); grp.position.y=1.4; scene.add(grp);
  const ribbon = new THREE.Mesh(new THREE.BoxGeometry(.5,1.4,.02), new THREE.MeshStandardMaterial({color:0x2a4fbf, roughness:.6})); ribbon.position.set(0,2.6,-.05); grp.add(ribbon); ribbon.position.set(0,1.15,-.02);
  const sparks=[]; for(let i=0;i<40;i++){ const s=glowBall(.018+rnd()*.02,'#ffe9a8',3); s.position.set((rnd()-.5)*4, .3+rnd()*3, (rnd()-.5)*2); scene.add(s); sparks.push([s,rnd()*6]); }
  if (CFG.label) hudLabel(CFG.label,'#ffd23f',.33);
  draw=t=>{ grp.rotation.y = -0.5 + t*1.6; grp.position.y = 1.4+.05*Math.sin(t*6);
    sparks.forEach(([s,p])=>{ const k=Math.max(0,Math.sin(t*8+p)); s.scale.setScalar(.3+k); });
    camera.position.set(0,1.5,6.2-.6*t); camera.lookAt(0,1.6,0); composer.render(); };
}

if (CFG.type==='photo' || CFG.type==='photon_hit') {
  scene.background = grad('#0b1026','#020308'); keyLight(-3,6,5,2.4); scene.add(new THREE.AmbientLight(0x404a70,.5));
  const plateM = new THREE.MeshStandardMaterial({color:0x9aa7b8, metalness:.45, roughness:.32});
  const plate = new THREE.Mesh(new THREE.BoxGeometry(3.4,.35,2.2), plateM); plate.position.y=.0; plate.receiveShadow=true; plate.castShadow=true; scene.add(plate);
  const blue = CFG.color!=='red'; const pc = blue ? '#5aa8ff' : '#ff3b30';
  const N = CFG.type==='photon_hit' ? 1 : (blue ? 14 : 40);
  const photons=[], electrons=[];
  for(let i=0;i<N;i++){ const p=glowBall(CFG.type==='photon_hit'?.09:.055, pc, blue?3.5:3); const trail=new THREE.Mesh(new THREE.CylinderGeometry(.012,.04,.7,10), new THREE.MeshBasicMaterial({color:new THREE.Color(pc).multiplyScalar(1.2), transparent:true, opacity:.6, toneMapped:false}));
    const x=(rnd()-.5)*2.6, z=(rnd()-.5)*1.4; const delay = CFG.type==='photon_hit' ? .15 : rnd()*.75; photons.push({p,trail,x,z,delay}); scene.add(p); scene.add(trail);
    if (blue) { const e=glowBall(CFG.type==='photon_hit'?.07:.045,'#7dfcff',3); e.visible=false; scene.add(e); electrons.push({e,x,z,dir:new THREE.Vector3((rnd()-.5)*.8,1,(rnd()-.5)*.6).normalize(),delay}); } }
  // 원자 격자 (photon_hit)
  if (CFG.type==='photon_hit') for(let i=-3;i<=3;i++) for(let k=-2;k<=2;k++){ const a=new THREE.Mesh(new THREE.SphereGeometry(.12,20,14), new THREE.MeshStandardMaterial({color:0x8f9bb3, metalness:.6, roughness:.35})); a.position.set(i*.45,.24,k*.45); a.castShadow=true; scene.add(a); }
  if (CFG.label) hudLabel(CFG.label, blue?'#7dfcff':'#ff6b6b', .33);
  const dur = CFG.type==='photon_hit' ? .45 : .25;
  draw=t=>{
    photons.forEach(o=>{ const f=(t-o.delay)/dur; const from=new THREE.Vector3(o.x-2.2, 3.4, o.z+1.2), to=new THREE.Vector3(o.x, .2, o.z);
      if (f<0||f>1.05){ o.p.visible=false; o.trail.visible=false; return; } o.p.visible=o.trail.visible=true;
      const pos=from.clone().lerp(to,Math.min(1,f)); o.p.position.copy(pos); o.trail.position.copy(pos.clone().lerp(from,.12)); o.trail.lookAt(to); o.trail.rotateX(Math.PI/2);
      if (!blue && f>=1){ o.p.scale.setScalar(Math.max(.01,1-(f-1)*20)); } });
    electrons.forEach(o=>{ const f=(t-o.delay-dur); if (f<0){o.e.visible=false; return;} o.e.visible=true; const sp = CFG.type==='photon_hit'?3.2:4.5;
      o.e.position.set(o.x,.25,o.z).add(o.dir.clone().multiplyScalar(f*sp)); });
    const cz = CFG.type==='photon_hit' ? 3.4 : 5.6; camera.position.set(Math.sin(t*.6)*1.2, 2.9, cz); camera.lookAt(0,.5,0); composer.render(); };
}

if (CFG.type==='scientist') {
  scene.background = grad(CFG.mode==='medal'?'#2a1838':'#10203f', '#04060f'); stage(0x1b2238);
  const key=keyLight(2.5,6,4,2.6); key.target.position.set(0,1.2,0); scene.add(new THREE.AmbientLight(0x6070a0,.45)); const rim=new THREE.DirectionalLight(0x88aaff,.8); rim.position.set(-3,3,-4); scene.add(rim);
  const sc = scientist(); scene.add(sc);
  const orbs=[]; if (CFG.mode==='think') for(let i=0;i<10;i++){ const o=glowBall(.06,i%2?'#5aa8ff':'#ffd23f',3.5); scene.add(o); orbs.push([o,i/10*Math.PI*2, .9+rnd()*.5, 1.2+rnd()*1.2]); }
  let medal=null; if (CFG.mode==='medal'){ medal=new THREE.Mesh(new THREE.CylinderGeometry(.24,.24,.04,48), new THREE.MeshStandardMaterial({color:0xffc94a, metalness:.6, roughness:.25, emissive:0xb07a10, emissiveIntensity:.9}));
    medal.rotation.x=Math.PI/2; medal.position.set(0,1.25,.48); sc.add(medal); }
  const confetti=[]; if (CFG.mode==='medal') for(let i=0;i<60;i++){ const c=new THREE.Mesh(new THREE.PlaneGeometry(.06,.1), new THREE.MeshBasicMaterial({color:new THREE.Color().setHSL(rnd(),.8,.6), side:THREE.DoubleSide}));
    c.position.set((rnd()-.5)*4, 3+rnd()*2, (rnd()-.5)*2); scene.add(c); confetti.push([c,.5+rnd()]); }
  if (CFG.label) hudLabel(CFG.label, '#ffd23f', .33);
  draw=t=>{
    if (CFG.mode==='flip'){ const ph=(t*(CFG.flips||1.6))%1; const up=ph<.75 ? Math.sin(Math.PI*ph/.75) : 0; sc.position.y=up*1.6; sc.rotation.x = ph<.75 ? -2*Math.PI*ease(ph/.75) : 0;
      camera.position.set(1.4, 2.6, 7.4); camera.lookAt(0,1.9,0); }
    else if (CFG.mode==='think'){ sc.rotation.y = .25*Math.sin(t*2); orbs.forEach(([o,a,r,h],i)=>{ const b=a+t*4; o.position.set(Math.cos(b)*r*1.4, h+.3*Math.sin(b*2), Math.sin(b)*r); });
      camera.position.set(0, 1.9, 6.2-.8*t); camera.lookAt(0,1.6,0); }
    else { sc.rotation.y = -.3+.6*t; confetti.forEach(([c,s])=>{ c.position.y -= .03*s; c.rotation.x+=.1*s; c.rotation.y+=.07; if(c.position.y<0) c.position.y=4; });
      camera.position.set(0,1.8,5.8-.6*t); camera.lookAt(0,1.5,0); }
    composer.render(); };
}

if (CFG.type==='solar') {
  scene.background = grad('#2f6fd6','#a9cdf5'); keyLight(3,7,4,2.2); scene.add(new THREE.HemisphereLight(0xffffff,0x88aacc,.45)); stage(0x557a3c);
  const cell=document.createElement('canvas'); cell.width=cell.height=512; const cg=cell.getContext('2d'); cg.fillStyle='#0b1f4d'; cg.fillRect(0,0,512,512); cg.strokeStyle='#8fa8d8'; cg.lineWidth=4;
  for(let i=0;i<=8;i++){ cg.beginPath(); cg.moveTo(i*64,0); cg.lineTo(i*64,512); cg.stroke(); cg.beginPath(); cg.moveTo(0,i*64); cg.lineTo(512,i*64); cg.stroke(); }
  const panel=new THREE.Mesh(new THREE.BoxGeometry(2.8,.06,1.8), [0,0,new THREE.MeshStandardMaterial({map:new THREE.CanvasTexture(cell), metalness:.6, roughness:.25}),0,0,0].map(m=>m||new THREE.MeshStandardMaterial({color:0x9aa3ad, metalness:.8, roughness:.3})));
  panel.position.set(-.4,1.0,0); panel.rotation.x=.75; panel.castShadow=true; scene.add(panel);
  const leg=new THREE.Mesh(new THREE.CylinderGeometry(.05,.05,1,12), new THREE.MeshStandardMaterial({color:0x777777})); leg.position.set(-.5,.5,.2); scene.add(leg);
  const sunB=glowBall(.45,'#fff3b0',2.2); sunB.position.set(2.6,4.4,-2); scene.add(sunB);
  const bulbG=new THREE.Mesh(new THREE.SphereGeometry(.28,32,24), new THREE.MeshStandardMaterial({color:0xfff6d5, emissive:0xffd060, emissiveIntensity:0, transparent:true, opacity:.9})); bulbG.position.set(1.9,.9,.6); scene.add(bulbG);
  const base=new THREE.Mesh(new THREE.CylinderGeometry(.12,.14,.25,16), new THREE.MeshStandardMaterial({color:0x888888, metalness:.8})); base.position.set(1.9,.55,.6); scene.add(base);
  const wire=new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(.8,.8,.2),new THREE.Vector3(1.3,.3,.5),new THREE.Vector3(1.9,.45,.6)]),40,.025,8), new THREE.MeshStandardMaterial({color:0x222222})); scene.add(wire);
  const rays=[]; for(let i=0;i<26;i++){ const r=glowBall(.05,'#ffe066',3); scene.add(r); rays.push([r,rnd(),(rnd()-.5)*2.2,(rnd()-.5)*1.4]); }
  if (CFG.label) hudLabel(CFG.label,'#0b1f4d',.33);
  draw=t=>{ rays.forEach(([r,d,x,z])=>{ const f=((t*1.6+d)%1); r.position.set(2.6+(x-.5-2.6)*f, 4.4+(1.0-4.4)*f, -2+(z+2)*f); });
    bulbG.material.emissiveIntensity = Math.min(2.5, Math.max(0,(t-.35)*5)); camera.position.set(-.2+.4*t, 3.0, 5.6); camera.lookAt(.4,1,0); composer.render(); };
}
// ── 공통: 비네트 + 필름 그레인 (애니메이션 키트 기법) ──
const SEC = CFG.seconds||4;
const gradePass = new THREE.ShaderPass({uniforms:{tDiffuse:{value:null}, uT:{value:0}, uVig:{value:CFG.vignette??0.32}},
  vertexShader:'varying vec2 vUv; void main(){vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
  fragmentShader:'uniform sampler2D tDiffuse; uniform float uT,uVig; varying vec2 vUv; float h(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233))+uT*7.13)*43758.5453);} void main(){ vec4 c=texture2D(tDiffuse,vUv); vec2 q=vUv-.5; c.rgb*=1.-uVig*smoothstep(.22,.72,length(q)); c.rgb+=(h(vUv*1080.)-.5)*.022; gl_FragColor=c; }'});
composer.addPass(gradePass);
function sunLight(x,y,z,int,size){ const l=new THREE.DirectionalLight(0xfff1dc,int); l.position.set(x,y,z); l.castShadow=true; l.shadow.mapSize.set(2048,2048);
  const c=l.shadow.camera; c.left=c.bottom=-(size||6); c.right=c.top=(size||6); c.near=.5; c.far=60; l.shadow.bias=-0.0005; l.shadow.normalBias=.02; scene.add(l); scene.add(l.target); return l; }
function sph(r,m,p,s,seg){ const o=new THREE.Mesh(new THREE.SphereGeometry(r,seg||40,(seg||40)*.7|0),m); o.position.set(...p); if(s) o.scale.set(...s); o.castShadow=true; return o; }
function feather(){ const g=new THREE.Group(); const sh=new THREE.Shape(); sh.moveTo(0,-.2); sh.quadraticCurveTo(.09,-.05,.035,.2); sh.quadraticCurveTo(0,.24,-.035,.2); sh.quadraticCurveTo(-.09,-.05,0,-.2);
  const vane=new THREE.Mesh(new THREE.ShapeGeometry(sh,24), new THREE.MeshStandardMaterial({color:0xf2ece0, roughness:.9, side:THREE.DoubleSide})); vane.castShadow=true; g.add(vane);
  const q=new THREE.Mesh(new THREE.CylinderGeometry(.005,.007,.48,8), new THREE.MeshStandardMaterial({color:0xcbbd9f})); q.position.y=-.02; g.add(q);
  for(let i=0;i<6;i++){ const b=new THREE.Mesh(new THREE.PlaneGeometry(.12,.01), new THREE.MeshBasicMaterial({color:0x9c8f78, side:THREE.DoubleSide})); b.position.set(0,-.12+i*.05,.001); b.rotation.z=(i%2?.5:-.5); g.add(b); }
  return g; }
function tag(text,color,w){ const L=label(text,color,110); const k=w||1.6; L.scale.set(k,k*.186,1); scene.add(L); return L; }

// ── 갈릴레이풍 만화 캐릭터: 대머리 정수리 + 옆머리, 풍성한 수염, 검은 학자 가운, 흰 깃 / 눈꺼풀·입·눈썹 표정 ──
function galileo(){
  const g=new THREE.Group();
  const skin=new THREE.MeshStandardMaterial({color:0xeab48d, roughness:.58}), hairM=new THREE.MeshStandardMaterial({color:0x9a8270, roughness:.95});
  const robe=new THREE.MeshStandardMaterial({color:0x2b2433, roughness:.8}), white=new THREE.MeshStandardMaterial({color:0xf4efe4, roughness:.7});
  const body=new THREE.Mesh(new THREE.CylinderGeometry(.36,.64,1.45,48), robe); body.position.y=.76; body.castShadow=true; g.add(body);
  const collar=new THREE.Mesh(new THREE.CylinderGeometry(.44,.5,.09,48), white); collar.position.y=1.5; g.add(collar);
  for(const x of [-.12,.12]) g.add(sph(.05,new THREE.MeshStandardMaterial({color:0xc9a23a, metalness:.8, roughness:.3}),[x*.0,1.2-(x>0?.25:0),.47],[1,1,.5],16));
  const H=new THREE.Group(); H.position.y=1.98; g.add(H);
  H.add(sph(.4,skin,[0,0,0],[1,1.08,.98],48));
  const side=new THREE.Mesh(new THREE.SphereGeometry(.425,48,24,Math.PI*.78,Math.PI*1.44,Math.PI*.36,Math.PI*.36), hairM); side.castShadow=true; H.add(side);
  for(const x of [-1,1]) H.add(sph(.13,hairM,[x*.36,.02,-.05],[.6,1.1,1.1],24));
  H.add(sph(.31,hairM,[0,-.3,.15],[1.08,1.2,.82],40));               // 수염
  const must=sph(.12,hairM,[0,-.1,.385],[1.7,.48,.6],24); H.add(must);
  H.add(sph(.072,skin,[0,.0,.42],[1,1.3,1.2],24));                  // 코
  for(const x of [-1,1]) H.add(sph(.07,skin,[x*.4,0,0],[.5,1,.8],20));  // 귀
  const mouth=sph(.06,new THREE.MeshStandardMaterial({color:0x3a1414, roughness:.6}),[0,-.2,.43],[1.2,.25,.4],20); H.add(mouth);
  const lids=[], brows=[];
  for(const x of [-1,1]){ H.add(sph(.072,new THREE.MeshStandardMaterial({color:0xffffff, roughness:.25}),[x*.145,.1,.335],null,24));
    H.add(sph(.042,new THREE.MeshStandardMaterial({color:0x4a3220, roughness:.2}),[x*.145,.1,.39],[1,1,.5],20));
    H.add(sph(.022,new THREE.MeshStandardMaterial({color:0x0c0c0c, roughness:.1}),[x*.145,.1,.405],[1,1,.4],16));
    H.add(sph(.008,new THREE.MeshBasicMaterial({color:0xffffff}),[x*.145+.012,.115,.415],null,8));
    const lid=new THREE.Mesh(new THREE.SphereGeometry(.077,24,12,0,Math.PI*2,0,Math.PI/2), skin); lid.position.set(x*.145,.1,.335); H.add(lid); lids.push(lid);
    const b=new THREE.Mesh(new THREE.BoxGeometry(.17,.04,.05), hairM); b.position.set(x*.15,.215,.37); H.add(b); brows.push([b,x]); }
  const arms=[]; for(const x of [-1,1]){ const P=new THREE.Group(); P.position.set(x*.43,1.38,0); g.add(P);
    const a=new THREE.Mesh(new THREE.CylinderGeometry(.1,.13,.78,20), robe); a.position.y=-.39; a.castShadow=true; P.add(a);
    const cuff=new THREE.Mesh(new THREE.CylinderGeometry(.135,.135,.06,20), white); cuff.position.y=-.76; P.add(cuff);
    P.add(sph(.1,skin,[0,-.86,0],null,20)); P.rotation.z=x*.22; arms.push(P); }
  for(const x of [-.18,.18]) g.add(sph(.13,new THREE.MeshStandardMaterial({color:0x1d1712, roughness:.6}),[x,.05,.14],[1,.6,1.6],20));
  function face(open,close,raise){ mouth.scale.set(1.2-open*.2,.25+open*1.6,.4); mouth.position.y=-.2-open*.03;
    lids.forEach(l=>l.rotation.x=-.55+close*1.75); brows.forEach(([b,x])=>{ b.position.y=.215+raise*.05; b.rotation.z=-x*raise*.3; }); }
  face(0,.15,0); return {g,H,arms,face};
}

if (CFG.type==='galileo') {
  scene.background = grad(CFG.mode==='flip'?'#3d2a5c':'#173a5e', '#05070f'); stage(0x1c2135);
  const key=keyLight(2.5,6,4,2.8); key.target.position.set(0,1.3,0); scene.add(new THREE.AmbientLight(0x6070a0,.42));
  const rim=new THREE.DirectionalLight(0xffc98a,1.0); rim.position.set(-3,3,-4); scene.add(rim);
  const G=galileo(); scene.add(G.g);
  const qs=[]; if (CFG.mode==='think') for(let i=0;i<5;i++){ const q=label('?','#ffd23f',220); q.scale.set(1.5,.28,1); scene.add(q); qs.push([q,i/5*Math.PI*2]); }
  if (CFG.label) hudLabel(CFG.label,'#ffd23f',.33);
  draw=t=>{ const s=t*SEC;
    if (CFG.mode==='flip'){ const ph=(s*.42)%1; const up=ph<.75?Math.sin(Math.PI*ph/.75):0; G.g.position.y=up*1.7; G.g.rotation.x = ph<.75 ? -2*Math.PI*ease(ph/.75) : 0;
      G.arms[0].rotation.z=-.22-1.9*up; G.arms[1].rotation.z=.22+1.9*up; G.face(.9,0,1);
      camera.position.set(1.5,2.6,7.6); camera.lookAt(0,1.9,0); }
    else { const blink = (s%2.3)<.12 ? 1 : 0; G.face(.15, blink?1:.25, .6+.4*Math.sin(s*3)); G.H.rotation.z=.18*Math.sin(s*1.4); G.H.rotation.x=-.06;
      G.arms[1].rotation.set(-2.15,0,-.62); G.arms[0].rotation.z=-.25;
      qs.forEach(([q,a],i)=>{ const b=a+s*1.2; q.position.set(Math.cos(b)*1.25, 2.45+.25*Math.sin(s*2.5+i), Math.sin(b)*.7); q.material.opacity=.6+.4*Math.sin(s*3+i); });
      camera.position.set(.3, 2.0, 5.2-.5*t); camera.lookAt(0,1.75,0); }
    gradePass.uniforms.uT.value=s; composer.render(); };
}

function tower(M,M2){ const T=new THREE.Group(), h=.52;
  for(let i=0;i<7;i++){ const r=i<6?.8:.55; const core=new THREE.Mesh(new THREE.CylinderGeometry(r*.9,r*.9,h,48), M2); core.position.y=i*h+h/2; core.castShadow=core.receiveShadow=true; T.add(core);
    const band=new THREE.Mesh(new THREE.CylinderGeometry(r+.1,r+.1,.06,48), M); band.position.y=(i+1)*h; band.castShadow=true; T.add(band);
    const n=i<6?18:12; for(let k=0;k<n;k++){ const a=k/n*Math.PI*2; const c=new THREE.Mesh(new THREE.CylinderGeometry(.032,.036,h-.06,10), M); c.position.set(Math.cos(a)*r, i*h+h/2, Math.sin(a)*r); c.castShadow=true; T.add(c); } }
  return T; }

if (CFG.type==='tower') {
  scene.background = grad('#27477f','#f0b27c'); const sun=sunLight(-5,7,4,2.3,6); sun.target.position.set(0,1.5,0);
  scene.add(new THREE.HemisphereLight(0xbcd2ff,0x7a5a3a,.55));
  const fl=new THREE.Mesh(new THREE.CircleGeometry(14,96), new THREE.MeshStandardMaterial({color:0x6f8d4a, roughness:.95})); fl.rotation.x=-Math.PI/2; fl.receiveShadow=true; scene.add(fl);
  const path=new THREE.Mesh(new THREE.CircleGeometry(1.6,64), new THREE.MeshStandardMaterial({color:0xcfc4b0, roughness:.9})); path.rotation.x=-Math.PI/2; path.position.y=.005; path.receiveShadow=true; scene.add(path);
  const M=new THREE.MeshStandardMaterial({color:0xf3ecdf, roughness:.45}), M2=new THREE.MeshStandardMaterial({color:0xb9ab92, roughness:.7});
  const T=tower(M,M2); T.rotation.z=-.07; scene.add(T);
  const iron=sph(.15,new THREE.MeshStandardMaterial({color:0x3b3f46, metalness:.85, roughness:.35}),[.62,3.72,.45]); T.add(iron);
  const wood=sph(.075,new THREE.MeshStandardMaterial({color:0xb07a45, roughness:.6}),[.62,3.65,-.1]); T.add(wood);
  const q=label('?','#ffe066',220); q.scale.set(2.2,.41,1); scene.add(q);
  if (CFG.label) hudLabel(CFG.label,'#ffe066',.33);
  draw=t=>{ const s=t*SEC; const k=ease(Math.min(1,t*1.1));
    camera.position.set(2.6-1.0*k, .9+2.7*k, 7.2-1.6*k); camera.lookAt(.2, 1.6+2.0*k, 0);
    const wp=new THREE.Vector3(); iron.getWorldPosition(wp); q.position.set(wp.x+.25, wp.y+.75+.06*Math.sin(s*4), wp.z+.2); q.material.opacity=Math.min(1,Math.max(0,(t-.35)*4));
    gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='ancient') {
  scene.background = grad('#c9773a','#2a1a2e'); const sun=sunLight(4,5,3,2.1,7); scene.add(new THREE.HemisphereLight(0xffd9a8,0x3a2430,.5));
  const M=new THREE.MeshStandardMaterial({color:0xe9dcc4, roughness:.55});
  const fl=new THREE.Mesh(new THREE.CircleGeometry(14,64), new THREE.MeshStandardMaterial({color:0x8a6a4e, roughness:.95})); fl.rotation.x=-Math.PI/2; fl.receiveShadow=true; scene.add(fl);
  const temple=new THREE.Group(); temple.position.z=-2.2; scene.add(temple);
  for(let i=0;i<3;i++){ const st=new THREE.Mesh(new THREE.BoxGeometry(5.2-i*.3,.14,2.2-i*.3), M); st.position.y=.07+i*.14; st.castShadow=st.receiveShadow=true; temple.add(st); }
  for(let k=0;k<6;k++) for(const z of [-.6,.6]){ const c=new THREE.Mesh(new THREE.CylinderGeometry(.15,.18,2.3,20), M); c.material.flatShading=true; c.position.set(-2+k*.8,.42+1.15,z); c.castShadow=true; temple.add(c); }
  const arch=new THREE.Mesh(new THREE.BoxGeometry(5,.3,1.7), M); arch.position.y=2.87; arch.castShadow=true; temple.add(arch);
  const tri=new THREE.Shape(); tri.moveTo(-2.6,0); tri.lineTo(2.6,0); tri.lineTo(0,.75); tri.lineTo(-2.6,0);
  const ped=new THREE.Mesh(new THREE.ExtrudeGeometry(tri,{depth:1.6,bevelEnabled:false}), M); ped.position.set(0,3.02,-.8); ped.castShadow=true; temple.add(ped);
  const heavy=sph(.22,new THREE.MeshStandardMaterial({color:0x3b3f46, metalness:.8, roughness:.35}),[-.7,2.5,1.6]); scene.add(heavy);
  const light=sph(.11,new THREE.MeshStandardMaterial({color:0xc08a52, roughness:.6}),[.7,2.5,1.6]); scene.add(light);
  const ghosts=[]; for(let i=0;i<5;i++){ const gh=sph(.2,new THREE.MeshBasicMaterial({color:0x8899aa, transparent:true, opacity:.12}),[-.7,2.5,1.6]); gh.castShadow=false; scene.add(gh); ghosts.push(gh); }
  const yr=tag('약 2,000년','#ffd36b',5.6); yr.position.set(0,.5,2.6);
  if (CFG.label) hudLabel(CFG.label,'#ffe9c0',.33);
  draw=t=>{ const s=t*SEC; const ph=(s/1.9)%1;
    const fh=Math.min(1,ph/.38), fl2=Math.min(1,ph/.95); heavy.position.y=2.5-2.28*fh*fh; light.position.y=2.5-2.39*fl2;
    ghosts.forEach((g,i)=>{ const p=Math.max(0,fh-(i+1)*.12); g.position.y=2.5-2.28*p*p; g.visible=fh<1; });
    yr.material.opacity=Math.min(1,s*1.5);
    camera.position.set(-.5+.4*t, 2.2, 9.4-.5*t); camera.lookAt(0,1.75,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='incline') {
  scene.background = grad('#3a2a1e','#0c0806'); const key=keyLight(-1,7,5,4.2); key.target.position.set(0,.6,0); scene.add(new THREE.AmbientLight(0xa08a75,.9)); scene.add(new THREE.HemisphereLight(0xffe2b8,0x3a2a1e,.6));
  const desk=new THREE.Mesh(new THREE.BoxGeometry(16,.2,12), new THREE.MeshStandardMaterial({color:0x5a3a22, roughness:.7})); desk.position.y=-.1; desk.receiveShadow=true; scene.add(desk);
  const L=4.6, ang=.2; const R=new THREE.Group(); R.position.set(-2.2,1.05,0); R.rotation.z=-ang; scene.add(R);
  const wood=new THREE.MeshStandardMaterial({color:0xa8784a, roughness:.55});
  const ramp=new THREE.Mesh(new THREE.BoxGeometry(L,.1,.7), wood); ramp.position.x=L/2; ramp.castShadow=ramp.receiveShadow=true; R.add(ramp);
  for(const z of [-.27,.27]){ const rail=new THREE.Mesh(new THREE.BoxGeometry(L,.08,.05), new THREE.MeshStandardMaterial({color:0x6b4426})); rail.position.set(L/2,.09,z); R.add(rail); }
  const sup=new THREE.Mesh(new THREE.BoxGeometry(.15,1.05,.5), wood); sup.position.set(-2.1,.5,0); sup.castShadow=true; scene.add(sup);
  const ball=sph(.17,new THREE.MeshStandardMaterial({color:0xc8862e, metalness:.85, roughness:.25}),[0,.18,0]); R.add(ball);
  const unit=L*.92/16, marks=[], nums=[];
  for(let k=1;k<=4;k++){ const m=new THREE.Mesh(new THREE.BoxGeometry(.03,.02,.72), new THREE.MeshStandardMaterial({color:0x222222, emissive:0xffcc55, emissiveIntensity:0})); m.position.set(.12+unit*k*k,.06,0); R.add(m); marks.push(m);
    const n=label(String(2*k-1),'#ffe066',200); n.scale.set(2.4,.45,1); n.position.set(.12+unit*((k-1)**2+(k*k-(k-1)**2)/2),.7,0); n.material.opacity=0; R.add(n); nums.push(n); }
  if (CFG.label) hudLabel(CFG.label,'#ffe9a8',.33);
  draw=t=>{ const s=t*SEC; const f=Math.min(1,Math.max(0,(s-.3)/(SEC*.68))); const x=.12+unit*16*f*f; ball.position.x=x; ball.position.y=.22; ball.rotation.z=-x/.17;
    marks.forEach((m,i)=>{ const on = x>=m.position.x; m.material.emissiveIntensity = on?2.2:0; nums[i].material.opacity = on?1:0; });
    camera.position.set(-.2+.4*t, 1.9, 8.8); camera.lookAt(0,.55,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='vacuum') {
  scene.background = grad('#0f2a3d','#03070c'); const key=keyLight(2,6,5,2.8); key.target.position.set(0,1.5,0); scene.add(new THREE.AmbientLight(0x5a7a9a,.5));
  const rim=new THREE.DirectionalLight(0x9fd8ff,1.1); rim.position.set(-3,4,-4); scene.add(rim); stage(0x14202c);
  const metal=new THREE.MeshStandardMaterial({color:0x8d969f, metalness:.9, roughness:.3});
  const tubes=[]; for(const [x,air] of [[-.95,true],[.95,false]]){ const glass=new THREE.Mesh(new THREE.CylinderGeometry(.42,.42,3.2,48,1,true), new THREE.MeshPhysicalMaterial({color:0xddeeff, transparent:true, opacity:.16, roughness:.05, metalness:0, clearcoat:1, side:THREE.DoubleSide, depthWrite:false}));
    glass.position.set(x,1.85,0); scene.add(glass);
    for(const y of [.2,3.5]){ const cap=new THREE.Mesh(new THREE.CylinderGeometry(.48,.48,.18,48), metal); cap.position.set(x,y,0); cap.castShadow=true; scene.add(cap); }
    const ball=sph(.11,new THREE.MeshStandardMaterial({color:0xd8443a, roughness:.35, metalness:.2}),[x-.12,3.1,0]); scene.add(ball);
    const fe=feather(); fe.position.set(x+.13,3.1,0); scene.add(fe);
    const lb=tag(air?'공기 있음':'공기 없음', air?'#ffffff':'#7dfcff',4.2); lb.position.set(x,-.1,.7);
    tubes.push({x,air,ball,fe}); }
  if (CFG.label) hudLabel(CFG.label,'#7dfcff',.33);
  draw=t=>{ const s=t*SEC; const ph=(s/(SEC*.5))%1; const top=3.1, bot=.42;
    tubes.forEach(o=>{ const fb=Math.min(1,ph/.42); o.ball.position.y=top-(top-bot)*fb*fb;
      if (o.air){ const ff=Math.min(1,ph/1.6); o.fe.position.set(o.x+.13+.1*Math.sin(s*5), top-(top-bot)*ff, 0); o.fe.rotation.z=.6*Math.sin(s*4); }
      else { o.fe.position.set(o.x+.13, top-(top-bot)*fb*fb, 0); o.fe.rotation.z=0; } });
    camera.position.set(0, 2.0, 7.4-.4*t); camera.lookAt(0,1.55,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='moon_drop') {
  scene.background = new THREE.Color(0x000000);
  const sun=sunLight(-7,3.2,2,3.2,5); sun.target.position.set(0,0,0); scene.add(new THREE.HemisphereLight(0x8090b0,0x202020,.18));
  const G=new THREE.PlaneGeometry(40,40,200,200); const P=G.attributes.position; const cr=[]; for(let i=0;i<70;i++){ const a=rnd()*Math.PI*2, d=2.2+rnd()*16; cr.push([Math.cos(a)*d,Math.sin(a)*d,.25+rnd()*1.6]); }
  for(let i=0;i<P.count;i++){ const x=P.getX(i), y=P.getY(i); let h=.02*Math.sin(x*3.1+y*1.7)+.015*Math.sin(x*7.3-y*5.1);
    for(const [cx,cy,r] of cr){ const d=Math.hypot(x-cx,y-cy)/r; if(d<1) h-= .22*r*(1-d*d); else if(d<1.4) h+= .06*r*Math.sin((d-1)/.4*Math.PI); }
    P.setZ(i,h*Math.min(1,Math.hypot(x,y)/2.2)); }
  G.computeVertexNormals(); const ground=new THREE.Mesh(G, new THREE.MeshStandardMaterial({color:0x9a9894, roughness:1})); ground.rotation.x=-Math.PI/2; ground.receiveShadow=true; scene.add(ground);
  const sv=[]; for(let i=0;i<900;i++){ const a=rnd()*Math.PI*2, b=rnd()*Math.PI*.45; sv.push(Math.cos(a)*Math.cos(b)*60, 4+Math.sin(b)*60, Math.sin(a)*Math.cos(b)*60); }
  const sg=new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.Float32BufferAttribute(sv,3)); scene.add(new THREE.Points(sg, new THREE.PointsMaterial({color:0xffffff, size:.12, sizeAttenuation:true})));
  const foil=new THREE.MeshStandardMaterial({color:0xd8a93a, metalness:.95, roughness:.38}), dark=new THREE.MeshStandardMaterial({color:0x3a3a3e, metalness:.6, roughness:.5});
  const lander=new THREE.Group(); lander.position.set(-4.6,0,-6.4); lander.rotation.y=.5; scene.add(lander);
  const lb=new THREE.Mesh(new THREE.CylinderGeometry(1.0,1.0,.8,8), foil); lb.position.y=1.0; lb.castShadow=true; lander.add(lb);
  const top=new THREE.Mesh(new THREE.BoxGeometry(1.2,.8,1.1), new THREE.MeshStandardMaterial({color:0xb9bcc2, metalness:.5, roughness:.45})); top.position.y=1.8; top.castShadow=true; lander.add(top);
  for(let k=0;k<4;k++){ const a=k/4*Math.PI*2+.4; const A=new THREE.Vector3(Math.cos(a)*.85,.75,Math.sin(a)*.85), B=new THREE.Vector3(Math.cos(a)*1.45,.05,Math.sin(a)*1.45); const leg=new THREE.Mesh(new THREE.CylinderGeometry(.04,.04,A.distanceTo(B),8), dark); leg.position.copy(A).add(B).multiplyScalar(.5); leg.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), B.clone().sub(A).normalize()); leg.castShadow=true; lander.add(leg);
    const pad=new THREE.Mesh(new THREE.CylinderGeometry(.18,.2,.05,16), dark); pad.position.set(Math.cos(a)*1.45,.03,Math.sin(a)*1.45); lander.add(pad); }
  const hammer=new THREE.Group(); const hdl=new THREE.Mesh(new THREE.CylinderGeometry(.018,.022,.36,12), new THREE.MeshStandardMaterial({color:0x8f949a, metalness:.7, roughness:.35})); hdl.castShadow=true; hammer.add(hdl);
  const hh=new THREE.Mesh(new THREE.BoxGeometry(.14,.045,.045), new THREE.MeshStandardMaterial({color:0xb7bcc2, metalness:.9, roughness:.25})); hh.position.y=.18; hh.castShadow=true; hammer.add(hh); scene.add(hammer);
  const fe=feather(); fe.scale.setScalar(.9); scene.add(fe);
  const tH=tag('망치 1.32kg','#ffffff',1.3), tF=tag('깃털 (몇 g)','#ffffff',1.3);
  const dust=[]; for(let i=0;i<46;i++){ const d=sph(.018+rnd()*.02,new THREE.MeshBasicMaterial({color:0xb8b5ae, transparent:true, opacity:.8}),[0,0,0],null,8); d.castShadow=false; d.visible=false; scene.add(d);
    dust.push([d, i<23?-.2:.2, rnd()*Math.PI*2, .3+rnd()*.7, .4+rnd()*.8]); }
  const hudA = hudLabel(CFG.label||'1971년 · 아폴로 15호 · 달','#ffe066',.33);
  const hudB = hudLabel(CFG.label2||'동시에 착지!','#7dfcff',.33); hudB.visible=false;
  const T0=CFG.drop||2.7, SLOW=1.5, Y0=.9, g=1.62; const tLand=T0+SLOW*Math.sqrt(2*(Y0-.03)/g);
  draw=t=>{ const s=t*SEC; const tau=Math.max(0,(s-T0)/SLOW); let y=Y0-.5*g*tau*tau; const landed=y<=.03; if(landed) y=.03;
    hammer.position.set(-.2,y+.17,0); hammer.rotation.z = landed ? Math.min(1.45,(s-tLand)*6) : .25;
    if (landed) hammer.position.y = .05;
    fe.position.set(.2,y+.2,0); fe.rotation.z = landed ? Math.min(1.5,(s-tLand)*5) : 0; if (landed) fe.position.y=.02;
    tH.position.set(-.38,Y0-.3,0); tF.position.set(.38,Y0-.3,0); const tagOn = s>2.2 && s<T0+.6; tH.visible=tF.visible=tagOn;
    dust.forEach(([d,x,a,sp,up])=>{ const u=s-tLand; d.visible=u>0&&u<1.6; if(!d.visible) return; d.position.set(x+Math.cos(a)*sp*u*.5, up*u*.5-.5*g*.3*u*u+.02, Math.sin(a)*sp*u*.5); d.material.opacity=.8*(1-u/1.6); });
    hudA.visible = s<T0+.2; hudB.visible = s>tLand+.15;
    if (s<2.2){ const k=s/2.2; camera.position.set(4.6-1.2*k, 2.0-.3*k, 6.8-1.6*k); camera.lookAt(-1.2,1.0,-2); }
    else { const k=ease(Math.min(1,(s-2.2)/.8)), lk=ease(Math.min(1,Math.max(0,(s-tLand)/1.0))), o=(s-2.2)*.04;
      const d=2.9-1.2*lk, h=.95-.55*lk, lkY=.75-.65*lk; const P1=new THREE.Vector3(d*Math.sin(.3+o), h, d*Math.cos(.3+o));
      camera.position.copy(new THREE.Vector3(3.4,1.7,5.2).lerp(P1,k)); camera.lookAt(new THREE.Vector3(-1.2,1,-2).lerp(new THREE.Vector3(0,lkY,0),k)); }
    gradePass.uniforms.uT.value=s; composer.render(); };
}

// ── 자막 자리 비우기: 장면 속 글씨(스프라이트)가 정사각 아래 ~21%(대본 자막 상자) 안으로 들어가면 렌더 순간 위로 올림 ──
const CAP_NDC = -0.56;
const _render = composer.render.bind(composer);
composer.render = function(){ const saved=[]; camera.updateMatrixWorld(); const up=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,1).normalize();
  const k=Math.tan(camera.fov*Math.PI/360);
  scene.traverse(o=>{ if(!o.isSprite||!o.visible||o.parent===camera) return; let vis=true; o.traverseAncestors(a=>{ if(!a.visible) vis=false; }); if(!vis) return;
    const wp=new THREE.Vector3(); o.getWorldPosition(wp); const v=wp.clone().project(camera); if(v.z>1||Math.abs(v.x)>1.2) return;
    const dist=wp.distanceTo(camera.position), ws=new THREE.Vector3(); o.getWorldScale(ws);
    const bottom=v.y-(ws.y*.25)/(dist*k); if(bottom>=CAP_NDC) return;
    const nw=wp.clone().addScaledVector(up,(CAP_NDC-bottom)*dist*k); saved.push([o,o.position.clone()]); o.parent.worldToLocal(nw); o.position.copy(nw); });
  _render(); saved.forEach(([o,q])=>o.position.copy(q)); };
window.draw=draw; window.ready=new Promise(r=>setTimeout(r,800));
</script></body></html>"""


async def _render(cfg, out):
    from playwright.async_api import async_playwright
    libs = "".join(f"<script>{(A3 / f).read_text()}</script>" for f in LIBS)
    html = HTML.replace("__LIBS__", libs).replace("__CFG__", json.dumps(cfg, ensure_ascii=False)).replace("__S__", str(S))
    tmp = Path(tempfile.mkdtemp(prefix="s3p-"))
    (tmp / "s.html").write_text(html, "utf-8")
    n = int(cfg.get("seconds", 4) * FPS)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": S, "height": S})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto((tmp / "s.html").as_uri())
        await pg.evaluate("window.ready")
        if errs:
            raise RuntimeError("3D 페이지 오류: " + " | ".join(errs)[:500])
        for i in range(n):
            await pg.evaluate(f"window.draw({i / max(1, n - 1)})")
            await pg.screenshot(path=str(tmp / f"f{i:04d}.jpg"), type="jpeg", quality=92)
        await b.close()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.jpg"),
                    "-f", "lavfi", "-t", f"{n / FPS:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    print(f"[scene3d_pro] {cfg['type']} {n}프레임 → {out}")
    return Path(out)


async def _snap(cfg, ts, out_prefix):
    """렌더 전 스틸 확인 (애니메이션 키트의 --snap). ts = 0~1 비율 목록."""
    from playwright.async_api import async_playwright
    libs = "".join(f"<script>{(A3 / f).read_text()}</script>" for f in LIBS)
    html = HTML.replace("__LIBS__", libs).replace("__CFG__", json.dumps(cfg, ensure_ascii=False)).replace("__S__", str(S))
    tmp = Path(tempfile.mkdtemp(prefix="s3s-")); (tmp / "s.html").write_text(html, "utf-8")
    outs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": S, "height": S}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto((tmp / "s.html").as_uri()); await pg.evaluate("window.ready")
        if errs:
            raise RuntimeError("3D 페이지 오류: " + " | ".join(errs)[:500])
        for t in ts:
            await pg.evaluate(f"window.draw({t})"); o = f"{out_prefix}_{t:.2f}.jpg"
            await pg.screenshot(path=o, type="jpeg", quality=80); outs.append(o)
            from PIL import Image, ImageDraw   # 자막 자리 표시(빨간 띠) — 여기에 장면 글씨가 있으면 안 됨
            im = Image.open(o).convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(ov).rectangle((0, int(S * .79), S, int(S * .97)), fill=(255, 0, 0, 60), outline=(255, 0, 0, 200), width=4)
            Image.alpha_composite(im, ov).convert("RGB").save(o, quality=80)
        await b.close()
    return outs


def snap(cfg, ts, out_prefix):
    return asyncio.run(_snap(cfg, ts, out_prefix))


def render(cfg, out):
    return asyncio.run(_render(cfg, out))


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[3] == "--snap":   # python -m bot.scene3d_pro 장면.json 접두어 --snap 0.2,0.8
        print(snap(json.loads(Path(sys.argv[1]).read_text("utf-8")), [float(x) for x in sys.argv[4].split(",")], sys.argv[2])); sys.exit()
    render(json.loads(Path(sys.argv[1]).read_text("utf-8")), sys.argv[2])
