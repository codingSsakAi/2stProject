const PATH_ACCIDENT = '/static/json/사고처리.json';
const PATH_EVIDENCE = '/static/json/증거확보.json';
const PATH_VARIANTS = '/static/json/다양한처리.json';
async function loadJSON(url){ const res = await fetch(url); if(!res.ok) throw new Error('fetch error: '+url); return await res.json(); }

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
    ${step._extraButtons || ''}${step._extraContent || ''}</div>`;
}
function renderSectionTitle(title){ return `<h6 class="mt-4 mb-2">${title}</h6>`; }

const STEP_IMG = {
  '01': STATIC_IMG('img/image1.png'),
  '02': STATIC_IMG('img/image2.png'),
  '03': STATIC_IMG('img/image3.png'),
  '04': STATIC_IMG('img/image4.png'),
  '05': STATIC_IMG('img/image5.png'),
  '06': STATIC_IMG('img/image6.png'),
};
function STATIC_IMG(rel){ return (window.STATIC_PREFIX || '/static/') + rel; }
const getStepImg = n => STEP_IMG[String(n).padStart(2,'0')] || null;

function renderStepCard(step){
  const stepNo = step.step || '';
  const title  = step.title || '';
  const subtitle = step.subtitle ? `<div class="subtitle">${step.subtitle}</div>` : '';
  const details  = (step.details && step.details.length) ? ul(step.details) : '';
  const buttons  = step._extraButtons || '';
  const extra    = step._extraContent || '';
  const imgSrc   = getStepImg(stepNo);
  const imgBlock = imgSrc ? `<div class="thumb"><img src="${imgSrc}" alt="${title}"></div>` : '';
  return `
    <div class="guide-card">
      ${imgBlock}
      <div class="head"><div class="step-badge">${stepNo}</div><div class="title">${title}</div></div>
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
    policeStep._extraButtons = `<button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}">경찰서 절차 상세 열기/닫기</button>`;
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
    insurerStep._extraButtons = `<button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}">보험사 절차 상세 열기/닫기</button>`;
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
            <div><div class="flow-title">${s.title || ''}</div>${subtitle}</div>
          </div>${details}${s._extraButtons || ''}${s._extraContent || ''}
        </div>`;
    }).join('') + `</div>`;
  };
  if(variants?.피해물?.절차?.length){
    const areaId = 'victim-car-' + Date.now();
    html += `
      <div class="flow-section">
        <h6 class="mb-2">피해물(차량) 처리 흐름</h6>
        <button class="flow-toggle" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}">내용 열기/닫기</button>
        <div id="${areaId}" class="collapse">${renderFlowList(variants.피해물.절차)}</div>
      </div>`;
  }
  if(variants?.피해자?.절차?.length){
    const areaId = 'victim-human-' + Date.now();
    html += `
      <div class="flow-section">
        <h6 class="mb-2">피해자 처리 흐름</h6>
        <button class="flow-toggle" type="button" data-bs-toggle="collapse" data-bs-target="#${areaId}">내용 열기/닫기</button>
        <div id="${areaId}" class="collapse">${renderFlowList(variants.피해자.절차)}</div>
      </div>`;
  }
  return html;
}

async function openGuide(){
  try{
    const [base, evidence, variants] = await Promise.all([
      loadJSON(PATH_ACCIDENT), loadJSON(PATH_EVIDENCE), loadJSON(PATH_VARIANTS)
    ]);
    const merged = mergeGuide([...base], evidence, variants);
    const body = document.getElementById('guideBody');
    let html = '';
    html += `<div class="alert alert-info py-2 mb-3">기본 사고 처리 순서와 절차 요약입니다.</div>`;
    html += `<div class="guide-grid">` + merged.map(renderStepCard).join('') + `</div>`;
    html += appendVictimAndProperty(variants);
    body.innerHTML = html;
    const modal = new bootstrap.Modal(document.getElementById('guideModal')); modal.show();
  }catch(e){
    document.getElementById('guideBody').innerHTML = `<div class="text-danger">가이드를 불러오지 못했습니다: ${e}</div>`;
    const modal = new bootstrap.Modal(document.getElementById('guideModal')); modal.show();
  }
}
document.getElementById('guide-fab')?.addEventListener('click', openGuide);
