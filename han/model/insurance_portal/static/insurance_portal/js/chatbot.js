// -*- coding: utf-8 -*-
// 완전한 과실비율 대화형 챗봇 (모든 누락된 함수 포함)

console.info("[FAULT-BOT] loaded with full conversation support. endpoint=/api/fault/answer/");
const FAULT_ASK_URL = "/api/fault/answer/";

// 선택된 답변들을 저장하는 객체
let selectedAnswers = {};

// ---- 대화 히스토리 관리 ----
class ConversationSession {
    constructor() {
        this.history = [];
        this.maxHistory = 20; // 최대 20개 메시지 유지
    }

    addMessage(role, content) {
        this.history.push({
            role: role,
            content: content,
            timestamp: Date.now()
        });
        
        // 최대 개수 초과 시 오래된 것부터 제거
        if (this.history.length > this.maxHistory) {
            this.history = this.history.slice(-this.maxHistory);
        }
        
        console.info(`[CONVERSATION] Added ${role} message. Total: ${this.history.length}`);
    }

    getHistory() {
        return this.history;
    }

    getRecentHistory(turns = 3) {
        // 최근 N턴 (사용자-AI 쌍)을 반환
        const maxMessages = turns * 2;
        return this.history.slice(-maxMessages);
    }

    clear() {
        this.history = [];
        console.info("[CONVERSATION] History cleared");
    }
}

// 전역 세션 객체
const conversationSession = new ConversationSession();

// ---- DOM refs ----
const BOX      = document.getElementById("chatbot-messages") || document.querySelector("#chatbot-messages");
const INPUT    = document.getElementById("chatbot-text")     || document.querySelector("#chatbot-text");
const SEND     = document.getElementById("chatbot-send")     || document.querySelector("#chatbot-send");
const CONTAINER= document.getElementById("chatbot-container")|| document.querySelector("#chatbot-container");
const FAB      = document.getElementById("chatbot-fab")      || document.querySelector("#chatbot-fab");
const CLOSEBTN = document.getElementById("chatbot-close")    || document.querySelector("#chatbot-close");
const RESETBTN = document.getElementById("chatbot-reset")    || document.querySelector("#chatbot-reset");
const HEADER   = document.getElementById("chatbot-header")   || document.querySelector("#chatbot-header");

// ---- utils ----
function getCookie(name){
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
  return "";
}

function scrollBottom(){ 
    try{ 
        BOX.scrollTop = BOX.scrollHeight; 
    } catch(_) {} 
}

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

