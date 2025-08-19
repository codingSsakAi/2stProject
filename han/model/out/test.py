# print_samples_markdown.py
# 목적: JSONL 레코드를 간단한 마크다운으로 정리한 뒤, Python-Markdown으로 HTML 변환하여 콘솔에 출력
# 필요 패키지: pip install Markdown

import argparse
import json
import sys
from typing import Any, Dict
import markdown

def iter_jsonl(path: str):
    """JSON Lines 파일을 한 줄씩 파싱."""
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[경고] JSON 파싱 실패 (line {lineno}): {e}", file=sys.stderr)

def _to_pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)

def record_to_markdown(rec: Dict[str, Any], index: int) -> str:
    """
    레코드를 Markdown 문자열로 변환.
    - 짧은 스칼라 값들은 목록으로
    - 긴 문자열/구조화 데이터(dict/list)는 코드블록(JSON)으로
    """
    lines = []
    lines.append(f"### 샘플 {index}\n")

    # 키 정렬하여 안정적으로 출력
    for k in sorted(rec.keys()):
        v = rec[k]
        if v is None:
            lines.append(f"- **{k}**: null")
        elif isinstance(v, (int, float, bool)):
            lines.append(f"- **{k}**: {v}")
        elif isinstance(v, str):
            txt = v.strip()
            if "\n" in txt or len(txt) > 200:
                lines.append(f"- **{k}**:")
                lines.append("")
                lines.append("```")
                lines.append(txt)
                lines.append("```")
                lines.append("")
            else:
                # 한 줄로 충분히 표시 가능한 짧은 문자열
                lines.append(f"- **{k}**: {txt}")
        elif isinstance(v, (list, dict)):
            lines.append(f"- **{k}** (JSON):")
            lines.append("")
            lines.append("```json")
            lines.append(_to_pretty_json(v))
            lines.append("```")
            lines.append("")
        else:
            # 기타 타입은 문자열화
            lines.append(f"- **{k}**: `{str(v)}`")

    return "\n".join(lines).strip() + "\n"

def main():
    parser = argparse.ArgumentParser(
        description="JSONL 레코드를 Markdown→HTML로 변환해 콘솔에 출력"
    )
    parser.add_argument("--path", default="fault.jsonl", help="JSONL 파일 경로")
    parser.add_argument("--n", type=int, default=3, help="앞에서부터 출력할 샘플 개수")
    parser.add_argument(
        "--show-md", action="store_true",
        help="HTML과 함께 원본 Markdown도 같이 출력"
    )
    args = parser.parse_args()

    count = 0
    for i, rec in enumerate(iter_jsonl(args.path), start=1):
        if count >= args.n:
            break
        md_text = record_to_markdown(rec, index=i)
        html = markdown.markdown(md_text, extensions=["extra"])

        # 구분선
        print("=" * 80)
        print(f"[샘플 {i}] HTML 출력")
        print("-" * 80)
        print(html)

        if args.show_md:
            print("-" * 80)
            print(f"[샘플 {i}] 원본 Markdown")
            print("-" * 80)
            print(md_text)

        count += 1

    if count == 0:
        print("[정보] 출력할 레코드를 찾지 못했습니다. 파일 경로와 형식을 확인하세요.", file=sys.stderr)

if __name__ == "__main__":
    main()
