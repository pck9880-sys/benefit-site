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
  // 검색 결과 페이지
  var sq=document.getElementById('sq');
  if(sq){var v=new URLSearchParams(location.search).get('q')||'';sq.value=v;
    if(v)load(function(){var r=find(v);document.getElementById('sn').textContent="'"+v+"' 검색 결과 "+r.length+"건";
      document.getElementById('sr').innerHTML=r.map(function(d){return '<li><a href="'+BASE+'/'+d.u+'"><span class="card-b"><span class="card-tags"><span class="tag">'+esc(d.f)+'</span></span><strong>'+esc(d.t)+'</strong>'+(d.m?'<span class="card-amt">'+esc(d.m)+'</span>':'')+'</span></a></li>'}).join('')||'<li class="empty">검색 결과가 없어요. 다른 단어로 찾아보세요.</li>'})}
})();
