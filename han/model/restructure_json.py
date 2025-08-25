import json
import os

def restructure_json_file(file_path):
    """
    하나의 리스트에 있는 데이터를 카테고리별 딕셔너리로 재구성하여
    동일한 파일명으로 저장합니다.
    """
    if not os.path.exists(file_path):
        print(f"오류: 파일 '{file_path}'을 찾을 수 없습니다.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파일 디코딩 오류. 파일이 올바른 형식이 아닙니다: {e}")
        return

    # 딕셔너리 키를 실제 데이터와 일치하도록 수정
    restructured_data = {
        "차 vs. 차": [],
        "차 vs. 사람": [],
        "차 vs. 기타": []
    }
    
    for item in data_list:
        category = item.get("category")
        if category in restructured_data:
            restructured_data[category].append(item)
        else:
            print(f"경고: 알 수 없는 카테고리 '{category}'의 항목이 발견되어 무시됩니다.")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(restructured_data, f, ensure_ascii=False, indent=2)
    
    print(f"'{file_path}' 파일의 구조가 성공적으로 변경되었습니다.")
    print(f"총 {len(data_list)}개의 항목이 {len(restructured_data.keys())}개의 카테고리로 재분류되었습니다.")

if __name__ == "__main__":
    json_file = "accident_data_complete.json"
    restructure_json_file(json_file)