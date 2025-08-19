// -*- coding: utf-8 -*-
// A안: 과실 전용 챗봇 프런트. /api/fault/answer/ 만 호출.
// - 버튼(#chatbot-fab)으로 열기, #chatbot-close/ESC로 닫기
// - 재질문이면 질문만, 최종답변에서만 KNIA 링크 표시
// - 추가: 팝업 우측에서 조금 띄운 기본 위치/큰 기본 크기 + 드래그/리사이즈 가능
// - 개선: 마크다운 렌더링 강화 및 재질문 메시지 스타일링

console.info("[FAULT-BOT A] loaded. endpoint=/api/fault/answer/");
const FAULT_ASK_URL = "/api/fault/answer/";

// ---- DOM refs ----
const BOX      = document.getElementById("chatbot-messages") || document.querySelector("#chatbot-messages");
const INPUT    = document.getElementById("chatbot-text")     || document.querySelector("#chatbot-text");
const SEND     = document.getElementById("chatbot-send")     || document.querySelector("#chatbot-send");
const CONTAINER= document.getElementById("chatbot-container")|| document.querySelector("#chatbot-container");
const FAB      = document.getElementById("chatbot-fab")      || document.querySelector("#chatbot-fab");
const CLOSEBTN = document.getElementById("chatbot-close")    || document.querySelector("#chatbot-close");
// 드래그 핸들(헤더)
const HEADER   = document.getElementById("chatbot-header")   || document.querySelector("#chatbot-header");

// ---- utils ----
function getCookie(name){
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
  return "";
}
function scrollBottom(){ try{ BOX.scrollTop = BOX.scrollHeight; }catch(_){} }

