// static/insurance_portal/js/knowhow.js
// 최신 수정 적용 버전: FAB 대응 + 외부 openKnowhow 함수 제공

(() => {
  const BTN_ID = 'weekly-fab';
  const MODAL_ID = 'knowhow-modal';
  const LIST_ID = 'kh-list';
  const DETAIL_ID = 'kh-detail';

  const JSON_URL =
    window.KNOWHOW_JSON_URL || '/static/insurance_portal/json/weekly_articles.json';

  let loaded = false;
  let items = [];

  const esc = (s) =>
    String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

  function filterContent(text) {
    if (!text) return text;
    return text
      .replace(/\*\s*\*\*보험통계\*\*[^*]*(?:\*[^*]*)*?(?=\*\s*\*\*|$)/g, '')
      .replace(/\*\s*\*\*알쓸보험\*\*[^*]*(?:\*[^*]*)*?(?=\*\s*\*\*|$)/g, '')
      .replace(/\*\s*\*\*MY보험\*\*[^*]*(?:\*[^*]*)*?(?=\*\s*\*\*|$)/g, '')
      .replace(/\*\s*\*\*보험소식\*\*[^*]*(?:\*[^*]*)*?(?=\*\s*\*\*|$)/g, '')
      .replace(/\n\s*\n\s*\n/g, '\n\n')
      .trim();
  }

  function renderWeeklyHTML(raw) {
    const parts = [];
    if (raw.main_h4) {
      const filteredH4 = filterContent(raw.main_h4);
      if (filteredH4) parts.push(`<h6 class="kh-subtitle">${esc(filteredH4)}</h6>`);
    }
    if (Array.isArray(raw.main_strongs) && raw.main_strongs.length) {
      const filteredStrongs = raw.main_strongs
        .map(s => filterContent(s))
        .filter(s => s && !/(보험통계|알쓸보험|MY보험|보험소식)/.test(s));
      if (filteredStrongs.length) {
        parts.push('<ul class="kh-strongs">');
        for (const s of filteredStrongs) parts.push(`<li>${esc(s)}</li>`);
        parts.push('</ul>');
      }
    }
    if (Array.isArray(raw.main_ps) && raw.main_ps.length) {
      for (const p of raw.main_ps) {
        const text = filterContent((p ?? '').toString().trim());
        if (text && !/(보험통계|알쓸보험|MY보험|보험소식)/.test(text)) {
          parts.push(`<p>${esc(text)}</p>`);
        }
      }
    }
    if (raw.url) {
      parts.push(
        `<div class="kh-link"><a href="${esc(raw.url)}" target="_blank" rel="noopener">자세히 보기</a></div>`
      );
    }
    return parts.join('');
  }

  function normItem(raw, idx) {
    return {
      id: idx,
      title: raw.title || `항목 ${idx + 1}`,
      category: raw.category || '',
      date: raw.date || '',
      html: renderWeeklyHTML(raw)
    };
  }

  function renderList() {
    const listEl = document.getElementById(LIST_ID);
    listEl.innerHTML = '';
    items.forEach((it, i) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'kh-item';
      btn.setAttribute('role', 'option');
      btn.dataset.idx = i;
      btn.innerHTML = `
        <div class="kh-item-title">${esc(it.title)}</div>
        ${it.category || it.date ? `<div class="kh-item-meta">
          ${it.category ? `<span class="cat">${esc(it.category)}</span>` : ''}
          ${it.date ? `<span class="date">${esc(it.date)}</span>` : ''}
        </div>` : ''}
      `;
      btn.addEventListener('click', () => select(i));
      listEl.appendChild(btn);
    });
  }

  function select(i) {
    const it = items[i];
    document.querySelectorAll(`#${LIST_ID} .kh-item`).forEach((el, idx) => {
      el.classList.toggle('active', idx === i);
    });
    const detailEl = document.getElementById(DETAIL_ID);
    detailEl.innerHTML = `
      <h6 class="kh-title">${esc(it.title)}</h6>
      <div class="kh-meta">
        ${it.category ? `<span class="cat">${esc(it.category)}</span>` : ''}
        ${it.date ? `<span class="date">${esc(it.date)}</span>` : ''}
      </div>
      <div class="kh-content">${it.html || '<em>본문이 없습니다.</em>'}</div>
    `;
  }

  async function loadOnce() {
    if (loaded) return;
    const res = await fetch(JSON_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const arr = Array.isArray(data)
      ? data
      : (data.articles || data.items || data.data || data.list || []);
    items = arr.map(normItem);
    renderList();
    if (items.length) select(0);
    loaded = true;
  }

  function openModal() {
    const modal = document.getElementById(MODAL_ID);
    modal.removeAttribute('hidden');
    requestAnimationFrame(() => { modal.classList.add('show'); });
  }

  function closeModal() {
    const modal = document.getElementById(MODAL_ID);
    modal.classList.remove('show');
    const dlg = modal.querySelector('.kh-dialog');
    const onEnd = (e) => {
      if (e.target !== dlg) return;
      modal.setAttribute('hidden', '');
      dlg.removeEventListener('transitionend', onEnd);
    };
    dlg.addEventListener('transitionend', onEnd);
  }

  document.getElementById(BTN_ID)?.addEventListener('click', async () => {
    await loadOnce();
    openModal();
  });

  document.querySelector('#knowhow-modal .kh-close')?.addEventListener('click', closeModal);
  document.querySelector('#knowhow-modal .kh-backdrop')?.addEventListener('click', closeModal);

  // 외부 FAB 등을 위한 전역 함수 등록
  window.openKnowhow = async () => {
    try {
      await loadOnce();
      openModal();
    } catch (e) {
      console.error('보험상식 모달 열기 실패:', e);
    }
  };
})();
