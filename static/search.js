(function(){var q=document.getElementById('q'),out=document.getElementById('results'),idx=null;
function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
q.addEventListener('input',function(){var v=q.value.trim();if(!v){out.innerHTML='';return}
var go=function(){var w=v.split(/\s+/),r=idx.filter(function(d){var s=d.t+' '+d.k;return w.every(function(x){return s.indexOf(x)>=0})}).slice(0,10);
out.innerHTML=r.length?r.map(function(d){return '<a href="'+BASE+'/'+d.u+'">'+esc(d.t)+'</a>'}).join(''):'<small>검색 결과가 없습니다</small>'};
if(idx)go();else fetch(BASE+'/search.json').then(function(r){return r.json()}).then(function(j){idx=j;go()})});})();
