from pinecone import Pinecone, ServerlessSpec
import os

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

# 환경변수로 인덱스 이름 관리
INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "insurance-clauses-second")

def create_index():
    existing_indexes = [i["name"] for i in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=INDEX_NAME,
            dimension=1024,  # 업로드 모델과 일치하도록 768로 변경
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws',
                region=os.environ.get("PINECONE_REGION", "us-east-1")
            )
        )

def get_index():
    api_key = os.getenv('PINECONE_API_KEY', '')
    index_name = os.getenv('PINECONE_INDEX_NAME', '')
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY가 설정되어 있지 않습니다.")
    if not index_name:
        raise RuntimeError("PINECONE_INDEX_NAME가 설정되어 있지 않습니다.")
    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name)