// 개선된 마크다운 렌더링
function renderMarkdown(md){
  if (!md) return "";
  
  // marked.js가 있으면 사용
  if (window.marked && typeof window.marked.parse === "function"){
    if (window.marked.setOptions) {
      window.marked.setOptions({ 
        mangle: false, 
        headerIds: false,
        breaks: true,  // 줄바꿈 지원
        gfm: true      // GitHub 마크다운 지원
      });
    }
    return window.marked.parse(md);
  }
  
  // marked.js가 없으면 간단한 마크다운 파싱
  let html = md;
  
  // 이모지와 함께 헤더 처리
  html = html.replace(/^### (.*$)/gim, '<h6 class="mt-3 mb-2 text-primary">$1</h6>');
  html = html.replace(/^## (.*$)/gim, '<h5 class="mt-3 mb-2 text-info">$1</h5>');
  html = html.replace(/^# (.*$)/gim, '<h4 class="mt-3 mb-2 text-dark">$1</h4>');
  
  // 굵은 글씨
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // 리스트
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul class="mb-3">$1</ul>');
  
  // 줄바꿈
  html = html.replace(/\n/g, '<br>');
  
  // div로 감싸기
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.innerHTML;
}

function addMsg(role, html){
  const row = document.createElement("div");
  row.className = role === "user" ? "chat-row user" : "chat-row bot";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  
  // 재질문 메시지인 경우 특별한 스타일 적용
  if (role === "bot" && html.includes("추가 정보가 필요해요")) {
    bubble.className += " clarify-bubble";
  }
  
  bubble.innerHTML = html;
  row.appendChild(bubble);
  BOX.appendChild(row);
  scrollBottom();
}

// ---- typing ----
let typingEl=null;
function showTyping(){
  if (typingEl) return;
  const row = document.createElement("div");
  row.className = "chat-row bot";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = "<span class='typing-dots'>...</span>";
  row.appendChild(bubble);
  BOX.appendChild(row);
  typingEl = row;
  scrollBottom();
}
function hideTyping(){ if(typingEl && typingEl.parentNode){ typingEl.parentNode.removeChild(typingEl); } typingEl=null; }

// ---- drag/resize helpers ----
let isDragging = false;
let dragOffsetX = 0, dragOffsetY = 0;

function clamp(val, min, max){ return Math.max(min, Math.min(max, val)); }

function ensureResizable(){
  if (!CONTAINER) return;
  // 리사이즈 가능 + 내용 스크롤 보정
  CONTAINER.style.resize = "both";
  CONTAINER.style.overflow = "hidden";
}

function setInitialSize(){
  if (!CONTAINER) return;
  // 한 번만 적용(이미 지정되어 있으면 유지)
  const rect = CONTAINER.getBoundingClientRect();
  if (rect.width < 420)  CONTAINER.style.width  = "440px";
  if (rect.height < 560) CONTAINER.style.height = "620px";
}

function setInitialPosition(){
  if (!CONTAINER) return;
  // 아직 left/top이 지정되지 않았다면(최초 open) 우측에서 약간 띄운 좌표로 설정
  const hasPos = CONTAINER.style.left || CONTAINER.style.top;
  const rect   = CONTAINER.getBoundingClientRect();
  const w = (rect.width  || 440);
  const h = (rect.height || 620);
  const margin = 56; // 우/하단 여백

  const left = clamp(window.innerWidth  - w - margin, 16, window.innerWidth  - w - 16);
  const top  = clamp(Math.round((window.innerHeight - h) / 2), 16, window.innerHeight - h - 16);

  // 드래그를 위해 left/top 기준으로 전환
  CONTAINER.style.right  = "auto";
  CONTAINER.style.bottom = "auto";
  if (!hasPos){
    CONTAINER.style.left   = `${left}px`;
    CONTAINER.style.top    = `${top}px`;
  }else{
    // 화면 리사이즈 등으로 벗어났을 수 있어 보정
    const cur = CONTAINER.getBoundingClientRect();
    const nx = clamp(cur.left, 8, window.innerWidth  - cur.width  - 8);
    const ny = clamp(cur.top,  8, window.innerHeight - cur.height - 8);
    CONTAINER.style.left = `${nx}px`;
    CONTAINER.style.top  = `${ny}px`;
  }
}

function wireDrag(){
  if (!HEADER || !CONTAINER) return;

  HEADER.style.cursor = "move";
  HEADER.addEventListener("mousedown", (ev)=>{
    if (ev.button !== 0) return; // 좌클릭만
    isDragging = true;
    const rect = CONTAINER.getBoundingClientRect();
    dragOffsetX = ev.clientX - rect.left;
    dragOffsetY = ev.clientY - rect.top;
    document.body.classList.add("noselect"); // 선택 방지(옵션: CSS 필요)
    ev.preventDefault();
  });

  document.addEventListener("mousemove", (ev)=>{
    if (!isDragging) return;
    const rect = CONTAINER.getBoundingClientRect();
    const w = rect.width, h = rect.height;
    let x = ev.clientX - dragOffsetX;
    let y = ev.clientY - dragOffsetY;
    x = clamp(x, 8, window.innerWidth  - w - 8);
    y = clamp(y, 8, window.innerHeight - h - 8);
    CONTAINER.style.left   = `${x}px`;
    CONTAINER.style.top    = `${y}px`;
    CONTAINER.style.right  = "auto";
    CONTAINER.style.bottom = "auto";
  });

  document.addEventListener("mouseup", ()=>{
    if (!isDragging) return;
    isDragging = false;
    document.body.classList.remove("noselect");
  });

  // 창 리사이즈 시 화면 밖으로 밀려나 있으면 보정
  window.addEventListener("resize", ()=>{
    if (!CONTAINER) return;
    const rect = CONTAINER.getBoundingClientRect();
    const w = rect.width, h = rect.height;
    let x = rect.left, y = rect.top;
    x = clamp(x, 8, window.innerWidth  - w - 8);
    y = clamp(y, 8, window.innerHeight - h - 8);
    CONTAINER.style.left = `${x}px`;
    CONTAINER.style.top  = `${y}px`;
    // 창 크기 변경 후에도 대화는 하단에 보이도록
    scrollBottom();
  });
}

// ---- open/close ----
function openBot(){
  if (!CONTAINER) return;
  // 표시 전에 사이즈/리사이즈 속성 지정
  ensureResizable();
  setInitialSize();

  CONTAINER.style.display = "block";
  // 위치는 표시 후 계산(브라우저가 크기를 알아야 함)
  setInitialPosition();

  setTimeout(()=>INPUT && INPUT.focus(), 0);
  // 열리면 메시지 하단으로
  setTimeout(scrollBottom, 0);
  console.info("[FAULT-BOT A] open");
}
function closeBot(){
  if (!CONTAINER) return;
  CONTAINER.style.display = "none";
  console.info("[FAULT-BOT A] close");
}
function wireOpenClose(){
  // 초기엔 닫아둠(스타일이 없다면 보일 수 있으므로)
  if (CONTAINER && getComputedStyle(CONTAINER).display !== "none"){
    CONTAINER.style.display = "none";
  }
  if (FAB)      FAB.addEventListener("click", openBot);
  if (CLOSEBTN) CLOSEBTN.addEventListener("click", closeBot);
  document.addEventListener("keydown", (e)=>{ if (e.key === "Escape") closeBot(); });
  wireDrag();
}

// ---- renderers ----
function renderFollowups(list){
  const qs = Array.isArray(list) ? list : [];
  if (!qs.length) return;
  
  const html = `
    <div class="followups mt-3">
      <div class="mb-2 text-muted small">
        <i class="fas fa-lightbulb me-1"></i>
        이런 식으로 물어보세요:
      </div>
      <div class="followup-buttons">
        ${qs.map(q=>`
          <button type="button" class="btn btn-sm btn-outline-primary mb-2 me-2 followup-btn" 
                  style="white-space: normal; text-align: left;">
            <i class="fas fa-comment me-1"></i>
            ${q}
          </button>
        `).join("")}
      </div>
    </div>`;
    
  addMsg("bot", html);
  
  // 버튼 클릭 이벤트 바인딩
  document.querySelectorAll(".followup-btn").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const t = btn.textContent || "";
      const cleanText = t.replace(/^\s*\S+\s*/, '').trim(); // 아이콘 제거
      if (!INPUT) return;
      INPUT.value = cleanText;
      // 자동 전송
      sendUserText(cleanText);
    });
  });
}

