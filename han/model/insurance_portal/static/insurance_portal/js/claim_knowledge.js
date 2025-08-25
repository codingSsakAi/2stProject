// static/insurance_portal/js/claim_knowledge.js
// [보상 상식] 기능 전용 스크립트 (JSON Array 전용, 안정화 버전)

const DATA_URL = window.CLAIM_KNOWLEDGE_URL || '/static/insurance_portal/json/accident_data_complete.json';

const ckmModal = document.getElementById('claim-knowledge-modal');
const fabCKM   = document.getElementById('claim-knowledge-fab');
const backdrop = ckmModal?.querySelector('.ckm-backdrop');
const closeBtn = ckmModal?.querySelector('.ckm-close');
const tabs     = ckmModal?.querySelectorAll('.ckm-tab');
const listEl   = document.getElementById('ckm-list');
const detailEl = document.getElementById('ckm-detail');

let byCat = { '차 vs. 차': [], '차 vs. 사람': [], '차 vs. 기타': [] };
let dataLoading = false;

function safeParseJSONArray(text) {
  if (!text) return [];
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  const s = text.indexOf('[');
  const e = text.lastIndexOf(']');
  if (s === -1 || e === -1 || e < s) throw new Error('JSON 배열 구간을 찾지 못함');
  const slice = text.slice(s, e + 1).trim();
  const arr = JSON.parse(slice);
  return Array.isArray(arr) ? arr : [arr];
}

