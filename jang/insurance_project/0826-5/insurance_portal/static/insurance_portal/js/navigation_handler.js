/* Feature: 보험 상식 | Purpose: 파일 용도 주석 추가 | Notes: 해당 파일은 보험 상식 기능에 사용됩니다. */
// -*- coding: utf-8 -*-
// navigation_handler.js - 챗봇 네비게이션 상태 관리

console.info("[NAVIGATION-HANDLER] loaded");

class NavigationHandler {
    constructor() {
        this.currentPath = [];
        this.currentLevel = 0;
        this.maxLevel = 3; // 대분류 → 중분류 → 소분류 → 확인
        this.navigationData = null;
        this.selectedOptions = [];
        this.isNavigationMode = false;
    }

    /**
     * 네비게이션 모드 시작
     */
    startNavigation() {
        this.reset();
        this.isNavigationMode = true;
        this.showProgressBar();
        this.loadNavigationLevel();
        console.info("[NAV] Navigation started");
    }

    /**
     * 네비게이션 초기화
     */
    reset() {
        this.currentPath = [];
        this.currentLevel = 0;
        this.selectedOptions = [];
        this.navigationData = null;
        this.hideProgressBar();
        this.isNavigationMode = false;
        console.info("[NAV] Navigation reset");
    }

    /**
     * 현재 레벨의 네비게이션 데이터 로드
     */
    async loadNavigationLevel() {
        try {
            showTyping();
            
            const response = await fetch('/api/fault/navigation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') || ''
                },
                body: JSON.stringify({
                    path: this.currentPath
                })
            });

            const data = await response.json();
            hideTyping();

            if (!response.ok || !data.result) {
                throw new Error(data.error || '네비게이션 데이터를 가져올 수 없습니다.');
            }

            this.navigationData = data.result;
            this.renderNavigationLevel();
            this.updateProgressBar();
            
        } catch (error) {
            hideTyping();
            console.error('[NAV] Load error:', error);
            addMsg("bot", `<span class="text-danger">오류: ${error.message}</span>`);
        }
    }

    /**
     * 현재 레벨의 네비게이션 UI 렌더링
     */
    renderNavigationLevel() {
        if (!this.navigationData) return;

        let html = '';

        // 환영 메시지 (첫 번째 레벨에만)
        if (this.currentLevel === 0) {
            html += `
                <div class="welcome-message">
                    <h3><i class="fas fa-car-crash me-2"></i>교통사고 과실비율 안내</h3>
                    <p>사고 상황을 단계별로 선택해주시면 정확한 과실비율을 안내해드리겠습니다.</p>
                </div>
            `;
        }

        // 네비게이션 컨테이너
        html += `<div class="navigation-container">`;
        
        // 제목
        html += `<div class="nav-title">${this.navigationData.title}</div>`;

        // 최종 선택인 경우
        if (this.navigationData.is_final) {
            html += this.renderFinalOptions();
        } else {
            // 일반 네비게이션 버튼들
            html += this.renderNavigationButtons();
        }

        // 액션 버튼들
        html += this.renderActionButtons();
        
        html += `</div>`;

        addMsg("bot", html);
        this.attachEventListeners();
    }

    /**
     * 네비게이션 버튼들 렌더링
     */
    renderNavigationButtons() {
        if (!this.navigationData.items) return '';

        let html = `<div class="nav-buttons">`;
        
        this.navigationData.items.forEach(item => {
            html += `
                <button class="nav-button" data-key="${item.key}">
                    <div class="d-flex align-items-center">
                        <i class="${item.icon} me-3"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${item.title}</div>
                            <div class="small text-muted">${item.description}</div>
                        </div>
                        <i class="fas fa-chevron-right icon"></i>
                    </div>
                </button>
            `;
        });
        
        html += `</div>`;
        return html;
    }

    /**
     * 최종 선택 옵션들 렌더링
     */
    renderFinalOptions() {
        if (!this.navigationData.options) return '';

        let html = `
            <div class="mb-3 text-center">
                <i class="${this.navigationData.icon} text-primary me-2"></i>
                <span class="text-muted">${this.navigationData.description}</span>
            </div>
            <div class="nav-buttons final-options">
        `;
        
        this.navigationData.options.forEach((option, index) => {
            html += `
                <button class="nav-button option-button" data-option="${option}" data-index="${index}">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-check-circle me-3 text-success" style="opacity: 0.3;"></i>
                        <div class="flex-grow-1 text-left">
                            ${option}
                        </div>
                    </div>
                </button>
            `;
        });
        
        html += `</div>`;
        return html;
    }

    /**
     * 액션 버튼들 렌더링
     */
    renderActionButtons() {
        let html = `<div class="action-buttons mt-3">`;

        // 뒤로가기 버튼 (첫 번째 레벨이 아닌 경우)
        if (this.currentLevel > 0) {
            html += `
                <button class="action-btn secondary" id="nav-back-btn">
                    <i class="fas fa-arrow-left me-1"></i>
                    이전으로
                </button>
            `;
        }

        // 처음으로 버튼
        html += `
            <button class="action-btn warning" id="nav-reset-btn">
                <i class="fas fa-redo me-1"></i>
                처음으로
            </button>
        `;

        // 확인하기 버튼 (최종 선택 단계에서만)
        if (this.navigationData && this.navigationData.is_final) {
            html += `
                <button class="action-btn primary d-none" id="nav-confirm-btn">
                    <i class="fas fa-search me-1"></i>
                    과실비율 확인하기
                </button>
            `;
        }

        html += `</div>`;
        return html;
    }

    /**
     * 이벤트 리스너 연결
     */
    attachEventListeners() {
        // 네비게이션 버튼 클릭
        document.querySelectorAll('.nav-button:not(.option-button)').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const key = e.currentTarget.getAttribute('data-key');
                this.selectNavigationItem(key);
            });
        });

        // 옵션 버튼 클릭
        document.querySelectorAll('.option-button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const option = e.currentTarget.getAttribute('data-option');
                const index = e.currentTarget.getAttribute('data-index');
                this.selectOption(option, index, e.currentTarget);
            });
        });

        // 뒤로가기 버튼
        const backBtn = document.getElementById('nav-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.goBack());
        }

        // 초기화 버튼
        const resetBtn = document.getElementById('nav-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.startNavigation());
        }

        // 확인하기 버튼
        const confirmBtn = document.getElementById('nav-confirm-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmSelection());
        }
    }

    /**
     * 네비게이션 항목 선택
     */
    selectNavigationItem(key) {
        this.currentPath.push(key);
        this.currentLevel++;
        
        console.info(`[NAV] Selected: ${key}, Path: ${this.currentPath.join(' → ')}, Level: ${this.currentLevel}`);
        
        // 다음 레벨 로드
        this.loadNavigationLevel();
    }

    /**
     * 최종 옵션 선택
     */
    selectOption(option, index, buttonElement) {
        // 이전 선택 초기화
        document.querySelectorAll('.option-button').forEach(btn => {
            btn.classList.remove('selected');
            btn.querySelector('.fa-check-circle').style.opacity = '0.3';
        });

        // 현재 선택 표시
        buttonElement.classList.add('selected');
        buttonElement.querySelector('.fa-check-circle').style.opacity = '1';

        // 선택 저장
        this.selectedOptions = [{
            option: option,
            index: index
        }];

        // 확인하기 버튼 표시
        const confirmBtn = document.getElementById('nav-confirm-btn');
        if (confirmBtn) {
            confirmBtn.classList.remove('d-none');
        }

        console.info(`[NAV] Option selected: ${option}`);
    }

    /**
     * 뒤로가기
     */
    goBack() {
        if (this.currentLevel > 0) {
            this.currentPath.pop();
            this.currentLevel--;
            this.selectedOptions = [];
            
            console.info(`[NAV] Back to level ${this.currentLevel}, Path: ${this.currentPath.join(' → ')}`);
            
            this.loadNavigationLevel();
        }
    }

    /**
     * 최종 선택 확인 및 결과 요청
     */
    async confirmSelection() {
        if (this.selectedOptions.length === 0) {
            alert('옵션을 선택해주세요.');
            return;
        }

        try {
            showTyping();
            
            // 선택된 경로와 옵션을 조합하여 쿼리 생성
            const fullPath = [...this.currentPath];
            const selectedOption = this.selectedOptions[0].option;
            const queryContext = `${fullPath.join(' > ')} > ${selectedOption}`;

            const response = await fetch('/api/fault/answer/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') || ''
                },
                body: JSON.stringify({
                    query: queryContext,
                    navigation_context: {
                        path: fullPath,
                        selected_option: selectedOption,
                        is_navigation_query: true
                    }
                })
            });

            const data = await response.json();
            hideTyping();

            if (!response.ok || !data.result) {
                throw new Error(data.error || '분석 결과를 가져올 수 없습니다.');
            }

            // 네비게이션 모드 종료
            this.isNavigationMode = false;
            this.hideProgressBar();

            // 결과 렌더링
            this.renderFaultResult(data.result, queryContext);
            
            console.info(`[NAV] Final result rendered for: ${queryContext}`);

        } catch (error) {
            hideTyping();
            console.error('[NAV] Confirm error:', error);
            addMsg("bot", `<span class="text-danger">오류: ${error.message}</span>`);
        }
    }

    /**
     * 과실비율 분석 결과 렌더링
     */
    renderFaultResult(result, queryContext) {
        // 선택 요약 표시
        const summaryHtml = `
            <div class="result-container">
                <div class="system-message mb-3">
                    <i class="fas fa-info-circle me-2"></i>
                    선택하신 사고 유형: <strong>${queryContext}</strong>
                </div>
            </div>
        `;
        addMsg("bot", summaryHtml);

        // 기존 결과 렌더링 로직 재사용
        this.renderDetailedResult(result);
    }

    /**
     * 상세 결과 렌더링 (6개 섹션)
     */
    renderDetailedResult(result) {
        // 1. 사고 설명
        if (result.accident_description) {
            const accidentHtml = `
                <div class="result-card accident-info">
                    <div class="result-card-header">
                        <i class="fas fa-info-circle me-2"></i>사고 설명
                    </div>
                    <div class="result-card-content">
                        ${result.accident_description}
                    </div>
                </div>
            `;
            addMsg("bot", accidentHtml);
        }

        // 2. 기본과실 + 설명
        if (result.base_fault || result.base_fault_description) {
            const baseFaultHtml = `
                <div class="result-card base-fault">
                    <div class="result-card-header">
                        <i class="fas fa-balance-scale me-2"></i>기본 과실비율
                    </div>
                    <div class="result-card-content">
                        ${result.base_fault ? `<div class="fault-ratio">
                            <div class="fault-ratio-main">${result.base_fault}</div>
                            <div class="fault-ratio-description">기본 과실비율</div>
                        </div>` : ''}
                        ${result.base_fault_description ? `<div class="mt-3">${result.base_fault_description}</div>` : ''}
                    </div>
                </div>
            `;
            addMsg("bot", baseFaultHtml);
        }

        // 3. 수정항목 + 설명
        if (result.modification_factors || result.modification_description) {
            const modificationHtml = `
                <div class="result-card modification">
                    <div class="result-card-header">
                        <i class="fas fa-edit me-2"></i>과실 수정요소
                    </div>
                    <div class="result-card-content">
                        ${result.modification_factors ? `<div class="mb-3">${result.modification_factors}</div>` : ''}
                        ${result.modification_description ? `<div>${result.modification_description}</div>` : ''}
                    </div>
                </div>
            `;
            addMsg("bot", modificationHtml);
        }

        // 4. 수정된 과실
        if (result.final_fault) {
            const finalFaultHtml = `
                <div class="result-card final-fault">
                    <div class="result-card-header">
                        <i class="fas fa-flag-checkered me-2"></i>최종 과실비율
                    </div>
                    <div class="result-card-content">
                        <div class="fault-ratio">
                            <div class="fault-ratio-main">${result.final_fault}</div>
                            <div class="fault-ratio-description">최종 결정 과실비율</div>
                        </div>
                    </div>
                </div>
            `;
            addMsg("bot", finalFaultHtml);
        }

        // 5. 관련 법규
        if (result.legal_info) {
            const legalHtml = `
                <div class="result-card legal">
                    <div class="result-card-header">
                        <i class="fas fa-gavel me-2"></i>관련 법규
                    </div>
                    <div class="result-card-content">
                        ${result.legal_info}
                    </div>
                </div>
            `;
            addMsg("bot", legalHtml);
        }

        // 6. 관련 판례
        if (result.precedents) {
            const precedentHtml = `
                <div class="result-card precedent">
                    <div class="result-card-header">
                        <i class="fas fa-university me-2"></i>관련 판례
                    </div>
                    <div class="result-card-content">
                        ${result.precedents}
                    </div>
                </div>
            `;
            addMsg("bot", precedentHtml);
        }

        // 7. 참고사항 (기존 로직 재사용)
        if (result.citations || result.notice) {
            this.renderCitations(result);
        }

        // 새로운 검색 버튼
        const newSearchHtml = `
            <div class="action-buttons mt-4">
                <button class="action-btn primary" onclick="navigationHandler.startNavigation()">
                    <i class="fas fa-plus me-1"></i>
                    새로운 사고 유형 검색
                </button>
            </div>
        `;
        addMsg("bot", newSearchHtml);
    }

    /**
     * 참고사항 렌더링
     */
    renderCitations(result) {
        const enhancedKniaInfo = `
            <div class="result-card">
                <div class="result-card-header">
                    <i class="fas fa-info-circle me-2"></i>참고사항
                </div>
                <div class="result-card-content">
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
                    <div class="text-muted">
                        <small>
                            <i class="fas fa-book me-1"></i>
                            <strong>참고자료:</strong> 『자동차사고 과실비율 인정기준』- 자동차사고 과실비율 인정기준(제10차 개정) 전문
                        </small>
                    </div>
                </div>
            </div>
        `;
        addMsg("bot", enhancedKniaInfo);
    }

    /**
     * 진행상황 표시바 표시
     */
    showProgressBar() {
        const container = document.querySelector('.progress-bar-container');
        if (container) {
            container.style.display = 'block';
        }
    }

    /**
     * 진행상황 표시바 숨김
     */
    hideProgressBar() {
        const container = document.querySelector('.progress-bar-container');
        if (container) {
            container.style.display = 'none';
        }
    }

    /**
     * 진행상황 표시바 업데이트
     */
    updateProgressBar() {
        const progressFill = document.querySelector('.progress-fill');
        const progressStep = document.querySelector('.progress-step');
        const breadcrumb = document.querySelector('.breadcrumb');

        if (progressFill && progressStep && breadcrumb) {
            // 진행률 계산 (0-100%)
            const progressPercent = Math.min((this.currentLevel / this.maxLevel) * 100, 100);
            progressFill.style.width = `${progressPercent}%`;

            // 단계 표시
            progressStep.textContent = `${this.currentLevel + 1}/${this.maxLevel + 1}단계`;

            // breadcrumb 업데이트
            let breadcrumbText = '사고 유형';
            if (this.currentPath.length > 0) {
                breadcrumbText += ' > ' + this.currentPath.join(' > ');
            }
            breadcrumb.innerHTML = breadcrumbText;
        }
    }
}

