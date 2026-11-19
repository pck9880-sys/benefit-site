(function(){
  // 배너 슬라이드
  var hero=document.getElementById('hero');
  if(hero){var s=hero.querySelectorAll('.slide'),d=hero.querySelectorAll('.dots button'),i=0;
    function go(n){s[i].classList.remove('on');d[i].classList.remove('on');i=(n+s.length)%s.length;s[i].classList.add('on');d[i].classList.add('on')}
    d.forEach(function(b,k){b.onclick=function(){go(k)}});setInterval(function(){go(i+1)},5000)}
  // 모바일 메뉴
  var mb=document.getElementById('menuBtn');if(mb)mb.onclick=function(){document.getElementById('gnb').classList.toggle('open')};
  // 링크 복사
  var cl=document.getElementById('copyLink');if(cl)cl.onclick=function(){navigator.clipboard.writeText(location.href);cl.textContent='복사됨'};
  // 검색
  var q=document.getElementById('q'),out=document.getElementById('results'),idx=null;
  function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  if(q)q.addEventListener('input',function(){var v=q.value.trim();if(!v){out.innerHTML='';return}
    var go=function(){var w=v.split(/\s+/),r=idx.filter(function(d){var s=d.t+' '+d.k;return w.every(function(x){return s.indexOf(x)>=0})}).slice(0,8);
      out.innerHTML=r.length?r.map(function(d){return '<a href="'+BASE+'/'+d.u+'">'+esc(d.t)+'</a>'}).join(''):'<a>검색 결과가 없습니다</a>'};
    if(idx)go();else fetch(BASE+'/search.json').then(function(r){return r.json()}).then(function(j){idx=j;go()})});
})();
