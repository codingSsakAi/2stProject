// 챗봇 JavaScript - LLM + RAG + OpenAI 통합

class ChatBot {
    constructor() {
        this.isOpen = false;
        this.isTyping = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadChatHistory();
    }

    bindEvents() {
        const toggleBtn = document.getElementById('chatbotToggle');
        const closeBtn = document.getElementById('chatbotClose');
        const sendBtn = document.getElementById('sendBtn');
        const chatInput = document.getElementById('chatInput');
        const quickBtns = document.querySelectorAll('.quick-btn');

        // 챗봇 열기/닫기
        toggleBtn?.addEventListener('click', () => this.toggleChat());
        closeBtn?.addEventListener('click', () => this.closeChat());

        // 메시지 전송
        sendBtn?.addEventListener('click', () => this.sendMessage());
        chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        // 빠른 버튼
        quickBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.getAttribute('data-message');
                this.sendQuickMessage(message);
            });
        });
    }

    toggleChat() {
        const chatWindow = document.getElementById('chatbotWindow');
        
        if (this.isOpen) {
            this.closeChat();
        } else {
            chatWindow.classList.add('active');
            this.isOpen = true;
            
            // 챗봇 열 때 입력창에 포커스
            setTimeout(() => {
                document.getElementById('chatInput')?.focus();
            }, 300);
        }
    }

    closeChat() {
        const chatWindow = document.getElementById('chatbotWindow');
        chatWindow.classList.remove('active');
        this.isOpen = false;
    }

    async sendMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message || this.isTyping) return;

        // 사용자 메시지 표시
        this.addUserMessage(message);
        chatInput.value = '';

        // AI 응답 처리
        await this.processAIResponse(message);
    }

    sendQuickMessage(message) {
        const chatInput = document.getElementById('chatInput');
        chatInput.value = message;
        this.sendMessage();
    }

    addUserMessage(message) {
        const chatBody = document.getElementById('chatbotBody');
        
        const messageContainer = document.createElement('div');
        messageContainer.className = 'message-container';
        messageContainer.innerHTML = `
            <div class="user-message">
                <div class="message-bubble">
                    ${this.escapeHtml(message)}
                </div>
            </div>
        `;
        
        chatBody.appendChild(messageContainer);
        this.scrollToBottom();
        
        // 환영 메시지 숨기기
        const welcomeMessage = chatBody.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
    }

    addBotMessage(response) {
        const chatBody = document.getElementById('chatbotBody');
        
        const messageContainer = document.createElement('div');
        messageContainer.className = 'message-container';
        
        let buttonsHtml = '';
        if (response.buttons && response.buttons.length > 0) {
            buttonsHtml = '<div class="message-buttons">';
            response.buttons.forEach(button => {
                if (button.url) {
                    buttonsHtml += `<a href="${button.url}" class="message-btn" target="_blank">${button.text}</a>`;
                } else if (button.action === 'message') {
                    buttonsHtml += `<button class="message-btn quick-btn" data-message="${button.value}">${button.text}</button>`;
                } else if (button.action === 'phone') {
                    buttonsHtml += `<a href="tel:${button.value}" class="message-btn">${button.text}</a>`;
                }
            });
            buttonsHtml += '</div>';
        }
        
        messageContainer.innerHTML = `
            <div class="bot-message">
                <div class="message-bubble">
                    ${response.text.replace(/\n/g, '<br>')}
                    ${buttonsHtml}
                </div>
            </div>
        `;
        
        chatBody.appendChild(messageContainer);
        
        // 새로운 빠른 버튼에 이벤트 리스너 추가
        const newQuickBtns = messageContainer.querySelectorAll('.quick-btn');
        newQuickBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.getAttribute('data-message');
                this.sendQuickMessage(message);
            });
        });
        
        this.scrollToBottom();
    }

    showTypingIndicator() {
        const chatBody = document.getElementById('chatbotBody');
        
        const typingContainer = document.createElement('div');
        typingContainer.className = 'message-container typing-container';
        typingContainer.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        chatBody.appendChild(typingContainer);
        this.scrollToBottom();
        
        return typingContainer;
    }

    removeTypingIndicator(container) {
        if (container && container.parentNode) {
            container.parentNode.removeChild(container);
        }
    }

    async processAIResponse(userMessage) {
        this.isTyping = true;
        const typingContainer = this.showTypingIndicator();

        try {
            // 1단계: RAG에서 관련 정보 검색 시뮬레이션
            const ragResult = await this.searchRAG(userMessage);
            
            // 2단계: 로컬 ML 모델로 의도 분석 시뮬레이션
            const intent = await this.analyzeIntent(userMessage);
            
            // 3단계: 응답 생성 (RAG + 규칙 기반 + OpenAI)
            let response;
            if (ragResult.hasRelevantInfo) {
                // RAG에서 정보를 찾은 경우
                response = await this.generateRAGResponse(userMessage, ragResult);
            } else if (intent.confidence > 0.7) {
                // 규칙 기반 응답
                response = await this.generateRuleBasedResponse(userMessage, intent);
            } else {
                // OpenAI API 호출
                response = await this.generateOpenAIResponse(userMessage);
            }

            // 응답 지연 시뮬레이션 (실제로는 API 호출 시간)
            await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
            
            this.removeTypingIndicator(typingContainer);
            this.addBotMessage(response);
            
        } catch (error) {
            console.error('AI 응답 처리 중 오류:', error);
            this.removeTypingIndicator(typingContainer);
            
            this.addBotMessage({
                text: '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
                buttons: [
                    { text: '고객센터 연결', action: 'phone', value: '1588-0000' }
                ]
            });
        }
        
        this.isTyping = false;
    }

    async searchRAG(query) {
        // RAG 검색 시뮬레이션 - 실제로는 벡터 DB 검색
        const ragKeywords = [
            '보험용어', '용어', '뜻', '의미', '정의',
            '과실비율', '추돌', '교차로', '신호위반',
            '보상', '청구', '서류', '절차',
            '특약', '배상', '자기차량', '무보험차'
        ];

        const hasRelevantInfo = ragKeywords.some(keyword => 
            query.toLowerCase().includes(keyword)
        );

        if (hasRelevantInfo) {
            return {
                hasRelevantInfo: true,
                data: {
                    source: 'insurance_knowledge_base',
                    confidence: 0.85,
                    relevantDocs: ['보험용어사전', '과실비율가이드', '보상절차안내']
                }
            };
        }

        return { hasRelevantInfo: false };
    }

    async analyzeIntent(message) {
        // 로컬 ML 모델 의도 분석 시뮬레이션
        const intents = {
            '보험료': { intent: 'calculate_premium', confidence: 0.9 },
            '계산': { intent: 'calculate_premium', confidence: 0.85 },
            '사고': { intent: 'accident_guide', confidence: 0.9 },
            '신고': { intent: 'accident_report', confidence: 0.8 },
            '추천': { intent: 'recommend_insurance', confidence: 0.9 },
            '상품': { intent: 'recommend_insurance', confidence: 0.75 },
            '과실': { intent: 'fault_ratio', confidence: 0.9 },
            '비율': { intent: 'fault_ratio', confidence: 0.8 },
            '용어': { intent: 'term_definition', confidence: 0.9 },
            '뜻': { intent: 'term_definition', confidence: 0.8 }
        };

        for (const [keyword, intentData] of Object.entries(intents)) {
            if (message.includes(keyword)) {
                return intentData;
            }
        }

        return { intent: 'unknown', confidence: 0.3 };
    }

    async generateRAGResponse(query, ragResult) {
        // RAG 기반 응답 생성
        if (query.includes('용어') || query.includes('뜻')) {
            return {
                text: 'RAG 검색 결과를 바탕으로 보험용어를 설명드리겠습니다. 구체적으로 어떤 용어에 대해 알고 싶으신가요?',
                buttons: [
                    { text: '대인배상', url: '/common/terms/#대인배상' },
                    { text: '대물배상', url: '/common/terms/#대물배상' },
                    { text: '자기신체사고', url: '/common/terms/#자기신체사고' },
                    { text: '전체 용어사전', url: '/common/terms/' }
                ]
            };
        }

        if (query.includes('과실') || query.includes('비율')) {
            return {
                text: '과실비율은 사고 당사자들의 책임 정도를 백분율로 나타낸 것입니다. 사고 유형별로 과실비율이 다르게 적용됩니다.',
                buttons: [
                    { text: '추돌사고 과실비율', url: '/guide/fault-ratio/#추돌' },
                    { text: '교차로사고 과실비율', url: '/guide/fault-ratio/#교차로' },
                    { text: '전체 과실비율 가이드', url: '/guide/fault-ratio/' }
                ]
            };
        }

        return {
            text: 'RAG 데이터베이스에서 관련 정보를 찾았습니다. 더 구체적인 질문을 해주시면 정확한 답변을 드릴 수 있습니다.',
            buttons: [
                { text: '보험 용어 질문', action: 'message', value: '보험 용어 알려주세요' },
                { text: '과실비율 질문', action: 'message', value: '과실비율 알려주세요' },
                { text: '사고처리 질문', action: 'message', value: '사고처리 방법 알려주세요' }
            ]
        };
    }

    async generateRuleBasedResponse(message, intent) {
        // 규칙 기반 응답 생성 (기존 Django 뷰의 로직 활용)
        const responses = {
            'calculate_premium': {
                text: 'ML 모델 기반 보험료 계산을 도와드리겠습니다. 차량정보와 운전패턴을 분석하여 최적의 보험료를 산출해드립니다.',
                buttons: [
                    { text: 'AI 보험료 계산', url: '/insurance/recommend/' },
                    { text: '맞춤형 설계', url: '/insurance/custom/' },
                    { text: '보험사 비교', url: '/insurance/companies/' }
                ]
            },
            'accident_guide': {
                text: '사고 발생 시 신속하고 정확한 대처가 중요합니다. 단계별 가이드를 제공해드리겠습니다.',
                buttons: [
                    { text: '사고처리 가이드', url: '/guide/accident/' },
                    { text: '과실비율 확인', url: '/guide/fault-ratio/' },
                    { text: '보상절차 안내', url: '/guide/compensation/' }
                ]
            },
            'accident_report': {
                text: '사고 신고는 다음 순서로 진행해주세요:\n1. 인명구조 최우선\n2. 2차 사고 방지\n3. 증거수집\n4. 보험사 신고',
                buttons: [
                    { text: '상세 가이드 보기', url: '/guide/accident/' },
                    { text: '긴급전화 1588-0000', action: 'phone', value: '1588-0000' }
                ]
            },
            'recommend_insurance': {
                text: 'AI와 ML 모델을 활용한 맞춤형 보험 추천 서비스입니다. 고객님의 운전패턴과 라이프스타일을 분석하여 최적의 상품을 제안합니다.',
                buttons: [
                    { text: 'AI 추천받기', url: '/insurance/recommend/' },
                    { text: '보험사 비교', url: '/insurance/companies/' },
                    { text: '맞춤 설계', url: '/insurance/custom/' }
                ]
            },
            'fault_ratio': {
                text: '과실비율은 사고 유형별로 다르게 적용됩니다. 추돌사고, 교차로사고 등 상황별 과실비율을 확인해보세요.',
                buttons: [
                    { text: '과실비율 가이드', url: '/guide/fault-ratio/' },
                    { text: '사고처리 절차', url: '/guide/accident/' }
                ]
            },
            'term_definition': {
                text: 'RAG 기반 보험용어사전에서 정확한 정보를 제공합니다. 어려운 보험용어를 쉽게 설명해드리겠습니다.',
                buttons: [
                    { text: '용어사전 보기', url: '/common/terms/' },
                    { text: '기본용어', url: '/common/terms/#기본' },
                    { text: '특약용어', url: '/common/terms/#특약' }
                ]
            }
        };

        return responses[intent.intent] || {
            text: '죄송합니다. 정확히 이해하지 못했습니다. 다시 말씀해 주시겠어요?',
            buttons: [
                { text: '자주 묻는 질문', url: '/guide/knowledge/' },
                { text: '고객센터 연결', action: 'phone', value: '1588-0000' }
            ]
        };
    }

    async generateOpenAIResponse(message) {
        // OpenAI API 호출 시뮬레이션 - 실제로는 서버에서 처리
        try {
            const response = await fetch('/chatbot/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    message: message,
                    use_openai: true
                })
            });

            const data = await response.json();
            
            if (data.success) {
                return data.response;
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('OpenAI API 오류:', error);
            
            // Fallback 응답
            return {
                text: '죄송합니다. 현재 AI 서비스에 일시적인 문제가 있습니다. 고객센터로 연결해드릴까요?',
                buttons: [
                    { text: '고객센터 연결', action: 'phone', value: '1588-0000' },
                    { text: '자주 묻는 질문', url: '/guide/knowledge/' },
                    { text: '기본 가이드', url: '/guide/accident/' }
                ]
            };
        }
    }

    scrollToBottom() {
        const chatBody = document.getElementById('chatbotBody');
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    loadChatHistory() {
        // 로컬 스토리지에서 채팅 기록 로드 (선택사항)
        const history = localStorage.getItem('chatbot_history');
        if (history) {
            try {
                const messages = JSON.parse(history);
                const chatBody = document.getElementById('chatbotBody');
                
                // 환영 메시지 숨기기
                const welcomeMessage = chatBody.querySelector('.welcome-message');
                if (welcomeMessage && messages.length > 0) {
                    welcomeMessage.style.display = 'none';
                }
                
                messages.forEach(msg => {
                    if (msg.type === 'user') {
                        this.addUserMessage(msg.content);
                    } else {
                        this.addBotMessage(msg.content);
                    }
                });
            } catch (error) {
                console.error('채팅 기록 로드 오류:', error);
            }
        }
    }

    saveChatHistory() {
        // 채팅 기록을 로컬 스토리지에 저장 (선택사항)
        const chatBody = document.getElementById('chatbotBody');
        const messages = [];
        
        chatBody.querySelectorAll('.message-container').forEach(container => {
            const userMsg = container.querySelector('.user-message');
            const botMsg = container.querySelector('.bot-message');
            
            if (userMsg) {
                messages.push({
                    type: 'user',
                    content: userMsg.querySelector('.message-bubble').textContent
                });
            }
            
            if (botMsg) {
                const bubble = botMsg.querySelector('.message-bubble');
                const text = bubble.childNodes[0].textContent.trim();
                const buttons = Array.from(bubble.querySelectorAll('.message-btn')).map(btn => ({
                    text: btn.textContent,
                    url: btn.href || btn.getAttribute('data-message')
                }));
                
                messages.push({
                    type: 'bot',
                    content: { text, buttons }
                });
            }
        });
        
        localStorage.setItem('chatbot_history', JSON.stringify(messages.slice(-20))); // 최근 20개만 저장
    }

    clearChatHistory() {
        localStorage.removeItem('chatbot_history');
        const chatBody = document.getElementById('chatbotBody');
        const messageContainers = chatBody.querySelectorAll('.message-container:not(.welcome-message)');
        messageContainers.forEach(container => container.remove());
        
        // 환영 메시지 다시 표시
        const welcomeMessage = chatBody.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'block';
        }
    }
}

// 챗봇 인스턴스 생성 및 전역 함수
let chatBot;

document.addEventListener('DOMContentLoaded', function() {
    chatBot = new ChatBot();
    
    // 전역 함수들
    window.clearChatHistory = () => chatBot.clearChatHistory();
    window.saveChatHistory = () => chatBot.saveChatHistory();
});

// 페이지 언로드 시 채팅 기록 저장
window.addEventListener('beforeunload', function() {
    if (chatBot) {
        chatBot.saveChatHistory();
    }
});

// 개발자 도구용 디버그 함수들
if (typeof window !== 'undefined') {
    window.debugChatBot = {
        testMessage: (message) => {
            if (chatBot) {
                chatBot.addUserMessage(message);
                chatBot.processAIResponse(message);
            }
        },
        testResponse: (response) => {
            if (chatBot) {
                chatBot.addBotMessage(response);
            }
        },
        clearHistory: () => {
            if (chatBot) {
                chatBot.clearChatHistory();
            }
        },
        getHistory: () => {
            return localStorage.getItem('chatbot_history');
        }
    };
}