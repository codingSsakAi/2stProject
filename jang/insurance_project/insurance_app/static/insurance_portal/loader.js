// insurance_app/static/insurance_portal/loader.js
(function(){
  // ---- 경로 후보(0826-5 매핑된 /static/insurance_portal/ 아래에서 탐색) ----
  const bases = [ "/static/insurance_portal/" ];
  const prefixes = ["", "js/", "css/", "dist/", "build/", "assets/", "static/"];

  const cssNames = [
    "portal.css","menu.css","radial-menu.css","toggle.css","floating-menu.css",
    "index.css","main.css","styles.css","style.css","bundle.css","app.css"
  ];
  const jsNames = [
    "portal.js","menu.js","radial-menu.js","toggle.js","floating-menu.js",
    "index.js","main.js","app.js","bundle.js","bundle.min.js","ui.js","portal.min.js"
  ];

  function combos(names){
    const urls = [];
    for(const b of bases){
      for(const p of prefixes){
        for(const n of names){
          urls.push(b + p + n);
        }
      }
    }
    return urls;
  }

  async function findFirstExisting(candidates){
    for(const url of candidates){
      try{
        const res = await fetch(url, {method:"GET", cache:"no-store"});
        if(res.ok) return url;
      }catch(e){}
    }
    return null;
  }

  function injectCSS(href){
    return new Promise((resolve,reject)=>{
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.onload = ()=>resolve(href);
      link.onerror = ()=>reject(new Error("CSS load fail: "+href));
      document.head.appendChild(link);
    });
  }

  function injectJS(src){
    return new Promise((resolve,reject)=>{
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = ()=>resolve(src);
      s.onerror = ()=>reject(new Error("JS load fail: "+src));
      document.head.appendChild(s);
    });
  }

  // ---- 루트 엘리먼트 확보(원본이 필요로 할 수 있음) ----
  function ensureRoot(){
    let root = document.querySelector("#portal-root, [data-portal-root]");
    if(!root){
      root = document.createElement("div");
      root.id = "portal-root";
      document.body.appendChild(root);
    }
    return root;
  }

  // ---- 설정 객체 확보: window.PORTAL_MENU 또는 호환 이름 ----
  function getConfig(){
    return window.PORTAL_MENU
        || window.InsurancePortalConfig
        || window.portalConfig
        || null;
  }

  // ---- 원본 초기화 함수/객체 자동 탐색 & 호출 ----
  function tryInitPortal(){
    const cfg = getConfig() || {
      // 최소 기본값(혹시 전역 설정이 전혀 없다면 이걸로라도 띄움)
      brand: "보험 포털",
      position: "right",
      items: [
        { title: "🏠 홈", url: "/" }
      ]
    };

    // 1) 네임스페이스 형태
    if (window.Portal && typeof window.Portal.init === "function"){
      window.Portal.init(cfg);
      return true;
    }
    if (window.InsurancePortal && typeof window.InsurancePortal.init === "function"){
      window.InsurancePortal.init(cfg);
      return true;
    }
    if (window.PortalMenu && typeof window.PortalMenu.mount === "function"){
      window.PortalMenu.mount(cfg);
      return true;
    }
    if (window.RadialMenu && typeof window.RadialMenu.mount === "function"){
      window.RadialMenu.mount(cfg);
      return true;
    }

    // 2) 전역 함수형
    if (typeof window.initPortal === "function"){ window.initPortal(cfg); return true; }
    if (typeof window.initMenu === "function"){ window.initMenu(cfg); return true; }
    if (typeof window.createPortalMenu === "function"){ window.createPortalMenu(cfg); return true; }

    // 3) 원본이 DOM만 기대한다면, 루트만 만들어 줌(원본 JS가 DOM을 스캔하여 그린다면 이것만으로 충분)
    ensureRoot();
    return false;
  }

  // ---- 부트스트랩 ----
  (async function boot(){
    try{
      const cssURL = await findFirstExisting(combos(cssNames));
      if(cssURL) await injectCSS(cssURL);

      const jsURL  = await findFirstExisting(combos(jsNames));
      if(jsURL) await injectJS(jsURL);

      // 초기화 시도: 즉시 & 1초 지연 재시도(원본이 onload 시점 의존 시)
      let ok = tryInitPortal();
      if(!ok){
        setTimeout(()=>{
          ok = tryInitPortal();
          if(!ok){
            console.warn("[portal] 초기화 함수를 찾지 못했습니다. 원본 JS의 init 진입점을 확인하세요.");
          }
        }, 1000);
      }
    }catch(e){
      console.error("[portal] 로딩 실패:", e);
    }
  })();
})();
