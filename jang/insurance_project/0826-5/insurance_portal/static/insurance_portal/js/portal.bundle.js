/* ============================================================================
 * insurance_portal / portal.bundle.js
 * - 전역 번들 진입점
 * - #enable-portal 마커가 있는 페이지에서 '사이드 토글' UI 활성
 * - window.Portal.{open,close,toggle} 공개
 * ========================================================================== */

(function () {
  "use strict";

  // 항상 전역 API 스텁 제공(마커가 없어도 호출 에러 방지)
  if (!window.Portal) {
    window.Portal = { open: function(){}, close: function(){}, toggle: function(){} };
  }

  // 중복 주입 방지
  if (window.__PORTAL_BUNDLE_MOUNTED__) return;
  window.__PORTAL_BUNDLE_MOUNTED__ = true;

  const root = document.getElementById("portal-root");
  if (!root) return;

  // 홈/특정 페이지만 활성화: 마커 감지
  const marker = document.getElementById("enable-portal");
  if (!marker) {
    // 마커 없으면 UI를 만들지 않음(전역 API는 스텁 그대로 유지)
    return;
  }
  const mode = (marker.getAttribute("data-portal-mode") || "toggle").toLowerCase();

  const log = (...args) => { try { console.debug("[portal]", ...args); } catch(_) {} };

  const el = (tag, attrs = {}, children = []) => {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (v === null || v === undefined) return;
      if (k === "class") node.className = v;
      else if (k.startsWith("data-")) node.setAttribute(k, v);
      else if (k === "text") node.textContent = String(v);
      else node.setAttribute(k, v);
    });
    for (const c of children) node.appendChild(c);
    return node;
  };

  const state = {
    version: root.getAttribute("data-version") || "v1",
    shell: null,
    toggleBtn: null,
    mounted: false,
    open: false,
  };

  function createShell() {
    const header = el("div", { class: "portal-header" }, [
      el("div", { text: "보험 포털" }),
      el("button", { class: "btn", type: "button", "aria-label": "닫기", id: "portal-close-btn" }, [
        el("span", { text: "닫기" })
      ]),
    ]);

    const content = el("div", { class: "portal-content", id: "portal-content" }, [
      el("div", { text: "포털이 정상 주입되었습니다. 필요한 위젯이 여기에 장착됩니다." })
    ]);

    const shell = el("section", { class: "portal-shell", role: "dialog", "aria-modal": "false", hidden: "" }, [
      header, content
    ]);

    shell.addEventListener("click", (e) => {
      const t = e.target;
      if (t && t.id === "portal-close-btn") hideShell();
    });

    mountWidgets(content);
    return shell;
  }

  function createToggle() {
    const btn = el("button", { class: "portal-toggle", type: "button", id: "portal-toggle-btn" }, [
      el("span", { text: "포털" })
    ]);
    btn.addEventListener("click", () => {
      if (state.open) hideShell(); else showShell();
    });
    return btn;
  }

  function showShell() {
    if (!state.shell) return;
    state.shell.removeAttribute("hidden");
    state.open = true;
  }
  function hideShell() {
    if (!state.shell) return;
    state.shell.setAttribute("hidden", "");
    state.open = false;
  }

  function mountWidgets(container) {
    try {
      if (window.ClaimKnowledge && typeof window.ClaimKnowledge.mount === "function") {
        const wrap = el("div", { id: "claim-knowledge-host" });
        container.appendChild(wrap);
        window.ClaimKnowledge.mount("#claim-knowledge-host");
        log("ClaimKnowledge mounted");
      }
      if (window.InsureChatbot && typeof window.InsureChatbot.mount === "function") {
        const wrap = el("div", { id: "insure-chatbot-host" });
        container.appendChild(wrap);
        window.InsureChatbot.mount("#insure-chatbot-host");
        log("InsureChatbot mounted");
      }
    } catch (err) {
      log("widget mount error:", err && err.message ? err.message : err);
    }
  }

  function init() {
    if (state.mounted) return;

    state.shell = createShell();
    root.appendChild(state.shell);

    if (mode === "toggle") {
      state.toggleBtn = createToggle();
      root.appendChild(state.toggleBtn);
    } else if (mode === "auto") {
      showShell();
    }

    // 전역 API 실제 구현 바인딩
    window.Portal.open = function() { if (!state.mounted) init(); showShell(); };
    window.Portal.close = function() { hideShell(); };
    window.Portal.toggle = function() { if (!state.mounted) init(); state.open ? hideShell() : showShell(); };

    state.mounted = true;
    log("mounted", state.version, "mode:", mode);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
