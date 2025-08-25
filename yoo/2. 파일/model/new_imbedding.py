import re
import json

def parse_markdown_to_json(markdown_path):
    """
    output.md 파일을 읽어 제2편과 제3편의 내용을 JSON 형식으로 변환합니다.
    """
    try:
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"파일을 찾을 수 없습니다: {markdown_path}"}

    # 제2편 총 설 내용 추출 (패턴 수정)
    part2_match = re.search(r'\*\*제2편 총 설\*\*.*?(?=\*\*제3편 과실비율 적용기준)', content, re.DOTALL)
    part2_text = part2_match.group(0).strip() if part2_match else ""
    part2_summary = "제2편 총 설은 과실비율 인정기준의 기본 원칙과 과실의 의의, 신뢰의 원칙 등을 설명하는 보강 자료입니다."

    # 제3편 과실비율 적용기준 내용 추출 (패턴 수정)
    part3_content_match = re.search(r'\*\*제3편 과실비율 적용기준.*?사고유형별\)\*\*.*?(\*\*제\d+장|\Z)', content, re.DOTALL)
    if not part3_content_match:
        return {"error": "제3편 과실비율 적용기준 섹션을 찾을 수 없습니다. 파일 형식을 확인해주세요."}
    part3_content = part3_content_match.group(0)

    # 제3편을 장(챕터) 단위로 분리 (패턴 수정)
    chapters = re.split(r'\*\*제\d+장.*?사고\*\*', part3_content)[1:]
    chapter_titles = re.findall(r'\*\*제\d+장.*?사고\*\*', part3_content)

    all_cases = []

    for chapter_idx, chapter_content in enumerate(chapters):
        chapter_title = chapter_titles[chapter_idx].replace('**', '').strip()

        # 각 장에서 '4. 세부유형별' 섹션만 추출 (패턴 수정)
        section4_content = re.search(r'\*\*4\. 세부유형별 과실비율 적용기준\*\*(.*?)(?=\*\*제\d+장|\Z)', chapter_content, re.DOTALL)
        if not section4_content:
            continue

        section4_text = section4_content.group(1).strip()

        # 각 사고 유형(case) 단위로 분리 (표 식별자를 기준으로, 패턴 수정)
        case_blocks = re.split(r'(\|\*\*?([보차거]\d+-\d+|[보차거]\d+)\*\*?\|)', section4_text, re.DOTALL)
        
        # 첫 번째 항목은 분리 기준이므로 무시하고, 실제 케이스는 세 개 단위로 순회
        case_blocks = case_blocks[1:]
        
        for i in range(0, len(case_blocks), 3):
            case_id_raw = case_blocks[i+1]
            case_content = case_blocks[i+2].strip()

            case_id = case_id_raw.replace('*', '').replace('|', '')
            
            # 사고 유형 요약 추출
            summary_match = re.search(r'^\*\*(.*?)\*\*', case_content, re.MULTILINE)
            case_summary = summary_match.group(1).strip() if summary_match else ""
            
            # 표와 본문 분리
            text_without_table = re.sub(r'\|.*\|.*\n\|-.*\|', '', case_content, flags=re.DOTALL)
            
            # 상세 설명, 법규, 판례 추출
            description_text = re.split(r'(\*\*관련법규\*\*|\*\*참고판례\*\*)', text_without_table)[0].strip()
            
            related_laws = re.search(r'\*\*관련법규\*\*\n(.*?)(?=\*\*참고판례\*\*|\Z)', text_without_table, re.DOTALL)
            related_laws_list = [law.strip() for law in related_laws.group(1).split('\n') if law.strip()] if related_laws else []

            precedents = re.search(r'\*\*참고판례\*\*\n(.*)', text_without_table, re.DOTALL)
            precedents_list = [precedent.strip() for precedent in precedents.group(1).split('\n') if precedent.strip()] if precedents else []

            case_data = {
                "part": "제3편",
                "chapter": chapter_title,
                "case_id": case_id,
                "case_summary": case_summary,
                "description": description_text,
                "related_laws": related_laws_list,
                "precedents": precedents_list,
                "part2_summary": part2_summary
            }
            all_cases.append(case_data)

    return all_cases

# 스크립트 실행
if __name__ == "__main__":
    file_path = 'output.md'
    structured_data = parse_markdown_to_json(file_path)

    if "error" in structured_data:
        print(structured_data["error"])
    else:
        output_file_name = 'negligence_data.json'
        with open(output_file_name, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=4)
        print(f"JSON 파일이 성공적으로 생성되었습니다: {output_file_name}")