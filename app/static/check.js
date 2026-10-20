const $=s=>document.querySelector(s);
const ctx=()=>document.querySelector('input[name=context]:checked').value;
let samples={};let started=false;
if(window.Motion)Motion.pageIn();
setTimeout(()=>{started=true},50);
function mode(){
  const l=ctx()==='listing';
  $('#m-listing').hidden=!l; $('#m-package').hidden=l;
  if(window.Motion&&started)Motion.swap(l?$('#m-listing'):$('#m-package'));
  const box=$('#sample-btns'); box.textContent='';
  (samples[ctx()]||[]).forEach(s=>{
    const b=document.createElement('button');b.type='button';b.className='ghost';b.textContent=s.title;
    b.onclick=()=>{$('#text').value=s.text;if(s.category)$('#category').value=s.category;if(window.Motion)Motion.flash($('#text'))};
    box.appendChild(b);
  });
}
document.querySelectorAll('input[name=context]').forEach(r=>r.onchange=mode);
fetch('/api/samples').then(r=>r.json()).then(j=>{samples=j;mode()}).catch(mode);
$('#f').onsubmit=async e=>{
  e.preventDefault();
  const err=$('#err'),go=$('#go');err.hidden=true;
  const fd=new FormData();
  fd.set('context',ctx());fd.set('category',$('#category').value);
  const url=$('#url').value.trim(),file=$('#image').files[0],text=$('#text').value;
  let endpoint='/api/check';
  if(ctx()==='listing'&&url&&!text.trim()){endpoint='/api/check-url';fd.set('url',url)}
  else if(ctx()==='package'&&file&&!text.trim()){fd.set('image',file)}
  else if(text.trim()){fd.set('text',text)}
  else{err.textContent=ctx()==='listing'?'Enter a product page URL or paste the listing text.':'Choose a label photo or paste the label text.';err.hidden=false;return}
  const stop=window.Motion?Motion.scan($('#text').closest('.field')):()=>{};
  go.disabled=true;go.textContent=endpoint==='/api/check-url'?'Capturing page...':'Checking...';
  try{
    const r=await fetch(endpoint,{method:'POST',body:fd});
    const j=await r.json().catch(()=>({}));
    if(!r.ok){err.textContent=j.detail||'Something went wrong. Try again.';err.hidden=false;return}
    sessionStorage.setItem('lm_result',JSON.stringify(j));location.href='/results';
  }catch(x){err.textContent='Could not reach the server.';err.hidden=false}
  finally{stop();go.disabled=false;go.textContent='Check'}
};

