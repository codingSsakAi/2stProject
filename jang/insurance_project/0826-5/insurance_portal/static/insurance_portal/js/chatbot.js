// -*- coding: utf-8 -*-
// 네비게이션 방식 과실비율 챗봇 (전면 개편)
console.log('nav handler present?', !!window.navigationHandler);
console.info("[FAULT-BOT] loaded with navigation support. endpoint=/api/fault/answer/");

// ---- 전역 변수 ----
const FAULT_ANSWER_URL = "/api/fault/answer/";
const FAULT_NAVIGATION_URL = "/api/fault/navigation/";

// FAB 컨트롤러와의 연동을 위한 참조
let fabController = null;

// ---- DOM refs ----
const BOX = document.getElementById("chatbot-messages") || document.querySelector("#chatbot-messages");
const INPUT = document.getElementById("chatbot-text") || document.querySelector("#chatbot-text");
const SEND = document.getElementById("chatbot-send") || document.querySelector("#chatbot-send");
const CONTAINER = document.getElementById("chatbot-container") || document.querySelector("#chatbot-container");
const FAB = document.getElementById("chatbot-fab") || document.querySelector("#chatbot-fab");
const CLOSEBTN = document.getElementById("chatbot-close") || document.querySelector("#chatbot-close");
const RESETBTN = document.getElementById("chatbot-reset") || document.querySelector("#chatbot-reset");
const HEADER = document.getElementById("chatbot-header") || document.querySelector("#chatbot-header");

// ---- utils ----
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
    return "";
}

function scrollBottom() {
    try {
        BOX.scrollTop = BOX.scrollHeight;
    } catch (_) {}
}

// ---- 메시지 추가 함수 ----
function addMsg(role, html) {
    const row = document.createElement("div");
    row.className = role === "user" ? "chat-row user" : "chat-row bot";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = html;
    row.appendChild(bubble);
    BOX.appendChild(row);
    scrollBottom();
}

// ---- typing indicator ----
let typingEl = null;

function showTyping() {
    if (typingEl) return;
    const row = document.createElement("div");
    row.className = "chat-row bot";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    row.appendChild(bubble);
    BOX.appendChild(row);
    typingEl = row;
    scrollBottom();
}

function hideTyping() {
    if (typingEl && typingEl.parentNode) {
        typingEl.parentNode.removeChild(typingEl);
    }
    typingEl = null;
}

// ---- drag/resize helpers ----
let isDragging = false;
let dragOffsetX = 0, dragOffsetY = 0;

function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
}

function ensureResizable() {
    if (!CONTAINER) return;
    CONTAINER.style.resize = "both";
    CONTAINER.style.overflow = "hidden";
}

function setInitialSize() {
    if (!CONTAINER) return;
    const rect = CONTAINER.getBoundingClientRect();
    if (rect.width < 1000) CONTAINER.style.width = "1000px";
    if (rect.height < 700) CONTAINER.style.height = "700px";
}

function setInitialPosition() {
    if (!CONTAINER) return;
    const hasPos = CONTAINER.style.left || CONTAINER.style.top;
    const rect = CONTAINER.getBoundingClientRect();
    const w = (rect.width || 420);
    const h = (rect.height || 600);
    const margin = 56;

    const left = clamp(window.innerWidth - w - margin, 16, window.innerWidth - w - 16);
    const top = clamp(Math.round((window.innerHeight - h) / 2), 16, window.innerHeight - h - 16);

    CONTAINER.style.right = "auto";
    CONTAINER.style.bottom = "auto";
    if (!hasPos) {
        CONTAINER.style.left = `${left}px`;
        CONTAINER.style.top = `${top}px`;
    } else {
        const cur = CONTAINER.getBoundingClientRect();
        const nx = clamp(cur.left, 8, window.innerWidth - cur.width - 8);
        const ny = clamp(cur.top, 8, window.innerHeight - cur.height - 8);
        CONTAINER.style.left = `${nx}px`;
        CONTAINER.style.top = `${ny}px`;
    }
}

