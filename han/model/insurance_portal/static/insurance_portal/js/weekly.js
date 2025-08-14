// insurance_portal/static/insurance_portal/js/weekly.js
// 기능: 보험상식(주간 정보) 모달 열기/닫기 및 목록 데이터 로딩

document.addEventListener("DOMContentLoaded", function () {
    // 1) 엘리먼트 캐시
    const fab = document.getElementById("weekly-fab");           // 플로팅 버튼
    const modal = document.getElementById("weekly-modal");       // 모달 루트
    const closeBtn = document.getElementById("weekly-close");    // 닫기 버튼
    const body = document.getElementById("weeklyBody");          // 목록 주입 영역

    // 2) 렌더 함수: 아이템 리스트를 모달 본문에 그립니다.
    function renderItems(items) {
        if (!Array.isArray(items) || items.length === 0) {
            body.innerHTML = "<p>데이터가 없습니다.</p>";
            return;
        }
        body.innerHTML = items.map(item => `
            <div class="weekly-item">
                <h4>${item.title || ""}</h4>
                <p>${item.content || ""}</p>
                ${item.date ? `<small>${item.date}</small>` : ""}
            </div>
        `).join("");
    }

    // 3) 데이터 로드 함수: 서버 API에서 JSON을 가져옵니다.
    async function loadWeekly() {
        body.innerHTML = "<p>불러오는 중...</p>";
        try {
            const resp = await fetch("/api/weekly/list/");
            if (!resp.ok) throw new Error("API 호출 실패");
            const data = await resp.json();
            renderItems(data.items);
        } catch (err) {
            body.innerHTML = "<p>서버 오류로 데이터를 불러오지 못했습니다.</p>";
            console.error(err);
        }
    }

    // 4) 열기/닫기 이벤트
    fab.addEventListener("click", () => {
        modal.style.display = "block";
        loadWeekly(); // 열릴 때마다 최신 데이터 로드
    });

    closeBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });

    // 5) ESC 키로 닫기 (접근성 보완)
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal.style.display === "block") {
            modal.style.display = "none";
        }
    });

    // 6) 모달 바깥 클릭 시 닫기
    modal.addEventListener("click", (e) => {
        const isBackdrop = e.target.classList.contains("weekly-backdrop");
        if (isBackdrop) modal.style.display = "none";
    });
});
