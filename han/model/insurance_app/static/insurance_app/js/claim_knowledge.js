const DATA_URL = "/static/json/merged_cases.jsonl";

const ckmModal = document.getElementById('claim-knowledge-modal');
const fabCKM   = document.getElementById('claim-knowledge-fab');
const backdrop = ckmModal?.querySelector('.ckm-backdrop');
const closeBtn = ckmModal?.querySelector('.ckm-close');
const tabs     = ckmModal?.querySelectorAll('.ckm-tab');
const listEl   = document.getElementById('ckm-list');
const detailEl = document.getElementById('ckm-detail');

let byCat = {};

// claim_knowledge.js
function openCKM(){
  ckmModal.removeAttribute('hidden');          // 먼저 표시
  requestAnimationFrame(() => {
    ckmModal.classList.add('show');            // 다음 프레임에 애니메이션 시작
  });
}
function closeCKM(){
  ckmModal.classList.remove('show');           // 애니메이션 종료
  const dlg = ckmModal.querySelector('.ckm-dialog');
  const onEnd = (e) => {
    if (e.target !== dlg) return;
    ckmModal.setAttribute('hidden', '');       // 완전히 숨김
    dlg.removeEventListener('transitionend', onEnd);
  };
  dlg.addEventListener('transitionend', onEnd);
}


function parseJSONL(text){
  return text.split('\n').map(s=>s.trim()).filter(Boolean).map(line=>{
    try { return JSON.parse(line); } catch(e){ return null; }
  }).filter(Boolean);
}
function normalizeCategory(raw){
  if(!raw) return '';
  const s = String(raw).trim();
  if(s.includes('차 vs. 차')) return '차 vs. 차';
  if(s.includes('차 vs. 사람') || s.includes('차 vs. 보행자')) return '차 vs. 사람';
  if(s.includes('차 vs. 기타') || s.includes('차 vs. 자전거') || s.includes('차 vs. 이륜')) return '차 vs. 기타';
  return s;
}
function groupByCategory(data){
  const m = {'차 vs. 차':[], '차 vs. 사람':[], '차 vs. 기타':[]};
  data.forEach(it=>{
    const cat = normalizeCategory(it.category);
    const row = { category: cat||'', num:(it.num||'').trim(), title:(it.title||'').trim(), body:(it.body||'').trim() };
    if(!m[cat]) m[cat] = [];
    m[cat].push(row);
  });
  for(const k in m){
    m[k].sort((a,b)=>{
      const na = parseInt((a.num||'').replace(/\D/g,'')) || 9999;
      const nb = parseInt((b.num||'').replace(/\D/g,'')) || 9999;
      if(na !== nb) return na - nb;
      return (a.title||'').localeCompare(b.title||'', 'ko');
    });
  }
  return m;
}
function renderList(category){
  listEl.innerHTML = '';
  const arr = byCat[category] || [];
  if(arr.length === 0){
    listEl.innerHTML = '<div class="ckm-empty">해당 분류의 사례가 없습니다.</div>';
    detailEl.innerHTML = '<div class="ckm-empty">좌측에서 사례를 선택하세요.</div>';
    return;
  }
  arr.forEach((item, idx)=>{
    const el = document.createElement('div');
    el.className = 'ckm-item';
    el.setAttribute('role','option');
    el.setAttribute('tabindex','0');
    el.dataset.index = idx;
    let displayNum;
    if(item.num && item.num.trim()){ displayNum = item.num.trim(); }
    else { displayNum = String(idx+1).padStart(2,'0') + '.'; }
    el.innerHTML = '<span class="num">' + displayNum + '</span>' +
                   '<span class="title">' + (item.title || '(제목 없음)') + '</span>';
    el.addEventListener('click', ()=> renderDetail(category, idx));
    el.addEventListener('keydown', (e)=>{ if(e.key==='Enter') renderDetail(category, idx); });
    listEl.appendChild(el);
  });
  renderDetail(category, 0);
}
function renderDetail(category, index){
  const arr = byCat[category] || [];
  const item = arr[index];
  if(!item){
    detailEl.innerHTML = '<div class="ckm-empty">좌측에서 사례를 선택하세요.</div>'; return;
  }
  const body = (item.body || '').replace(/\n{3,}/g, '\n\n');
  detailEl.innerHTML = '<div class="d-title">'+(item.title || '(제목 없음)')+'</div>'+
                       '<div class="d-body">'+body+'</div>';
}
function selectTab(btn){
  tabs.forEach(t => t.setAttribute('aria-selected', t===btn ? 'true' : 'false'));
  const cat = btn.dataset.cat; renderList(cat);
}
fabCKM?.addEventListener('click', openCKM);
closeBtn?.addEventListener('click', closeCKM);
backdrop?.addEventListener('click', closeCKM);
tabs?.forEach(t => t.addEventListener('click', ()=> selectTab(t)));

fetch(DATA_URL, {cache:'no-store'})
  .then(res => { if(!res.ok) throw new Error('데이터 로드 실패'); return res.text(); })
  .then(text => {
    const all = parseJSONL(text);
    byCat = groupByCategory(all);
    const first = Array.from(tabs).find(b => b.getAttribute('aria-selected') === 'true') || tabs[0];
    if(first) selectTab(first);
  })
  .catch(err => {
    console.error(err);
    listEl.innerHTML = '<div class="ckm-empty">데이터를 불러오지 못했습니다.</div>';
  });
