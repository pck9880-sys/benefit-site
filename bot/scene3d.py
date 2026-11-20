"""정보형 숏츠용 3D 장면 엔진 — three.js(WebGL) 장면을 Playwright 로 한 프레임씩 찍어 mp4 로.

Blender 는 이 iMac(2013 i5, 화면 없는 실행)에서 Eevee 가 충돌하고 Cycles 는 프레임당 7초라 실사용이 어려워
(2026-11-20 시험) 같은 3D 를 브라우저 엔진으로 렌더한다. 결과는 1080x1080 30fps mp4 → plan media {"video": "clipN.mp4"}.

사용:
  python -m bot.scene3d <장면.json> <출력.mp4>
장면 JSON:
  {"type": "globe_route", "from": [37.46, 126.44, "인천"], "to": [40.64, -73.78, "뉴욕"], "seconds": 4}
  {"type": "map_compare", "from": [...], "to": [...], "seconds": 5,
   "labels": {"straight": "항정선 약 13,800km", "curve": "대권항로 약 11,090km"}}
  {"type": "orbit_plane", "seconds": 4}
  {"type": "moon_lock", "locked": true, "seconds": 8, "label": "늘 같은 면이 지구를 봄"}   (locked false = 자전 안 할 때 비교)
  {"type": "moon_face", "seconds": 5, "label": "달의 앞면"}
텍스처·라이브러리: assets/3d (NASA 퍼블릭 도메인 지구, three.js MIT) — 출처 assets/3d/credits.json
"""
import asyncio
import base64
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config

A3 = config.ROOT / "assets" / "3d"
FPS = 30
S = 1080


def _xyz(lat, lon):
    p, l = math.radians(lat), math.radians(lon)
    return (math.cos(p) * math.cos(l), math.cos(p) * math.sin(l), math.sin(p))


def great_circle(a, b, n=180):
    """(lat, lon) 점 목록 — 지구 위 최단 경로."""
    x1, x2 = _xyz(*a), _xyz(*b)
    d = math.acos(max(-1, min(1, sum(i * j for i, j in zip(x1, x2)))))
    pts = []
    for k in range(n + 1):
        f = k / n
        A, B = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
        x, y, z = (A * x1[i] + B * x2[i] for i in range(3))
        pts.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return pts


