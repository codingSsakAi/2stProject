# purge_all_vectors.py
import os
import dotenv
from pinecone import Pinecone

dotenv.load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not PINECONE_API_KEY or not INDEX_NAME:
    raise SystemExit("PINECONE_API_KEY 또는 PINECONE_INDEX_NAME 환경변수가 없습니다.")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# 현재 인덱스의 네임스페이스 목록 조회
stats = index.describe_index_stats()
namespaces = list((stats.get("namespaces") or {}).keys())
if not namespaces:
    namespaces = [None]  # 네임스페이스가 없으면 기본 네임스페이스 하나만 대상으로

print(f"[INFO] 대상 인덱스: {INDEX_NAME}")
print(f"[INFO] 발견된 네임스페이스: {namespaces}")

# 네임스페이스별 전체 삭제
for ns in namespaces:
    print(f"[INFO] 삭제 중... namespace={ns}")
    index.delete(delete_all=True, namespace=ns)

# 확인
stats_after = index.describe_index_stats()
print("[INFO] 삭제 완료. 현재 통계:", stats_after)
