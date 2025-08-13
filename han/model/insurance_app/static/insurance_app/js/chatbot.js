// static/insurance_app/js/chatbot.js
(function(){
  const fab = document.getElementById('chatbot-fab');
  const box = document.getElementById('chatbot-container');
  const closeBtn = document.getElementById('chatbot-close');
  const messagesEl = document.getElementById('chatbot-messages');
  const inputEl = document.getElementById('chatbot-text');
  const sendBtn = document.getElementById('chatbot-send');
  const headerEl = document.getElementById('chatbot-header');
  let isDragging = false, offsetX = 0, offsetY = 0;

  function scrollBottom(){ messagesEl.scrollTop = messagesEl.scrollHeight; }
  function addMsg(role, html){
    const div = document.createElement('div');
    div.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
    div.innerHTML = html;
    messagesEl.appendChild(div);
    scrollBottom();
  }

  fab?.addEventListener('click', () => { box.style.display = 'flex'; });
  closeBtn?.addEventListener('click', () => { box.style.display = 'none'; });

  async function ask(){
    const t = inputEl.value.trim();
    if(!t) return;
    addMsg('user', t);
    inputEl.value = '';

    // 로딩 메시지
    const loading = document.createElement('div');
    loading.className = 'msg bot';
    loading.textContent = '답변 생성 중...';
    messagesEl.appendChild(loading); scrollBottom();

    try{
      const resp = await fetch('/api/chatbot/ask/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ messages: [{ role: 'user', content: t }] })
      });

      const data = await resp.json();

      // 로딩 제거
      messagesEl.removeChild(loading);

      if(!resp.ok || !data.success){
        addMsg('bot', '오류: ' + (data.error || '처리 중 문제가 발생했습니다.'));
        return;
      }

      // 요약 답변 우선 노출
      if (data.representative_answer) {
        // 대표(요약) 답변만 출력 — 링크는 붙이지 않음
        addMsg('bot', data.representative_answer);

      } else if (data.final_answer) {
        // 최종 답변 출력
        addMsg('bot', data.final_answer);

        // ⬇️ 최종 결과에만 KNIA 링크 추가로 출력
        addMsg('bot',
          '<div class="knia-tip">정확한 최종 과실비율은 상황·증거에 따라 달라질 수 있어요. ' +
          '<a href="https://accident.knia.or.kr/myaccident1" target="_blank" rel="noopener">손보협회 과실비율 확인</a>에서 최종 기준을 확인해보세요.</div>'
        );

      } else {
        addMsg('bot', '답변을 생성하지 못했습니다.');
      }

      // 추가 질문 제안
      if(data.need_more && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length){
        const qs = data.clarifying_questions.map(q => `• ${q}`).join('<br>');
        addMsg('bot', qs);
      }

      // 근거 표(선택)
      if(Array.isArray(data.top_matches) && data.top_matches.length){
        const table = `
          <details class="source"><summary>근거 보기</summary>
            <table>
              <thead><tr><th>유사도</th><th>파일</th><th>페이지</th><th>요약</th></tr></thead>
              <tbody>
                ${data.top_matches.map(m=>`
                  <tr>
                    <td>${m.score||''}</td>
                    <td>${m.file||''}</td>
                    <td>${m.page||''}</td>
                    <td>${m.snippet||''}</td>
                  </tr>`).join('')}
              </tbody>
            </table>
          </details>`;
        addMsg('bot', table);
      }
    }catch(e){
      // 로딩 제거 후 에러 출력
      try{ messagesEl.removeChild(loading); }catch(_){}
      console.error(e);
      addMsg('bot', '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    }
  }

  sendBtn?.addEventListener('click', ask);
  inputEl?.addEventListener('keydown', (e)=>{ if(e.key === 'Enter') ask(); });

  // 드래그 이동
  headerEl?.addEventListener('mousedown', (e) => {
    isDragging = true;
    const rect = box.getBoundingClientRect();
    if (!box.style.left && !box.style.top) {
      box.style.left = rect.left + 'px';
      box.style.top = rect.top + 'px';
      box.style.right = '';
      box.style.bottom = '';
    }
    offsetX = e.clientX - rect.left; offsetY = e.clientY - rect.top;
    document.body.style.userSelect = 'none';
  });
  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    let x = e.clientX - offsetX, y = e.clientY - offsetY;
    const maxX = window.innerWidth - box.offsetWidth, maxY = window.innerHeight - box.offsetHeight;
    if (x < 0) x = 0; if (y < 0) y = 0;
    if (x > maxX) x = maxX; if (y > maxY) y = maxY;
    box.style.left = x + 'px'; box.style.top = y + 'px';
  });
  document.addEventListener('mouseup', () => { if (isDragging) { document.body.style.userSelect = ''; } isDragging = false; });

  // 쿠키에서 CSRF 토큰 얻기
  function getCookie(name){
    const m = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }

  // 최초 안내 메시지
  addMsg('bot','사고 상황을 입력하면 필요한 정보를 단계적으로 물어보고 안내합니다.');
})();
