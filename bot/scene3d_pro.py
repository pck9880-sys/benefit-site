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
  archimedes   아르키메데스풍 만화 학자(흰 곱슬 수염·월계관·흰 토가+붉은 띠) mode: "think" / "flip"
  ship_float   파도치는 바다 위에 뜬 강철 화물선 + 물음표 (label)
  nail_sink    물 수조에 쇠못이 떨어져 꼬르륵 가라앉음 (label)
  bath         욕조에 학자가 앉자 물이 차올라 넘침 → "유레카!" (label)
  buoy         수조에 돌덩이를 넣자 넘친 물이 비커로, 위로 미는 빨간 화살표(부력) (label)
  float_proof  긴 클립: 같은 쇠 — 덩어리는 가라앉고 그릇 모양은 뜸 (label/label2, drop 초)
  pasteur      파스퇴르풍 만화 학자(검은 머리·턱수염·나비넥타이) mode: "think" / "flip" — galileo() 옵션으로 만듦
  broth_jar    유리병 고기 국물이 맑은 금빛 → 뿌옇게 썩음(거품·곰팡이 점) + 물음표
  spont_old    접시 위 고기에서 파리가 '저절로' 생겨나는 옛 상식(자연발생설) 장면 (tag)
  swan_flask   백조목(S자 목) 플라스크. mode "boil" 알코올램프로 국물 끓임·김 / "dust" 공기는 통과, 먼지는 휜 목에 걸림
  swan_break   긴 클립: 목이 부러져 떨어짐 → 먼지가 바로 들어가 국물이 뿌옇게, 미생물 증식 (label/label2, drop 초)
  moon_drop    달 표면·착륙선, 망치와 깃털이 동시에 떨어짐(슬로모션·먼지) — 긴 클립(라벨 label/label2, drop 초)
  earth_tape   우주 속 회전 지구본에 금색 줄자가 한 바퀴 감기며 물음표 (label)
  syene_well   하짓날 정오, 해가 머리 위에서 우물 바닥까지 비침(그림자 없는 막대) (label, tag)
  eratos       에라토스테네스풍 만화 학자(갈색 머리·수염·파란 토가·두루마리) mode: "think"(작은 지구본+물음표) / "flip"
  shadow_stick 알렉산드리아 막대(오벨리스크)에 7.2° 기운 햇빛과 짧은 그림자, 각도 호 (label, tag)
  earth_angle  지구 단면: 평행한 햇빛 + 두 막대 → 중심각 7.2° = 원의 1/50 (그림은 과장 각도) (label)
  earth_proof  긴 클립: 두 도시 사이 호가 ×1→×50 으로 지구를 한 바퀴 채움 → 인공위성·오늘날 값 (label/label2, drop 초)
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
function galileo(o){ o=o||{};
  const g=new THREE.Group();
  const skin=new THREE.MeshStandardMaterial({color:0xeab48d, roughness:.58}), hairM=new THREE.MeshStandardMaterial({color:o.hair||0x9a8270, roughness:.95});
  const robe=new THREE.MeshStandardMaterial({color:o.robe||0x2b2433, roughness:.8}), white=new THREE.MeshStandardMaterial({color:0xf4efe4, roughness:.7});
  const body=new THREE.Mesh(new THREE.CylinderGeometry(.36,.64,1.45,48), robe); body.position.y=.76; body.castShadow=true; g.add(body);
  const collar=new THREE.Mesh(new THREE.CylinderGeometry(.44,.5,.09,48), white); collar.position.y=1.5; g.add(collar);
  for(const x of [-.12,.12]) g.add(sph(.05,new THREE.MeshStandardMaterial({color:0xc9a23a, metalness:.8, roughness:.3}),[x*.0,1.2-(x>0?.25:0),.47],[1,1,.5],16));
  const H=new THREE.Group(); H.position.y=1.98; g.add(H);
  H.add(sph(.4,skin,[0,0,0],[1,1.08,.98],48));
  const side=new THREE.Mesh(new THREE.SphereGeometry(.425,48,24,Math.PI*.78,Math.PI*1.44,Math.PI*.36,Math.PI*.36), hairM); side.castShadow=true; H.add(side);
  for(const x of [-1,1]) H.add(sph(.13,hairM,[x*.36,.02,-.05],[.6,1.1,1.1],24));
  if (o.top){ const cap=new THREE.Mesh(new THREE.SphereGeometry(.43,48,24,0,Math.PI*2,0,Math.PI*.36), hairM); cap.position.y=.03; cap.rotation.x=-.32; cap.castShadow=true; H.add(cap);
    const part=sph(.16,hairM,[-.12,.3,.18],[1.6,.5,1],24); H.add(part); }   // 덮인 앞머리(가르마)
  H.add(sph(.31,hairM,[0,-.3,.15],o.beard||[1.08,1.2,.82],40));               // 수염
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
  if (o.bow){ const bm=new THREE.MeshStandardMaterial({color:0x111116, roughness:.5}); for(const x of [-1,1]){ const c=new THREE.Mesh(new THREE.ConeGeometry(.07,.13,12), bm); c.rotation.z=x*Math.PI/2; c.position.set(x*.065,1.52,.42); g.add(c); } g.add(sph(.03,bm,[0,1.52,.44],null,10)); }
  if (o.laurel){ const lm=new THREE.MeshStandardMaterial({color:0x5a8f3c, roughness:.55}); for(let i=0;i<20;i++){ const a=Math.PI*.22+i/19*Math.PI*1.56;
    const lf=sph(.065,lm,[Math.sin(a)*.42,.2+.02*Math.sin(i*1.7),Math.cos(a)*.42],[.42,1,.22],10); lf.rotation.y=a; lf.rotation.z=(i%2?.7:-.7); H.add(lf); } }
  if (o.sash){ const sm=new THREE.MeshStandardMaterial({color:0x8e2f2a, roughness:.7}); const sa=new THREE.Mesh(new THREE.BoxGeometry(.2,1.35,.05), sm); sa.position.set(.02,1.0,.47); sa.rotation.set(-.17,0,.62); sa.castShadow=true; g.add(sa); }
  face(0,.15,0); return {g,H,arms,face};
}
const ARCH={hair:0xdedad0, robe:0xf0ebdf, top:true, beard:[1.12,1.3,.86], laurel:true, sash:true};

