// insurance_app/static/insurance_portal/loader_strict.js
// ✅ 원본(0826-5/insurance_portal/static/insurance_portal)의 CSS/JS만 "로드"
// ✅ 어떤 메뉴 구성도 주입 안 함(원본 그대로)
// ✅ ESM(type="module") 가능성까지 고려해 로드

(function(){
  const ROOT = "/static/insurance_portal/";
  const CSS_CANDIDATES = [
    ROOT + "css/portal.css",          // ✓ 로그에 200 찍히던 경로
  ];
  const JS_CANDIDATES = [
    ROOT + "js/portal.js",            // ✓ 로그에 200 찍히던 경로
  ];

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

  function injectJS(src, asModule=false){
    return new Promise((resolve,reject)=>{
      const s = document.createElement("script");
      if(asModule) s.type = "module";
      s.src = src;
      s.async = true;
      s.onload = ()=>resolve({src, asModule});
      s.onerror = ()=>reject(new Error("JS load fail: "+src+(asModule?" (module)":"")));
      document.head.appendChild(s);
    });
  }

  async function firstOK(urls, loader){
    for(const u of urls){
      try{ await loader(u); return u; }catch(e){}
    }
    return null;
  }

  function tryInitNoArg(){
    // 원본이 제공할 법한 초기화 포인트를 "인자 없이" 호출
    const c = (fn)=>{ try{ return fn(), true; }catch(_){ return false; } };
    if (window.Portal?.init && c(window.Portal.init)) return true;
    if (window.InsurancePortal?.init && c(window.InsurancePortal.init)) return true;
    if (window.PortalMenu?.mount && c(window.PortalMenu.mount)) return true;
    if (window.RadialMenu?.mount && c(window.RadialMenu.mount)) return true;
    if (typeof window.initPortal === "function" && c(window.initPortal)) return true;
    if (typeof window.initMenu === "function" && c(window.initMenu)) return true;
    if (typeof window.createPortalMenu === "function" && c(window.createPortalMenu)) return true;
    return false; // 엔트리포인트가 없어도, 원본이 자동 마운트면 이대로 OK
  }

  (async function boot(){
    try{
      // CSS 1개만(404 소음 제거)
      await firstOK(CSS_CANDIDATES, injectCSS);

      // JS: 먼저 module 시도 → 실패 시 nomodule 시도
      let loaded = null;
      try{
        for(const u of JS_CANDIDATES){
          await injectJS(u, true);  // type="module"
          loaded = {u, asModule:true};
          break;
        }
      }catch(e){}
      if(!loaded){
        for(const u of JS_CANDIDATES){
          await injectJS(u, false); // 일반 스크립트
          loaded = {u, asModule:false};
          break;
        }
      }

      // 인자 없이 초기화만 시도(원본 그대로)
      let ok = tryInitNoArg();
      if(!ok){
        // 혹시 늦게 전역 노출되면 한 번 더
        setTimeout(()=>tryInitNoArg(), 600);
      }
    }catch(e){
      console.error("[portal:strict] load failed:", e);
    }
  })();
})();
