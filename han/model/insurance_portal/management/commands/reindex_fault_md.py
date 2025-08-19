# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pinecone import Pinecone, ServerlessSpec
from insurance_portal.utils.md_chunker import chunk_markdown, save_jsonl
from insurance_portal.services.pinecone_search_fault import upstage_embed

import os
import json
import re
import hashlib
import unicodedata


class Command(BaseCommand):
    help = "output.md (과실비율 인정기준) → JSONL 생성 → Pinecone 업서트"

    def add_arguments(self, parser):
        parser.add_argument("--md", required=True, help="Markdown 파일 경로 (예: output.md)")
        parser.add_argument("--index", default=None, help="Pinecone 인덱스명(없으면 settings.FAULT_INDEX_NAME)")
        parser.add_argument("--namespace", default="", help="Pinecone namespace (선택)")
        parser.add_argument("--jsonl", default="out/accident_fault_rules.jsonl", help="생성할 JSONL 경로")

    def handle(self, *args, **opts):
        md_path = opts["md"]
        index_name = opts["index"] or getattr(settings, "FAULT_INDEX_NAME", None)
        namespace = opts["namespace"]
        jsonl_path = opts["jsonl"]

        if not os.path.exists(md_path):
            raise CommandError(f"MD not found: {md_path}")
        if not index_name:
            raise CommandError("FAULT_INDEX_NAME 설정이 없고 --index 미지정입니다.")

        self.stdout.write(self.style.NOTICE(f"[1/4] 읽는 중: {md_path}"))
        md_text = open(md_path, "r", encoding="utf-8").read()

        self.stdout.write(self.style.NOTICE("[2/4] 청크 생성"))
        chunks = chunk_markdown(md_text, source_name=os.path.basename(md_path))
        save_jsonl(chunks, jsonl_path)
        self.stdout.write(self.style.SUCCESS(f" → {len(chunks)} chunks, JSONL: {jsonl_path}"))

        self.stdout.write(self.style.NOTICE("[3/4] Pinecone 연결"))
        pc = Pinecone(api_key=getattr(settings, "PINECONE_API_KEY_MY"))
        idx_names = pc.list_indexes().names()
        if index_name not in idx_names:
            # 인덱스가 없으면 현재 임베딩 차원으로 생성
            dim = len(upstage_embed("ping"))  # Upstage 임베딩 차원 자동 추출
            self.stdout.write(self.style.WARNING(f"인덱스가 없어 생성합니다: {index_name} (dim={dim})"))
            pc.create_index(
                name=index_name,
                dimension=dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-west-2"),
            )
        index = pc.Index(index_name)

        self.stdout.write(self.style.NOTICE("[4/4] 업서트(배치)"))

        def _sanitize_meta(meta: dict, max_str_len: int = 12000) -> dict:
            """
            Pinecone 메타 형식 제한 준수:
            - 허용: str, int/float, bool, [str, ...]
            - 그 외(dict/복합 list 등)는 JSON 문자열로 직렬화(길이 제한 적용)
            """
            def _to_allowed(v):
                if v is None:
                    return None
                if isinstance(v, (str, bool, int, float)):
                    return v
                if isinstance(v, list):
                    out = []
                    for x in v:
                        if isinstance(x, (str, bool, int, float)):
                            s = str(x)
                        else:
                            s = json.dumps(x, ensure_ascii=False, separators=(",", ":"))
                        if len(s) > max_str_len:
                            s = s[:max_str_len]
                        out.append(s)
                    return out
                # dict 또는 기타 → 문자열
                s = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
                if len(s) > max_str_len:
                    s = s[:max_str_len]
                return s

            clean = {}
            for k, v in (meta or {}).items():
                cv = _to_allowed(v)
                if cv is not None:
                    clean[k] = cv
            return clean

        vectors = []
        for i, obj in enumerate(chunks, 1):
            # 임베딩 소스: 표가 있으면 table_md, 아니면 본문 text
            src = obj.get("table_md") or obj.get("text") or ""
            if not src.strip():
                continue

            vec = upstage_embed(src)
            # Pinecone는 float만 허용 → 모든 요소를 float로 강제
            vec = [float(x) for x in vec]

            # 벡터 ID를 ASCII로 보정
            orig_id = obj.get("id") or "chunk"
            vid = orig_id
            vid = unicodedata.normalize("NFKD", vid).encode("ascii", "ignore").decode("ascii")
            vid = re.sub(r"[^A-Za-z0-9_.:-]+", "-", vid).strip("-_.:").lower()
            if not vid:
                h = hashlib.sha1((src or orig_id).encode("utf-8")).hexdigest()[:8]
                vid = f"chunk-{h}"
            vid = vid[:64]

            # 메타데이터 구성(+원본 id 추적)
            meta = {k: v for k, v in obj.items() if k not in {"text"}}
            meta["id_original"] = orig_id
            meta["vector_id"] = vid

            # 필요 시 table_json을 완전히 제거하고 싶다면 아래 한 줄을 활성화
            # meta.pop("table_json", None)

            # Pinecone 허용 타입으로 변환
            meta = _sanitize_meta(meta)

            vectors.append({"id": vid, "values": vec, "metadata": meta})

            if len(vectors) >= 100:
                index.upsert(vectors=vectors, namespace=namespace)
                vectors.clear()
                if i % 500 == 0:
                    self.stdout.write(self.style.SUCCESS(f"  upserted: {i}"))

        if vectors:
            index.upsert(vectors=vectors, namespace=namespace)

        self.stdout.write(self.style.SUCCESS("완료!"))
