/* Feature: 사고 가이드 | Purpose: 파일 용도 주석 추가 | Notes: 해당 파일은 사고 가이드 기능에 사용됩니다. */
/* ============================================================================
 * [보상상식] accident_data.json 전용 모달 렌더
 * - 좌측: 대타이틀만 리스트(검색 제거)
 * - 우측: 섹션 카드 + 문단/목록 자동 분리(가독성 개선)
 * - "추가 정보"는 키별 그룹으로 접힘 표시
 * - "원문 전체 보기(JSON)"는 제거
 * ========================================================================== */
(function () {
  "use strict";

  // ---------- 유틸 ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const CE = (tag, cls, text) => {
    const el = document.createElement(tag);
    if (cls) (Array.isArray(cls) ? el.classList.add(...cls) : el.classList.add(cls));
    if (text != null) el.textContent = text;
    return el;
  };
  const safe = (v, fb = "") => (v == null ? fb : String(v));
  const isArr = Array.isArray;
  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);
  const normCat = (s) => (s || "").replace(/\u00A0/g, " ").replace(/\s+/g, "").trim();

  // ---------- 루트 ----------
  const modal = document.getElementById("claim-knowledge-modal");
  if (!modal) return;

  const DATA_URL = modal.getAttribute("data-src") || "/static/insurance_portal/json/accident_data.json";

  // 캐시 DOM
  const listBox    = $("#ckm-list", modal);
  const detail     = $("#ckm-detail", modal);
  const detailBody = $("#ckm-detail-body", modal);
  const extrasWrap = $("#ckm-extras", modal);
  const extrasBody = $(".ckm-extras-body", modal);
  const tabs       = $$(".ckm-tab", modal);
  const closeBtn   = $(".ckm-close", modal);

  // 상태
  let allItems = [];
  let loadedOnce = false;
  let currentCat = tabs.find(b => b.getAttribute("aria-selected") === "true")?.dataset.cat || "차 vs. 차";

  // ---------- 데이터 로딩/정규화 ----------
  async function loadData() {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`데이터 로딩 실패: ${res.status}`);
    const json = await res.json();
    const arr = Array.isArray(json) ? json : Array.isArray(json.items) ? json.items : [];
    return normalizeLegacy(arr);
  }

  function normalizeLegacy(raw) {
    return raw.map((it, idx) => {
      const category  = safe(it.category, "차 vs. 차");
      const title     = safe(it.title, `제목 미상 #${idx + 1}`);
      const preview   = safe(it.situation_highlight) || safe(it.visual_title) || safe(it.situation);

      const sections  = buildSectionsFromLegacy(it);
      // extras: 스키마에 안 잡힌 필드 모으기
      const white = new Set(["title","category","case_id","situation","situation_highlight","visual_title","fault_ratio","keypoint","tips","qa"]);
      const extras = {};
      Object.keys(it).forEach(k => { if (!white.has(k) && it[k]!=null && String(it[k]).trim()) extras[k]=it[k]; });

      return { _raw: it, _idx: idx, category, title, preview, sections, extras };
    });
  }

  function buildSectionsFromLegacy(it) {
    const secs = [];

    // 1) 과실비율
    if (isObj(it.fault_ratio) && (it.fault_ratio.title || it.fault_ratio.content)) {
      const ratioText = safe(it.fault_ratio.content);
      const ratioMatch = ratioText.match(/(\d+\s*[:：]\s*\d+)/); // "50:50"
      const blocks = [];
      if (ratioMatch) {
        blocks.push({ kind: "main_ratio", title: safe(it.fault_ratio.title, "기본 과실비율"), value: ratioMatch[1] });
        const remain = ratioText.replace(ratioMatch[0], "").trim();
        if (remain) blocks.push({ kind: "details", title: "세부 해설", items: textToList(remain) });
      } else {
        blocks.push({ kind: "details", title: safe(it.fault_ratio.title, "기본 과실/해설"), items: textToList(ratioText) });
      }
      secs.push({ type: "과실비율", title: safe(it.fault_ratio.title), blocks });
    }

    // 2) 핵심 해설(key point)
    if (isObj(it.keypoint) && (it.keypoint.title || it.keypoint.content)) {
      secs.push({ type: "key point", title: safe(it.keypoint.title),
        blocks: [{ kind: "details", title: safe(it.keypoint.title, "핵심 해설"), items: textToList(safe(it.keypoint.content)) }]});
    }

    // 3) 실무 팁/절차(tips)
    if (isObj(it.tips) && (it.tips.title || it.tips.content)) {
      const t = safe(it.tips.content);
      const steps = detectSteps(t);
      secs.push(steps.length
        ? { type: "꿀팁", title: safe(it.tips.title), blocks: [{ kind: "steps", title: safe(it.tips.title, "실무 팁/절차"), steps }] }
        : { type: "꿀팁", title: safe(it.tips.title), blocks: [{ kind: "details", title: safe(it.tips.title, "실무 팁"), items: textToList(t) }] });
    }

    // 4) Q&A
    if (isObj(it.qa) && (it.qa.title || it.qa.content)) {
      secs.push({ type: "Q&A", title: safe(it.qa.title),
        blocks: [{ kind: "details", title: safe(it.qa.title, "자주 묻는 질문"), items: textToList(safe(it.qa.content)) }] });
    }

    return secs;
  }

  // 텍스트 → 목록 아이템
  function textToList(txt) {
    const lines = String(txt).replace(/\r\n?/g,"\n").split("\n").map(s=>s.trim()).filter(Boolean);
    if (!lines.length) return [];
    return lines.map(s => ({ label: "", text: s }));
  }
  // 번호형 단계 추출
  function detectSteps(txt) {
    const lines = String(txt).replace(/\r\n?/g,"\n").split("\n").map(s=>s.trim()).filter(Boolean);
    const steps = [];
    lines.forEach(s => {
      const m = s.match(/^(\d+[\.\)]|[①-⑳]|[-•▪])\s*(.+)$/);
      if (m) steps.push({ title:"", text:m[2].trim() });
    });
    return steps;
  }

  // ---------- 좌측 리스트 ----------
  function renderList(items) {
    listBox.innerHTML = "";
    if (!items.length) {
      const empty = CE("div", "ckm-empty");
      empty.appendChild(CE("h3", null, "표시할 항목이 없습니다."));
      empty.appendChild(CE("p", null, "선택한 분류에 해당하는 사례가 없습니다."));
      listBox.appendChild(empty);
      renderEmptyDetail();
      return;
    }

    // “대타이틀만” 단순 리스트 (검색 제거)
    const body = CE("div", "ckm-list-body");
    listBox.appendChild(body);

    items.forEach((it, i) => {
      const btn = CE("button", ["ckm-item"]);
      btn.setAttribute("role","option");
      btn.setAttribute("aria-selected", i===0 ? "true":"false");
      btn.appendChild(CE("div","title", it.title));
      if (it.preview) btn.appendChild(CE("div","ckm-item-sub", it.preview));
      btn.addEventListener("click", () => {
        $$(".ckm-item", body).forEach(b => b.classList.remove("active"));
        $$(".ckm-item", body).forEach(b => b.setAttribute("aria-selected","false"));
        btn.classList.add("active");
        btn.setAttribute("aria-selected","true");
        renderDetail(it);
      });
      if (i===0) btn.classList.add("active");
      body.appendChild(btn);
    });

    // 첫 항목 표시
    renderDetail(items[0]);
  }

  // ---------- 상세 ----------
  function renderEmptyDetail() {
    detailBody.innerHTML = "";
    const empty = CE("div", "ckm-empty");
    empty.appendChild(CE("h3", null, "사례를 선택해주세요"));
    empty.appendChild(CE("p", null, "좌측 목록에서 항목을 선택하면 상세가 표시됩니다."));
    detailBody.appendChild(empty);
    extrasWrap.hidden = true;
  }

  function renderDetail(item) {
    detailBody.innerHTML = "";

    // 제목
    const head = CE("div", "ckm-detail-header");
    head.appendChild(CE("h3", "ckm-detail-title", item.title));
    if (item.preview) head.appendChild(CE("p", "ckm-detail-desc", item.preview));
    detailBody.appendChild(head);

    // 섹션 카드 렌더
    detailBody.appendChild(renderSections(item.sections));

    // 추가 정보(있을 때만, 접힘 기본)
    const keys = Object.keys(item.extras || {});
    if (keys.length) {
      extrasBody.innerHTML = "";
      keys.forEach(k => {
        const box = CE("div","ckm-section");
        box.appendChild(CE("h4","ckm-section-title", k));
        box.appendChild(renderRichText(item.extras[k]));
        extrasBody.appendChild(box);
      });
      extrasWrap.hidden = false;
      extrasWrap.open = false;
    } else {
      extrasWrap.hidden = true;
    }

    detail.scrollTop = 0;
  }

  // ---------- 섹션 / 블록 ----------
  function renderSections(sections) {
    const wrap = CE("div","ckm-sections");
    if (!isArr(sections) || !sections.length) {
      wrap.appendChild(CE("p","ckm-empty","세부 섹션이 없습니다."));
      return wrap;
    }

    // 우선순위 정렬
    const order = ["과실비율","key point","꿀팁","Q&A"];
    const buckets = {};
    const others = [];
    sections.forEach(sec => {
      const t = safe(sec.type, "기타");
      if (!buckets[t]) buckets[t]=[];
      buckets[t].push(sec);
      if (!order.includes(t)) others.push(t);
    });
    const ordered = [...order, ...others.filter((v,i,a)=>a.indexOf(v)===i)].filter(t=>buckets[t]);

    ordered.forEach(type => {
      const sect = CE("section","ckm-section");
      sect.appendChild(CE("h4","ckm-section-title", labelOfType(type)));
      buckets[type].forEach(sec => sect.appendChild(renderSectionBlocks(sec)));
      wrap.appendChild(sect);
    });

    return wrap;
  }

  function labelOfType(type){
    switch(type){
      case "과실비율": return "기본 과실/세부 비율";
      case "key point": return "핵심 해설";
      case "꿀팁": return "실무 팁/절차";
      case "Q&A": return "자주 묻는 질문";
      default: return type || "세부 내용";
    }
  }

  function renderSectionBlocks(section){
    const box = CE("div","ckm-sec-box");
    if (section.title) box.appendChild(CE("h5","ckm-block-title", safe(section.title)));

    const blocks = isArr(section.blocks) ? section.blocks : [];
    if (!blocks.length){ box.appendChild(CE("p","ckm-empty","내용 없음")); return box; }

    blocks.forEach(blk=>{
      const kind = safe(blk.kind).toLowerCase();
      if (kind==="main_ratio")       box.appendChild(renderMainRatio(blk));
      else if (kind==="details")     box.appendChild(renderDetails(blk));
      else if (kind==="steps")       box.appendChild(renderSteps(blk));
      else                           box.appendChild(renderGeneric(blk));
    });

    return box;
  }

  function renderMainRatio(blk){
    const card = CE("div","ckm-main-ratio");
    if (blk.title) card.appendChild(CE("div","ckm-badge", safe(blk.title)));
    if (blk.value != null) card.appendChild(CE("p",null, safe(blk.value)));
    if (blk.note) card.appendChild(CE("p","ckm-detail-desc", safe(blk.note)));
    return card;
  }

  function renderDetails(blk){
    const frag = document.createDocumentFragment();
    if (blk.title) frag.appendChild(CE("div","ckm-badge", safe(blk.title)));
    const ul = CE("ul","ckm-bullets");
    (isArr(blk.items)?blk.items:[]).forEach(it=>{
      const li = document.createElement("li");
      if (isObj(it) && (it.label || it.text)) {
        if (it.label) li.appendChild(CE("strong",null, it.label+" "));
        if (it.text)  li.appendChild(CE("span",null, it.text));
      } else {
        li.textContent = safe(it);
      }
      ul.appendChild(li);
    });
    frag.appendChild(ul);
    return frag;
  }

  function renderSteps(blk){
    const frag = document.createDocumentFragment();
    if (blk.title) frag.appendChild(CE("div","ckm-badge", safe(blk.title)));
    const ol = CE("ol","ckm-steps");
    (isArr(blk.steps)?blk.steps:[]).forEach(st=>{
      const li = document.createElement("li");
      if (isObj(st) && st.text) li.textContent = st.text;
      else li.textContent = safe(st);
      ol.appendChild(li);
    });
    frag.appendChild(ol);
    return frag;
  }

  // 문자열을 문단/목록으로 자동 분리해 요소화
  function renderRichText(raw){
    const wrap = document.createElement("div");
    if (!raw) return wrap;

    const lines = String(raw).replace(/\r\n?/g,"\n").split("\n").map(s=>s.trim());
    const blocks = [];
    let buf = [];
    const flush = ()=>{ if(buf.length){ blocks.push(buf.join("\n")); buf=[]; } };
    for(const ln of lines){ if(!ln) flush(); else buf.push(ln); } flush();

    blocks.forEach(block=>{
      const allList = block.split("\n").every(ln => /^(\d+[\.\)]|[-•▪])\s+/.test(ln));
      if (allList){
        const ul = document.createElement("ul");
        block.split("\n").forEach(ln=>{
          const li = document.createElement("li");
          li.textContent = ln.replace(/^(\d+[\.\)]|[-•▪])\s+/, "");
          ul.appendChild(li);
        });
        wrap.appendChild(ul);
      } else {
        const p = document.createElement("p");
        if (/:$/.test(block.split("\n")[0]) || block.length <= 20){
          const b = document.createElement("strong");
          b.textContent = block;
          p.appendChild(b);
        } else {
          p.textContent = block;
        }
        wrap.appendChild(p);
      }
    });
    return wrap;
  }

  function renderGeneric(blk){
    const frag = document.createDocumentFragment();
    if (blk.title) frag.appendChild(CE("div","ckm-badge", safe(blk.title)));
    if (blk.text)  frag.appendChild(renderRichText(blk.text));
    if (isArr(blk.items) && blk.items.length){
      const ul = CE("ul","ckm-bullets");
      blk.items.forEach(v=>{
        const li = document.createElement("li");
        if (isObj(v) && (v.label || v.text)){
          if (v.label) li.appendChild(CE("strong",null,v.label+" "));
          if (v.text)  li.appendChild(CE("span",null,v.text));
        } else {
          li.textContent = safe(v);
        }
        ul.appendChild(li);
      });
      frag.appendChild(ul);
    }
    return frag;
  }

  // ---------- 탭/모달 ----------
  function bindTabs(){
    tabs.forEach(btn=>{
      btn.addEventListener("click", ()=>{
        if (btn.dataset.cat === currentCat) return;
        tabs.forEach(b => b.setAttribute("aria-selected","false"));
        btn.setAttribute("aria-selected","true");
        currentCat = btn.dataset.cat;
        filterAndRender();
      });
    });
  }

  function filterAndRender(){
    if (!allItems.length){ renderList([]); return; }
    const want = normCat(currentCat);
    const filtered = allItems.filter(it => normCat(it.category) === want);
    renderList(filtered.length ? filtered : allItems);
  }

  function bindClose(){
    if (closeBtn && !closeBtn.__bound){
      closeBtn.addEventListener("click", ()=>{
        modal.classList.remove("show");
        modal.setAttribute("hidden","");
      });
      closeBtn.__bound = true;
    }
    const backdrop = $(".ckm-backdrop", modal);
    if (backdrop && !backdrop.__bound){
      backdrop.addEventListener("click", ()=>{
        modal.classList.remove("show");
        modal.setAttribute("hidden","");
      });
      backdrop.__bound = true;
    }
  }

  async function openClaimKnowledge(){
    modal.removeAttribute("hidden");
    requestAnimationFrame(()=>modal.classList.add("show"));

    if (!loadedOnce){
      listBox.innerHTML = `<div class="ckm-loading"><div class="loading-spinner" aria-hidden="true"></div><p>사례를 불러오는 중입니다...</p></div>`;
      try{
        allItems = await loadData();
        loadedOnce = true;
        filterAndRender();
      }catch(err){
        listBox.innerHTML = "";
        const error = CE("div","ckm-empty");
        error.appendChild(CE("h3",null,"데이터를 불러오지 못했습니다."));
        error.appendChild(CE("p",null,String(err.message||err)));
        listBox.appendChild(error);
        console.error(err);
      }
    } else {
      filterAndRender();
    }
  }

  // 전역 노출
  window.openClaimKnowledge = openClaimKnowledge;

  // 모달 표시 자동 감지(다른 코드에서 hidden/class 토글 시 자동 로드)
  if ("MutationObserver" in window){
    const obs = new MutationObserver(()=>{
      const visible = !modal.hasAttribute("hidden") && modal.classList.contains("show");
      if (visible && !loadedOnce) openClaimKnowledge();
    });
    obs.observe(modal, { attributes:true, attributeFilter:["hidden","class"] });
  }

  // 초기 바인딩
  bindTabs();
  bindClose();
})();
