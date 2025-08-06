import os
from dotenv import load_dotenv
from pinecone import Pinecone
from docx import Document
from openai import OpenAI
import unicodedata
from tqdm import tqdm
import requests
import time

# 환경변수
load_dotenv()
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
PINECONE_API_KEY_MY = os.getenv("PINECONE_API_KEY_MY")
INDEX_NAME = "solar-embedding-index"  # Pinecone에서 만든 1024차원 인덱스명
DOCX_PATH = "accident_ratio_text_markdown.docx"  # 분석할 docx 파일명

# 임베딩 클라이언트 (Upstage Solar)
def get_upstage_embedding(texts):
    url = "https://api.upstage.ai/v1/solar/embeddings"
    headers = {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "embedding-query",
        "input": texts
    }
    
    max_retries = 5
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('retry-after', 60))
            print(f"⏳ Rate Limit 도달. {retry_after + 5}초 대기 중... (시도 {attempt+1}/{max_retries})")
            time.sleep(retry_after + 5)
            continue
        elif response.ok:
            return response.json()["data"]
        else:
            print(f"❌ 오류: {response.text}")
            time.sleep(10)
    
    print("❌ 최대 재시도 횟수 초과")
    return None

# 벡터ID 영문변환
def to_ascii(s):
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")

# docx -> 전체 텍스트
def extract_full_text(docx_path):
    doc = Document(docx_path)
    all_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            all_text.append(text)
    return " ".join(all_text)

# 500토큰, 100토큰 겹침 슬라이딩 청크
def chunk_text(text, chunk_size=500, overlap=100):
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = " ".join(tokens[i:i+chunk_size])
        if chunk:
            chunks.append(chunk)
        if i + chunk_size >= len(tokens):
            break
        i += (chunk_size - overlap)
    return chunks

if __name__ == "__main__":
    # 1. 텍스트 청크화
    full_text = extract_full_text(DOCX_PATH)
    chunks = chunk_text(full_text, chunk_size=500, overlap=100)
    print(f"총 {len(chunks)}개 청크 생성")

    # 샘플 임베딩 차원 직접 출력 (청크가 있을 때만!)
    if len(chunks) > 0:
        print("샘플 벡터 차원 확인:", len(get_upstage_embedding([chunks[0]])[0]["embedding"]))

# 2. Pinecone Index 연결 및 기존 데이터 확인
    pc = Pinecone(api_key=PINECONE_API_KEY_MY)
    index = pc.Index(INDEX_NAME)
    
    # 기존 데이터 확인
    stats = index.describe_index_stats()
    current_count = stats['total_vector_count']
    print(f"현재 업로드된 벡터 수: {current_count}")
    
    batch_size = 8  # 16 → 8로 줄임
    
    # 시작점 계산
    if current_count > 0:
        start_index = current_count
        print(f"청크 {start_index}부터 재시작...")
    else:
        start_index = 0
        print("처음부터 시작...")

    # 3. 임베딩 & 업로드 (이어서 진행)
    for i in tqdm(range(start_index, len(chunks), batch_size)):
        batch = chunks[i:i+batch_size]
        
        response_data = get_upstage_embedding(batch)
        if response_data is None:
            print(f"배치 {i//batch_size + 1} 실패, 건너뛰기")
            continue
        
        print("임베딩 벡터 차원:", len(response_data[0]["embedding"]))   

        embeddings = [item["embedding"] for item in response_data]
        vectors = []
        for j, (text, vec) in enumerate(zip(batch, embeddings)):
            vector_id = f"chunk_{i+j}_{to_ascii(text)[:40]}"
            meta = {
                "text": text,
                "chunk_idx": i+j
            }
            vectors.append({
                "id": vector_id,
                "values": [float(x) for x in vec],
                "metadata": meta
            })
        index.upsert(vectors=vectors)
        
        # 배치 간 대기 시간 추가
        if i + batch_size < len(chunks):
            print("⏳ Rate Limit 방지를 위해 15초 대기...")
            time.sleep(15)
            
    print("모든 청크 임베딩 및 Pinecone 업로드 완료!")