def rhumb(a, b, n=180):
    """(lat, lon) 점 목록 — 같은 방위로 쭉 가는 길(메르카토르 지도의 직선)."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = (b[1] - a[1] + 540) % 360 - 180
    m1 = math.log(math.tan(math.pi / 4 + p1 / 2))
    m2 = math.log(math.tan(math.pi / 4 + p2 / 2))
    pts = []
    for k in range(n + 1):
        f = k / n
        m = m1 + (m2 - m1) * f
        pts.append((math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2), a[1] + dl * f))
    return pts


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000;overflow:hidden}</style>
<script>__THREE__</script></head><body><script>
const CFG = __CFG__;
const W = __S__, H = __S__;
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setSize(W, H); renderer.setPixelRatio(1); document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 100);
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 0.9); sun.position.set(3, 4, 5); scene.add(sun);
const loader = new THREE.TextureLoader();
const earthTex = loader.load(CFG.earth);
const moonTex = CFG.moon ? loader.load(CFG.moon) : null;
function label(text, color, size){
  const c = document.createElement('canvas'); c.width = 1024; c.height = 256; const g = c.getContext('2d');
  g.font = `800 ${size||96}px "Apple SD Gothic Neo","Noto Sans KR",sans-serif`; g.textAlign='center'; g.textBaseline='middle';
  g.lineWidth = 18; g.strokeStyle = 'rgba(0,0,0,.85)'; g.strokeText(text, 512, 128); g.fillStyle = color||'#fff'; g.fillText(text, 512, 128);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c), transparent:true, depthTest:false}));
  s.scale.set(1.0, 0.25, 1); s.renderOrder = 10; return s;
}
function airplane(scale){
  const g = new THREE.Group(); const m = new THREE.MeshStandardMaterial({color:0xf4f6fb, metalness:.2, roughness:.45});
  const accent = new THREE.MeshStandardMaterial({color:0x2f6fe4, metalness:.2, roughness:.5});
  const body = new THREE.Mesh(new THREE.CylinderGeometry(.09,.09,1,24), m); body.rotation.x = Math.PI/2; g.add(body);
  const nose = new THREE.Mesh(new THREE.SphereGeometry(.09,24,16), m); nose.position.z = .5; nose.scale.z = 1.8; g.add(nose);
  const tailc = new THREE.Mesh(new THREE.ConeGeometry(.09,.25,24), m); tailc.rotation.x = -Math.PI/2; tailc.position.z = -.62; g.add(tailc);
  const wing = new THREE.Mesh(new THREE.BoxGeometry(1.15,.025,.24), m); wing.position.z = .05; g.add(wing);
  const stab = new THREE.Mesh(new THREE.BoxGeometry(.42,.02,.12), m); stab.position.z = -.58; g.add(stab);
  const fin = new THREE.Mesh(new THREE.BoxGeometry(.02,.22,.16), accent); fin.position.set(0,.13,-.6); g.add(fin);
  const stripe = new THREE.Mesh(new THREE.CylinderGeometry(.092,.092,.7,24,1,true), accent); stripe.rotation.x = Math.PI/2; stripe.scale.set(1,1,.08); g.add(stripe);
  for (const x of [-.32,.32]) { const e = new THREE.Mesh(new THREE.CylinderGeometry(.04,.04,.18,16), accent); e.rotation.x = Math.PI/2; e.position.set(x,-.06,.12); g.add(e); }
  g.scale.setScalar(scale||1); return g;
}
function v3(lat, lon, r){ const phi=(90-lat)*Math.PI/180, th=(lon+180)*Math.PI/180;
  return new THREE.Vector3(-r*Math.sin(phi)*Math.cos(th), r*Math.cos(phi), r*Math.sin(phi)*Math.sin(th)); }
const ease = x => x<.5 ? 2*x*x : 1-Math.pow(-2*x+2,2)/2;
let draw = ()=>{};

if (CFG.type === 'globe_route') {
  scene.background = new THREE.Color(0x05070f);
  const stars = new THREE.BufferGeometry(); const sp=[]; for(let i=0;i<1500;i++){const v=new THREE.Vector3(Math.random()*2-1,Math.random()*2-1,Math.random()*2-1).normalize().multiplyScalar(30+Math.random()*10); sp.push(v.x,v.y,v.z);}
  stars.setAttribute('position', new THREE.Float32BufferAttribute(sp,3)); scene.add(new THREE.Points(stars,new THREE.PointsMaterial({color:0xffffff,size:.06})));
  const earth = new THREE.Mesh(new THREE.SphereGeometry(1,96,64), new THREE.MeshStandardMaterial({map:earthTex, roughness:1})); scene.add(earth);
  const atm = new THREE.Mesh(new THREE.SphereGeometry(1.03,64,48), new THREE.MeshBasicMaterial({color:0x5aa8ff, transparent:true, opacity:.12, side:THREE.BackSide})); scene.add(atm);
  const P = CFG.path.map(([la,lo],i,a)=>{ const f=i/(a.length-1); return v3(la,lo,1.012+0.07*Math.sin(Math.PI*f)); });
  const dots = P.filter((_,i)=>i%3===0).map(p=>{ const d=new THREE.Mesh(new THREE.SphereGeometry(.0085,8,6), new THREE.MeshBasicMaterial({color:0xffd23f})); d.position.copy(p); scene.add(d); return d; });
  for (const [la,lo,name] of [CFG.from, CFG.to]) { const d=new THREE.Mesh(new THREE.SphereGeometry(.022,16,12), new THREE.MeshBasicMaterial({color:0xff3b30})); d.position.copy(v3(la,lo,1.005)); scene.add(d);
    const L=label(name,'#ffffff',110); L.position.copy(v3(la,lo,1.16)); scene.add(L); }
  const plane = airplane(.07); scene.add(plane);
  const mid = P[Math.floor(P.length/2)].clone().normalize();
  draw = t => {
    const k = Math.min(P.length-2, Math.floor(ease(Math.min(1,t/0.92))*(P.length-1)));
    dots.forEach((d,i)=> d.visible = i*3 <= k);
    plane.position.copy(P[k]); plane.up.copy(P[k].clone().normalize()); plane.lookAt(P[k+1]);
    const cam = mid.clone().multiplyScalar(3.7).applyAxisAngle(new THREE.Vector3(0,1,0), -0.35 + 0.25*t);
    camera.position.copy(cam); camera.up.set(0,1,0); camera.lookAt(mid.clone().multiplyScalar(0.35));
    renderer.render(scene, camera);
  };
}

if (CFG.type === 'map_compare') {
  scene.background = new THREE.Color(0x0b1220);
  earthTex.wrapS = THREE.RepeatWrapping; earthTex.offset.x = 0.5;  // 태평양이 가운데
  const map = new THREE.Mesh(new THREE.PlaneGeometry(4,2), new THREE.MeshBasicMaterial({map:earthTex})); scene.add(map);
  const xy = ([la,lo]) => { let x=((lo-180+540)%360)-180; return new THREE.Vector3(x/180*2, la/90, 0.01); };
  function line(pts, color, dashed){ const g=new THREE.BufferGeometry().setFromPoints(pts.map(xy));
    const m = dashed ? new THREE.LineDashedMaterial({color, dashSize:.05, gapSize:.035, linewidth:2}) : new THREE.LineBasicMaterial({color, linewidth:2});
    const l = new THREE.Line(g,m); if (dashed) l.computeLineDistances(); scene.add(l); return l; }
  // 굵은 선: 작은 구 이어 붙이기
  function thick(pts, color){ return pts.filter((_,i)=>i%2===0).map(p=>{ const d=new THREE.Mesh(new THREE.CircleGeometry(.018,12), new THREE.MeshBasicMaterial({color})); d.position.copy(xy(p)); scene.add(d); return d; }); }
  const st = thick(CFG.straight, 0xff4d4d), cv = thick(CFG.path, 0xffd23f);
  for (const [la,lo,name] of [CFG.from, CFG.to]) { const d=new THREE.Mesh(new THREE.CircleGeometry(.04,20), new THREE.MeshBasicMaterial({color:0xffffff})); d.position.copy(xy([la,lo])); d.position.z=.02; scene.add(d);
    const L=label(name,'#ffffff',100); L.position.copy(xy([la-8,lo])); L.position.z=.05; L.scale.set(.8,.2,1); scene.add(L); }
  const L1 = label(CFG.labels.straight, '#ff6b6b', 84), L2 = label(CFG.labels.curve, '#ffd23f', 84);
  const cx = (xy(CFG.from).x + xy(CFG.to).x)/2;
  L1.position.set(cx, 0.18, .05); L2.position.set(cx, 1.02, .05); [L1,L2].forEach(l=>{l.scale.set(1.25,.31,1); scene.add(l);});
  const plane = airplane(.08); scene.add(plane);
  draw = t => {
    const a = Math.min(1, t/0.42), b = Math.max(0, Math.min(1, (t-0.45)/0.42));
    st.forEach((d,i)=> d.visible = i/(st.length-1) <= a); cv.forEach((d,i)=> d.visible = i/(cv.length-1) <= b);
    L1.material.opacity = Math.min(1, Math.max(0,(t-0.3)*5)); L2.material.opacity = Math.min(1, Math.max(0,(t-0.8)*5));
    const src = b>0 ? CFG.path : CFG.straight, f = b>0 ? b : a, k = Math.min(src.length-2, Math.floor(f*(src.length-1)));
    const p = xy(src[k]), q = xy(src[k+1]); plane.position.set(p.x, p.y, .12); plane.up.set(0,0,1); plane.lookAt(q.x, q.y, .12);
    camera.position.set(cx, 0.5, 3.0 - 0.12*t); camera.lookAt(cx, 0.5, 0); renderer.render(scene, camera);
  };
}

if (CFG.type === 'orbit_plane') {
  const c = document.createElement('canvas'); c.width = 4; c.height = 256; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0,0,0,256); gr.addColorStop(0,'#1e5bd8'); gr.addColorStop(.6,'#7fb5ff'); gr.addColorStop(1,'#e8f2ff'); g.fillStyle=gr; g.fillRect(0,0,4,256);
  scene.background = new THREE.CanvasTexture(c);
  const plane = airplane(1); scene.add(plane);
  const clouds = []; for (let i=0;i<14;i++){ const cl=new THREE.Mesh(new THREE.SphereGeometry(.35+Math.random()*.3,16,12), new THREE.MeshStandardMaterial({color:0xffffff, transparent:true, opacity:.85}));
    cl.position.set((Math.random()-.5)*8, -1.2-Math.random()*.6, (Math.random()-.5)*8); cl.scale.y=.45; scene.add(cl); clouds.push(cl); }
  draw = t => { const ang = -0.6 + 2.0*t; camera.position.set(Math.sin(ang)*2.4, 0.55, Math.cos(ang)*2.4); camera.lookAt(0,0,0);
    plane.rotation.z = 0.12*Math.sin(t*Math.PI*2); clouds.forEach((cl,i)=> cl.position.z += 0.0); renderer.render(scene, camera); };
}

if (CFG.type === 'moon_lock' || CFG.type === 'moon_face') {
  scene.background = new THREE.Color(0x03040a);
  const stars = new THREE.BufferGeometry(); const sp=[]; for(let i=0;i<2000;i++){const v=new THREE.Vector3(Math.random()*2-1,Math.random()*2-1,Math.random()*2-1).normalize().multiplyScalar(40+Math.random()*10); sp.push(v.x,v.y,v.z);}
  stars.setAttribute('position', new THREE.Float32BufferAttribute(sp,3)); scene.add(new THREE.Points(stars,new THREE.PointsMaterial({color:0xffffff,size:.08})));
  sun.position.set(8, 3, 6); sun.intensity = 1.1;
  const moonG = new THREE.Group(); scene.add(moonG);
  const R0 = CFG.type==='moon_face' ? 1 : .36;
  const moon = new THREE.Group(); moonG.add(moon);  // +z = 달의 앞면(지구 쪽)
  const ball = new THREE.Mesh(new THREE.SphereGeometry(R0,64,48), new THREE.MeshStandardMaterial({map:moonTex, roughness:1}));
  ball.rotation.y = -Math.PI/2; moon.add(ball);  // 텍스처 경도 0(앞면 중심)을 +z 로
  const mark = new THREE.Mesh(new THREE.SphereGeometry(CFG.type==='moon_face'?.05:.055,16,12), new THREE.MeshBasicMaterial({color:0xff3b30}));
  mark.position.set(0,0,R0*1.01); moon.add(mark);
  if (CFG.type !== 'moon_face') {  // 앞면 방향을 보여주는 빨간 막대
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(.018,.018,.42,12), new THREE.MeshBasicMaterial({color:0xff3b30}));
    rod.rotation.x = Math.PI/2; rod.position.set(0,0,R0+.21); moon.add(rod);
  }
  if (CFG.type === 'moon_face') {
    const L = label(CFG.label||'달의 앞면', '#ffffff', 100); L.position.set(0,1.35,0); L.scale.set(1.4,.35,1); scene.add(L);
    draw = t => { moon.rotation.y = -0.25 + 0.35*t; camera.position.set(0, .15, 3.4 - .3*t); camera.lookAt(0,0,0); renderer.render(scene,camera); };
  } else {
    const earth = new THREE.Mesh(new THREE.SphereGeometry(.55,64,48), new THREE.MeshStandardMaterial({map:earthTex, roughness:1})); scene.add(earth);
    const orbitR = 2.1, ring=[]; for(let i=0;i<=128;i++){const a=i/128*Math.PI*2; ring.push(new THREE.Vector3(Math.cos(a)*orbitR,0,Math.sin(a)*orbitR));}
    const ringL = new THREE.Line(new THREE.BufferGeometry().setFromPoints(ring), new THREE.LineDashedMaterial({color:0x6f8fff, dashSize:.08, gapSize:.06})); ringL.computeLineDistances(); scene.add(ringL);
    const arrow = new THREE.ArrowHelper(new THREE.Vector3(1,0,0), new THREE.Vector3(), .5, 0xffd23f, .14, .09); scene.add(arrow);
    const L = label(CFG.label || (CFG.locked ? '늘 같은 면이 지구를 봄' : '자전 안 하면 면이 바뀜'), CFG.locked ? '#ffd23f' : '#ff6b6b', 86);
    L.position.set(0, 0.3, -3.0); L.scale.set(4.2,1.05,1); scene.add(L);
    const turns = CFG.turns || 1;
    draw = t => { const a = Math.PI/2 + t*Math.PI*2*turns;
      moonG.position.set(Math.cos(a)*orbitR, 0, Math.sin(a)*orbitR);
      // locked: 빨간 점(+z)이 늘 지구(원점)를 향하게 / 아니면 처음 방향 그대로
      if (CFG.locked) { moon.lookAt(0,0,0); } else { moon.rotation.set(0, Math.PI, 0); }  // 처음엔 지구 쪽(-z)을 봄
      const tang = new THREE.Vector3(-Math.sin(a),0,Math.cos(a)); arrow.position.copy(moonG.position).add(new THREE.Vector3(0,.42,0)); arrow.setDirection(tang);
      earth.rotation.y = t*Math.PI*2*turns*3;
      camera.position.set(0, 6.2, 4.6); camera.lookAt(0,-.3,-.3); renderer.render(scene,camera); };
  }
}

function starsBg(n){ const g=new THREE.BufferGeometry(); const sp=[]; for(let i=0;i<(n||2200);i++){const v=new THREE.Vector3(Math.random()*2-1,Math.random()*2-1,Math.random()*2-1).normalize().multiplyScalar(40+Math.random()*10); sp.push(v.x,v.y,v.z);}
  g.setAttribute('position', new THREE.Float32BufferAttribute(sp,3)); scene.add(new THREE.Points(g,new THREE.PointsMaterial({color:0xffffff,size:.09}))); }
function bigLabel(text,color,y){ const L=label(text,color,92); L.scale.set(2.8,.7,1); L.position.set(0,y,0); return L; }

if (CFG.type === 'analogy') {  // 비유: 가운데를 보며 도는 사람 → 한 바퀴 돌면 몸도 한 바퀴
  scene.background = new THREE.Color(0x0d1222);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(3.2,64), new THREE.MeshStandardMaterial({color:0x1b2440, roughness:1})); floor.rotation.x=-Math.PI/2; scene.add(floor);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(.32,32,24), new THREE.MeshStandardMaterial({color:0xffd23f, emissive:0xffb000, emissiveIntensity:.8})); lamp.position.y=.5; scene.add(lamp);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(.05,.05,.5,12), new THREE.MeshStandardMaterial({color:0x8892b0})); pole.position.y=.25; scene.add(pole);
  const R=2.0, ring=[]; for(let i=0;i<=128;i++){const a=i/128*Math.PI*2; ring.push(new THREE.Vector3(Math.cos(a)*R,.02,Math.sin(a)*R));}
  const rl=new THREE.Line(new THREE.BufferGeometry().setFromPoints(ring), new THREE.LineDashedMaterial({color:0x7f9cff,dashSize:.1,gapSize:.07})); rl.computeLineDistances(); scene.add(rl);
  const man = new THREE.Group(); scene.add(man);
  const skin = new THREE.MeshStandardMaterial({color:0xf2c9a0, roughness:.8}), suit = new THREE.MeshStandardMaterial({color:0x4f7cff, roughness:.6});
  const body = new THREE.Mesh(new THREE.CylinderGeometry(.18,.2,.6,20), suit); body.position.y=.45; man.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.17,24,18), skin); head.position.y=.92; man.add(head);
  const nose = new THREE.Mesh(new THREE.ConeGeometry(.07,.22,16), new THREE.MeshBasicMaterial({color:0xff3b30})); nose.rotation.x=Math.PI/2; nose.position.set(0,.92,.22); man.add(nose);
  for (const x of [-.09,.09]) { const leg=new THREE.Mesh(new THREE.CylinderGeometry(.06,.06,.3,10), suit); leg.position.set(x,.13,0); man.add(leg); }
  const L = bigLabel(CFG.label||'', CFG.locked?'#ffd23f':'#ff6b6b', 2.6); scene.add(L);
  draw = t => { const a = Math.PI/2 + t*Math.PI*2*(CFG.turns||1);
    man.position.set(Math.cos(a)*R, 0, Math.sin(a)*R);
    if (CFG.locked) man.lookAt(0,0,0); else man.rotation.set(0,Math.PI,0);
    man.children.forEach(c=>{}); const bob=Math.abs(Math.sin(t*Math.PI*14))*.05; man.position.y=bob;
    camera.position.set(0, 5.4, 5.6); camera.lookAt(0,.2,0); renderer.render(scene,camera); };
}

if (CFG.type === 'moon_far') {  // 달이 돌아서 뒷면이 보임 (지구에선 못 보는 면)
  scene.background = new THREE.Color(0x02030a); starsBg();
  sun.position.set(-6, 2, 6);
  const g = new THREE.Group(); scene.add(g);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(1,64,48), new THREE.MeshStandardMaterial({map:moonTex, roughness:1})); ball.rotation.y=-Math.PI/2; g.add(ball);
  const L = bigLabel(CFG.label||'달의 뒷면', '#ff6b6b', 1.55); scene.add(L);
  draw = t => { const e = ease(Math.min(1,t/0.8)); g.rotation.y = Math.PI*e; L.material.opacity = Math.max(0,(t-0.55)*3);
    camera.position.set(0,.2,3.6); camera.lookAt(0,0,0); renderer.render(scene,camera); };
}

if (CFG.type === 'two_dials') {  // 공전·자전 주기 비교: 두 원판이 같은 속도로 돌고 숫자 카운트
  scene.background = new THREE.Color(0x0b0f1d);
  function dial(x, color, name){ const grp=new THREE.Group(); grp.position.set(x,0,0); scene.add(grp);
    const ring=new THREE.Mesh(new THREE.TorusGeometry(.8,.06,16,96), new THREE.MeshStandardMaterial({color:0x2a3355})); grp.add(ring);
    const arc=new THREE.Mesh(new THREE.TorusGeometry(.8,.07,16,96,0.001), new THREE.MeshBasicMaterial({color})); grp.add(arc);
    const hand=new THREE.Mesh(new THREE.BoxGeometry(.05,.7,.05), new THREE.MeshBasicMaterial({color})); hand.position.y=.35; const piv=new THREE.Group(); piv.add(hand); grp.add(piv);
    const L=label(name, color, 110); L.scale.set(1.8,.45,1); L.position.set(0,1.3,0); grp.add(L);
    const N=label('0일', '#ffffff', 110); N.scale.set(1.2,.3,1); N.position.set(0,-1.2,0); grp.add(N);
    return {grp,arc,piv,N,color}; }
  const A=dial(-1.2,'#7f9cff',CFG.left||'공전'), B=dial(1.2,'#ffd23f',CFG.right||'자전');
  const eq=label('=', '#ffffff', 200); eq.scale.set(1.6,.4,1); eq.position.set(0,0,0); scene.add(eq);
  const days = CFG.days || 27.3; let last=-1;
  draw = t => { const e=ease(Math.min(1,t/0.85));
    for (const d of [A,B]) { d.piv.rotation.z = -e*Math.PI*2; d.grp.remove(d.arc); d.arc = new THREE.Mesh(new THREE.TorusGeometry(.8,.07,16,96,Math.max(0.001,e*Math.PI*2)), new THREE.MeshBasicMaterial({color:d.color, side:THREE.DoubleSide})); d.arc.rotation.z=Math.PI/2; d.arc.scale.x=-1; d.grp.add(d.arc); }
    const v=(days*e).toFixed(1); if (v!==last){ for (const d of [A,B]) { d.grp.remove(d.N); d.N=label(v+'일','#ffffff',130); d.N.scale.set(1.9,.48,1); d.N.position.set(0,-1.2,0); d.grp.add(d.N);} last=v; }
    camera.position.set(0,0,5.6); camera.lookAt(0,0,0); renderer.render(scene,camera); };
}

if (CFG.type === 'starfield') {  // 공중제비 배경용 별밤 (재탕 방지용 새 배경)
  scene.background = new THREE.Color(0x070a1a); starsBg(3500);
  const neb = new THREE.Mesh(new THREE.SphereGeometry(3,32,24), new THREE.MeshBasicMaterial({color:0x3b2a7a, transparent:true, opacity:.25})); neb.position.set(2,-1,-8); scene.add(neb);
  draw = t => { camera.position.set(0,0,0.01); camera.rotation.set(0, t*.2, 0); renderer.render(scene,camera); };
}

if (CFG.type === 'moon_pullback') {  // 달에서 멀어지며 '늘 이 면' 표시
  scene.background = new THREE.Color(0x02030a); starsBg();
  sun.position.set(4, 3, 6);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(1,64,48), new THREE.MeshStandardMaterial({map:moonTex, roughness:1})); ball.rotation.y=-Math.PI/2; scene.add(ball);
  const L = bigLabel(CFG.label||'늘 이 면만 지구 쪽', '#ffd23f', 0.9); scene.add(L);
  draw = t => { camera.position.set(.3*Math.sin(t*2), .1, 2.4 + 2.2*ease(t)); camera.lookAt(0,0,0); renderer.render(scene,camera); };
}
window.draw = draw;
window.ready = new Promise(r => { THREE.DefaultLoadingManager.onLoad = r; setTimeout(r, 4000); });
</script></body></html>"""


