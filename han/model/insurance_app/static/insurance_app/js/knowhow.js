// 보험상식 모달(JSON 렌더) - weekly_articles.json 전용 필드 지원
(() => {
  const BTN_ID = 'weekly-fab';
  const MODAL_ID = 'knowhowModal';
  const LIST_ID = 'kh-list';
  const DETAIL_ID = 'kh-detail';

  const JSON_URL =
    window.KNOWHOW_JSON_URL || '/static/json/weekly_articles.json';

  let loaded = false;
  let items = [];

  // 간단 escape
  const esc = (s) =>
    String(s ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  // weekly_articles.json 전용 HTML 생성기
  function renderWeeklyHTML(raw){
    const parts = [];

    if (raw.main_h4) {
      parts.push(`<h6 class="kh-subtitle">${esc(raw.main_h4)}</h6>`);
    }
    if (Array.isArray(raw.main_strongs) && raw.main_strongs.length) {
      parts.push('<ul class="kh-strongs">');
      for (const s of raw.main_strongs) parts.push(`<li>${esc(s)}</li>`);
      parts.push('</ul>');
    }
    if (Array.isArray(raw.main_ps) && raw.main_ps.length) {
      for (const p of raw.main_ps) {
        const text = (p ?? '').toString().trim();
        if (text) parts.push(`<p>${esc(text)}</p>`);
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
      // 상세는 HTML로 미리 만들어 둠
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

  document.getElementById(BTN_ID)?.addEventListener('click', async () => {
    await loadOnce();
    new bootstrap.Modal(document.getElementById(MODAL_ID)).show();
  });
})();
