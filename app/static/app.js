const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const state={black:{version:0}};let errorKind='signed_error';let active='black';let zoom=1;
const labels={fd_price:'Finite difference',analytical_price:'Analytical',signed_error:'Signed error',absolute_error:'Absolute error'};
let fittedWidth=0;
function fitImage(){
  const img=$('#viewer-image');
  if(!img.naturalWidth)return;
  const viewport=$('.viewer-scroll');
  fittedWidth=Math.min(img.naturalWidth,viewport.clientWidth-24,(viewport.clientHeight-24)*img.naturalWidth/img.naturalHeight);
  zoom=1;
  img.style.width=Math.max(1,Math.floor(fittedWidth))+'px';
  viewport.scrollTo(0,0);
}
function openImage(src,alt){
  const img=$('#viewer-image');
  img.onload=fitImage;
  img.alt=alt;
  $('#image-download').href=src;
  $('#image-download').download=alt.replace(/[^\w.-]+/g,'-')+'.png';
  img.style.width='';
  img.src=src;
  $('#image-dialog').showModal();
  $('.viewer-scroll').scrollTo(0,0);
  if(img.complete)fitImage();
}
$('#viewer-close').onclick=()=>$('#image-dialog').close();
$('#zoom-in').onclick=()=>{
  zoom=Math.min(zoom+0.5,4);
  $('#viewer-image').style.width=Math.round(fittedWidth*zoom)+'px';
};
$('#zoom-reset').onclick=fitImage;
window.addEventListener('resize',()=>{if($('#image-dialog').open)fitImage();});
$$('[data-image]').forEach(b=>b.onclick=()=>openImage(b.dataset.image,b.querySelector('img').alt));
const methodLabels = {analytical: 'Analytical', implicit: 'Implicit', cn_direct: 'CN Direct', rannacher: 'Rannacher stepping'};
function render() {
  const grid = $('#results-black'), s = state.black;
  grid.replaceChildren();
  if (!s.plots) return;
  for (const p of s.plots) {
    const isError = p.kind?.endsWith('_error');
    if (isError && p.kind !== errorKind) continue;
    if (p.kind === 'analytical_price' && s.method !== 'analytical') continue;
    const card = document.createElement('article');
    card.className = 'result-card';
    const heading = document.createElement('div');
    heading.className = 'result-heading';
    const title = document.createElement('h3');
    const imageLabel = isError ? `${methodLabels[s.method]} — ${labels[p.kind]}` : methodLabels[s.method];
    title.textContent = isError ? 'Error' : imageLabel;
    heading.append(title);
    if (isError) {
      const toggle = document.createElement('div');
      toggle.className = 'error-switch';
      toggle.setAttribute('role', 'group');
      toggle.setAttribute('aria-label', 'Error measure');
      for (const [kind, label] of [['signed_error', 'Signed'], ['absolute_error', 'Absolute']]) {
        const control = document.createElement('button');
        control.type = 'button';
        control.dataset.error = kind;
        control.textContent = label;
        control.classList.toggle('selected', kind === errorKind);
        control.setAttribute('aria-pressed', String(kind === errorKind));
        control.onclick = () => {
          errorKind = kind;
          render();
          $(`[data-error="${kind}"]`).focus();
        };
        toggle.append(control);
      }
      heading.append(toggle);
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'figure-button';
    button.setAttribute('aria-label', 'Enlarge ' + imageLabel);
    const img = new Image();
    img.src = 'data:image/png;base64,' + p.image;
    img.alt = imageLabel;
    button.onclick = () => openImage(img.src, `${imageLabel} ${s.signature}`);
    button.append(img);
    card.append(heading, button);
    grid.append(card);
  }
}
function syncCompare() {
  $('#compare-analytical').disabled = $('#black-method').value === 'analytical';
}
syncCompare();
$('#black-method').addEventListener('change', syncCompare);
async function run() {
  const s = state.black, form = $('#black-form'), status = $('#black-status');
  if (!form.reportValidity()) return;
  s.started = true;
  s.controller?.abort();
  s.controller = new AbortController();
  const version = ++s.version;
  s.plots = null;
  render();
  status.textContent = 'Generating…';
  status.className = 'form-status';
  const payload = Object.fromEntries(new FormData(form));
  for (const k of ['K','T','r','sigma','n','m']) payload[k] = Number(payload[k]);
  payload.compare_analytical = payload.method !== 'analytical' && $('#compare-analytical').checked;
  payload.include_analytical = false;
  payload.error_mode = 'both';
  try {
    const response = await fetch('/api/black-scholes', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload), signal: s.controller.signal
    });
    const data = await response.json();
    if (version !== s.version) return;
    if (!response.ok) throw Error(Array.isArray(data.detail) ? data.detail.map(e => e.loc.slice(1).join('.') + ': ' + e.msg).join('; ') : data.detail || 'Please try again.');
    s.plots = data.plots;
    s.method = payload.method;
    s.signature = Object.entries(payload).filter(([k,v]) => typeof v === 'number' || k === 'method').map(([k,v]) => k + '-' + v).join('_');
    render();
    status.textContent = '';
  } catch (e) {
    if (version !== s.version || e.name === 'AbortError') return;
    status.textContent = e.message;
    status.classList.add('error');
  }
}
$('#black-form').addEventListener('submit', e => { e.preventDefault(); run(); });
$('#black-form').addEventListener('input', () => {
  state.black.version++;
  state.black.controller?.abort();
  state.black.plots = null;
  render();
  $('#black-status').textContent = 'Run to update.';
});
const tabs = $$('.tabs [role=tab]');
function activate(tab) {
  active = tab.dataset.tab;
  tabs.forEach(b => {
    const on = b === tab;
    b.setAttribute('aria-selected', String(on));
    b.tabIndex = on ? 0 : -1;
    $('#panel-' + b.dataset.tab).hidden = !on;
  });
  if (active === 'black' && !state.black.started) run();
}
tabs.forEach((b, i) => {
  b.onclick = () => activate(b);
  b.onkeydown = e => {
    let n;
    if (e.key === 'ArrowRight') n = (i + 1) % tabs.length;
    if (e.key === 'ArrowLeft') n = (i + tabs.length - 1) % tabs.length;
    if (e.key === 'Home') n = 0;
    if (e.key === 'End') n = tabs.length - 1;
    if (n !== undefined) { e.preventDefault(); tabs[n].focus(); activate(tabs[n]); }
  };
});
function hash() {
  const target = document.getElementById(location.hash.slice(1));
  const panel = target?.closest('[role=tabpanel]');
  if (panel) activate(tabs.find(tab => tab.getAttribute('aria-controls') === panel.id));
  const background = target?.closest('.background');
  if (background) background.open = true;
  if (panel) target.scrollIntoView();
}
if (location.pathname === '/background') $('#background').open = true;
window.addEventListener('hashchange', hash);
hash();
new IntersectionObserver((entries, observer) => {
  if (entries.some(e => e.isIntersecting)) {
    if (active === 'black' && !state.black.started) run();
    observer.disconnect();
  }
}, {rootMargin: '100px'}).observe($('#solver'));