async def _render(cfg, out):
    from playwright.async_api import async_playwright
    earth = "data:image/jpeg;base64," + base64.b64encode((A3 / "earth_nasa_land_ocean_ice_2048.jpg").read_bytes()).decode()
    moon = "data:image/jpeg;base64," + base64.b64encode((A3 / "moon_nasa_lroc_1k.jpg").read_bytes()).decode()
    cfg = {**cfg, "earth": earth, "moon": moon}
    if cfg["type"] in ("globe_route", "map_compare"):
        a, b = cfg["from"][:2], cfg["to"][:2]
        cfg["path"] = great_circle(a, b)
        cfg["straight"] = rhumb(a, b)
    html = HTML.replace("__THREE__", (A3 / "three.min.js").read_text()).replace("__CFG__", json.dumps(cfg, ensure_ascii=False)).replace("__S__", str(S))
    tmp = Path(tempfile.mkdtemp(prefix="s3d-"))
    (tmp / "s.html").write_text(html, "utf-8")
    n = int(cfg.get("seconds", 4) * FPS)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": S, "height": S})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto((tmp / "s.html").as_uri())
        if errs:
            raise RuntimeError("3D 페이지 오류: " + " | ".join(errs)[:500])
        await pg.evaluate("window.ready")
        await pg.wait_for_timeout(300)
        for i in range(n):
            await pg.evaluate(f"window.draw({i / max(1, n - 1)})")
            await pg.screenshot(path=str(tmp / f"f{i:04d}.jpg"), type="jpeg", quality=92)
        await b.close()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.jpg"),
                    "-f", "lavfi", "-t", f"{n / FPS:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    print(f"[scene3d] {cfg['type']} {n}프레임 → {out}")
    return Path(out)


def render(cfg, out):
    return asyncio.run(_render(cfg, out))


if __name__ == "__main__":
    render(json.loads(Path(sys.argv[1]).read_text("utf-8")), sys.argv[2])