function wireDrag() {
    if (!HEADER || !CONTAINER) return;

    HEADER.style.cursor = "move";
    HEADER.addEventListener("mousedown", (ev) => {
        // 헤더 버튼 클릭 시에는 드래그 시작하지 않음
        if (ev.target.closest('.header-btn') || ev.target.closest('.header-controls')) return;

        if (ev.button !== 0) return;
        isDragging = true;
        const rect = CONTAINER.getBoundingClientRect();
        dragOffsetX = ev.clientX - rect.left;
        dragOffsetY = ev.clientY - rect.top;
        document.body.classList.add("noselect");
        ev.preventDefault();
    });

    document.addEventListener("mousemove", (ev) => {
        if (!isDragging) return;
        const rect = CONTAINER.getBoundingClientRect();
        const w = rect.width, h = rect.height;
        let x = ev.clientX - dragOffsetX;
        let y = ev.clientY - dragOffsetY;
        x = clamp(x, 8, window.innerWidth - w - 8);
        y = clamp(y, 8, window.innerHeight - h - 8);
        CONTAINER.style.left = `${x}px`;
        CONTAINER.style.top = `${y}px`;
        CONTAINER.style.right = "auto";
        CONTAINER.style.bottom = "auto";
    });

    document.addEventListener("mouseup", () => {
        if (!isDragging) return;
        isDragging = false;
        document.body.classList.remove("noselect");
    });

    window.addEventListener("resize", () => {
        if (!CONTAINER) return;
        const rect = CONTAINER.getBoundingClientRect();
        const w = rect.width, h = rect.height;
        let x = rect.left, y = rect.top;
        x = clamp(x, 8, window.innerWidth - w - 8);
        y = clamp(y, 8, window.innerHeight - h - 8);
        CONTAINER.style.left = `${x}px`;
        CONTAINER.style.top = `${y}px`;
        scrollBottom();
    });
}

// ---- FAB 상태 동기화 함수 ----
function notifyFABStateChange(isOpen) {
    try {
        // FAB 컨트롤러가 존재하면 상태 동기화
        if (window.FloatingFABController && fabController) {
            if (isOpen) {
                fabController.syncActiveState('chatbot');
            } else {
                fabController.clearActiveAction();
            }
        }
        
        // 전역 이벤트 발생 (다른 시스템에서 감지 가능)
        const event = new CustomEvent('chatbotStateChange', {
            detail: { isOpen: isOpen }
        });
        document.dispatchEvent(event);
    } catch (error) {
        console.warn('FAB 상태 동기화 중 오류:', error);
    }
}

// ---- 챗봇 초기화 및 관리 ----
function resetChatbot() {
    // 확인 다이얼로그
    if (!confirm("대화를 처음부터 새로 시작하시겠습니까?")) {
        return;
    }
    
    // UI 초기화
    BOX.innerHTML = "";
    
    // 네비게이션 핸들러 초기화
    if (window.navigationHandler) {
        navigationHandler.reset();
    }
    
    // 입력창 숨기기 (네비게이션 방식이므로)
    hideTextInput();
    
    // 초기화 완료 후 네비게이션 시작
    setTimeout(() => {
        startNavigationFlow();
    }, 100);
    
    console.info("[FAULT-BOT] Reset completed, starting navigation");
}

function startNavigationFlow() {
    if (window.navigationHandler) {
        navigationHandler.startNavigation();
    } else {
        console.error("[FAULT-BOT] Navigation handler not found");
        addMsg("bot", `<span class="text-danger">시스템 오류: 네비게이션 핸들러를 찾을 수 없습니다.</span>`);
    }
}

function hideTextInput() {
    if (INPUT && INPUT.parentElement) {
        INPUT.parentElement.style.display = "none";
    }
}

function showTextInput() {
    if (INPUT && INPUT.parentElement) {
        INPUT.parentElement.style.display = "flex";
    }
}

// ---- open/close ----
function openBot() {
    if (!CONTAINER) return;
    ensureResizable();
    setInitialSize();

    CONTAINER.style.display = "flex";
    setInitialPosition();

    // 네비게이션 시작
    setTimeout(() => {
        startNavigationFlow();
        scrollBottom();
    }, 100);
    
    // FAB 상태 동기화
    notifyFABStateChange(true);
    
    console.info("[FAULT-BOT] opened with navigation mode");
}