// ---- 대화 초기화 관련 ----
function resetConversation() {
    // 확인 다이얼로그
    if (!confirm("대화 내용을 모두 삭제하고 새로 시작하시겠습니까?")) {
        return;
    }
    
    // 세션 초기화
    conversationSession.clear();
    
    // UI 초기화
    BOX.innerHTML = "";
    
    // 입력창 비우기
    if (INPUT) {
        INPUT.value = "";
    }
    
    // 초기화 완료 메시지
    addMsg("bot", `
        <div class="reset-message">
            <i class="fas fa-refresh text-success me-2"></i>
            <strong>대화가 초기화되었습니다.</strong><br>
            <small class="text-muted">새로운 사고 상황에 대해 문의해주세요.</small>
        </div>
    `);
    
    console.info("[CONVERSATION] Reset completed");
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
function hideTyping(){ 
    if(typingEl && typingEl.parentNode){ 
        typingEl.parentNode.removeChild(typingEl); 
    } 
    typingEl=null; 
}

// ---- drag/resize helpers ----
let isDragging = false;
let dragOffsetX = 0, dragOffsetY = 0;

function clamp(val, min, max){ return Math.max(min, Math.min(max, val)); }

function ensureResizable(){
  if (!CONTAINER) return;
  CONTAINER.style.resize = "both";
  CONTAINER.style.overflow = "hidden";
}

function setInitialSize(){
  if (!CONTAINER) return;
  const rect = CONTAINER.getBoundingClientRect();
  if (rect.width < 420)  CONTAINER.style.width  = "440px";
  if (rect.height < 560) CONTAINER.style.height = "620px";
}

function setInitialPosition(){
  if (!CONTAINER) return;
  const hasPos = CONTAINER.style.left || CONTAINER.style.top;
  const rect   = CONTAINER.getBoundingClientRect();
  const w = (rect.width  || 440);
  const h = (rect.height || 620);
  const margin = 56;

  const left = clamp(window.innerWidth  - w - margin, 16, window.innerWidth  - w - 16);
  const top  = clamp(Math.round((window.innerHeight - h) / 2), 16, window.innerHeight - h - 16);

  CONTAINER.style.right  = "auto";
  CONTAINER.style.bottom = "auto";
  if (!hasPos){
    CONTAINER.style.left   = `${left}px`;
    CONTAINER.style.top    = `${top}px`;
  }else{
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
    if (ev.target.closest('.header-btn')) return;
    
    if (ev.button !== 0) return;
    isDragging = true;
    const rect = CONTAINER.getBoundingClientRect();
    dragOffsetX = ev.clientX - rect.left;
    dragOffsetY = ev.clientY - rect.top;
    document.body.classList.add("noselect");
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

  window.addEventListener("resize", ()=>{
    if (!CONTAINER) return;
    const rect = CONTAINER.getBoundingClientRect();
    const w = rect.width, h = rect.height;
    let x = rect.left, y = rect.top;
    x = clamp(x, 8, window.innerWidth  - w - 8);
    y = clamp(y, 8, window.innerHeight - h - 8);
    CONTAINER.style.left = `${x}px`;
    CONTAINER.style.top  = `${y}px`;
    scrollBottom();
  });
}

// ---- open/close ----
function openBot(){
  if (!CONTAINER) return;
  ensureResizable();
  setInitialSize();

  CONTAINER.style.display = "block";
  setInitialPosition();

  setTimeout(()=>INPUT && INPUT.focus(), 0);
  setTimeout(scrollBottom, 0);
  console.info("[FAULT-BOT] open");
}

function closeBot(){
  if (!CONTAINER) return;
  CONTAINER.style.display = "none";
  console.info("[FAULT-BOT] close");
}

function wireOpenClose(){
  if (CONTAINER && getComputedStyle(CONTAINER).display !== "none"){
    CONTAINER.style.display = "none";
  }
  if (FAB)      FAB.addEventListener("click", openBot);
  if (CLOSEBTN) CLOSEBTN.addEventListener("click", closeBot);
  if (RESETBTN) RESETBTN.addEventListener("click", resetConversation);
  document.addEventListener("keydown", (e)=>{ if (e.key === "Escape") closeBot(); });
  wireDrag();
}

// ---- 다중 선택 렌더링 ----
function renderQuestions(questions){
  if (!Array.isArray(questions) || questions.length === 0) return;
  
  selectedAnswers = {};
  
  const html = `
    <div class="questions-section mt-3">
      <div class="mb-3 text-muted small">
        <i class="fas fa-hand-pointer me-1"></i>
        해당되는 상황을 클릭하세요:
      </div>
      ${questions.map((q, index) => `
        <div class="question-item mb-3" data-question-index="${index}">
          <div class="question-text mb-2">${q.question}</div>
          <div class="question-options">
            ${(q.options || []).map(opt => `
              <button type="button" class="btn btn-sm btn-outline-primary me-2 mb-1 option-btn" 
                      data-question-index="${index}" 
                      data-question="${q.question}" 
                      data-answer="${opt}">
                ${opt}
              </button>
            `).join('')}
          </div>
          <div class="selected-indicator" style="display: none;">
            <small class="text-success">
              <i class="fas fa-check-circle me-1"></i>
              선택됨: <span class="selected-value"></span>
            </small>
          </div>
        </div>
      `).join('')}
      <div class="submit-section mt-4" style="display: none;">
        <button type="button" class="btn btn-success btn-submit-answers">
          <i class="fas fa-paper-plane me-2"></i>
          답변 전송
        </button>
        <button type="button" class="btn btn-outline-secondary ms-2 btn-reset-answers">
          <i class="fas fa-redo me-2"></i>
          다시 선택
        </button>
      </div>
    </div>`;
    
  addMsg("bot", html);
  
  // 옵션 버튼 클릭 이벤트
  document.querySelectorAll(".option-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const questionIndex = btn.getAttribute("data-question-index");
      const question = btn.getAttribute("data-question");
      const answer = btn.getAttribute("data-answer");
      
      const questionItem = btn.closest('.question-item');
      questionItem.querySelectorAll('.option-btn').forEach(otherBtn => {
        otherBtn.classList.remove('btn-primary');
        otherBtn.classList.add('btn-outline-primary');
      });
      
      btn.classList.remove('btn-outline-primary');
      btn.classList.add('btn-primary');
      
      selectedAnswers[questionIndex] = {
        question: question,
        answer: answer
      };
      
      const indicator = questionItem.querySelector('.selected-indicator');
      const valueSpan = questionItem.querySelector('.selected-value');
      valueSpan.textContent = answer;
      indicator.style.display = 'block';
      
      checkAllAnswered(questions.length);
    });
  });
  
  // 전송/리셋 버튼 이벤트
  document.querySelector('.btn-submit-answers').addEventListener('click', submitAllAnswers);
  document.querySelector('.btn-reset-answers').addEventListener('click', resetAllSelections);
}