// 전역 네비게이션 핸들러 인스턴스
const navigationHandler = new NavigationHandler();

// 전역 함수로 노출
window.navigationHandler = navigationHandler;

/* ==== [추가] navigation_handler.js 의 홈 진입용 shim ==== */
// chatbot.js 맨 아래쪽에 존재하도록
(function(){
  'use strict';
  const panel = document.getElementById('chatbot-container');
  const msgWrap = document.getElementById('chatbot-messages');

  // 홈 그리기
  function renderHomeNow(){
    try {
      // 메시지 비우기
      msgWrap && (msgWrap.innerHTML = '');
      // 네비 시작
      window.navigationHandler?.renderHome?.();
    } catch(e){
      console.error('[chatbot] 홈 렌더 중 오류', e);
    }
  }

  // 챗봇 열기(없어서 추가한 함수)
  function openChatbot(){
    if (!panel) return;
    panel.style.display = 'block';
    panel.classList.add('open');
    panel.dataset.sticky = 'true';
    renderHomeNow();
  }
  window.openFaultBot = openChatbot;

  // FAB 버튼 바인딩
  document.addEventListener('click', (e)=>{
    const btn = e.target.closest('[data-action="chatbot"]');
    if (btn) { openChatbot(); e.preventDefault(); }
  });
})();
