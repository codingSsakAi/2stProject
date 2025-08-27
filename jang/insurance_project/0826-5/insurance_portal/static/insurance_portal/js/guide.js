/* Feature: 사고 가이드 | Purpose: 파일 용도 주석 추가 | Notes: 해당 파일은 사고 가이드 기능에 사용됩니다. */
// static/insurance_portal/js/guide.js
// UX 개선된 사고가이드 버전

const PATH_ACCIDENT = (window.GUIDE_JSONS && window.GUIDE_JSONS.accident) || '/static/insurance_portal/json/accident_flow.json';
const PATH_EVIDENCE = (window.GUIDE_JSONS && window.GUIDE_JSONS.evidence) || '/static/insurance_portal/json/evidence_collection.json';
const PATH_VARIANTS = (window.GUIDE_JSONS && window.GUIDE_JSONS.others)   || '/static/insurance_portal/json/other_processes.json';

let isLoading = false;

async function loadJSON(url){
  const res = await fetch(url, { cache: 'no-store' });
  if(!res.ok) throw new Error(`fetch error: ${url} (${res.status})`);
  return await res.json();
}

const ul = arr => `<ul class="mb-2">${(arr||[]).map(t=>`<li>${t}</li>`).join('')}</ul>`;
const badge = (txt, cls='bg-secondary') => `<span class="badge ${cls} me-2">${txt}</span>`;

function renderStep(step){
  return `
  <div class="border rounded p-3 mb-3">
    <div class="d-flex align-items-center mb-1">
      ${badge(step.step || '', 'bg-primary')}
      <strong>${step.title || ''}</strong>
    </div>
    ${step.subtitle ? `<div class="text-muted mb-2">${step.subtitle}</div>` : ''}
    ${step.details && step.details.length ? ul(step.details) : ''}
    ${step._extraButtons || ''}${step._extraContent || ''}
  </div>`;
}

function renderSectionTitle(title){ 
  return `<h6 class="mt-4 mb-2">${title}</h6>`; 
}

function STATIC_IMG(rel){
  const prefix = window.STATIC_PREFIX || '/static/insurance_portal/';
  return prefix + rel;
}

const STEP_IMG = {
  '01': STATIC_IMG('img/image1.png'),
  '02': STATIC_IMG('img/image2.png'),
  '03': STATIC_IMG('img/image3.png'),
  '04': STATIC_IMG('img/image4.png'),
  '05': STATIC_IMG('img/image5.png'),
  '06': STATIC_IMG('img/image6.png'),
};

const getStepImg = n => STEP_IMG[String(n).padStart(2,'0')] || null;

function renderStepCard(step){
  const stepNo = step.step || '';
  const title  = step.title || '';
  const subtitle = step.subtitle ? `<div class="subtitle">${step.subtitle}</div>` : '';
  const details  = (step.details && step.details.length) ? ul(step.details) : '';
  const buttons  = step._extraButtons || '';
  const extra    = step._extraContent || '';
  const imgSrc   = getStepImg(stepNo);
  const imgBlock = imgSrc ? `<div class="thumb"><img src="${imgSrc}" alt="${title}" loading="lazy"></div>` : '';
  
  return `
    <div class="guide-card" data-step="${stepNo}">
      ${imgBlock}
      <div class="head">
        <div class="step-badge">${stepNo}</div>
        <div class="title">${title}</div>
      </div>
      ${subtitle}${details}${buttons ? `<div class="btn-toggle">${buttons}</div>` : ''}${extra}
    </div>`;
}

function mergeGuide(baseSteps, evidence, variants){
  const target1 = baseSteps.find(s => (s.title||'').includes('사고현장보존'));
  if(target1 && evidence?.items?.length){
    target1.details = (target1.details || []).concat(['[증거확보 체크리스트]']).concat(evidence.items);
  }
  
  const policeStep = baseSteps.find(s => (s.title||'').includes('경찰서'));
  if(policeStep && variants?.섹션?.length){
    const policeHtml = variants.섹션.map(sec => `
      <div class="border rounded p-2 mb-2">
        <div class="fw-semibold mb-1">${sec.제목}</div>
        ${(sec.절차||[]).map(p=>`
          <div class="ms-2">
            ${badge(p.step,'bg-info')} <strong>${p.title}</strong>
            ${p.details && p.details.length ? ul(p.details) : ''}
            ${p["비고"] && p["비고"].length ? `<div class="small text-muted">비고: ${p["비고"].join(', ')}</div>` : ''}
          </div>`).join('')}
      </div>`).join('');
    
    const areaId = 'police-extra-' + Date.now();
    policeStep._extraButtons = `<button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}" aria-expanded="false" aria-controls="${areaId}">경찰서 절차 상세 보기</button>`;
    policeStep._extraContent = `<div id="${areaId}" class="collapse mt-2">${policeHtml}</div>`;
  }
  
  const insurerStep = baseSteps.find(s => (s.title||'').includes('보험사'));
  if(insurerStep && variants?.보험회사?.절차?.length){
    const insHtml = (variants.보험회사.절차||[]).map(p=>`
      <div class="ms-2">
        ${badge(p.step,'bg-warning')} <strong>${p.title}</strong>
        ${p.details && p.details.length ? ul(p.details) : ''}
      </div>`).join('');
    
    const areaId = 'ins-extra-' + Date.now();
    insurerStep._extraButtons = `<button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}" aria-expanded="false" aria-controls="${areaId}">보험사 절차 상세 보기</button>`;
    insurerStep._extraContent = `<div id="${areaId}" class="collapse mt-2">${insHtml}</div>`;
  }
  
  return baseSteps;
}