function checkAllAnswered(totalQuestions) {
  const answeredCount = Object.keys(selectedAnswers).length;
  const submitSection = document.querySelector('.submit-section');
  
  if (answeredCount === totalQuestions) {
    submitSection.style.display = 'block';
  }
}

function submitAllAnswers() {
  if (Object.keys(selectedAnswers).length === 0) return;
  
  const answers = Object.values(selectedAnswers).map(item => 
    `${item.question} → ${item.answer}`
  ).join(', ');
  
  if (!INPUT) return;
  INPUT.value = answers;
  
  sendUserText(answers);
  selectedAnswers = {};
}

function resetAllSelections() {
  selectedAnswers = {};
  
  document.querySelectorAll('.option-btn').forEach(btn => {
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-outline-primary');
  });
  
  document.querySelectorAll('.selected-indicator').forEach(indicator => {
    indicator.style.display = 'none';
  });
  
  document.querySelector('.submit-section').style.display = 'none';
}

// ---- 기타 렌더링 함수들 ----
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
  const enhancedKniaInfo = `
    <div class="final-notice mt-4 p-3">
      <div class="notice-content">
        <p class="mb-2">
          <strong>본 답변은 손해보험협회에서 발간한 『자동차사고 과실비율 인정기준』의 내용을 기반으로 작성되었습니다.</strong><br>
          해당 기준서는 법원 판례와 보험업계 관행을 종합하여 만들어진 자료입니다.
        </p>
        <p class="mb-3">
          정확한 최종 과실비율은 사고 당시의 구체적 상황, 증거자료, 법적 판단에 따라 달라질 수 있으므로,
          <a href="https://accident.knia.or.kr/myaccident1" target="_blank" rel="noopener" class="text-decoration-none">
            <i class="fas fa-external-link-alt me-1"></i>손보협회 과실비율 확인 포털
          </a>에서 상세 기준을 확인하시거나 전문가와 상담받으시기 바랍니다.
        </p>
        <div class="reference-info">
          <small class="text-muted">
            <i class="fas fa-book me-1"></i>
            <strong>참고자료:</strong> 『자동차사고 과실비율 인정기준』- 자동차사고 과실비율 인정기준(제10차 개정) 전문
          </small>
        </div>
      </div>
    </div>`;
  
  addMsg("bot", enhancedKniaInfo);
}

function renderFaultResult(r){
  const nmi = !!r.needs_more_input;
  console.info("[FAULT-BOT] render nmi=", nmi);

  if (nmi){
    const summary = r.summary || "사고 상황을 조금 더 구체적으로 알려주세요.";
    const renderedSummary = renderMarkdown(summary);
    addMsg("bot", renderedSummary);
    
    conversationSession.addMessage("assistant", summary);
    
    if (r.questions) {
      renderQuestions(r.questions);
    }
    return;
  }
  
  if (r.table_markdown) addMsg("bot", renderMarkdown(r.table_markdown));

  if (r.final_answer){
    const main = renderMarkdown(r.final_answer);
    addMsg("bot", main);
    conversationSession.addMessage("assistant", r.final_answer);
  }
  
  renderRatioTable(r);
  renderFactors(r);
  renderCitations(r);
}

// ---- API / send ----
async function askFaultAPI(text, conversationHistory){
  const headers = {"Content-Type":"application/json"};
  const csrftoken = getCookie("csrftoken"); 
  if (csrftoken) headers["X-CSRFToken"] = csrftoken;

  const payload = { 
    query: text,
    conversation_history: conversationHistory || []
  };

  console.info("[FAULT-BOT] POST", FAULT_ASK_URL, payload);
  const res = await fetch(FAULT_ASK_URL, { 
    method: "POST", 
    headers, 
    body: JSON.stringify(payload) 
  });
  
  let data; 
  try{ 
    data = await res.json(); 
  } catch(e) { 
    throw new Error(`응답 파싱 실패(${res.status})`); 
  }
  
  if (!res.ok || !data || !data.result){ 
    throw new Error(data && data.error ? data.error : "응답 형식이 올바르지 않습니다."); 
  }
  
  return data.result;
}

async function sendUserText(raw){
  const t = (raw||"").trim(); 
  if (!t) return;
  
  conversationSession.addMessage("user", t);
  
  addMsg("user", t);
  showTyping();
  
  try{ 
    const history = conversationSession.getRecentHistory(3);
    const result = await askFaultAPI(t, history); 
    hideTyping(); 
    renderFaultResult(result); 
  }
  catch(e){ 
    hideTyping(); 
    addMsg("bot", `<span class="text-danger">오류: ${e.message}</span>`); 
  }
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
      const v = INPUT ? INPUT.value : ""; 
      if (INPUT) INPUT.value = "";
      sendUserText(v);
    });
  }
}

document.addEventListener("DOMContentLoaded", ()=>{
  wireOpenClose();
  wireInput();
});