if (CFG.type==='galileo' || CFG.type==='pasteur' || CFG.type==='archimedes') {
  scene.background = grad(CFG.mode==='flip'?'#3d2a5c':'#173a5e', '#05070f'); stage(0x1c2135);
  const key=keyLight(2.5,6,4,2.8); key.target.position.set(0,1.3,0); scene.add(new THREE.AmbientLight(0x6070a0,.42));
  const rim=new THREE.DirectionalLight(0xffc98a,1.0); rim.position.set(-3,3,-4); scene.add(rim);
  const G=galileo(CFG.type==='pasteur'?{hair:0x2b2019, robe:0x15161c, top:true, bow:true, beard:[1.0,1.0,.8]}:CFG.type==='archimedes'?ARCH:{}); scene.add(G.g);
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

// ── 파스퇴르 편: 국물·유리병·백조목 플라스크 ──
const glassMat=()=>new THREE.MeshPhysicalMaterial({color:0xe6f3ff, transparent:true, opacity:.2, roughness:.04, metalness:0, clearcoat:1, side:THREE.DoubleSide, depthWrite:false});
const BROTH=new THREE.Color(0xd9a13c), ROT=new THREE.Color(0x6a6a3a);
function table(c){ const d=new THREE.Mesh(new THREE.BoxGeometry(16,.2,12), new THREE.MeshStandardMaterial({color:c||0x5a3a22, roughness:.7})); d.position.y=-.1; d.receiveShadow=true; scene.add(d); return d; }
function swanFlask(){ const g=new THREE.Group(), gm=glassMat();
  const bulb=new THREE.Mesh(new THREE.SphereGeometry(.7,48,32), gm); bulb.position.y=.7; g.add(bulb);
  const lm=new THREE.MeshStandardMaterial({color:BROTH.clone(), roughness:.15, transparent:true, opacity:.88, emissive:0x3a2000, emissiveIntensity:.25});
  const liq=new THREE.Mesh(new THREE.SphereGeometry(.66,48,24,0,Math.PI*2,Math.PI*.45,Math.PI*.55), lm); liq.position.y=.7; g.add(liq);
  const top=new THREE.Mesh(new THREE.CircleGeometry(.652,48), lm); top.rotation.x=-Math.PI/2; top.position.y=.7+.103; g.add(top);
  const low=new THREE.Mesh(new THREE.CylinderGeometry(.07,.09,.42,20,1,true), gm); low.position.y=1.5; g.add(low);
  const curve=new THREE.CatmullRomCurve3([[0,1.7,0],[.05,1.95,0],[.35,2.18,0],[.75,1.9,0],[1.05,1.58,0],[1.35,1.7,0],[1.6,2.05,0]].map(a=>new THREE.Vector3(...a)));
  const up=new THREE.Group(); up.add(new THREE.Mesh(new THREE.TubeGeometry(curve,80,.07,16,false), gm)); g.add(up);
  return {g,liq:lm,up,curve}; }
function burner(){ const g=new THREE.Group(); const gl=glassMat(); gl.opacity=.35;
  const b=new THREE.Mesh(new THREE.SphereGeometry(.32,32,16,0,Math.PI*2,Math.PI*.35,Math.PI*.65), gl); b.position.y=.3; g.add(b);
  const wick=new THREE.Mesh(new THREE.CylinderGeometry(.05,.05,.18,12), new THREE.MeshStandardMaterial({color:0xcccccc, metalness:.8, roughness:.3})); wick.position.y=.48; g.add(wick);
  const fl=new THREE.Mesh(new THREE.ConeGeometry(.08,.34,20), new THREE.MeshBasicMaterial({color:new THREE.Color(0x66aaff).multiplyScalar(1.4), toneMapped:false, transparent:true, opacity:.85})); fl.position.y=.72; g.add(fl);
  const fo=new THREE.Mesh(new THREE.ConeGeometry(.05,.22,16), new THREE.MeshBasicMaterial({color:new THREE.Color(0xffb040).multiplyScalar(1.5), toneMapped:false})); fo.position.y=.8; g.add(fo);
  return {g,fl,fo}; }
function stand(){ const g=new THREE.Group(), m=new THREE.MeshStandardMaterial({color:0x2c2f36, metalness:.85, roughness:.35});
  const ring=new THREE.Mesh(new THREE.TorusGeometry(.5,.025,10,48), m); ring.rotation.x=Math.PI/2; ring.position.y=1.0; g.add(ring);
  for(let k=0;k<3;k++){ const a=k/3*Math.PI*2; const l=new THREE.Mesh(new THREE.CylinderGeometry(.025,.025,1.0,8), m); l.position.set(Math.cos(a)*.5,.5,Math.sin(a)*.5); l.castShadow=true; g.add(l); } return g; }

if (CFG.type==='broth_jar') {
  scene.background = grad('#3b2a1c','#0b0705'); const key=keyLight(1.5,6,4,3.4); key.target.position.set(0,.8,0); scene.add(new THREE.AmbientLight(0xa08a75,.7));
  const rim=new THREE.DirectionalLight(0xffd8a0,1.0); rim.position.set(-3,3,-4); scene.add(rim); table();
  const jar=new THREE.Mesh(new THREE.CylinderGeometry(.75,.75,1.7,64,1,true), glassMat()); jar.position.y=.85; scene.add(jar);
  const lm=new THREE.MeshStandardMaterial({color:BROTH.clone(), roughness:.2, transparent:true, opacity:.85, emissive:0x3a2000, emissiveIntensity:.25});
  const liq=new THREE.Mesh(new THREE.CylinderGeometry(.72,.72,1.2,64), lm); liq.position.y=.62; scene.add(liq);
  const spots=[]; for(let i=0;i<14;i++){ const a=rnd()*Math.PI*2, r=rnd()*.6; const sp=sph(.05+rnd()*.07,new THREE.MeshStandardMaterial({color:0x8fa36a, roughness:1}),[Math.cos(a)*r,1.23,Math.sin(a)*r],[1,.35,1],16); sp.visible=false; scene.add(sp); spots.push([sp,i/14]); }
  const bub=[]; for(let i=0;i<20;i++){ const b=sph(.025+rnd()*.03,new THREE.MeshStandardMaterial({color:0xfff0c0, transparent:true, opacity:.6}),[(rnd()-.5)*1.1,.1,(rnd()-.5)*1.1],null,10); scene.add(b); bub.push([b,rnd()]); }
  const q=label('?','#ffd23f',220); q.scale.set(2.2,.41,1); scene.add(q);
  if (CFG.label) hudLabel(CFG.label,'#ffd23f',.33);
  draw=t=>{ const s=t*SEC; const k=Math.min(1,Math.max(0,(t-.15)/.7));
    lm.color.copy(BROTH).lerp(ROT,k); lm.opacity=.85+.12*k; lm.emissiveIntensity=.25*(1-k);
    spots.forEach(([sp,th])=>{ sp.visible=k>th; sp.scale.setScalar(Math.min(1,(k-th)*4)); sp.scale.y*=.35; });
    bub.forEach(([b,o])=>{ const u=(s*.5+o)%1; b.position.y=.1+1.1*u; b.visible=k>.2; });
    q.position.set(.9,2.15+.06*Math.sin(s*4),0); q.material.opacity=Math.min(1,Math.max(0,(t-.3)*4));
    camera.position.set(1.4-.6*t, 2.2-.2*t, 5.6-.8*t); camera.lookAt(0,.9,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='spont_old') {
  scene.background = grad('#5a3a22','#120a08'); const key=keyLight(-1.5,6,4,3.2); key.target.position.set(0,.4,0); scene.add(new THREE.AmbientLight(0xb09070,.6)); table(0x4a3020);
  const plate=new THREE.Mesh(new THREE.CylinderGeometry(1.25,1.05,.08,64), new THREE.MeshStandardMaterial({color:0xf2ede2, roughness:.35})); plate.position.y=.04; plate.receiveShadow=true; plate.castShadow=true; scene.add(plate);
  const meat=sph(.55,new THREE.MeshStandardMaterial({color:0x9c3a2e, roughness:.55}),[0,.22,0],[1.25,.36,.9],40); scene.add(meat);
  for(let i=0;i<5;i++){ const f=sph(.1,new THREE.MeshStandardMaterial({color:0xf3e3d0, roughness:.6}),[-.4+i*.2,.33,(rnd()-.5)*.4],[1.4,.3,.6],16); scene.add(f); }
  const flies=[]; for(let i=0;i<12;i++){ const f=new THREE.Group(); f.add(sph(.045,new THREE.MeshStandardMaterial({color:0x111111, roughness:.3}),[0,0,0],[1.4,1,1],12));
    const wm=new THREE.MeshBasicMaterial({color:0xd8e8ff, transparent:true, opacity:.55, side:THREE.DoubleSide}); const ws=[];
    for(const x of [-1,1]){ const w=new THREE.Mesh(new THREE.CircleGeometry(.05,12), wm); w.position.set(0,.03,x*.04); w.rotation.x=Math.PI/2; f.add(w); ws.push(w); }
    f.visible=false; scene.add(f); flies.push([f,ws,i/12,rnd()*Math.PI*2,.5+rnd()*.7,.4+rnd()*.6]); }
  if (CFG.label) hudLabel(CFG.label,'#ffe9c0',.33);
  draw=t=>{ const s=t*SEC;
    flies.forEach(([f,ws,th,a,r,h],i)=>{ const u=(t-.08)-th*.7; f.visible=u>0; if(!f.visible) return; const k=Math.min(1,u*4);
      const b=a+s*(1.5+i%3*.4); f.position.set(Math.cos(b)*r*k, .3+h*k+.08*Math.sin(s*7+i), Math.sin(b)*r*k*.8); f.rotation.y=-b; ws.forEach((w,j)=>w.rotation.y=(j?1:-1)*.6*Math.sin(s*60+i)); });
    camera.position.set(.4+.3*t, 2.4-.3*t, 4.4-.5*t); camera.lookAt(0,.55,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='swan_flask') {
  const dust=CFG.mode==='dust';
  scene.background = grad(dust?'#13314a':'#2c2240','#05070c'); const key=keyLight(2,6,5,3.0); key.target.position.set(.5,1.2,0); scene.add(new THREE.AmbientLight(0x6a7a9a,.6));
  const rim=new THREE.DirectionalLight(0x9fd8ff,1.0); rim.position.set(-3,4,-4); scene.add(rim); table(0x3a2a20);
  const F=swanFlask(); F.g.position.y=dust?0:1.0; scene.add(F.g);
  let B=null; if(!dust){ const st=stand(); scene.add(st); B=burner(); scene.add(B.g); }
  const steam=[]; if(!dust) for(let i=0;i<16;i++){ const p=sph(.06+rnd()*.05,new THREE.MeshBasicMaterial({color:0xffffff, transparent:true, opacity:.3}),[0,0,0],null,10); p.castShadow=false; scene.add(p); steam.push([p,rnd()]); }
  const bub=[]; if(!dust) for(let i=0;i<14;i++){ const b=sph(.03,new THREE.MeshStandardMaterial({color:0xfff2c8, transparent:true, opacity:.7}),[(rnd()-.5)*.8,0,(rnd()-.5)*.8],null,8); F.g.add(b); bub.push([b,rnd()]); }
  const parts=[]; if(dust){ for(let i=0;i<26;i++){ const isDust=i%2==0; const p=sph(isDust?.045:.025,new THREE.MeshBasicMaterial({color:isDust?new THREE.Color(0xc89a5a).multiplyScalar(1.2):new THREE.Color(0x7dfcff).multiplyScalar(1.3), toneMapped:false}),[0,0,0],null,10); p.castShadow=false; scene.add(p); parts.push([p,isDust,i/26]); }
    const t1=tag('먼지','#e8c08a',2.0), t2=tag('공기','#7dfcff',2.0); parts.t1=t1; parts.t2=t2; }
  if (CFG.label) hudLabel(CFG.label,dust?'#7dfcff':'#ffd23f',.33);
  const dip=.62;  // 곡선에서 가장 낮은 곳(먼지가 걸리는 자리) 비율
  draw=t=>{ const s=t*SEC;
    if(!dust){ const fk=1+.12*Math.sin(s*23)+.08*Math.sin(s*37); B.fl.scale.set(1,fk,1); B.fo.scale.set(1,fk*1.1,1);
      bub.forEach(([b,o])=>{ const u=(s*.8+o)%1; b.position.y=.25+.55*u; });
      const end=F.curve.getPoint(1).add(F.g.position); steam.forEach(([p,o])=>{ const u=(s*.45+o)%1; p.position.set(end.x+.15*u+.05*Math.sin(s*3+o*9), end.y+.1+1.0*u, 0); p.scale.setScalar(.6+1.6*u); p.material.opacity=.32*(1-u); });
      camera.position.set(.9+.3*t, 2.0, 8.6-.5*t); camera.lookAt(.7,1.55,0); }
    else { parts.forEach(([p,isDust,o])=>{ const u=Math.min(1,Math.max(0,(s/SEC*1.5-o*.9)));
        let pos; if(u<.25){ const e=F.curve.getPoint(1); const k=u/.25; pos=new THREE.Vector3(e.x+1.2*(1-k), e.y+.6*(1-k), 0); }
        else { const k=(u-.25)/.75; const f=1-k; if(isDust && f<dip) pos=F.curve.getPoint(dip).add(new THREE.Vector3((o-.5)*.08,-.02,0));
          else if(f>0) pos=F.curve.getPoint(f); else pos=new THREE.Vector3(0,1.3-.3*Math.min(1,k),0); }
        p.position.copy(pos); p.visible=u>0; });
      parts.t1.position.copy(F.curve.getPoint(dip)).add(new THREE.Vector3(.05,-.45,0)); parts.t1.material.opacity=Math.min(1,Math.max(0,(t-.45)*4));
      parts.t2.position.set(-.45,1.95,0); parts.t2.material.opacity=Math.min(1,Math.max(0,(t-.6)*4));
      camera.position.set(.6, 1.4, 5.9-.4*t); camera.lookAt(.65,.95,0); }
    gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='swan_break') {
  scene.background = grad('#2a1f3a','#05060a'); const key=keyLight(2,6,5,3.0); key.target.position.set(.4,1,0); scene.add(new THREE.AmbientLight(0x6a7a9a,.6));
  const rim=new THREE.DirectionalLight(0xffc98a,1.0); rim.position.set(-3,4,-4); scene.add(rim); table(0x3a2a20);
  const F=swanFlask(); scene.add(F.g);
  const shards=[]; for(let i=0;i<10;i++){ const sh=new THREE.Mesh(new THREE.TetrahedronGeometry(.03+rnd()*.03), new THREE.MeshPhysicalMaterial({color:0xe6f3ff, transparent:true, opacity:.6, roughness:.05})); sh.visible=false; scene.add(sh); shards.push([sh,(rnd()-.3)*1.4,.6+rnd()*1.2,rnd()*6]); }
  const dust=[]; for(let i=0;i<30;i++){ const d=sph(.03+rnd()*.02,new THREE.MeshBasicMaterial({color:new THREE.Color(0xc89a5a).multiplyScalar(1.2), toneMapped:false}),[0,0,0],null,8); d.castShadow=false; d.visible=false; scene.add(d); dust.push([d,rnd(),(rnd()-.5)*.08]); }
  const mic=[]; for(let i=0;i<60;i++){ const a=rnd()*Math.PI*2, r=Math.sqrt(rnd())*.5, y=.2+rnd()*.6; const m=sph(.028+rnd()*.03,new THREE.MeshBasicMaterial({color:new THREE.Color(0x7dff8a).multiplyScalar(1.1), toneMapped:false, transparent:true, opacity:.9}),[Math.cos(a)*r,y,Math.sin(a)*r],[1.6,1,1],10); m.castShadow=false; m.visible=false; scene.add(m); mic.push([m,i/60,a]); }
  const hudA=hudLabel(CFG.label||'목을 부러뜨리면?','#ffe066',.33), hudB=hudLabel(CFG.label2||'범인은 미생물!','#7dff8a',.33); hudB.visible=false;
  const T0=CFG.drop||2.6, T1=T0+1.4;
  draw=t=>{ const s=t*SEC; const fall=Math.max(0,s-T0);
    if(fall>0){ const k=Math.min(1,fall/.9); F.up.position.set(.9*k, -1.5*k*k, 0); F.up.rotation.z=-1.1*k; F.up.visible=fall<.9; }
    shards.forEach(([sh,vx,vy,r])=>{ const u=fall; sh.visible=u>0&&u<1.2; if(!sh.visible) return; sh.position.set(vx*u, 1.72+vy*u-2.5*u*u, .05); sh.rotation.set(r*u,r*u*.7,0); });
    dust.forEach(([d,o,dx])=>{ const u=((s-T0-.6)*.55-o*1.2); d.visible=u>0&&u<1; if(!d.visible) return; d.position.set(dx, 2.6-1.9*u, 0); });
    const rot=Math.min(1,Math.max(0,(s-T1)/(SEC*.45))); F.liq.color.copy(BROTH).lerp(ROT,rot); F.liq.emissiveIntensity=.25*(1-rot);
    mic.forEach(([m,th,a])=>{ m.visible=rot>th*.9; if(m.visible){ m.rotation.y=a+s; m.scale.setScalar(1+.15*Math.sin(s*5+a*7)); m.scale.x*=1.6; } });
    hudA.visible=s<T1+1.2; hudB.visible=s>=T1+1.2;
    const o=s*.05; const d=5.6-.9*Math.min(1,s/SEC*1.6); camera.position.set(Math.sin(.25+o)*d+.3, 1.6+.2*Math.sin(s*.3), Math.cos(.25+o)*d); camera.lookAt(.3,.75,0);
    gradePass.uniforms.uT.value=s; composer.render(); };
}


// ── 아르키메데스 편: 바다·수조·욕조·부력 ──
const waterMat=()=>new THREE.MeshPhysicalMaterial({color:0x2f8fd8, transparent:true, opacity:.5, roughness:.05, metalness:0, clearcoat:1, depthWrite:false});
const steelMat=()=>new THREE.MeshStandardMaterial({color:0x8a929c, metalness:.85, roughness:.32});
function tank(w,h,d){ const g=new THREE.Group(); const gl=new THREE.Mesh(new THREE.BoxGeometry(w,h,d), glassMat()); gl.position.y=h/2; g.add(gl);
  const ed=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(w,h,d)), new THREE.LineBasicMaterial({color:0xcfe8ff, transparent:true, opacity:.55})); ed.position.y=h/2; g.add(ed);
  const wg=new THREE.BoxGeometry(w-.04,1,d-.04); wg.translate(0,.5,0); const water=new THREE.Mesh(wg,waterMat()); water.position.y=.02; water.renderOrder=2; g.add(water);
  return {g,water,set:l=>water.scale.y=Math.max(.001,l-.02)}; }
function splash(n,color){ const ps=[]; for(let i=0;i<n;i++){ const d=sph(.025+rnd()*.025,new THREE.MeshStandardMaterial({color:color||0x9fd6ff, transparent:true, opacity:.8, roughness:.1}),[0,0,0],null,8); d.castShadow=false; d.visible=false; scene.add(d);
    ps.push([d,rnd()*Math.PI*2,.4+rnd()*.9,1.2+rnd()*1.6]); }
  return (x,y,z,u)=>ps.forEach(([d,a,sp,up])=>{ d.visible=u>0&&u<.9; if(!d.visible) return; d.position.set(x+Math.cos(a)*sp*u*.6, y+up*u-4.9*u*u, z+Math.sin(a)*sp*u*.4); }); }
function bubbles(n){ const bs=[]; for(let i=0;i<n;i++){ const b=sph(.02+rnd()*.025,new THREE.MeshStandardMaterial({color:0xe8f6ff, transparent:true, opacity:.65, roughness:.05}),[0,0,0],null,8); b.castShadow=false; b.visible=false; scene.add(b); bs.push([b,rnd(),(rnd()-.5)*.25,(rnd()-.5)*.2]); }
  return (x,y,top,on,s)=>bs.forEach(([b,o,dx,dz])=>{ const u=(s*.9+o)%1; b.visible=on; if(on) b.position.set(x+dx+.03*Math.sin(s*6+o*9), y+(top-y)*u, dz); }); }
function upArrow(color){ const g=new THREE.Group(), m=new THREE.MeshBasicMaterial({color:new THREE.Color(color||0xff4d4d).multiplyScalar(1.3), toneMapped:false});
  const sh=new THREE.Mesh(new THREE.CylinderGeometry(.05,.05,1,16), m); sh.position.y=.5; g.add(sh); const hd=new THREE.Mesh(new THREE.ConeGeometry(.13,.26,20), m); g.add(hd);
  g.setLen=L=>{ sh.scale.y=Math.max(.001,L); sh.position.y=L/2; hd.position.y=L+.12; g.visible=L>.03; }; return g; }

if (CFG.type==='ship_float') {
  scene.background=grad('#6a9fd4','#0d2238'); const sun=sunLight(-5,7,4,2.6,8); sun.target.position.set(0,0,0); scene.add(new THREE.HemisphereLight(0xcfe4ff,0x1a2a3a,.75));
  const sg=new THREE.PlaneGeometry(40,40,110,110); sg.rotateX(-Math.PI/2); const sea=new THREE.Mesh(sg,new THREE.MeshStandardMaterial({color:0x1b5f93, roughness:.2, metalness:.2})); sea.receiveShadow=true; scene.add(sea);
  const pos=sg.attributes.position;
  const ship=new THREE.Group(); scene.add(ship);
  const top=new THREE.Shape(); top.moveTo(-1.7,-.5); top.lineTo(1.0,-.5); top.quadraticCurveTo(1.7,-.35,2.0,0); top.quadraticCurveTo(1.7,.35,1.0,.5); top.lineTo(-1.7,.5); top.lineTo(-1.7,-.5);
  const mk=(d,c,y)=>{ const ge=new THREE.ExtrudeGeometry(top,{depth:d,bevelEnabled:false}); ge.rotateX(-Math.PI/2); const m=new THREE.Mesh(ge,new THREE.MeshStandardMaterial({color:c, metalness:.6, roughness:.38})); m.position.y=y; m.castShadow=true; ship.add(m); };
  mk(.36,0x9b2a24,-.3); mk(.55,0x313a46,.06);
  const box=(w,h,d,c,x,y,z,met)=>{ const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d), new THREE.MeshStandardMaterial({color:c, roughness:.5, metalness:met||.2})); m.position.set(x,y,z); m.castShadow=true; ship.add(m); return m; };
  box(.7,.55,.82,0xf2f2ee,-1.25,.88,0); box(.5,.22,.9,0xe6e6e0,-1.25,1.26,0);
  const fun=new THREE.Mesh(new THREE.CylinderGeometry(.11,.13,.5,20), new THREE.MeshStandardMaterial({color:0xd8432f, roughness:.5})); fun.position.set(-1.55,1.4,0); fun.castShadow=true; ship.add(fun);
  const cc=[0x2f6db5,0xd27a2c,0x3b8f5a,0xb8392f,0xe2c04a,0x5a5f6a]; let k=0;
  for(let x=-.65;x<1.05;x+=.42) for(const z of [-.22,.22]) for(let y=0;y<(x>.8?1:2);y++) box(.38,.24,.4,cc[(k++)%6],x,.74+y*.25,z,.35);
  const q=label('?','#ffe066',220); q.scale.set(2.4,.45,1); scene.add(q);
  const tS=tag(CFG.tag||'강철 배','#ffffff',1.6);
  if (CFG.label) hudLabel(CFG.label,'#ffe066',.33);
  draw=t=>{ const s=t*SEC;
    for(let i=0;i<pos.count;i++){ const x=pos.getX(i), z=pos.getZ(i); pos.setY(i,.05*Math.sin(x*.9+s*1.6)+.035*Math.sin(z*1.3-s*1.2)); } pos.needsUpdate=true; sg.computeVertexNormals();
    ship.position.y=.035*Math.sin(s*1.6); ship.rotation.z=.02*Math.sin(s*1.3); ship.rotation.x=.015*Math.sin(s*1.1);
    q.position.set(.35,1.75+.06*Math.sin(s*4),0); q.material.opacity=Math.min(1,Math.max(0,(t-.3)*4));
    tS.position.set(1.2,1.3,.3); tS.material.opacity=Math.min(1,Math.max(0,(t-.15)*4));
    const a=.55-.25*t; camera.position.set(Math.sin(a)*6.4, 2.0, Math.cos(a)*6.4); camera.lookAt(0,.75,0);
    gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='nail_sink') {
  scene.background=grad('#183247','#04080d'); const key=keyLight(2,6,5,3.0); key.target.position.set(0,1,0); scene.add(new THREE.AmbientLight(0x6a7f9a,.6));
  const rim=new THREE.DirectionalLight(0x9fd8ff,1.0); rim.position.set(-3,4,-4); scene.add(rim); stage(0x18222e);
  const T=tank(2.2,2.0,1.2); scene.add(T.g); const L=1.6; T.set(L);
  const nail=new THREE.Group(), sm=steelMat(); const sh=new THREE.Mesh(new THREE.CylinderGeometry(.04,.04,.8,16), sm); sh.castShadow=true; nail.add(sh);
  const hd=new THREE.Mesh(new THREE.CylinderGeometry(.11,.11,.035,24), sm); hd.position.y=.41; nail.add(hd); const tp=new THREE.Mesh(new THREE.ConeGeometry(.04,.14,16), sm); tp.rotation.x=Math.PI; tp.position.y=-.47; nail.add(tp); scene.add(nail);
  const sp=splash(16), bb=bubbles(12); const tN=tag('쇠못','#ffffff',1.8);
  if (CFG.label) hudLabel(CFG.label,'#ffe066',.33);
  const T0=.7, g=9.8*.35; const y0=2.9, tHit=T0+Math.sqrt(2*(y0-.55-L)/g), vS=1.1, bot=.62;
  draw=t=>{ const s=t*SEC; let y, rz=.25;
    if (s<T0) y=y0; else if (s<tHit){ const u=s-T0; y=y0-.5*g*u*u; } else { y=Math.max(bot, y0-.5*g*(tHit-T0)**2-vS*(s-tHit)); }
    if (y<=bot+.001){ const u=s-(tHit+(y0-.5*g*(tHit-T0)**2-bot)/vS); rz=.25+Math.min(1.32,u*3); y=bot-Math.min(.48,u*1.1)*Math.sin(Math.min(1.32,u*3))*.9; }
    nail.position.set(0,y,0); nail.rotation.z=rz;
    sp(0,L,0,s-tHit); bb(0,y,L,s>tHit&&s<tHit+2.2,s);
    tN.position.set(.75,Math.min(y,1.9)+.25,.3);
    camera.position.set(.6+.3*t, 2.1, 6.2-.4*t); camera.lookAt(0,.75,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='bath') {
  scene.background=grad('#35506a','#0a0f16'); const key=keyLight(1.5,6,4.5,3.2); key.target.position.set(0,.8,0); scene.add(new THREE.AmbientLight(0x8fa3bd,.6));
  const rim=new THREE.DirectionalLight(0xffd8a0,.9); rim.position.set(-3,4,-4); scene.add(rim);
  const fl=new THREE.Mesh(new THREE.PlaneGeometry(14,14), new THREE.MeshStandardMaterial({color:0xcfc6b4, roughness:.35})); fl.rotation.x=-Math.PI/2; fl.receiveShadow=true; scene.add(fl);
  const tm=new THREE.MeshStandardMaterial({color:0xf6f3ee, roughness:.25}); const W=2.6,D=1.3,Hh=1.0;
  const wall=(w,h,d,x,y,z)=>{ const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),tm); m.position.set(x,y,z); m.castShadow=m.receiveShadow=true; scene.add(m); };
  wall(W,Hh,.1,0,Hh/2,D/2-.05); wall(W,Hh,.1,0,Hh/2,-D/2+.05); wall(.1,Hh,D,W/2-.05,Hh/2,0); wall(.1,Hh,D,-W/2+.05,Hh/2,0); wall(W,.1,D,0,.05,0);
  const wg=new THREE.BoxGeometry(W-.2,1,D-.2); wg.translate(0,.5,0); const water=new THREE.Mesh(wg,waterMat()); water.position.y=.1; water.renderOrder=2; scene.add(water);
  const G=galileo(ARCH); G.g.scale.setScalar(.8); scene.add(G.g);
  const drops=[]; for(let i=0;i<40;i++){ const d=sph(.025+rnd()*.02,new THREE.MeshStandardMaterial({color:0x8fd0ff, transparent:true, opacity:.8, roughness:.05}),[0,0,0],null,8); d.castShadow=false; d.visible=false; scene.add(d); drops.push([d,(rnd()-.5)*2.2,rnd()]); }
  const pud=new THREE.Mesh(new THREE.CircleGeometry(1,48), new THREE.MeshPhysicalMaterial({color:0x6fb8ee, transparent:true, opacity:.45, roughness:.02, clearcoat:1})); pud.rotation.x=-Math.PI/2; pud.position.set(0,.004,D/2+.3); pud.scale.set(.001,.001,1); scene.add(pud);
  const eu=tag(CFG.tag||'유레카!','#ffe066',2.0); eu.visible=false;
  if (CFG.label) hudLabel(CFG.label,'#7dfcff',.33);
  draw=t=>{ const s=t*SEC; const k=ease(Math.min(1,Math.max(0,(s-.4)/(SEC*.45))));
    G.g.position.set(0,.1-.45*k,-.1); const lv=.5+.48*k; water.scale.y=Math.min(.9,lv-.1)+.0001;
    const over=Math.max(0,s-.4-SEC*.32); drops.forEach(([d,x,o])=>{ const u=(over*1.4+o)%1; d.visible=over>0; if(!d.visible) return; d.position.set(x, .99-1.0*u*u, D/2+.02+.25*u); });
    const pk=Math.min(1,over*.6); pud.scale.set(1.3*pk+.001,.45*pk+.001,1);
    const sur=k>.85; G.face(sur?.95:.2, sur?0:.25, sur?1:.3); if(sur){ G.arms[0].rotation.z=-2.4; G.arms[1].rotation.z=2.4; } else { G.arms[0].rotation.z=-.22; G.arms[1].rotation.z=.22; }
    eu.visible=sur; eu.position.set(1.25,1.55+.05*Math.sin(s*6),0);
    camera.position.set(1.1-.3*t, 2.6, 6.0-.5*t); camera.lookAt(0,.75,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='buoy') {
  scene.background=grad('#16384f','#03080d'); const key=keyLight(2,6,5,3.0); key.target.position.set(0,1,0); scene.add(new THREE.AmbientLight(0x6a7f9a,.6));
  const rim=new THREE.DirectionalLight(0x9fd8ff,1.0); rim.position.set(-3,4,-4); scene.add(rim); stage(0x18222e);
  const T=tank(1.6,1.7,1.0); T.g.position.x=-.7; scene.add(T.g); const L=1.55; T.set(L);
  const spout=new THREE.Mesh(new THREE.BoxGeometry(.4,.04,.22), glassMat()); spout.position.set(.25,L-.02,0); spout.rotation.z=-.25; scene.add(spout);
  const bk=new THREE.Mesh(new THREE.CylinderGeometry(.34,.3,.95,40,1,true), glassMat()); bk.position.set(.95,.475,0); scene.add(bk);
  const bw=new THREE.Mesh((()=>{const gg=new THREE.CylinderGeometry(.32,.3,1,40); gg.translate(0,.5,0); return gg;})(), waterMat()); bw.position.set(.95,.02,0); bw.renderOrder=2; scene.add(bw);
  const rock=new THREE.Mesh(new THREE.DodecahedronGeometry(.36,1), new THREE.MeshStandardMaterial({color:0x7d7468, roughness:.85, flatShading:true})); rock.scale.set(1.15,.9,1); rock.castShadow=true; scene.add(rock);
  const str=new THREE.Mesh(new THREE.CylinderGeometry(.008,.008,1,6), new THREE.MeshStandardMaterial({color:0xdddddd})); scene.add(str);
  const ar=upArrow(); scene.add(ar); const tB=tag('부력','#ff6b6b',1.9), tW=tag('밀어낸 물','#7dfcff',1.9);
  const drops=[]; for(let i=0;i<18;i++){ const d=sph(.025,new THREE.MeshStandardMaterial({color:0x8fd0ff, transparent:true, opacity:.85}),[0,0,0],null,8); d.castShadow=false; scene.add(d); drops.push([d,i/18]); }
  if (CFG.label) hudLabel(CFG.label,'#7dfcff',.33);
  draw=t=>{ const s=t*SEC; const k=ease(Math.min(1,Math.max(0,(s-.3)/(SEC*.6)))); const cy=2.05-1.25*k; rock.position.set(-.7,cy,0); rock.rotation.y=s*.3;
    str.scale.y=4.6-cy; str.position.set(-.7,(4.6+cy)/2,0);
    const f=Math.min(1,Math.max(0,(L-(cy-.33))/.66)); bw.scale.y=.02+.5*f;
    const flowing=k>0&&k<1&&f>0; drops.forEach(([d,o])=>{ const u=(s*1.6+o)%1; d.visible=flowing; d.position.set(.45+.25*u,L-.1-(L-.1-(.05+.5*f))*u*u,0); });
    ar.setLen(.55*f); ar.position.set(-.7,cy-.42-.55*f,.62); tB.position.set(-.05,cy-.25,.62); tB.material.opacity=f>.15?1:0;
    tW.position.set(.95,1.25,.3); tW.material.opacity=f>.15?1:0;
    camera.position.set(.2+.2*t, 2.0, 6.0-.4*t); camera.lookAt(.05,.85,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='float_proof') {
  scene.background=grad('#1f3550','#04070c'); const key=keyLight(1.5,7,5,3.2); key.target.position.set(0,1,0); scene.add(new THREE.AmbientLight(0x6a7f9a,.62));
  const rim=new THREE.DirectionalLight(0xffd8a0,1.0); rim.position.set(-3,4,-4); scene.add(rim); stage(0x18222e);
  const L0=.95, A=new THREE.Group(); const TL=tank(1.6,1.6,1.0), TR=tank(1.6,1.6,1.0); TL.g.position.x=-1.0; TR.g.position.x=1.0; scene.add(TL.g); scene.add(TR.g);
  const lump=new THREE.Mesh(new THREE.BoxGeometry(.3,.3,.3), steelMat()); lump.castShadow=true; scene.add(lump);
  const bowl=new THREE.Group(); const bm=steelMat(); bm.side=THREE.DoubleSide; const hs=new THREE.Mesh(new THREE.SphereGeometry(.5,48,24,0,Math.PI*2,Math.PI/2,Math.PI/2), bm); hs.scale.y=.6; hs.castShadow=true; bowl.add(hs);
  const rr=new THREE.Mesh(new THREE.TorusGeometry(.5,.02,10,64), bm); rr.rotation.x=Math.PI/2; bowl.add(rr); scene.add(bowl);
  const tL=tag('쇳덩이','#ffffff',2.0), tR=tag('그릇 모양','#ffffff',2.3), tS=tag('같은 쇠','#ffe066',1.8);
  const sL=splash(14), sR=splash(18), bbL=bubbles(10); const ars=[-.25,0,.25].map(x=>{ const a=upArrow(); a.scale.setScalar(.7); scene.add(a); return [a,x]; });
  const hudA=hudLabel(CFG.label||'물 1L ≈ 1kg 떠받침','#7dfcff',.33), hudB=hudLabel(CFG.label2||'그릇 모양이면 둥둥!','#ffe066',.33); hudB.visible=false;
  const T0=CFG.drop||3.0, g=9.8*.35, Y0=1.95; const hitL=T0+Math.sqrt(2*(Y0-.15-L0)/g), hitR=T0+Math.sqrt(2*(Y0-.3-L0)/g);
  draw=t=>{ const s=t*SEC; const u=Math.max(0,s-T0);
    let ly = s<hitL ? Y0-.5*g*u*u : Math.max(.17, L0+.15-1.0*(s-hitL)); lump.position.set(-1.0,ly,0); lump.rotation.y=s<T0?s*.4:T0*.4;
    const lvL=L0+(ly<L0+.15?.02*Math.min(1,(L0+.15-ly)/.3):0); TL.set(lvL);
    let by; const rise=s>hitR?.09*Math.min(1,(s-hitR)*1.5):0; const lvR=L0+rise; TR.set(lvR);
    if (s<hitR) by=Y0-.5*g*u*u; else { const v=s-hitR; by=lvR+.12+.18*Math.exp(-2.0*v)*Math.cos(5.5*v); }
    bowl.position.set(1.0,by,0); bowl.rotation.z = s>hitR ? .06*Math.exp(-1.2*(s-hitR))*Math.sin(4*(s-hitR)) : 0;
    sL(-1.0,L0,0,s-hitL); sR(1.0,L0,0,s-hitR); bbL(-1.0,ly,lvL,s>hitL&&s<hitL+2.5,s);
    const fl=s>hitR+1.0; ars.forEach(([a,x])=>{ a.visible=fl; a.position.set(1.0+x,.25,.55); a.setLen(fl?.45+.08*Math.sin(s*4+x*9):0); });
    tL.position.set(-1.0,.5,.55); tR.position.set(1.0,.5,.55); tS.position.set(0,1.95,0); tS.visible=s<T0+.4;
    hudA.visible=s<hitR+1.4; hudB.visible=s>=hitR+1.4;
    const c=ease(Math.min(1,s/SEC*2.2)), o=s*.02; camera.position.set(Math.sin(o)*1.2, 2.3-.2*c, 7.4-1.0*c); camera.lookAt(0,.85,0);
    gradePass.uniforms.uT.value=s; composer.render(); };
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

// ── 에라토스테네스 편: 지구본·우물·막대 그림자·단면 각도 ──
function earthTex(){ const c=document.createElement('canvas'); c.width=1024; c.height=512; const g=c.getContext('2d');
  const gr=g.createLinearGradient(0,0,0,512); gr.addColorStop(0,'#1d4f86'); gr.addColorStop(.5,'#1f6fb0'); gr.addColorStop(1,'#1d4f86'); g.fillStyle=gr; g.fillRect(0,0,1024,512);
  const blob=(x,y,r,col)=>{ g.fillStyle=col; for(let i=0;i<26;i++){ g.beginPath(); g.arc(x+(rnd()-.5)*r*1.6,y+(rnd()-.5)*r,r*(.35+rnd()*.45),0,7); g.fill(); } };
  [[180,170,70],[260,330,55],[520,150,60],[560,300,70],[760,170,95],[860,340,45],[300,90,40]].forEach(([x,y,r])=>blob(x,y,r,rnd()>.4?'#4f8a3a':'#9c8a55'));
  g.fillStyle='rgba(255,255,255,.92)'; g.fillRect(0,0,1024,26); g.fillRect(0,488,1024,24);
  const t=new THREE.CanvasTexture(c); t.encoding=THREE.sRGBEncoding; return t; }
function globe(r){ const m=new THREE.Mesh(new THREE.SphereGeometry(r,96,64), new THREE.MeshStandardMaterial({map:earthTex(), roughness:.62, metalness:.05})); m.castShadow=true;
  const atm=new THREE.Mesh(new THREE.SphereGeometry(r*1.04,64,48), new THREE.MeshBasicMaterial({color:0x6fb6ff, transparent:true, opacity:.13, side:THREE.BackSide})); m.add(atm); return m; }
function stars(n,R){ const v=[]; for(let i=0;i<n;i++){ const a=rnd()*Math.PI*2, b=(rnd()-.5)*Math.PI; v.push(Math.cos(a)*Math.cos(b)*R, Math.sin(b)*R, Math.sin(a)*Math.cos(b)*R); }
  const g=new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(v,3)); scene.add(new THREE.Points(g, new THREE.PointsMaterial({color:0xffffff, size:.12}))); }
function glowLine(pts,color,w){ return new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),Math.max(2,pts.length*8),w||.02,8,false), new THREE.MeshBasicMaterial({color:new THREE.Color(color).multiplyScalar(1.3), toneMapped:false})); }
function sunRay(x0,y0,z0,x1,y1,z1,color){ const m=glowLine([new THREE.Vector3(x0,y0,z0),new THREE.Vector3(x1,y1,z1)],color||'#ffd86b',.025); scene.add(m); return m; }
function arcTube(R,a0,a1,color,w){ const pts=[]; for(let i=0;i<=24;i++){ const a=a0+(a1-a0)*i/24; pts.push(new THREE.Vector3(Math.cos(a)*R,Math.sin(a)*R,0)); } return glowLine(pts,color,w); }
const ERA={hair:0x4a3526, robe:0x2f5a96, top:true, beard:[1.05,1.15,.84], sash:true};

if (CFG.type==='earth_tape') {
  scene.background=new THREE.Color(0x02040a); stars(1400,60); const sun=sunLight(-6,3,6,2.8,4); scene.add(new THREE.AmbientLight(0x30406a,.55));
  const E=globe(1.5); E.rotation.z=.41; scene.add(E);
  const tape=new THREE.Mesh(new THREE.TorusGeometry(1.56,.035,12,160,0.001), new THREE.MeshStandardMaterial({color:0xffd23f, emissive:0xb07a10, emissiveIntensity:.8, metalness:.3, roughness:.4})); scene.add(tape);
  const q=label('?','#ffe066',220); q.scale.set(2.6,.48,1); scene.add(q);
  if (CFG.label) hudLabel(CFG.label,'#ffe066',.33);
  draw=t=>{ const s=t*SEC; E.rotation.y=s*.35; const k=ease(Math.min(1,Math.max(0,(t-.1)/.6)));
    tape.geometry.dispose(); tape.geometry=new THREE.TorusGeometry(1.56,.035,12,160,Math.max(.001,k*Math.PI*2)); tape.rotation.set(Math.PI/2-.25,0,0);
    q.position.set(1.55,1.55+.06*Math.sin(s*4),0); q.material.opacity=Math.min(1,Math.max(0,(t-.35)*4));
    camera.position.set(.4,1.0,6.6-.7*t); camera.lookAt(0,.15,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='syene_well') {
  scene.background=grad('#d9843f','#2f4f86'); scene.add(new THREE.HemisphereLight(0xffe6c0,0x7a5a3a,.35));
  const sun=sunLight(0,10,.0001,1.5,5); sun.target.position.set(0,0,0);
  const sand=new THREE.Mesh(new THREE.CircleGeometry(16,64), new THREE.MeshStandardMaterial({color:0xd9b77a, roughness:.95})); sand.rotation.x=-Math.PI/2; sand.receiveShadow=true; scene.add(sand);
  const stone=new THREE.MeshStandardMaterial({color:0xb79a6e, roughness:.85, side:THREE.DoubleSide});
  const wall=new THREE.Mesh(new THREE.CylinderGeometry(.85,.9,.75,48,1,true), stone); wall.position.y=.375; wall.castShadow=wall.receiveShadow=true; scene.add(wall);
  const lip=new THREE.Mesh(new THREE.TorusGeometry(.87,.08,12,48), stone); lip.rotation.x=Math.PI/2; lip.position.y=.75; lip.castShadow=true; scene.add(lip);
  const shaft=new THREE.Mesh(new THREE.CylinderGeometry(.8,.8,2.4,48,1,true), new THREE.MeshStandardMaterial({color:0x6b5640, roughness:.9, side:THREE.BackSide})); shaft.position.y=-1.2+.02; scene.add(shaft);
  const hole=new THREE.Mesh(new THREE.CircleGeometry(.8,48), new THREE.MeshBasicMaterial({color:0x000000})); hole.rotation.x=-Math.PI/2; hole.position.y=.01; scene.add(hole);
  const wt=new THREE.Mesh(new THREE.CircleGeometry(.79,48), new THREE.MeshBasicMaterial({color:new THREE.Color(0xfff2b0), toneMapped:false, transparent:true, opacity:0})); wt.rotation.x=-Math.PI/2; wt.position.y=.03; scene.add(wt);
  const sunB=glowBall(.55,'#fff1a8',2.4); scene.add(sunB);
  const beams=[]; for(let i=0;i<9;i++){ const x=(i%3-1)*.4, z=(Math.floor(i/3)-1)*.4; const b=sunRay(x,6,z,x,.05,z,'#ffe27a'); b.material.transparent=true; beams.push(b); }
  const stick=new THREE.Mesh(new THREE.CylinderGeometry(.04,.04,1.2,12), new THREE.MeshStandardMaterial({color:0x7a5230, roughness:.7})); stick.position.set(1.8,.6,.3); stick.castShadow=true; scene.add(stick);
  const tg=tag(CFG.tag||'그림자 없음','#ffffff',2.4);
  if (CFG.label) hudLabel(CFG.label,'#ffe066',.33);
  draw=t=>{ const s=t*SEC; const k=ease(Math.min(1,t*1.4)); sunB.position.set(0,6.2,-1.2+1.2*k);
    beams.forEach((b,i)=>{ b.material.opacity=Math.min(.75,Math.max(0,(t-.25)*3)); }); wt.material.opacity=Math.min(1,Math.max(0,(t-.3)*3));
    tg.position.set(1.25,1.6,.3); tg.material.opacity=Math.min(1,Math.max(0,(t-.5)*4));
    camera.position.set(2.6-.8*t, 3.4+.6*t, 5.2-.8*t); camera.lookAt(.4,.3,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='eratos') {
  scene.background = grad(CFG.mode==='flip'?'#4a2f1e':'#1d4a66', '#05070f'); stage(0x1c2135);
  const key=keyLight(2.5,6,4,2.8); key.target.position.set(0,1.3,0); scene.add(new THREE.AmbientLight(0x6070a0,.42));
  const rim=new THREE.DirectionalLight(0xffc98a,1.0); rim.position.set(-3,3,-4); scene.add(rim);
  const G=galileo(ERA); scene.add(G.g);
  const sc=new THREE.Mesh(new THREE.CylinderGeometry(.07,.07,.7,20), new THREE.MeshStandardMaterial({color:0xe8dcc0, roughness:.8})); sc.rotation.z=Math.PI/2; sc.position.set(0,-.86,.05); G.arms[0].add(sc);  // 두루마리
  const qs=[]; if (CFG.mode==='think'){ for(let i=0;i<5;i++){ const q=label('?','#ffd23f',220); q.scale.set(1.5,.28,1); scene.add(q); qs.push([q,i/5*Math.PI*2]); } }
  const mini=CFG.mode==='think'?globe(.32):null; if(mini) scene.add(mini);
  if (CFG.label) hudLabel(CFG.label,'#ffd23f',.33);
  draw=t=>{ const s=t*SEC;
    if (CFG.mode==='flip'){ const ph=(s*.42)%1; const up=ph<.75?Math.sin(Math.PI*ph/.75):0; G.g.position.y=up*1.7; G.g.rotation.x = ph<.75 ? -2*Math.PI*ease(ph/.75) : 0;
      G.arms[0].rotation.z=-.22-1.9*up; G.arms[1].rotation.z=.22+1.9*up; G.face(.9,0,1); camera.position.set(1.5,2.6,7.6); camera.lookAt(0,1.9,0); }
    else { const blink=(s%2.3)<.12?1:0; G.face(.15, blink?1:.25, .6+.4*Math.sin(s*3)); G.H.rotation.z=.18*Math.sin(s*1.4); G.H.rotation.x=-.06;
      G.arms[1].rotation.set(-2.15,0,-.62); G.arms[0].rotation.z=-.25;
      mini.position.set(-1.1,2.3+.08*Math.sin(s*2),.2); mini.rotation.y=s*.8;
      qs.forEach(([q,a],i)=>{ const b=a+s*1.2; q.position.set(Math.cos(b)*1.3, 2.5+.25*Math.sin(s*2.5+i), Math.sin(b)*.7); q.material.opacity=.6+.4*Math.sin(s*3+i); });
      camera.position.set(.3,2.0,5.4-.5*t); camera.lookAt(0,1.8,0); }
    gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='shadow_stick') {
  scene.background=grad('#e99a55','#4f6fa8'); scene.add(new THREE.HemisphereLight(0xffe6c0,0x7a5a3a,.55));
  const ang=7.2*Math.PI/180; const sun=sunLight(-Math.sin(ang)*10,Math.cos(ang)*10,0,2.6,4); sun.target.position.set(0,0,0);
  const sand=new THREE.Mesh(new THREE.CircleGeometry(16,64), new THREE.MeshStandardMaterial({color:0xd9b77a, roughness:.95})); sand.rotation.x=-Math.PI/2; sand.receiveShadow=true; scene.add(sand);
  const Hs=2.4; const stick=new THREE.Mesh(new THREE.BoxGeometry(.14,Hs,.14), new THREE.MeshStandardMaterial({color:0xe9dcc4, roughness:.55})); stick.position.y=Hs/2; stick.castShadow=true; scene.add(stick);
  const tip=new THREE.Mesh(new THREE.ConeGeometry(.12,.22,4), new THREE.MeshStandardMaterial({color:0xd9b24a, metalness:.7, roughness:.3})); tip.position.y=Hs+.11; tip.castShadow=true; scene.add(tip);
  const L=Hs*Math.tan(ang); const ray=sunRay(-L*1.4, Hs*2.4, .3, 0, Hs, .3); ray.material.transparent=true;
  const R2=sunRay(0,Hs,.3,L,0,.3,'#ffe066'); R2.material.transparent=true;
  const arc=arcTube(1.2, -Math.PI/2, -Math.PI/2+ang, '#ff6b6b', .02); arc.position.set(0,Hs,.3); scene.add(arc);
  const vert=glowLine([new THREE.Vector3(0,Hs,.3),new THREE.Vector3(0,Hs-1.2,.3)],'#ffffff',.012); scene.add(vert);
  const tg=tag(CFG.tag||'7.2°','#ff6b6b',1.8);
  const sh=tag('그림자','#3a2a1a',1.6);
  if (CFG.label) hudLabel(CFG.label,'#ffe066',.33);
  draw=t=>{ const s=t*SEC; const k=Math.min(1,Math.max(0,(t-.35)*3)); [R2,arc,vert].forEach(o=>o.visible=k>0); R2.material.opacity=k; ray.material.opacity=Math.min(1,t*3);
    tg.position.set(.55,Hs-.95,.3); tg.material.opacity=k; sh.position.set(L+.2,.3,.9); sh.material.opacity=Math.min(1,Math.max(0,(t-.15)*4));
    camera.position.set(1.4-.6*t, 1.7, 5.4-.6*t); camera.lookAt(0,1.2,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='earth_angle') {
  scene.background=grad('#0c1a33','#020409'); stars(900,50); scene.add(new THREE.AmbientLight(0x8090b0,.55)); const key=keyLight(4,5,6,2.6); key.target.position.set(0,0,0);
  const R=1.6; const disc=new THREE.Mesh(new THREE.CircleGeometry(R,96), new THREE.MeshStandardMaterial({color:0x1f6fb0, roughness:.6})); scene.add(disc);
  const crust=new THREE.Mesh(new THREE.RingGeometry(R-.12,R,96), new THREE.MeshStandardMaterial({color:0x5f8a3a, roughness:.8})); crust.position.z=.002; scene.add(crust);
  const core=new THREE.Mesh(new THREE.CircleGeometry(.22,64), new THREE.MeshBasicMaterial({color:new THREE.Color(0xff8a3a), toneMapped:false})); core.position.z=.003; scene.add(core);
  const D=12*Math.PI/180;  // 보기 좋게 과장한 각도(화면 표시는 7.2°)
  const aS=Math.PI/2, aA=Math.PI/2+D;
  const stickAt=(a,c)=>{ const m=new THREE.Mesh(new THREE.BoxGeometry(.05,.34,.05), new THREE.MeshStandardMaterial({color:c})); m.position.set(Math.cos(a)*(R+.17),Math.sin(a)*(R+.17),.05); m.rotation.z=a-Math.PI/2; scene.add(m); return m; };
  stickAt(aS,0xffffff); stickAt(aA,0xffffff);
  const rays=[]; for(const x of [-1.1,Math.cos(aA)*R, 0, 1.1]){ const r=sunRay(x,4.2,.06,x,Math.sqrt(Math.max(0,R*R-x*x))+.34,.06); r.material.transparent=true; rays.push(r); }
  const lS=glowLine([new THREE.Vector3(0,0,.07),new THREE.Vector3(Math.cos(aS)*R,Math.sin(aS)*R,.07)],'#7dfcff',.018), lA=glowLine([new THREE.Vector3(0,0,.07),new THREE.Vector3(Math.cos(aA)*R,Math.sin(aA)*R,.07)],'#7dfcff',.018); scene.add(lS); scene.add(lA);
  const arcC=arcTube(.6,aS,aA,'#ff6b6b',.022); arcC.position.z=.08; scene.add(arcC);
  const arcE=arcTube(R+.02,aS,aA,'#ffe066',.04); arcE.position.z=.08; scene.add(arcE);
  const tA=tag('7.2°','#ff6b6b',1.4), tF=tag('= 원의 1/50','#ffe066',2.4), tS=tag('시에네','#ffffff',1.3), tAl=tag('알렉산드리아','#ffffff',1.9);
  if (CFG.label) hudLabel(CFG.label,'#7dfcff',.33);
  draw=t=>{ const s=t*SEC; const k1=Math.min(1,t*3), k2=Math.min(1,Math.max(0,(t-.3)*3)), k3=Math.min(1,Math.max(0,(t-.55)*3));
    rays.forEach(r=>r.material.opacity=k1); [lS,lA,arcC].forEach(o=>o.visible=k2>0); arcE.visible=k3>0;
    tA.position.set(-.35,.95,.1); tA.material.opacity=k2; tF.visible=false;
    tS.position.set(.55,R+.35,.1); tAl.position.set(-1.25,R+.15,.1);
    camera.position.set(.15, .9, 7.6-.5*t); camera.lookAt(0,.9,0); gradePass.uniforms.uT.value=s; composer.render(); };
}

if (CFG.type==='earth_proof') {
  scene.background=new THREE.Color(0x02040a); stars(1600,60); const sun=sunLight(-6,4,6,2.6,4); scene.add(new THREE.AmbientLight(0x30406a,.6));
  const R=1.6; const E=globe(R); scene.add(E);
  const segN=50, segs=[]; for(let i=0;i<segN;i++){ const a0=Math.PI/2+i*2*Math.PI/segN; const m=arcTube(R+.06,a0,a0+2*Math.PI/segN*.88,i===0?'#ff6b6b':'#ffd23f',.035); m.visible=false; scene.add(m); segs.push(m); }
  const cnt=tag('×1','#ffffff',3.2);
  const sat=new THREE.Group(); const body=new THREE.Mesh(new THREE.BoxGeometry(.16,.16,.22), new THREE.MeshStandardMaterial({color:0xd8a93a, metalness:.9, roughness:.35})); sat.add(body);
  for(const x of [-1,1]){ const p=new THREE.Mesh(new THREE.BoxGeometry(.4,.01,.14), new THREE.MeshStandardMaterial({color:0x1b3a7a, metalness:.6, roughness:.3, emissive:0x0a1a40})); p.position.x=x*.3; sat.add(p); }
  sat.visible=false; scene.add(sat);
  const hudA=hudLabel(CFG.label||'거리 × 50','#ffe066',.33), hudB=hudLabel(CFG.label2||'약 4만 km','#7dfcff',.33); hudB.visible=false;
  const T0=CFG.drop||2.2, T1=T0+5.0;
  draw=t=>{ const s=t*SEC; E.rotation.y=.4+s*.05;
    const n = s<T0 ? (s>.5?1:0) : Math.min(segN, 1+Math.floor((segN-1)*ease(Math.min(1,(s-T0)/(T1-T0-.5)))));
    segs.forEach((m,i)=>m.visible=i<n); cnt.position.set(0,.2,R+.4); cnt.visible=n>0 && s<T1+.3;
    if(cnt.visible && cnt._n!==n){ cnt.material.map.dispose(); const L2=label('×'+n,'#ffffff',110); cnt.material.map=L2.material.map; cnt._n=n; }
    sat.visible=s>T1; if(sat.visible){ const a=(s-T1)*.9; sat.position.set(Math.cos(a)*(R+.55), Math.sin(a)*.4*(R+.55), Math.sin(a)*(R+.55)); sat.lookAt(0,0,0); }
    hudA.visible=s<T1; hudB.visible=s>=T1;
    const c=ease(Math.min(1,s/SEC*1.5)); camera.position.set(.2, .3, 7.4-1.0*c); camera.lookAt(0,.1,0); gradePass.uniforms.uT.value=s; composer.render(); };
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
