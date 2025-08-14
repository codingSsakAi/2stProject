// insurance_portal/static/insurance_portal/js/claim_knowledge.js
// 기능: 보상상식 모달 열기/닫기 및 목록 데이터 로딩

document.addEventListener("DOMContentLoaded", function () {
    // 1) 엘리먼트 캐시
    const fab = document.getElementById("claim-fab");                    // 플로팅 버튼
    const modal = document.getElementById("claim-knowledge-modal");      // 모달 루트
    const closeBtn = document.getElementById("claim-close");             // 닫기 버튼
    const body = document.getElementById("claimBody");                   // 목록 주입 영역

    // 2) 렌더 함수
    function renderItems(items) {
        if (!Array.isArray(items) || items.length === 0) {
            body.innerHTML = "<p>데이터가 없습니다.</p>";
            return;
        }
        body.innerHTML = items.map(item => `
            <div class="claim-item">
                <h4>${item.title || ""}</h4>
                <p>${item.description || ""}</p>
            </div>
        `).join("");
    }

    // 3) 데이터 로드
    async function loadClaimKnowledge() {
        body.innerHTML = "<p>불러오는 중...</p>";
        try {
            const resp = await fetch("/api/claim-knowledge/list/");
            if (!resp.ok) throw new Error("API 호출 실패");
            const data = await resp.json();
            renderItems(data.items);
        } catch (err) {
            body.innerHTML = "<p>서버 오류로 데이터를 불러오지 못했습니다.</p>";
            console.error(err);
        }
    }

    // 4) 열기/닫기
    fab.addEventListener("click", () => {
        modal.style.display = "block";
        loadClaimKnowledge();
    });

    closeBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });

    // 5) ESC 닫기
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal.style.display === "block") {
            modal.style.display = "none";
        }
    });

    // 6) 배경 클릭 닫기
    modal.addEventListener("click", (e) => {
        const isBackdrop = e.target.classList.contains("claim-backdrop");
        if (isBackdrop) modal.style.display = "none";
    });
});