function closeBot() {
    if (!CONTAINER) return;
    CONTAINER.style.display = "none";
    
    // 네비게이션 상태 초기화
    if (window.navigationHandler) {
        navigationHandler.reset();
    }
    
    // FAB 상태 동기화
    notifyFABStateChange(false);
    
    console.info("[FAULT-BOT] closed");
}

function wireOpenClose() {
    if (CONTAINER && getComputedStyle(CONTAINER).display !== "none") {
        CONTAINER.style.display = "none";
    }
    
    // 기존 FAB 버튼 (호환성)
    if (FAB) FAB.addEventListener("click", openBot);
    
    // 새로운 FAB 시스템에서도 호출 가능하도록 전역으로 노출
    window.chatbotOpen = openBot;
    window.chatbotClose = closeBot;
    
    // 헤더 버튼들
    if (CLOSEBTN) CLOSEBTN.addEventListener("click", closeBot);
    if (RESETBTN) RESETBTN.addEventListener("click", resetChatbot);
    
    // ESC 키로 닫기
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && CONTAINER && getComputedStyle(CONTAINER).display !== "none") {
            closeBot();
        }
    });
    
    wireDrag();
}

// ---- FAB 컨트롤러 참조 획득 ----
function initFABIntegration() {
    // FAB 컨트롤러 로드를 기다림
    const checkFABController = () => {
        if (window.FloatingFABController) {
            console.info('[CHATBOT] FAB Controller detected');
            return true;
        }
        return false;
    };
    
    // 즉시 확인하고, 없으면 잠시 후 다시 확인
    if (!checkFABController()) {
        setTimeout(checkFABController, 500);
    }
}

// ---- 텍스트 입력 처리 (호환성 유지) ----
async function sendUserText(raw) {
    const t = (raw || "").trim();
    if (!t) return;
    
    addMsg("user", t);
    showTyping();
    
    try {
        const result = await askFaultAPI(t);
        hideTyping();
        renderFaultResult(result);
    } catch (e) {
        hideTyping();
        addMsg("bot", `<span class="text-danger">오류: ${e.message}</span>`);
    }
}

async function askFaultAPI(text) {
    const headers = { "Content-Type": "application/json" };
    const csrftoken = getCookie("csrftoken");
    if (csrftoken) headers["X-CSRFToken"] = csrftoken;

    const payload = {
        query: text,
        is_text_mode: true  // 텍스트 모드임을 표시
    };

    console.info("[FAULT-BOT] POST", FAULT_ANSWER_URL, payload);
    const res = await fetch(FAULT_ANSWER_URL, {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
    });

    let data;
    try {
        data = await res.json();
    } catch (e) {
        throw new Error(`응답 파싱 실패(${res.status})`);
    }

    if (!res.ok || !data || !data.result) {
        throw new Error(data && data.error ? data.error : "응답 형식이 올바르지 않습니다.");
    }

    return data.result;
}

function renderFaultResult(result) {
    if (result.needs_more_input) {
        // 재질문인 경우
        const summary = result.summary || "추가 정보가 필요합니다.";
        addMsg("bot", summary);
        
        if (result.questions) {
            // 질문이 있으면 텍스트 입력 모드로 전환
            showTextInput();
            renderQuestions(result.questions);
        }
        return;
    }
    
    // 최종 답변인 경우 네비게이션 핸들러의 렌더링 로직 사용
    if (window.navigationHandler) {
        navigationHandler.renderDetailedResult(result);
    } else {
        // 폴백 렌더링
        if (result.final_answer) {
            addMsg("bot", result.final_answer);
        }
    }
}

