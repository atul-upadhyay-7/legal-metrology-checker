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
    render(j);
  }catch(x){err.textContent='Could not reach the server.';err.hidden=false}
  finally{stop();go.disabled=false;go.textContent='Check'}
};

const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const TITLE={compliant:'No issue detected in checked rules',non_compliant:'Potential issues found',needs_review:'Needs review'};
const CHIP={pass:'Found',fail:'Potential issue',review:'Needs review',not_applicable:'Not applicable'};
function render(j){
  const out=$('#result');out.textContent='';out.hidden=false;
  const b=el('section','banner '+j.overall);
  const l=el('div');l.append(el('h2','',TITLE[j.overall]||j.overall),el('p','',j.summary||''));
  const c=el('div','counts');
  [['pass','Found'],['fail','Issues'],['review','Review'],['not_applicable','N/A']].forEach(([k,n])=>{
    const d=el('div');d.append(el('b','',String((j.counts||{})[k]||0)),document.createTextNode(n));c.append(d)});
  b.append(l,c);out.append(b);
  out.append(el('p','meta',(j.context==='listing'?'Online listing':'Package label')+' / '+(j.category==='food'?'Food':'General goods')));
  if(j.capture){const p=el('p','meta');p.append('Captured live by TinyFish: ');
    const a=el('a','',j.capture.final_url);a.href=j.capture.final_url;a.rel='noopener noreferrer';a.target='_blank';p.append(a,' at '+j.capture.captured_at);out.append(p)}
  const items=el('div','items');
  j.results.forEach(r=>{
    const row=el('div','item');row.append(el('span','chip '+r.status,CHIP[r.status]||r.status));
    const body=el('div');body.append(el('h3','',r.label));
    if(r.ref)body.append(el('span','ref',r.ref));
    body.append(el('p','',r.detail));
    if(r.evidence)body.append(el('div','found',r.evidence));
    row.append(body);items.append(row)});
  out.append(items);
  const d=el('details');d.append(el('summary','','Text that was checked'),el('pre','',j.extracted_text||''));out.append(d);
  out.append(el('p','disc','First-pass aid, not legal advice. "No issue" means no issue in the checked rules. Findings are potential issues until a person confirms them.'));
  out.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
  if(window.Motion)Motion.resultsIn();
}