function escapeHTML(str){
  return (str ?? '').toString().replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

function showLoading(){
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="ckm-empty"><div class="empty-icon">⏳</div><h3>불러오는 중...</h3></div>';
}
function showError(err){
  if (!detailEl) return;
  detailEl.innerHTML = `<div class="ckm-empty"><div class="empty-icon">⚠️</div><h3>오류가 발생했습니다</h3><p>${escapeHTML(err.message||String(err))}</p></div>`;
}

async function loadData() {
  if (dataLoading) return;
  dataLoading = true;

  try {
    showLoading();
    const res = await fetch(DATA_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

    const txt = await res.text();
    const data = safeParseJSONArray(txt);

    byCat = { '차 vs. 차': [], '차 vs. 사람': [], '차 vs. 기타': [] };
    data.forEach(item => {
      const cat = item?.category || '차 vs. 차';
      (byCat[cat] ||= []).push(item);
    });

    if (tabs && tabs.length) {
      const selected = Array.from(tabs).find(t => t.getAttribute('aria-selected') === 'true') || tabs[0];
      tabs.forEach(t => t.setAttribute('aria-selected', String(t === selected)));
    }

    renderListForActiveTab();
    if (detailEl) {
      detailEl.innerHTML = '<div class="ckm-empty"><div class="empty-icon">📋</div><h3>사례를 선택해주세요</h3></div>';
    }
  } catch (err) {
    console.error('보상상식 데이터 로드 오류:', err);
    showError(err);
  } finally {
    dataLoading = false;
  }
}

function activeCategory(){
  const tab = ckmModal?.querySelector('.ckm-tab[aria-selected="true"]');
  return tab?.dataset?.cat || '차 vs. 차';
}

function renderListForActiveTab(){
  if (!listEl) return;
  const cat = activeCategory();
  const arr = byCat[cat] || [];

  listEl.innerHTML = arr.map((item, idx) => {
    const sub = item.situation_highlight ? `<p class="ckm-item-sub">${escapeHTML(item.situation_highlight)}</p>` : '';
    return `
      <button class="ckm-item" type="button" data-cat="${escapeHTML(item.category||'')}" data-idx="${idx}" aria-label="${escapeHTML(item.title||'사례')}">
        <div class="ckm-item-title">${escapeHTML(item.title || '제목 없음')}</div>
        ${sub}
      </button>`;
  }).join('') || `<div class="ckm-empty"><p>해당 카테고리의 사례가 없습니다.</p></div>`;
}

function renderDetailFromCatIdx(cat, idx){
  const arr = byCat[cat] || [];
  const item = arr[+idx];
  if (!item) {
    detailEl.innerHTML = `<div class="ckm-empty"><p>사례를 찾지 못했습니다.</p></div>`;
    return;
  }
  detailEl.innerHTML = buildDetailHTML(item);
  detailEl.scrollTop = 0;
}

function buildDetailHTML(item){
  const cv = item.case_visual || {};
  const s1 = item.sections?.section_1;
  const s2 = item.sections?.section_2;
  const s3 = item.sections?.section_3;
  const s4 = item.sections?.section_4;

  const header = `
    <header class="ckm-detail-header">
      <span class="ckm-badge">${escapeHTML(item.category||'')}</span>
      <h3 class="ckm-detail-title">${escapeHTML(item.title||'제목 없음')}</h3>
      ${cv.description ? `<p class="ckm-detail-desc">${escapeHTML(cv.description)}</p>` : ''}
    </header>`;

  const sec1 = s1 ? `
    <section class="ckm-section">
      <h4 class="ckm-section-title">${escapeHTML(s1.title || s1.type || '과실비율')}</h4>
      ${s1.main_ratio ? `<div class="ckm-main-ratio">${escapeHTML(s1.main_ratio)}</div>`: ''}
      ${Array.isArray(s1.details) ? s1.details.map(d=>`<p class="ckm-p">${escapeHTML(d)}</p>`).join(''): ''}
      ${Array.isArray(s1.additional_cases) && s1.additional_cases.length ? `<div class="ckm-note"><h5>참고 사례</h5><ul>` + s1.additional_cases.map(a=>`<li>${escapeHTML(a)}</li>`).join('') + `</ul></div>`: ''}
    </section>` : '';

  const sec2 = s2 ? `
    <section class="ckm-section">
      <h4 class="ckm-section-title">${escapeHTML(s2.title || s2.type || '해설')}</h4>
      ${Array.isArray(s2.subtitles) && s2.subtitles.length ? `<ul class="ckm-bullets">` + s2.subtitles.map(s=>`<li>${escapeHTML(s)}</li>`).join('') + `</ul>`: ''}
      ${Array.isArray(s2.details) ? s2.details.map(d=>`<p class="ckm-p">${escapeHTML(d)}</p>`).join(''): ''}
    </section>` : '';

  const sec3 = s3 ? `
    <section class="ckm-section">
      <h4 class="ckm-section-title">${escapeHTML(s3.title || s3.type || '절차/팁')}</h4>
      ${Array.isArray(s3.steps) && s3.steps.length ? `<ol class="ckm-steps">` + s3.steps.map(st=>`<li>${escapeHTML(st)}</li>`).join('') + `</ol>`: ''}
      ${Array.isArray(s3.subtitles) && s3.subtitles.length ? `<ul class="ckm-bullets">` + s3.subtitles.map(s=>`<li>${escapeHTML(s)}</li>`).join('') + `</ul>`: ''}
      ${Array.isArray(s3.details) ? s3.details.map(d=>`<p class="ckm-p">${escapeHTML(d)}</p>`).join(''): ''}
    </section>` : '';

  const sec4 = s4 ? `
    <section class="ckm-section">
      <h4 class="ckm-section-title">${escapeHTML(s4.title || s4.type || 'Q&A')}</h4>
      ${s4.question ? `<div class="ckm-qa"><div class="q">Q. ${escapeHTML(s4.question.replace(/^Q\.\s*/,'') )}</div>`: ''}
      ${s4.answer_title ? `<div class="a-title">${escapeHTML(s4.answer_title)}</div>`: ''}
      ${Array.isArray(s4.answer_details) ? `<div class="a-body">` + s4.answer_details.map(a=>`<p>${escapeHTML(a)}</p>`).join('') + `</div>`: ''}
      ${s4.question ? `</div>`: ''}
    </section>` : '';

  return `<div class="ckm-detail-body">${header}${sec1}${sec2}${sec3}${sec4}
    ${item.case_id ? `<footer class="ckm-detail-foot"><small>Case ID: ${escapeHTML(item.case_id)}</small></footer>`: ''}
  </div>`;
}

listEl?.addEventListener('click', (e)=>{
  const btn = e.target.closest?.('.ckm-item');
  if (!btn) return;
  const cat = btn.dataset.cat;
  const idx = btn.dataset.idx;
  renderDetailFromCatIdx(cat, idx);
});

tabs?.forEach(tab => {
  tab.addEventListener('click', ()=>{
    tabs.forEach(t=>t.setAttribute('aria-selected', String(t===tab)));
    renderListForActiveTab();
    if (detailEl) {
      detailEl.innerHTML = '<div class="ckm-empty"><div class="empty-icon">📋</div><h3>사례를 선택해주세요</h3></div>';
    }
  });
});

function openCKM(){
  if (!ckmModal) return;
  ckmModal.removeAttribute('hidden');
  requestAnimationFrame(()=> ckmModal.classList.add('show'));
}
function closeCKM(){
  if (!ckmModal) return;
  ckmModal.classList.remove('show');
  const dlg = ckmModal.querySelector('.ckm-dialog');
  if (dlg) {
    const onEnd = e => {
      if (e.target !== dlg) return;
      ckmModal.setAttribute('hidden','');
      dlg.removeEventListener('transitionend', onEnd);
    };
    dlg.addEventListener('transitionend', onEnd);
    setTimeout(()=> ckmModal.setAttribute('hidden',''), 500);
  } else {
    ckmModal.setAttribute('hidden','');
  }
}

fabCKM?.addEventListener('click', openCKM);
closeBtn?.addEventListener('click', closeCKM);
backdrop?.addEventListener('click', closeCKM);

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadData);
} else {
  loadData();
}