function renderRatioTable(r){
  if (typeof r.ratio_table === "string" && r.ratio_table.trim()){
    addMsg("bot", renderMarkdown(r.ratio_table)); return;
  }
  const rows = Array.isArray(r.ratio_table) ? r.ratio_table : [];
  if (!rows.length) return;
  const body = rows.map(x=>`<tr><td>${x.situation||""}</td><td>${x.ratio||""}</td><td>${x.conditions||""}</td></tr>`).join("");
  addMsg("bot",
    `<details class="source"><summary>비율표 보기</summary>
       <div class="table-responsive">
         <table class="table table-sm">
           <thead><tr><th>상황</th><th>비율</th><th>조건</th></tr></thead>
           <tbody>${body}</tbody>
         </table>
       </div>
     </details>`
  );
}
function renderFactors(r){
  const plus  = Array.isArray(r.factors_plus)  ? r.factors_plus  : [];
  const minus = Array.isArray(r.factors_minus) ? r.factors_minus : [];
  const plain = Array.isArray(r.factors)       ? r.factors       : [];
  let html = "";
  if (plus.length || minus.length){
    const pos = plus.map(s=>`<span class="badge bg-success me-1">+ ${s}</span>`).join("");
    const neg = minus.map(s=>`<span class="badge bg-warning text-dark me-1">- ${s}</span>`).join("");
    html = pos + (pos && neg ? " " : "") + neg;
  } else if (plain.length){
    html = plain.map(s=>`<span class="badge bg-secondary me-1">${s}</span>`).join("");
  }
  if (html) addMsg("bot", html);
}
function renderCitations(r){
  const cits = Array.isArray(r.citations) ? r.citations : [];
  if (!cits.length) return;
  const line = cits.map(c=>`[${c.id}] ${c.file||""} ${c.page||""}`).join(" · ");
  addMsg("bot", `<div class="text-muted small">근거: ${line}</div>`);
}
function renderFaultResult(r){
  const nmi = !!r.needs_more_input;
  console.info("[FAULT-BOT A] render nmi=", nmi);

  if (nmi){
    // 개선된 재질문 메시지 렌더링
    const summary = r.summary || "사고 상황을 조금 더 구체적으로 알려주세요.";
    const renderedSummary = renderMarkdown(summary);
    addMsg("bot", renderedSummary);
    renderFollowups(r.followups);
    return;
  }
  if (r.table_markdown) addMsg("bot", renderMarkdown(r.table_markdown));

  if (r.final_answer){
    const main = renderMarkdown(r.final_answer);
    const knia =
      `<div class="knia-tip small text-muted mt-3 p-2 border-left border-info bg-light">
         <i class="fas fa-info-circle me-1"></i>
         정확한 최종 과실비율은 개별 사정·증거에 따라 달라질 수 있습니다.
         <a href="https://accident.knia.or.kr/myaccident1" target="_blank" rel="noopener" class="text-decoration-none">
           <i class="fas fa-external-link-alt me-1"></i>손보협회 과실비율 확인
         </a>에서 기준을 확인하세요.
       </div>`;
    addMsg("bot", main + knia);
  }
  renderRatioTable(r);
  renderFactors(r);
  renderCitations(r);
}

// ---- API / send ----
async function askFaultAPI(text){
  const headers = {"Content-Type":"application/json"};
  const csrftoken = getCookie("csrftoken"); if (csrftoken) headers["X-CSRFToken"] = csrftoken;

  console.info("[FAULT-BOT A] POST", FAULT_ASK_URL, {query:text});
  const res = await fetch(FAULT_ASK_URL, { method: "POST", headers, body: JSON.stringify({ query: text }) });
  let data; try{ data = await res.json(); }catch(e){ throw new Error(`응답 파싱 실패(${res.status})`); }
  if (!res.ok || !data || !data.result){ throw new Error(data && data.error ? data.error : "응답 형식이 올바르지 않습니다."); }
  return data.result;
}
async function sendUserText(raw){
  const t = (raw||"").trim(); if (!t) return;
  addMsg("user", t);
  showTyping();
  try{ const result = await askFaultAPI(t); hideTyping(); renderFaultResult(result); }
  catch(e){ hideTyping(); addMsg("bot", `<span class="text-danger">오류: ${e.message}</span>`); }
}

// ---- wiring ----
function wireInput(){
  if (INPUT){
    INPUT.addEventListener("keydown", (ev)=>{
      if (ev.key === "Enter" && !ev.shiftKey){
        ev.preventDefault();
        const v = INPUT.value; INPUT.value = "";
        sendUserText(v);
      }
    });
  }
  if (SEND){
    SEND.addEventListener("click", ()=>{
      const v = INPUT ? INPUT.value : ""; if (INPUT) INPUT.value = "";
      sendUserText(v);
    });
  }
}

document.addEventListener("DOMContentLoaded", ()=>{
  wireOpenClose();
  wireInput();
});