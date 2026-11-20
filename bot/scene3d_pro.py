"""고품질 3D 장면 (과학 숏츠) — three.js + 빛 번짐(UnrealBloom)·그림자·금속 질감·ACES 톤, Playwright 로 프레임 녹화.

  python -m bot.scene3d_pro <장면.json> <출력.mp4>
type:
  medal        회전하는 금메달 + 반짝임 (label, year)
  photo        금속판에 빛 알갱이가 쏟아짐 (color: "blue" 면 전자가 튀어나옴 / "red" 면 안 나옴, label)
  scientist    아인슈타인풍 3D 과학자 캐릭터 (mode: "flip" 공중제비 / "think" 빛 알갱이가 주위를 돔 / "medal" 메달 들고 축하)
  photon_hit   느린 화면: 빛 알갱이 하나가 원자에 부딪혀 전자 하나가 튕겨 나감
  solar        태양전지판에 빛이 쏟아지고 전구가 켜짐
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


def render(cfg, out):
    return asyncio.run(_render(cfg, out))


if __name__ == "__main__":
    render(json.loads(Path(sys.argv[1]).read_text("utf-8")), sys.argv[2])
