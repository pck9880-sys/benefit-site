(function(){
  var mb=document.getElementById('menuBtn');if(mb)mb.onclick=function(){document.getElementById('gnb').classList.toggle('open')};
  var cl=document.getElementById('copyLink');if(cl)cl.onclick=function(){navigator.clipboard.writeText(location.href);cl.textContent='복사됨'};
  var idx=null;
  function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function bind(q,out){if(!q)return;
    function run(){var v=q.value.trim();if(!v){out.innerHTML='';return}
      var go=function(){var w=v.split(/\s+/),r=idx.filter(function(d){var s=d.t+' '+d.k;return w.every(function(x){return s.indexOf(x)>=0})}).slice(0,8);
        out.innerHTML=r.length?r.map(function(d){return '<a href="'+BASE+'/'+d.u+'">'+esc(d.t)+'</a>'}).join(''):'<a>검색 결과가 없습니다</a>'};
      if(idx)go();else fetch(BASE+'/search.json').then(function(r){return r.json()}).then(function(j){idx=j;go()})}
    q.addEventListener('input',run);return run}
  bind(document.getElementById('q'),document.getElementById('results'));
  var q2=document.getElementById('q2'),run2=bind(q2,document.getElementById('results2'));
  document.querySelectorAll('.qk').forEach(function(b){b.onclick=function(){q2.value=b.textContent;run2();q2.focus()}});
})();
