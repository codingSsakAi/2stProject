# -*- coding: utf-8 -*-
"""
out/corpus.jsonl → Upstage 임베딩 → Pinecone 업서트

환경변수 필수:
- UPSTAGE_API_KEY
- PINECONE_API_KEY
선택:
- PINECONE_INDEX (기본: insurance-documents)
- PINECONE_REGION (기본: us-east-1)
- PINECONE_CLOUD  (기본: aws)
- NAMESPACE       (기본: insurance-hub)
- UPSTAGE_EMBED_URL (기본: https://api.upstage.ai/v1/embeddings)
- UPSTAGE_MODEL     (기본: solar-embedding-1-large)
"""

import os
import json
import time
from pathlib import Path

import requests
from tqdm import tqdm
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
load_dotenv()

CORPUS_PATH = Path("./out/corpus.jsonl")

UPSTAGE_API_KEY   = os.getenv("UPSTAGE_API_KEY")
UPSTAGE_EMBED_URL = os.getenv("UPSTAGE_EMBED_URL", "https://insurance-documents-fk9xf7k.svc.aped-4627-b74a.pinecone.io")
UPSTAGE_MODEL     = os.getenv("UPSTAGE_MODEL", "solar-embedding-1-large")

PINECONE_API_KEY  = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = "insurance-documents"
PINECONE_REGION = "us-east-1"
PINECONE_CLOUD = "aws"
NAMESPACE = "insurance-hub"

BATCH_SIZE = 64
RETRY_WAIT = 3

def upstage_embed(texts):
    """
    Upstage 임베딩 호출. 429 등 에러 시 재시도.
    반환: list[list[float]]
    """
    headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": UPSTAGE_MODEL, "input": texts}
    for attempt in range(5):
        r = requests.post(UPSTAGE_EMBED_URL, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            data = r.json()
            return [item["embedding"] for item in data["data"]]
        time.sleep(RETRY_WAIT * (attempt + 1))
    r.raise_for_status()

def ensure_index(pc: Pinecone, index_name: str, dim: int):
    names = [it.name for it in pc.list_indexes()]
    if index_name in names:
        return
    pc.create_index(
        name=index_name,
        dimension=dim,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
    )

def batched(xs, n=BATCH_SIZE):
    batch = []
    for x in xs:
        batch.append(x)
        if len(batch) == n:
            yield batch
            batch = []
    if batch:
        yield batch

def main():
    assert UPSTAGE_API_KEY, "UPSTAGE_API_KEY is required"
    assert PINECONE_API_KEY, "PINECONE_API_KEY is required"
    assert CORPUS_PATH.exists(), f"{CORPUS_PATH} not found"

    # 로드
    items = []
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))

    # 첫 배치로 차원 확인
    probe_texts = [it["content"] for it in items[:min(4, len(items))]]
    probe_vecs  = upstage_embed(probe_texts)
    dim = len(probe_vecs[0])

    pc = Pinecone(api_key=PINECONE_API_KEY)
    ensure_index(pc, PINECONE_INDEX, dim)
    index = pc.Index(PINECONE_INDEX)

    # 업서트
    total = 0
    for batch in tqdm(batched(items), total=(len(items)+BATCH_SIZE-1)//BATCH_SIZE, desc="Upserting"):
        texts = [it["content"] for it in batch]
        vecs  = upstage_embed(texts)
        to_upsert = []
        for it, v in zip(batch, vecs):
            to_upsert.append({
                "id": it["id"],
                "values": v,
                "metadata": {
                    "source_type": it.get("source_type"),
                    "title": it.get("title"),
                    "content": it.get("content"),
                }
            })
        index.upsert(vectors=to_upsert, namespace=NAMESPACE)
        total += len(to_upsert)

    print(f"OK - Upserted {total} vectors to index={PINECONE_INDEX}, namespace={NAMESPACE}, dim={dim}")

if __name__ == "__main__":
    main()
