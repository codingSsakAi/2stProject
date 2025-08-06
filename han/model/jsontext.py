import pdfplumber
import json

pdf_path = "!!230630_자동차사고과실비율인정기준(`23.6.)_최종.pdf"
output_json = "과실비율_인정기준_텍스트.json"

data = []

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages, 1):
        page_text = page.extract_text() or ""
        tables = page.extract_tables()
        table_texts = []
        for table in tables:
            # 여기서 None을 ''로 치환
            lines = [' | '.join([cell if cell is not None else '' for cell in row]) for row in table]
            table_texts.append('\n'.join(lines))
        all_text = page_text.strip()
        if table_texts:
            all_text += "\n\n[표]\n" + "\n\n".join(table_texts)
        data.append({
            "page": i,
            "text": all_text
        })

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"저장 완료: {output_json}")
