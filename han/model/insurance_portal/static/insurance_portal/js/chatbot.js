// insurance_portal/static/insurance_portal/js/chatbot.js

document.addEventListener("DOMContentLoaded", function () {
    const fab = document.getElementById("chatbot-fab");
    const container = document.getElementById("chatbot-container");
    const closeBtn = document.getElementById("chatbot-close");
    const sendBtn = document.getElementById("chatbot-send");
    const input = document.getElementById("chatbot-text");
    const messages = document.getElementById("chatbot-messages");

    // 플로팅 버튼 클릭 → 챗봇 열기
    fab.addEventListener("click", () => {
        container.style.display = "block";
    });

    // 닫기 버튼 클릭 → 챗봇 닫기
    closeBtn.addEventListener("click", () => {
        container.style.display = "none";
    });

    // 메시지 추가 함수
    function appendMessage(sender, text) {
        const div = document.createElement("div");
        div.className = sender;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    // 전송 버튼 클릭 → API 호출
    sendBtn.addEventListener("click", async () => {
        const question = input.value.trim();
        if (!question) return;
        appendMessage("user", question);
        input.value = "";

        try {
            const resp = await fetch("/api/fault-chatbot/?q=" + encodeURIComponent(question));
            const data = await resp.json();
            if (data.answer) {
                appendMessage("bot", data.answer);
            } else if (data.error) {
                appendMessage("bot", "오류: " + data.error);
            }
        } catch (err) {
            appendMessage("bot", "서버 오류가 발생했습니다.");
        }
    });

    // Enter 키 입력 시 전송
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            sendBtn.click();
        }
    });
});
