// insurance_portal/portal.js
(function(){
  const cfg = (window.PORTAL_MENU || {});
  const brand = cfg.brand || 'Insurance Portal';
  const pos   = (cfg.position === 'left') ? 'left' : 'right';
  const items = Array.isArray(cfg.items) ? cfg.items : [];

  function el(tag, attrs={}, children=[]){
    const e = document.createElement(tag);
    Object.entries(attrs||{}).forEach(([k,v])=>{
      if (k === 'class') e.className = v;
      else if (k === 'text') e.textContent = v;
      else e.setAttribute(k, v);
    });
    (children||[]).forEach(c => e.appendChild(c));
    return e;
  }

  function buildPanel(){
    // Overlay
    const overlay = el('div', { id: 'ip-overlay', 'aria-hidden': 'true' });

    // Panel
    const panel = el('aside', { id: 'ip-panel' });
    panel.classList.add(pos);

    // Head
    const head = el('div', { id: 'ip-head' }, [
      el('div', { id: 'ip-title', text: brand }),
      el('button', { id: 'ip-close', 'aria-label': '닫기', title:'닫기' }, [ el('span', { text: '×' }) ])
    ]);

    // List
    const list = el('div', { id: 'ip-list' });
    (items||[]).forEach((it)=>{
      if (!it || !it.title || !it.url) return;
      const a = el('a', { href: it.url });
      a.innerHTML = `
        <span class="ip-icon">≡</span>
        <span>
          <div style="font-weight:800">${it.title}</div>
          ${it.desc ? `<div class="ip-sub">${it.desc}</div>` : ``}
        </span>
      `;
      const item = el('div', { class: 'ip-item' }, [a]);
      list.appendChild(item);
    });

    panel.appendChild(head);
    panel.appendChild(list);

    // FAB
    const fab = el('button', { id:'ip-fab', 'aria-label': '메뉴 열기', title:'메뉴' }, [ el('span', { text: '≡' }) ]);

    // Toggle handlers
    function open(){
      overlay.classList.add('open');
      panel.classList.add('open');
      overlay.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    }
    function close(){
      overlay.classList.remove('open');
      panel.classList.remove('open');
      overlay.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }

    fab.addEventListener('click', open);
    overlay.addEventListener('click', close);
    panel.querySelector('#ip-close').addEventListener('click', close);
    document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape') close(); });

    // Mount
    document.body.appendChild(overlay);
    document.body.appendChild(panel);
    document.body.appendChild(fab);
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', buildPanel);
  } else {
    buildPanel();
  }
})();
