# insurance_portal/services/pinecone_client.py
import os
from functools import lru_cache
from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import NotFoundException

# 환경변수: PINECONE_API_KEY 또는 PINECONE_API_KEY_MY 중 하나 사용
ENV_KEYS = ("PINECONE_API_KEY", "PINECONE_API_KEY_MY")

def _get_api_key():
    for k in ENV_KEYS:
        v = os.getenv(k)
        if v:
            return v
    raise RuntimeError("Pinecone API key not found. Set PINECONE_API_KEY.")

@lru_cache(maxsize=1)
def get_pc() -> Pinecone:
    return Pinecone(api_key=_get_api_key())

def index_exists(name: str) -> bool:
    pc = get_pc()
    try:
        # describe로 존재 여부 확인
        pc.describe_index(name)
        return True
    except NotFoundException:
        return False

def get_index(name: str):
    """
    요청이 들어왔을 때에만 인덱스를 붙습니다.
    모듈 임포트 시점에는 어떤 네트워크 호출도 하지 않습니다.
    """
    pc = get_pc()
    # 존재하지 않으면 예외를 던지지 말고 None을 반환하고,
    # 호출부에서 사용자 친화적으로 처리하도록 합니다.
    try:
        return pc.Index(name)
    except NotFoundException:
        return None

def create_index_if_needed(name: str, dim: int, metric: str = "cosine",
                           cloud: str = "aws", region: str = "us-east-1") -> bool:
    """
    필요 시 인덱스를 서버리스로 생성. 생성했으면 True, 이미 있었으면 False.
    """
    pc = get_pc()
    if index_exists(name):
        return False
    pc.create_index(
        name=name,
        dimension=dim,
        metric=metric,
        spec=ServerlessSpec(cloud=cloud, region=region)
    )
    return True
