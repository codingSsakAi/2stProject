from pinecone import Pinecone, ServerlessSpec
import os

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

# 환경변수로 인덱스 이름 관리
INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "insurance-clauses-new")

def create_index():
    existing_indexes = [i["name"] for i in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=INDEX_NAME,
            dimension=768,  # 업로드 모델과 일치하도록 768로 변경
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws',
                region=os.environ.get("PINECONE_REGION", "us-east-1")
            )
        )

def get_index():
    return pc.Index(INDEX_NAME)