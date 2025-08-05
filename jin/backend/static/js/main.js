/* 자동차보험 추천 시스템 - 메인 JavaScript */

// 전역 변수
let isListening = false;
let currentStep = 0;
let userProfile = {};

// DOM 로드 완료 후 실행
document.addEventListener('DOMContentLoaded', function() {
    console.log('자동차보험 추천 시스템 초기화');
    initializeVoiceRecognition();
    initializeChatInterface();
});

// 음성 인식 초기화
function initializeVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        console.log('음성 인식 지원됨');
        setupVoiceRecognition();
    } else {
        console.log('음성 인식 지원되지 않음');
        hideVoiceButton();
    }
}

// 음성 인식 설정
function setupVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    window.recognition = new SpeechRecognition();
    
    window.recognition.continuous = false;
    window.recognition.interimResults = false;
    window.recognition.lang = 'ko-KR';
    
    window.recognition.onstart = function() {
        console.log('음성 인식 시작');
        isListening = true;
        updateVoiceButton(true);
    };
    
    window.recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        console.log('음성 입력:', transcript);
        processVoiceInput(transcript);
    };
    
    window.recognition.onend = function() {
        console.log('음성 인식 종료');
        isListening = false;
        updateVoiceButton(false);
    };
    
    window.recognition.onerror = function(event) {
        console.error('음성 인식 오류:', event.error);
        isListening = false;
        updateVoiceButton(false);
    };
}

// 음성 입력 처리
function processVoiceInput(transcript) {
    const lowerTranscript = transcript.toLowerCase();
    
    // 숫자 패턴 매칭
    const numberMatch = lowerTranscript.match(/(\d+)번/);
    if (numberMatch) {
        const number = parseInt(numberMatch[1]);
        selectOptionByNumber(number);
        return;
    }
    
    // 키워드 매칭
    if (lowerTranscript.includes('보험료') || lowerTranscript.includes('견적')) {
        startQuoteFlow();
    } else if (lowerTranscript.includes('비교') || lowerTranscript.includes('상품')) {
        startCompareFlow();
    } else if (lowerTranscript.includes('할인') || lowerTranscript.includes('혜택')) {
        startDiscountFlow();
    } else if (lowerTranscript.includes('다시')) {
        goBack();
    } else if (lowerTranscript.includes('취소')) {
        resetFlow();
    } else {
        addMessage('bot', '죄송합니다. 다시 말씀해주세요.');
    }
}

// 음성 입력 시작
function startVoiceInput() {
    if (!isListening) {
        window.recognition.start();
        
        // 10초 후 자동 종료
        setTimeout(() => {
            if (isListening) {
                stopVoiceInput();
            }
        }, 10000);
    } else {
        stopVoiceInput();
    }
}

// 음성 입력 중지
function stopVoiceInput() {
    if (isListening) {
        window.recognition.stop();
    }
}

// 음성 버튼 상태 업데이트
function updateVoiceButton(listening) {
    const voiceBtn = document.querySelector('.voice-btn');
    if (voiceBtn) {
        if (listening) {
            voiceBtn.classList.add('listening');
            voiceBtn.innerHTML = '🔴 듣는 중...';
        } else {
            voiceBtn.classList.remove('listening');
            voiceBtn.innerHTML = '🎤 음성 입력';
        }
    }
}

// 음성 버튼 숨기기
function hideVoiceButton() {
    const voiceBtn = document.querySelector('.voice-btn');
    if (voiceBtn) {
        voiceBtn.style.display = 'none';
    }
}

// 채팅 인터페이스 초기화
function initializeChatInterface() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.querySelector('.send-button');
    
    if (chatInput && sendButton) {
        // 엔터키로 메시지 전송
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // 전송 버튼 클릭
        sendButton.addEventListener('click', sendMessage);
    }
}

