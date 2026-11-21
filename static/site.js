(function(){
  var mb=document.getElementById('menuBtn');if(mb)mb.onclick=function(){document.getElementById('gnb').classList.toggle('open')};
  var cl=document.getElementById('copyLink');if(cl)cl.onclick=function(){navigator.clipboard.writeText(location.href);cl.textContent='복사됨'};
  var idx=null,wait=[];
  function load(cb){if(idx)return cb();wait.push(cb);if(wait.length>1)return;
    fetch(BASE+'/search.json').then(function(r){return r.json()}).then(function(j){idx=j;wait.forEach(function(f){f()});wait=[]})}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function norm(s){return String(s||'').toLowerCase().replace(/\s+/g,'')}
  // 띄어쓰기 무시 · 모든 단어 일치 우선, 없으면 일부 단어 일치 순으로
  function find(v){var w=v.trim().split(/\s+/).map(norm).filter(Boolean);if(!w.length)return[];
    var rs=idx.map(function(d){var title=norm(d.t+d.n),all=norm(d.t+d.n+d.f+d.k),hit=0,th=0;
      w.forEach(function(x){if(all.indexOf(x)>=0)hit++;if(title.indexOf(x)>=0)th++});
      return {d:d,s:(hit==w.length?100:0)+hit*10+th*3}}).filter(function(r){return r.s>0}).sort(function(a,b){return b.s-a.s});
    var full=rs.filter(function(r){return r.s>=100});return (full.length?full:rs).map(function(r){return r.d})}
  function row(d){return '<a href="'+BASE+'/'+d.u+'"><span>'+esc(d.n||d.t)+'</span>'+(d.m?'<b>'+esc(d.m)+'</b>':'')+'</a>'}
  function bind(q,out){if(!q)return;
    function run(){var v=q.value.trim();if(!v){out.innerHTML='';return}
      load(function(){var r=find(v).slice(0,6);out.innerHTML=r.length?r.map(row).join(''):'<a class="none">검색 결과가 없어요</a>'})}
    q.addEventListener('input',run);document.addEventListener('click',function(e){if(!q.form.contains(e.target))out.innerHTML=''});return run}
  bind(document.getElementById('q'),document.getElementById('results'));
  var q2=document.getElementById('q2'),run2=bind(q2,document.getElementById('results2'));
  document.querySelectorAll('.qk').forEach(function(b){b.onclick=function(){q2.value=b.textContent;run2();q2.focus()}});
  // 검색 결과 페이지: 검색어 + 조건(지역·나이·분야·대상)
  var sq=document.getElementById('sq');
  if(sq){var P=new URLSearchParams(location.search),$=function(i){return document.getElementById(i)};
    var F={q:sq,r:$('fr'),age:$('fa'),f:$('ff'),a:$('ft')};
    Object.keys(F).forEach(function(k){if(P.get(k))F[k].value=P.get(k)});
    function go(){load(function(){var v=sq.value.trim(),r=v?find(v):idx.slice(),reg=F.r.value,age=parseInt(F.age.value,10),fld=F.f.value,aud=F.a.value,open=$('fo').checked;
      r=r.filter(function(d){
        if(reg&&d.r!=='national'&&d.r!==reg)return false;
        if(!isNaN(age)&&((d.amin&&age<d.amin)||(d.amax&&age>d.amax)))return false;
        if(fld&&d.f!==fld)return false;
        if(aud&&(d.a||[]).indexOf(aud)<0)return false;
        if(open&&d.x==='closed')return false;return true});
      if(!isNaN(age)||reg)r.sort(function(x,y){function sc(d){var s=0;  // 내 조건에 딱 맞는 제도를 위로
          if(!isNaN(age)&&(d.amin||d.amax))s+=3;
          if(!isNaN(age)&&age>=19&&age<=39&&(d.a||[]).indexOf('youth')>=0)s+=3;
          if(!isNaN(age)&&age>=65&&(d.a||[]).indexOf('senior')>=0)s+=3;
          if(reg&&d.r===reg)s+=4;if(d.m)s+=1;return s}
        return sc(y)-sc(x)});
      var q=new URLSearchParams();Object.keys(F).forEach(function(k){if(F[k].value)q.set(k,F[k].value)});history.replaceState(null,'','?'+q);
      $('sn').textContent=(v?"'"+v+"' ":"")+'조건에 맞는 지원제도 '+r.length+'건';
      $('sr').innerHTML=r.map(function(d){return '<li><a href="'+BASE+'/'+d.u+'"><span class="card-b"><span class="card-tags"><span class="tag">'+esc(d.f)+'</span>'+(d.x==='always'?'<span class="st always">상시 신청</span>':'')+'</span><strong>'+esc(d.n||d.t)+'</strong>'+(d.m?'<span class="card-amt">'+esc(d.m)+'</span>':'')+'</span></a></li>'}).join('')||'<li class="empty">조건에 맞는 지원제도가 없어요. 조건을 줄여보세요.</li>'})}
    ['input','change'].forEach(function(ev){document.querySelector('.flt').addEventListener(ev,go)});sq.addEventListener('input',go);$('sf').onsubmit=function(){go();sq.blur();return false};go()}
})();