function renderQuestions(questions) {
    if (!Array.isArray(questions) || questions.length === 0) return;
    
    const html = `
        <div class="questions-section mt-3">
            <div class="mb-3 text-muted small">
                <i class="fas fa-hand-pointer me-1"></i>
                해당되는 상황을 선택하거나 직접 입력해주세요:
            </div>
            ${questions.map((q, index) => `
                <div class="question-item mb-3">
                    <div class="question-text mb-2">${q.question}</div>
                    <div class="question-options">
                        ${(q.options || []).map(opt => `
                            <button type="button" class="btn btn-sm btn-outline-primary me-2 mb-1 option-btn" 
                                    onclick="selectQuestionOption('${opt}')">
                                ${opt}
                            </button>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    addMsg("bot", html);
}

function selectQuestionOption(option) {
    if (!INPUT) return;
    INPUT.value = option;
    sendUserText(option);
}

function wireInput() {
    if (INPUT) {
        INPUT.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter" && !ev.shiftKey) {
                ev.preventDefault();
                const v = INPUT.value;
                INPUT.value = "";
                sendUserText(v);
            }
        });
    }
    if (SEND) {
        SEND.addEventListener("click", () => {
            const v = INPUT ? INPUT.value : "";
            if (INPUT) INPUT.value = "";
            sendUserText(v);
        });
    }
}

// ---- 모드 전환 함수 ----
function switchToTextMode() {
    // 네비게이션 모드 종료
    if (window.navigationHandler) {
        navigationHandler.isNavigationMode = false;
        navigationHandler.hideProgressBar();
    }
    
    // 텍스트 입력 표시
    showTextInput();
    
    // 안내 메시지
    addMsg("bot", `
        <div class="system-message">
            <i class="fas fa-keyboard me-2"></i>
            텍스트 입력 모드로 전환되었습니다. 사고 상황을 직접 입력해주세요.
        </div>
    `);
    
    // 입력창에 포커스
    if (INPUT) {
        setTimeout(() => INPUT.focus(), 100);
    }
}

function switchToNavigationMode() {
    // 텍스트 입력 숨기기
    hideTextInput();
    
    // 네비게이션 시작
    startNavigationFlow();
}

// ---- 전역 함수 노출 ----
window.switchToTextMode = switchToTextMode;
window.switchToNavigationMode = switchToNavigationMode;
window.selectQuestionOption = selectQuestionOption;

// ---- 초기화 ----
document.addEventListener("DOMContentLoaded", () => {
    wireOpenClose();
    wireInput();
    initFABIntegration();
    
    // 네비게이션 핸들러 로드 확인
    const checkNavigationHandler = () => {
        if (window.navigationHandler) {
            console.info('[CHATBOT] Navigation handler loaded');
            return true;
        }
        setTimeout(checkNavigationHandler, 100);
    };
    checkNavigationHandler();
});

// ==== [추가] 챗봇 열기 + 홈 네비게이션 시작 ====
// IIFE로 전역 오염 최소화
(function () {
  'use strict';

  // 디버깅: 네비 핸들러 로딩 여부
  console.log('nav handler present?', !!window.navigationHandler);

  // 템플릿에 존재해야 하는 DOM
  const panel = document.getElementById('chatbot-container');
  const msgWrap = document.getElementById('chatbot-messages');

  // 홈 화면(최상위 버튼/웰컴) 렌더링
  function renderHomeNow() {
  if (!window.navigationHandler) {
    console.warn('[chatbot] navigationHandler 미탑재');
    return;
  }
  try {
    if (msgWrap) msgWrap.innerHTML = '';
    // 네비게이션 초기화 후 "정식 진입"은 startNavigation()이 담당
    window.navigationHandler.reset();
    window.navigationHandler.startNavigation();   // ← 이것만 호출하면 1단계가 그려집니다
  } catch (e) {
    console.error('[chatbot] 홈 렌더 중 오류', e);
  }
}

  // 패널 열기 + 홈 시작
  function openChatbot() {
  // unified to openBot for consistent behavior
  if (typeof openBot === 'function') { openBot(); return; }
  if (!panel) return; panel.style.display='flex'; renderHomeNow();
}

  // 전역에서 호출 가능하도록 노출(원하면 fab-controller에서 호출)
  window.openFaultBot = openChatbot;

  // [바인딩 1] FAB 버튼 직접 클릭(예: data-action="chatbot")
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action="chatbot"]');
    if (btn) {
      openChatbot();
      e.preventDefault();
    }
  });

  // [바인딩 2] 커스텀 이벤트를 쓰는 경우(fab-controller가 이런 이벤트를 보낸다면 사용)
  window.addEventListener('fab:action', (ev) => {
    if (ev && ev.detail === 'chatbot') {
      openChatbot();
    }
  });

  // 옵션: 페이지 진입 시 자동 열기(원할 때만)
  if (panel && panel.dataset.autoOpen === '1') {
    openChatbot();
  }
})();
