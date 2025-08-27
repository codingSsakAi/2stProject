/* Feature: 보험 상식 | Purpose: 파일 용도 주석 추가 | Notes: 해당 파일은 보험 상식 기능에 사용됩니다. */
// fault_answer.js - 과실비율 답변 처리 로직

class FaultAnswerRenderer {
    constructor() {
        this.container = document.getElementById('fault-answer');
    }

    // 메인 렌더링 함수
    render(data) {
        this.clearAll();
        
        if (data.needs_more_input) {
            this.renderClarifyCard(data);
        } else {
            this.renderAnswerCards(data);
        }
    }

    // 모든 카드 숨기기
    clearAll() {
        const cards = [
            'fa-clarify-card', 'fa-summary-card', 'fa-table-card', 
            'fa-factors-card', 'fa-legal-card', 'fa-notice-card',
            'fa-citations-card', 'fa-disclaimer', 'fa-error'
        ];
        
        cards.forEach(id => {
            document.getElementById(id).classList.add('d-none');
        });
    }

    // 재질문 카드 렌더링
    renderClarifyCard(data) {
        const card = document.getElementById('fa-clarify-card');
        const messageEl = document.getElementById('fa-clarify-message');
        const questionsEl = document.getElementById('fa-clarify-questions');
        const examplesEl = document.getElementById('fa-clarify-examples');

        messageEl.textContent = data.message || '정확한 과실비율 산정을 위해 추가 정보가 필요합니다.';

        // 질문 렌더링
        if (data.questions) {
            questionsEl.innerHTML = data.questions.map(q => `
                <div class="mb-3">
                    <div class="fw-bold mb-2">${q.question}</div>
                    <div class="question-options">
                        ${q.options ? q.options.map(opt => 
                            `<span class="option-btn" onclick="selectOption('${opt}')">${opt}</span>`
                        ).join('') : ''}
                    </div>
                </div>
            `).join('');
        }

        // 예시 질문 렌더링
        if (data.examples) {
            examplesEl.innerHTML = data.examples.map(ex => 
                `<span class="example-btn" onclick="askExample('${ex}')">${ex}</span>`
            ).join('');
        }

        card.classList.remove('d-none');
    }

    // 답변 카드들 렌더링
    renderAnswerCards(data) {
        // 1. 과실비율 요약
        if (data.ratio_summary) {
            this.renderSummaryCard(data.ratio_summary);
        }

        // 2. 상세 표
        if (data.table_html) {
            this.renderTableCard(data.table_html);
        }

        // 3. 조정요소
        if (data.factors_plus || data.factors_minus) {
            this.renderFactorsCard(data.factors_plus, data.factors_minus);
        }

        // 4. 법령 및 판례
        if (data.legal_info) {
            this.renderLegalCard(data.legal_info);
        }

        // 5. 주의사항
        if (data.notice) {
            this.renderNoticeCard(data.notice);
        }

        // 6. 참고자료
        if (data.citations) {
            this.renderCitationsCard(data.citations);
        }

        // 7. 법률 자문 안내
        document.getElementById('fa-disclaimer').classList.remove('d-none');
    }

    // 과실비율 요약 카드
    renderSummaryCard(summary) {
        document.getElementById('fa-ratio-summary').textContent = summary.ratio;
        document.getElementById('fa-ratio-description').textContent = summary.description;
        document.getElementById('fa-summary-card').classList.remove('d-none');
    }

    // 표 카드
    renderTableCard(tableHtml) {
        document.getElementById('fa-table').innerHTML = tableHtml;
        document.getElementById('fa-table-card').classList.remove('d-none');
    }

    // 조정요소 카드
    renderFactorsCard(plusFactors, minusFactors) {
        if (plusFactors && plusFactors.length > 0) {
            document.getElementById('fa-factors-plus').innerHTML = `
                <ul class="list-unstyled mb-0">
                    ${plusFactors.map(factor => `<li><i class="fas fa-plus-circle text-danger me-2"></i>${factor}</li>`).join('')}
                </ul>
            `;
        }

        if (minusFactors && minusFactors.length > 0) {
            document.getElementById('fa-factors-minus').innerHTML = `
                <ul class="list-unstyled mb-0">
                    ${minusFactors.map(factor => `<li><i class="fas fa-minus-circle text-primary me-2"></i>${factor}</li>`).join('')}
                </ul>
            `;
        }

        document.getElementById('fa-factors-card').classList.remove('d-none');
    }

    // 법령 카드
    renderLegalCard(legalInfo) {
        document.getElementById('fa-legal-text').innerHTML = legalInfo;
        document.getElementById('fa-legal-card').classList.remove('d-none');
    }

    // 주의사항 카드
    renderNoticeCard(notice) {
        document.getElementById('fa-notice-text').innerHTML = notice;
        document.getElementById('fa-notice-card').classList.remove('d-none');
    }

    // 참고자료 카드
    renderCitationsCard(citations) {
        const citationHtml = citations.map(citation => 
            `<div><i class="fas fa-file-alt me-2"></i>${citation.file} (${citation.page || '페이지 미상'})</div>`
        ).join('');
        
        document.getElementById('fa-citations').innerHTML = citationHtml;
        document.getElementById('fa-citations-card').classList.remove('d-none');
    }

    // 에러 표시
    renderError(errorMessage) {
        document.getElementById('fa-error-text').textContent = errorMessage;
        document.getElementById('fa-error').classList.remove('d-none');
    }
}

// 전역 함수들
function selectOption(option) {
    // 선택된 옵션을 입력창에 추가하는 로직
    const input = document.querySelector('input[type="text"]'); // 실제 입력창 선택자로 수정 필요
    if (input) {
        input.value += (input.value ? ' ' : '') + option;
        input.focus();
    }
}

function askExample(example) {
    // 예시 질문을 바로 전송하는 로직
    const input = document.querySelector('input[type="text"]'); // 실제 입력창 선택자로 수정 필요
    if (input) {
        input.value = example;
        // 전송 버튼 클릭 또는 폼 제출 로직 추가 필요
        const submitBtn = document.querySelector('button[type="submit"]'); // 실제 버튼 선택자로 수정 필요
        if (submitBtn) {
            submitBtn.click();
        }
    }
}

// 사용 예시
// const renderer = new FaultAnswerRenderer();
// renderer.render(responseData);