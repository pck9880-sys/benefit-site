(function(){
  var data=null,go=document.getElementById('go'),res=document.getElementById('res');
  function esc(s){return String(s||'').replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function run(){
    var age=parseInt(document.getElementById('age').value,10),reg=document.getElementById('reg').value;
    var sel=[].slice.call(document.querySelectorAll('.chip input:checked')).map(function(x){return x.value});
    var names={};[].slice.call(document.querySelectorAll('.chip')).forEach(function(c){names[c.querySelector('input').value]=c.textContent.trim()});
    var out=data.map(function(d){
      if(!isNaN(age)){if(d.amin&&age<d.amin)return null;if(d.amax&&age>d.amax)return null}
      if(reg&&d.r!=='national'&&d.r!==reg)return null;
      var hit=sel.filter(function(s){return d.a.indexOf(s)>=0});
      if(sel.length&&!hit.length&&d.a.length)return null;
      var score=hit.length*3+(d.r===reg?2:0)+((d.amin||d.amax)&&!isNaN(age)?1:0);
      return {d:d,hit:hit,score:score};
    }).filter(Boolean).sort(function(a,b){return b.score-a.score});
    if(!out.length){res.innerHTML='<p class="r-h">조건에 맞는 지원제도를 아직 찾지 못했어요</p><p class="disc">새 지원제도가 매일 추가되니 다음에 다시 확인해 보세요.</p>';return}
    res.innerHTML='<p class="r-h">해당될 수 있는 지원제도 '+out.length+'건</p><ul>'+out.slice(0,30).map(function(o){
      var why=o.hit.map(function(h){return '<span class="why">'+esc(names[h])+'</span>'}).join('');
      if(o.d.r===reg&&reg)why+='<span class="why">'+esc(document.querySelector('#reg option:checked').textContent)+'</span>';
      if((o.d.amin||o.d.amax)&&!isNaN(age))why+='<span class="why">나이 조건 충족</span>';
      return '<li><a href="'+BASE+'/'+o.d.u+'"><strong>'+esc(o.d.t)+'</strong><small>'+esc(o.d.o)+'</small><br>'+why+'</a></li>'}).join('')+'</ul>';
    res.scrollIntoView({behavior:'smooth',block:'start'});
  }
  go.onclick=function(){if(data)run();else fetch(BASE+'/check.json').then(function(r){return r.json()}).then(function(j){data=j;run()})};
})();
