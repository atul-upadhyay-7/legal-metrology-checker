const j=JSON.parse(sessionStorage.getItem('lm_result')||'null');
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const TITLE={compliant:'No issue detected in checked rules',non_compliant:'Potential issues found',needs_review:'Needs review'};
const CHIP={pass:'Found',fail:'Potential issue',review:'Needs review',not_applicable:'Not applicable'};
if(j){
  const out=document.getElementById('out');out.textContent='';
  const b=el('section','banner '+j.overall);
  const l=el('div');l.append(el('h2','',TITLE[j.overall]||j.overall),el('p','',j.summary||''));
  const c=el('div','counts');
  [['pass','Found'],['fail','Issues'],['review','Review'],['not_applicable','N/A']].forEach(([k,n])=>{
    const d=el('div');d.append(el('b','',String((j.counts||{})[k]||0)),document.createTextNode(n));c.append(d)});
  b.append(l,c);out.append(b);
  const m=el('p','meta',(j.context==='listing'?'Online listing':'Package label')+' / '+(j.category==='food'?'Food':'General goods'));
  out.append(m);
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
}
