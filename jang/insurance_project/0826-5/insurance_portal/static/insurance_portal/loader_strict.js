/* Aggressive bootstrap for 0826-5 portal bundle */
(function () {
  const CFG = {
    bases: [
      "/static/insurance_portal/",
      "/static/insurance_portal/css/",
      "/static/insurance_portal/js/",
      "/0826-5/insurance_portal/static/insurance_portal/",
      "/0826-5/insurance_portal/static/insurance_portal/css/",
      "/0826-5/insurance_portal/static/insurance_portal/js/",
    ],
    css: [
      "portal.css","menu.css","radial-menu.css","toggle.css","floating-menu.css",
      "index.css","main.css","styles.css","style.css","bundle.css","app.css"
    ],
    js: [
      "portal.js","menu.js","radial-menu.js","toggle.js","floating-menu.js",
      "index.js","main.js","app.js","bundle.js","bundle.min.js","ui.js","portal.min.js"
    ],
    // 수동 오버라이드: window.__PORTAL_ENTRY__ = "IPortal.mount"
    //                 window.__PORTAL_ARGS__  = ["#portal-root", (window.PORTAL_MENU||window.IPORTAL||null)]
  };

  const loaded = new Set();
  const log = (...a)=>console.log("[portal-loader]", ...a);
  const warn = (...a)=>console.warn("[portal-loader]", ...a);

  function probe(url) {
    return fetch(url, { method:"GET", credentials:"same-origin" })
      .then(r=>{ if(!r.ok) throw new Error(String(r.status)); return url; });
  }

  function loadCSS(list) {
    const tasks = [];
    for (const nm of list) for (const b of CFG.bases) {
      const u = (b.endsWith("/")?b:b+"/")+nm;
      if (loaded.has(u)) continue;
      tasks.push(probe(u).then(ok=>{
        loaded.add(ok);
        const l=document.createElement("link");
        l.rel="stylesheet"; l.href=ok+"?v=4";
        document.head.appendChild(l);
        log("CSS", ok);
      }).catch(()=>{}));
    }
    return Promise.all(tasks);
  }

  function loadJS(list) {
    const urls=[];
    for (const nm of list) for (const b of CFG.bases) {
      const u=(b.endsWith("/")?b:b+"/")+nm;
      if (!loaded.has(u)) urls.push(u);
    }
    return urls.reduce((p,u)=>p.then(()=>probe(u).then(ok=>new Promise(res=>{
      loaded.add(ok);
      const s=document.createElement("script");
      s.src=ok+"?v=4";
      s.onload=()=>{ log("JS", ok); res(); };
      s.onerror=()=>{ warn("JS fail", ok); res(); };
      document.head.appendChild(s);
    })).catch(()=>Promise.resolve())), Promise.resolve());
  }

  function ensureRoot(){
    if (!document.getElementById("portal-root")){
      const r=document.createElement("div");
      r.id="portal-root";
      document.body.appendChild(r);
    }
  }

  function discover(win){
    const out=[];
    const names=Object.getOwnPropertyNames(win);
    const funHit=(n)=>/(init|render|mount|create)/i.test(n) && /(portal|menu|toggle|radial)/i.test(n);
    const objHit=(n)=>/(portal|menu|toggle|radial)/i.test(n);

    for (const n of names){
      let v; try{ v=win[n]; }catch{ continue; }
      if (typeof v==="function" && funHit(n)) out.push({kind:"fn", owner:win, name:n, fn:v});
    }
    for (const n of names){
      let o; try{ o=win[n]; }catch{ continue; }
      if (!o || typeof o!=="object") continue;
      let subs=[]; try{ subs=Object.getOwnPropertyNames(o); }catch{}
      for (const m of subs){
        let f; try{ f=o[m]; }catch{ continue; }
        if (typeof f==="function" && (funHit(m) || objHit(n))){
          out.push({kind:"method", owner:o, ownerName:n, name:m, fn:f});
        }
      }
    }
    // 후보 가중치: 이름에 'portal' 포함 > 'menu' 포함 > 그 외
    out.sort((a,b)=>{
      const A=(a.ownerName?`${a.ownerName}.`:"")+a.name;
      const B=(b.ownerName?`${b.ownerName}.`:"")+b.name;
      const score=(s)=> (/(portal)/i.test(s)?3:/(menu|toggle|radial)/i.test(s)?2:1) + (/(init|mount|render|create)/i.test(s)?1:0);
      return score(B)-score(A);
    });
    return out;
  }

  async function tryCall(fn, thisArg, rootSel, cfg){
    const rootEl=document.querySelector(rootSel);
    const signatures=[
      [rootSel, cfg],
      [{root:rootSel, config:cfg}],
      [rootEl, cfg],
      [cfg],
      []
    ];
    for (const args of signatures){
      try{
        const before=rootEl?rootEl.childElementCount:-1;
        const ret=fn.apply(thisArg, args);
        if (ret!==undefined) return {ok:true, args};
        if (before>=0){
          await new Promise(r=>setTimeout(r, 120));
          const after=rootEl.childElementCount;
          if (after>before) return {ok:true, args};
        }
      }catch(e){ /* 다음 시그니처 계속 */ }
    }
    return {ok:false};
  }

  function fallbackButton(){
    if (document.getElementById("ip-fallback")) return;
    const btn=document.createElement("button");
    btn.id="ip-fallback";
    btn.type="button";
    btn.textContent="≡";
    btn.style.cssText="position:fixed;right:18px;bottom:22px;width:56px;height:56px;border-radius:50%;border:0;background:#4a6cff;color:#fff;font-size:28px;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:9999;cursor:pointer";
    btn.addEventListener("click",()=>alert("포털 초기화 함수를 찾지 못했습니다. loader_strict.js에 __PORTAL_ENTRY__ 힌트를 지정해 주세요."));
    document.body.appendChild(btn);
  }

  async function bootstrap(){
    ensureRoot();
    const g=window;
    const cfg = g.PORTAL_MENU || g.IPORTAL || null;

    // 수동 오버라이드가 있으면 우선
    if (typeof g.__PORTAL_ENTRY__==="string"){
      try{
        const path=g.__PORTAL_ENTRY__.split(".");
        let ctx=g, fnName=path.pop();
        for (const p of path){ ctx=ctx[p]; }
        if (ctx && typeof ctx[fnName]==="function"){
          const args=Array.isArray(g.__PORTAL_ARGS__)? g.__PORTAL_ARGS__ : ["#portal-root", cfg];
          const r=await tryCall(ctx[fnName], ctx, "#portal-root", cfg);
          if (r.ok){ log("initialized via manual hint:", g.__PORTAL_ENTRY__, "args=", r.args); return; }
        }
      }catch(e){ warn("manual hint failed:", e); }
    }

    // 자동 탐지
    const cands=discover(g);
    log("candidates:", cands.map(c=>(c.ownerName?`${c.ownerName}.`:"")+c.name));
    g.__PORTAL_DEBUG__ = ()=>({
      candidates: cands.map(c=>(c.ownerName?`${c.ownerName}.`:"")+c.name),
      haveRoot: !!document.getElementById("portal-root"),
      loaded: Array.from(loaded),
    });

    for (const c of cands){
      const name=(c.ownerName?`${c.ownerName}.`:"")+c.name;
      const r=await tryCall(c.fn, c.owner, "#portal-root", cfg);
      if (r.ok){ log("initialized via", name, "args=", r.args); document.body.setAttribute("data-portal-mounted","1"); return; }
      else { warn("failed:", name); }
    }

    warn("no initializer worked; showing fallback");
    fallbackButton();
  }

  document.addEventListener("DOMContentLoaded", ()=>{
    loadCSS(CFG.css)
      .then(()=>loadJS(CFG.js))
      .then(()=>setTimeout(bootstrap, 60))
      .catch(()=>setTimeout(bootstrap, 60));
  });
})();