function appendVictimAndProperty(variants){
  let html = '';
  
  const renderFlowList = (steps) => {
    return `<div class="flow-list">` + steps.map(s => {
      const subtitle = s.subtitle ? `<div class="flow-sub">${s.subtitle}</div>` : '';
      const details  = (s.details && s.details.length) ? `<ul class="mb-2">${s.details.map(t=>`<li>${t}</li>`).join('')}</ul>` : '';
      return `
        <div class="flow-card">
          <div class="flow-head">
            <div class="flow-badge">${s.step || ''}</div>
            <div>
              <div class="flow-title">${s.title || ''}</div>
              ${subtitle}
            </div>
          </div>
          ${details}${s._extraButtons || ''}${s._extraContent || ''}
        </div>`;
    }).join('') + `</div>`;
  };
  
  if(variants?.피해물?.절차?.length){
    const areaId = 'victim-car-' + Date.now();
    html += `
      <div class="flow-section">
        <h6 class="mb-2">피해물(차량) 처리 흐름</h6>
        <button class="flow-toggle" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}" aria-expanded="false" aria-controls="${areaId}">내용 보기</button>
        <div id="${areaId}" class="collapse">${renderFlowList(variants.피해물.절차)}</div>
      </div>`;
  }
  
  if(variants?.피해자?.절차?.length){
    const areaId = 'victim-human-' + Date.now();
    html += `
      <div class="flow-section">
        <h6 class="mb-2">피해자 처리 흐름</h6>
        <button class="flow-toggle" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}" aria-expanded="false" aria-controls="${areaId}">내용 보기</button>
        <div id="${areaId}" class="collapse">${renderFlowList(variants.피해자.절차)}</div>
      </div>`;
  }
  
  return html;
}

function showLoading() {
  const body = document.getElementById('guideBody');
  body.innerHTML = `
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>사고처리 가이드를 불러오는 중입니다...</p>
    </div>`;
}

function showError(error) {
  const body = document.getElementById('guideBody');
  body.innerHTML = `
    <div class="alert alert-danger d-flex align-items-center" role="alert">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" class="me-2">
        <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <div>
        <strong>오류 발생</strong><br>
        가이드를 불러오지 못했습니다: ${error.message}<br>
        <small>네트워크 연결을 확인하고 다시 시도해주세요.</small>
      </div>
    </div>`;
}

async function openGuide(){
  if (isLoading) return;
  isLoading = true;
  
  try {
    showLoading();
    
    // 모달 미리 표시
    const modal = new bootstrap.Modal(document.getElementById('guideModal'));
    modal.show();
    
    const [base, evidence, variants] = await Promise.all([
      loadJSON(PATH_ACCIDENT), 
      loadJSON(PATH_EVIDENCE), 
      loadJSON(PATH_VARIANTS)
    ]);
    
    const merged = mergeGuide([...base], evidence, variants);
    const body = document.getElementById('guideBody');
    
    let html = '';
    html += `
      <div class="alert alert-info d-flex align-items-center py-3 mb-4" role="alert">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" class="me-2">
          <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <div>
          <strong>기본 사고처리 절차</strong><br>
          <small>체계적인 사고처리를 위한 단계별 가이드입니다.</small>
        </div>
      </div>`;
    
    html += `<div class="guide-grid">` + merged.map(renderStepCard).join('') + `</div>`;
    html += appendVictimAndProperty(variants);
    
    body.innerHTML = html;
    
    // 카드 애니메이션 효과
    setTimeout(() => {
      const cards = body.querySelectorAll('.guide-card');
      cards.forEach((card, index) => {
        setTimeout(() => {
          card.style.animation = 'fadeInUp 0.4s ease forwards';
        }, index * 100);
      });
    }, 100);
    
  } catch (error) {
    console.error('사고가이드 로드 오류:', error);
    showError(error);
    const modal = new bootstrap.Modal(document.getElementById('guideModal'));
    modal.show();
  } finally {
    isLoading = false;
  }
}

// 키보드 접근성 지원
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('guideModal');
    if (modal && modal.classList.contains('show')) {
      bootstrap.Modal.getInstance(modal)?.hide();
    }
  }
});

// 애니메이션 CSS 추가
const animationCSS = `
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
`;

if (!document.getElementById('guide-animations')) {
  const style = document.createElement('style');
  style.id = 'guide-animations';
  style.textContent = animationCSS;
  document.head.appendChild(style);
}

// 이벤트 리스너
document.getElementById('guide-fab')?.addEventListener('click', openGuide);

// 전역 함수 등록
window.openGuide = openGuide;