// 메시지 전송
function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (message) {
        addMessage('user', message);
        input.value = '';
        
        // AI 응답 시뮬레이션
        setTimeout(() => {
            processUserMessage(message);
        }, 1000);
        
        scrollToBottom();
    }
}

// 사용자 메시지 처리
function processUserMessage(message) {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('보험료') || lowerMessage.includes('견적')) {
        addMessage('bot', '보험료 견적을 시작하겠습니다! 🚗\n\n차량 정보를 입력해주세요.');
        startQuoteFlow();
    } else if (lowerMessage.includes('비교') || lowerMessage.includes('상품')) {
        addMessage('bot', '상품 비교를 시작하겠습니다! 🔍\n\n어떤 보험사를 비교해보시겠어요?');
        startCompareFlow();
    } else if (lowerMessage.includes('할인') || lowerMessage.includes('혜택')) {
        addMessage('bot', '할인 혜택을 알려드리겠습니다! 💰\n\n어떤 할인을 알아보시겠어요?');
        startDiscountFlow();
    } else {
        addMessage('bot', '궁금한 점을 자유롭게 물어보세요! 😊');
    }
}

// 메시지 추가
function addMessage(sender, content) {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = content;
        chatMessages.appendChild(messageDiv);
    }
}

// 스크롤을 맨 아래로
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 옵션 선택 (숫자)
function selectOptionByNumber(number) {
    const options = document.querySelectorAll('.option-btn, .quick-reply-btn');
    if (options[number - 1]) {
        const selectedOption = options[number - 1];
        const optionText = selectedOption.textContent;
        
        addMessage('user', `선택: ${optionText}`);
        addMessage('bot', `네, ${optionText}을 선택하셨군요!`);
        
        // 옵션에 따른 액션 실행
        selectedOption.click();
    } else {
        addMessage('bot', '죄송합니다. 다시 말씀해주세요.');
    }
}

// 보험료 견적 플로우 시작
function startQuoteFlow() {
    currentStep = 1;
    showQuoteOptions();
}

// 상품 비교 플로우 시작
function startCompareFlow() {
    currentStep = 1;
    showCompareOptions();
}

// 할인 혜택 플로우 시작
function startDiscountFlow() {
    currentStep = 1;
    showDiscountOptions();
}

// 이전 단계로
function goBack() {
    if (currentStep > 1) {
        currentStep--;
        showPreviousStep();
    } else {
        resetFlow();
    }
}

// 플로우 초기화
function resetFlow() {
    currentStep = 0;
    userProfile = {};
    showMainOptions();
}

// 옵션 표시 함수들 (구현 예정)
function showQuoteOptions() {
    addMessage('bot', '차종을 선택해주세요:\n1번: 경차\n2번: 소형차\n3번: 준중형차\n4번: 중형차\n5번: 대형차\n6번: SUV');
}

function showCompareOptions() {
    addMessage('bot', '비교할 보험사를 선택해주세요:\n1번: 삼성화재\n2번: 현대해상\n3번: KB손해보험');
}

function showDiscountOptions() {
    addMessage('bot', '할인 종류를 선택해주세요:\n1번: 무사고 할인\n2번: 장기 계약 할인\n3번: 다자녀 할인');
}

function showMainOptions() {
    addMessage('bot', '어떤 서비스를 이용하시겠어요?\n1번: 보험료 견적받기\n2번: 상품 비교하기\n3번: 할인 혜택 알아보기');
}

function showPreviousStep() {
    // 이전 단계 표시 로직 (구현 예정)
    addMessage('bot', '이전 단계로 돌아갑니다.');
}

// 유틸리티 함수들
function showLoading() {
    addMessage('bot', '잠시만 기다려주세요... ⏳');
}

function showError(message) {
    addMessage('bot', `오류가 발생했습니다: ${message}`);
}

// 전역 함수로 노출 (HTML에서 호출 가능)
window.startVoiceInput = startVoiceInput;
window.sendMessage = sendMessage;
window.selectOptionByNumber = selectOptionByNumber; 