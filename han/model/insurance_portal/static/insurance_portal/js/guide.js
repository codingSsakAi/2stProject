// insurance_portal/static/insurance_portal/js/guide.js
// 기능: 사고 처리 가이드 모달 UI 제어 및 데이터 로드

document.addEventListener("DOMContentLoaded", function () {
    const fab = document.getElementById("guide-fab");
    const modal = document.getElementById("guide-modal");
    const closeBtn = document.getElementById("guide-close");

    const tabs = document.querySelectorAll(".tab-btn");
    const panels = {
        basic: document.getElementById("panel-basic"),
        evidence: document.getElementById("panel-evidence"),
        various: document.getElementById("panel-various"),
    };

    // 이미지 파일명 매핑(실제 파일명으로 변경)
    const baseImg = "/static/insurance_portal/img/";
    const stepImages = ["01.png","02.png","03.png","04.png","05.png","06.png"];

    // 탭 전환 이벤트
    tabs.forEach(btn => {
        btn.addEventListener("click", () => {
            tabs.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const tab = btn.dataset.tab;
            Object.keys(panels).forEach(k => {
                panels[k].classList.toggle("active", k === tab);
            });
        });
    });

    // API 호출
    async function fetchGuideData() {
        const resp = await fetch("/api/guide/steps/");
        if (!resp.ok) throw new Error("API 호출 실패");
        return await resp.json();
    }

    // 기본 6단계 렌더링
    function renderBasicSteps(basic) {
        const grid = document.getElementById("guideGrid");
        if (!Array.isArray(basic) || basic.length === 0) {
            grid.innerHTML = "<p>기본 단계 데이터가 없습니다.</p>";
            return;
        }
        grid.innerHTML = basic.map((s, i) => {
            const num = s.step || String(i + 1).padStart(2, "0");
            const img = stepImages[i] ? (baseImg + stepImages[i]) : (baseImg + "guide_icon.png");
            const details = Array.isArray(s.details) ? s.details.map(d => `<li>${d}</li>`).join("") : "";
            return `
                <div class="guide-card">
                    <div class="thumb">
                        <img src="${img}" alt="사고 처리 ${num}">
                        <span class="badge">${num}</span>
                    </div>
                    <div class="body">
                        <div class="title">${s.title || ""}</div>
                        ${s.subtitle ? `<div class="subtitle">${s.subtitle}</div>` : ""}
                        <div class="desc">${details ? `<ul>${details}</ul>` : ""}</div>
                    </div>
                </div>
            `;
        }).join("");
    }

    // 증거 확보 렌더링
    function renderEvidence(evidence) {
        const titleEl = document.getElementById("evidence-title");
        const listEl = document.getElementById("evidence-list");
        if (!evidence || !Array.isArray(evidence.items)) {
            titleEl.textContent = "증거 확보";
            listEl.innerHTML = "<li>데이터가 없습니다.</li>";
            return;
        }
        titleEl.textContent = evidence.title || "증거 확보";
        listEl.innerHTML = evidence.items.map(t => `<li>${t}</li>`).join("");
    }

    // 상황별 절차 렌더링
    function renderVarious(various) {
        const pills = document.getElementById("various-pills");
        const body = document.getElementById("various-body");
        if (!various || !Array.isArray(various.섹션)) {
            pills.innerHTML = "";
            body.innerHTML = "<p>상황별 절차 데이터가 없습니다.</p>";
            return;
        }

        const categories = [
            { key: "경찰서", label: "경찰서" },
            { key: "보험회사", label: "보험회사" },
            { key: "피해물", label: "피해물(차량)" },
            { key: "피해자", label: "피해자" },
        ];

        pills.innerHTML = categories.map((c, i) =>
            `<span class="pill ${i === 0 ? 'active' : ''}" data-key="${c.key}">${c.label}</span>`
        ).join("");

        function renderCategory(key) {
            if (key === "경찰서") {
                const sections = various.섹션 || [];
                body.innerHTML = sections.map(sec => {
                    const items = (sec.절차 || []).map(it => {
                        const details = Array.isArray(it.details) ? it.details.map(d => `<li>${d}</li>`).join("") : "";
                        const note = Array.isArray(it.비고) ? `<div class="note">비고: ${it.비고.join(", ")}</div>` : "";
                        return `
                            <div class="flow-item">
                                <div><span class="step">${it.step || ""}</span>${it.title || ""}</div>
                                ${details ? `<ul>${details}</ul>` : ""}
                                ${note}
                            </div>
                        `;
                    }).join("");
                    return `
                        <div class="section-block">
                            <h4>${sec.제목 || ""}</h4>
                            <div class="flow">${items}</div>
                        </div>
                    `;
                }).join("");
                return;
            }

            const pack = various[key];
            if (!pack || !Array.isArray(pack.절차)) {
                body.innerHTML = "<p>데이터가 없습니다.</p>";
                return;
            }
            body.innerHTML = `
                <div class="section-block">
                    <h4>${key}</h4>
                    <div class="flow">
                        ${pack.절차.map(it => {
                            const details = Array.isArray(it.details) ? it.details.map(d => `<li>${d}</li>`).join("") : "";
                            return `
                                <div class="flow-item">
                                    <div><span class="step">${it.step || ""}</span>${it.title || ""}</div>
                                    ${details ? `<ul>${details}</ul>` : ""}
                                </div>
                            `;
                        }).join("")}
                    </div>
                </div>
            `;
        }

        renderCategory("경찰서");

        pills.querySelectorAll(".pill").forEach(p => {
            p.addEventListener("click", () => {
                pills.querySelectorAll(".pill").forEach(x => x.classList.remove("active"));
                p.classList.add("active");
                renderCategory(p.dataset.key);
            });
        });
    }

    // 모달 열기
    fab.addEventListener("click", async () => {
        modal.style.display = "block";
        try {
            const data = await fetchGuideData();
            renderBasicSteps(data.basic);
            renderEvidence(data.evidence);
            renderVarious(data.various);
        } catch (e) {
            document.getElementById("guideGrid").innerHTML = "<p>데이터를 불러오지 못했습니다.</p>";
            console.error(e);
        }
    });

    // 닫기
    closeBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });

    // ESC 닫기
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal.style.display === "block") {
            modal.style.display = "none";
        }
    });
});
