function handleKeyPress(event){ if(event.key === 'Enter') searchClauses(); }
function setQuery(q){ document.getElementById('searchInput').value = q; searchClauses(); }

async function searchClauses(){
  const query = document.getElementById('searchInput').value.trim();
  if(!query){ alert('검색어를 입력해주세요.'); return; }
  const searchBtn = document.getElementById('searchBtn');
  const loading = document.getElementById('loading');
  const results = document.getElementById('results');
  searchBtn.disabled = true; loading.style.display = 'block'; results.style.display = 'none';
  try{
    const response = await fetch('/insurance-recommendation/',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},
      body: JSON.stringify({query})
    });
    const data = await response.json();
    if(data.success && data.results) displayResults(data.results);
    else displayNoResults();
  }catch(e){
    console.error('검색 오류:', e);
    alert('검색 중 오류가 발생했습니다. 다시 시도해주세요.');
  }finally{
    searchBtn.disabled = false; loading.style.display = 'none';
  }
}

function displayResults(results){
  const resultsList = document.getElementById('resultsList');
  const resultsDiv = document.getElementById('results');
  if(results.length === 0){ displayNoResults(); return; }
  let html = '';
  results.forEach((r, i)=>{
    const score = (r.score * 100).toFixed(1);
    html += `
      <div class="result-item" style="animation-delay:${i*0.1}s">
        <div class="result-header">
          <div class="document-name">${r.document}</div>
          <div class="similarity-score">유사도 ${score}%</div>
        </div>
        <div class="result-text">${r.text}</div>
      </div>`;
  });
  resultsList.innerHTML = html;
  resultsDiv.style.display = 'block';
}
function displayNoResults(){
  const resultsList = document.getElementById('resultsList');
  const resultsDiv = document.getElementById('results');
  resultsList.innerHTML = `<div class="no-results"><h3>검색 결과가 없습니다</h3><p>다른 키워드로 다시 검색해보세요.</p></div>`;
  resultsDiv.style.display = 'block';
}
function getCookie(name){
  let cookieValue = null;
  if(document.cookie && document.cookie !== ''){
    const cookies = document.cookie.split(';');
    for(let i=0;i<cookies.length;i++){
      const cookie = cookies[i].trim();
      if(cookie.substring(0, name.length + 1) === (name + '=')){
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1)); break;
      }
    }
  }
  return cookieValue;
}
