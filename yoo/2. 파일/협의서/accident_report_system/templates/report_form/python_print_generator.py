import os
import base64
from pathlib import Path

def get_image_base64(image_name="damage_outline.png"):
    """이미지를 Base64로 인코딩하여 반환"""
    current_dir = Path(__file__).parent
    possible_paths = [
        current_dir / "static" / "images" / image_name,
        current_dir / "images" / image_name,
        current_dir / ".." / ".." / ".." / "static" / "images" / image_name,
        current_dir / ".." / ".." / "static" / "images" / image_name,
        current_dir / ".." / "static" / "images" / image_name,
        current_dir / image_name
    ]
    
    for image_path in possible_paths:
        if image_path.exists():
            try:
                with open(image_path, 'rb') as img_file:
                    base64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    return f"data:image/png;base64,{base64_string}"
            except Exception as e:
                print(f"이미지 읽기 오류: {e}")
                continue
    
    print(f"경고: {image_name}을 찾을 수 없습니다. 기본 경로를 사용합니다.")
    return f"images/{image_name}"

def generate_django_template():
    """Django 템플릿용 print.html 파일 생성"""
    
    damage_image_src = get_image_base64("damage_outline.png")
    
    html_content = '''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>교통사고 신속처리 표준 협의서</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * { box-sizing: border-box; }
    body { 
      font-family: 'Malgun Gothic', '맑은 고딕', NanumGothic, Arial, sans-serif; 
      margin: 0; 
      padding: 8px; 
      font-size: 11px;
      line-height: 1.2;
    }
    h2 { 
      margin: 0 0 8px 0; 
      text-align: center; 
      font-size: 16px; 
    }

    input, textarea, select { 
      width: 100%; 
      padding: 2px; 
      font-size: 10px; 
      border: none; 
      background: transparent; 
    }
    
    .box { 
      border: 1px solid #000; 
      background: #fff; 
      margin-bottom: 4px; 
    }
    
    .grid { display: grid; }
    .row { display: flex; }
    
    .cell { 
      padding: 4px; 
      border-bottom: 1px solid #000; 
      border-right: 1px solid #000; 
    }
    
    .cell:last-child { border-right: 0; }
    .hdr { background: #f7f7f7; font-weight: 700; }
    .tight { padding: 2px; }
    .label { font-weight: 700; white-space: nowrap; }

    /* 상단 메타 */
    table.meta { 
      width: 100%; 
      border-collapse: collapse; 
      margin-bottom: 4px; 
    }
    
    table.meta th, table.meta td { 
      border: 1px solid #000; 
      padding: 3px 4px; 
      text-align: left; 
      vertical-align: middle; 
      font-size: 9px;
    }
    
    .weather-row { 
      display: flex; 
      gap: 6px; 
      align-items: center; 
      white-space: nowrap; 
      flex-wrap: wrap; 
    }
    
    .weather-row label { 
      display: inline-flex; 
      align-items: center; 
      gap: 3px; 
      font-size: 8px;
    }
    
    .weather-row input[type="checkbox"] { 
      transform: scale(0.7); 
      margin: 0; 
    }

    /* 좌측 세로 라벨 */
    .title-v { 
      writing-mode: vertical-rl; 
      text-align: center; 
      font-weight: 700; 
      padding: 4px 2px; 
      border-right: 1px solid #000; 
      font-size: 10px;
    }

    /* 3단 비율 - A4 가로에 최적화 */
    .cols-3 { grid-template-columns: 33% 33% 34%; }
    .two-col { grid-template-columns: 18% 82%; }

    /* 파손부위 도면 + 마킹 */
    .damage-wrap { padding: 3px 4px; }
    .damage-head { 
      font-weight: 700; 
      margin-bottom: 3px; 
      font-size: 8px; 
    }
    
    .damage-img-box {
      border: 1px solid #000; 
      height: 90px; 
      display: flex;
      align-items: center; 
      justify-content: center; 
      background: #fff; 
      position: relative; 
      overflow: hidden;
    }
    
    .damage-img-box img { 
      max-width: 95%; 
      max-height: 95%; 
      object-fit: contain; 
    }
    
    /* 파손 마크 */
    .mark {
      position: absolute; 
      width: 12px; 
      height: 12px; 
      border: 2px solid #d00; 
      border-radius: 50%;
      transform: translate(-50%, -50%); 
      display: flex; 
      align-items: center; 
      justify-content: center;
      font-size: 8px; 
      font-weight: 900; 
      color: #d00; 
      background: rgba(255,255,255,0.9);
    }

    .desc-area { 
      height: 40px; 
      border: 1px solid #000; 
    }

    /* 사고내용 표 */
    table.acc { 
      width: 100%; 
      border-collapse: collapse; 
    }
    
    table.acc th, table.acc td { 
      border: 1px solid #000; 
      padding: 3px 4px; 
      vertical-align: top; 
      font-size: 9px;
    }

    /* '사고내용/약도' 2열 */
    .acc-wrap { 
      display: grid; 
      grid-template-columns: 75% 25%; 
    }
    
    .acc-left { border-right: 1px solid #000; }
    
    .acc-right { 
      position: relative; 
      background: #fff; 
      min-height: 100px; 
    }
    
    .acc-right .tag { 
      position: absolute; 
      top: 3px; 
      left: 4px; 
      font-weight: 700; 
      font-size: 9px;
    }

    /* 보험청구 서명 */
    .sign-table { 
      width: 100%; 
      border-collapse: collapse; 
    }
    
    .sign-table td { 
      border: 1px solid #000; 
      padding: 6px; 
      text-align: center; 
      font-size: 9px;
    }

    /* 섹션 타이틀 */
    .section-title { 
      font-weight: 800; 
      margin: 3px 0; 
      font-size: 10px; 
    }

    /* A4 가로 출력 최적화 */
    @page {
      size: A4 landscape !important;
      margin: 6mm;
      orientation: landscape;
    }
    
    @media print {
      @page {
        size: landscape !important;
      }
      body { 
        margin: 0; 
        padding: 2px; 
        font-size: 8px; 
      }
      .no-print { display: none !important; }
      input, textarea { border: none; background: transparent; }
      input[type="checkbox"]:checked::after { content: "✓"; }
      .damage-img-box { height: 70px; }
      h2 { font-size: 12px; }
      .weather-row label { font-size: 7px; }
      table.meta th, table.meta td { font-size: 7px; }
      table.acc th, table.acc td { font-size: 7px; }
      .sign-table td { font-size: 7px; }
    }

    /* 반응형 (모바일) */
    @media (max-width: 900px) {
      body { padding: 6px; font-size: 10px; }
      .cols-3 { grid-template-columns: 1fr; }
      .acc-wrap { grid-template-columns: 1fr; }
      .title-v {
        writing-mode: initial;
        border-right: 0; 
        border-bottom: 1px solid #000;
        padding: 4px 6px; 
        text-align: left;
      }
      .damage-img-box { height: 80px; }
      table.meta th, table.meta td { padding: 3px; }
      .two-col { grid-template-columns: 25% 75%; }
    }
  </style>
</head>
<body>
  <div id="sheet">
    <h2>교통사고 신속처리 표준 협의서</h2>

    <!-- 상단 메타 정보 -->
    <table class="meta">
      <tr>
        <th style="width:12%">사고일시</th>
        <td style="width:25%">{{ accident_date }}</td>
        <th style="width:10%">사고장소</th>
        <td style="width:28%">{{ location }}</td>
        <th style="width:7%">날씨</th>
        <td>{{ weather_join }}</td>
      </tr>
    </table>

    <!-- 사고 관계자 정보 및 피해상태 -->
    <div class="box">
      <div class="row" style="border-bottom:1px solid #000; align-items:stretch;">
        <div class="title-v">사고 관계자 정보 및 피해상태</div>
        <div style="flex:1;">
          <div class="grid cols-3">

            <!-- A 차량 -->
            <div style="border-right:1px solid #000;">
              <div class="section-title">A 차량</div>
              <div class="grid two-col">
                <div class="cell hdr">차량번호</div><div class="cell">{{ a_plate }}</div>
                <div class="cell hdr">보험사</div><div class="cell">{{ a_insurer }}</div>
              </div>
              <div class="grid two-col">
                <div class="cell hdr">운전자<br/>정보</div><div class="cell tight"></div>
                <div class="cell hdr">성 명</div><div class="cell">{{ a_name }}</div>
                <div class="cell hdr">주민번호</div><div class="cell">{{ a_id }}</div>
                <div class="cell hdr">전화번호</div><div class="cell">{{ a_phone }}</div>
                <div class="cell hdr">주 소</div><div class="cell">{{ a_address }}</div>
              </div>
              <div class="grid two-col">
                <div class="cell hdr">탑승인원<br/><span style="font-weight:400;">(운전자제외)</span></div>
                <div class="cell">
                  <div style="display:flex; gap:4px; align-items:center;">
                    남 {{ a_male }} 여 {{ a_female }}
                    <span style="flex:1"></span><b>합계</b> {{ a_total }}명
                  </div>
                </div>
              </div>

              <div class="damage-wrap">
                <div class="damage-head">[파손부위] : 해당 부위에 V 표시</div>
                <div class="damage-img-box" id="a_imgbox">
                  <img src="''' + damage_image_src + '''" alt="A차량 파손부위 도면" />
                  <!-- 파손부위 마킹은 views.py에서 처리 -->
                  {% if a_x_1 and a_y_1 %}<div class="mark" style="left:{{ a_x_1 }}%; top:{{ a_y_1 }}%;">V</div>{% endif %}
                  {% if a_x_2 and a_y_2 %}<div class="mark" style="left:{{ a_x_2 }}%; top:{{ a_y_2 }}%;">V</div>{% endif %}
                  {% if a_x_3 and a_y_3 %}<div class="mark" style="left:{{ a_x_3 }}%; top:{{ a_y_3 }}%;">V</div>{% endif %}
                  {% if a_x_4 and a_y_4 %}<div class="mark" style="left:{{ a_x_4 }}%; top:{{ a_y_4 }}%;">V</div>{% endif %}
                  {% if a_x_5 and a_y_5 %}<div class="mark" style="left:{{ a_x_5 }}%; top:{{ a_y_5 }}%;">V</div>{% endif %}
                </div>
              </div>

              <div style="border-top:1px solid #000;">
                <div class="cell hdr" style="border-bottom:0;">[구체적 파손정도 및 특이사항 기술]</div>
                <div class="desc-area">{{ a_damage_desc }}</div>
              </div>
            </div>

            <!-- B 차량 -->
            <div style="border-right:1px solid #000;">
              <div class="section-title">B 차량</div>
              <div class="grid two-col">
                <div class="cell hdr">차량번호</div><div class="cell">{{ b_plate }}</div>
                <div class="cell hdr">보험사</div><div class="cell">{{ b_insurer }}</div>
              </div>
              <div class="grid two-col">
                <div class="cell hdr">운전자<br/>정보</div><div class="cell tight"></div>
                <div class="cell hdr">성 명</div><div class="cell">{{ b_name }}</div>
                <div class="cell hdr">주민번호</div><div class="cell">{{ b_id }}</div>
                <div class="cell hdr">전화번호</div><div class="cell">{{ b_phone }}</div>
                <div class="cell hdr">주 소</div><div class="cell">{{ b_address }}</div>
              </div>
              <div class="grid two-col">
                <div class="cell hdr">탑승인원<br/><span style="font-weight:400;">(운전자제외)</span></div>
                <div class="cell">
                  <div style="display:flex; gap:4px; align-items:center;">
                    남 {{ b_male }} 여 {{ b_female }}
                    <span style="flex:1"></span><b>합계</b> {{ b_total }}명
                  </div>
                </div>
              </div>

              <div class="damage-wrap">
                <div class="damage-head">[파손부위] : 해당 부위에 V 표시</div>
                <div class="damage-img-box" id="b_imgbox">
                  <img src="''' + damage_image_src + '''" alt="B차량 파손부위 도면" />
                  <!-- 파손부위 마킹은 views.py에서 처리 -->
                  {% if b_x_1 and b_y_1 %}<div class="mark" style="left:{{ b_x_1 }}%; top:{{ b_y_1 }}%;">V</div>{% endif %}
                  {% if b_x_2 and b_y_2 %}<div class="mark" style="left:{{ b_x_2 }}%; top:{{ b_y_2 }}%;">V</div>{% endif %}
                  {% if b_x_3 and b_y_3 %}<div class="mark" style="left:{{ b_x_3 }}%; top:{{ b_y_3 }}%;">V</div>{% endif %}
                  {% if b_x_4 and b_y_4 %}<div class="mark" style="left:{{ b_x_4 }}%; top:{{ b_y_4 }}%;">V</div>{% endif %}
                  {% if b_x_5 and b_y_5 %}<div class="mark" style="left:{{ b_x_5 }}%; top:{{ b_y_5 }}%;">V</div>{% endif %}
                </div>
              </div>

              <div style="border-top:1px solid #000;">
                <div class="cell hdr" style="border-bottom:0;">[구체적 파손정도 및 특이사항 기술]</div>
                <div class="desc-area">{{ b_damage_desc }}</div>
              </div>
            </div>

            <!-- 보행자 -->
            <div>
              <div class="section-title">보행자</div>
              <div class="grid two-col">
                <div class="cell hdr">성명:</div><div class="cell">{{ p_name }}</div>
                <div class="cell hdr">주민번호:</div><div class="cell">{{ p_id }}</div>
                <div class="cell hdr">전화번호:</div><div class="cell">{{ p_phone }}</div>
                <div class="cell hdr">주소:</div><div class="cell">{{ p_address }}</div>
              </div>
              <div style="border-top:1px solid #000;">
                <div class="cell hdr" style="border-bottom:0;">[구체적 피해정도 및 특이사항 기술]</div>
                <div class="desc-area" style="height:190px;">{{ p_damage_desc }}</div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>

    <!-- 사고내용/사고약도 -->
    <div class="box" style="border-top:0;">
      <div class="row" style="align-items:stretch;">
        <div class="title-v">사고내용</div>
        <div style="flex:1;" class="acc-wrap">
          <div class="acc-left">
            <table class="acc">
              <tr>
                <th style="width:70px;">사고형태</th>
                <td>
                  <div class="label">자동차대 자동차</div>
                  <div style="margin:2px 0;">{{ type_cc_join }}</div>
                  <div class="label" style="margin-top:2px;">자동차대 보행자</div>
                  <div style="margin:2px 0;">{{ type_cp_join }}</div>
                </td>
              </tr>
              <tr>
                <th>사고원인</th>
                <td>{{ cause_join }}</td>
              </tr>
              <tr>
                <th>[구체적 사고 개요 및 특이사항]</th>
                <td>{{ accident_description }}</td>
              </tr>
            </table>
          </div>

          <div class="acc-right">
            <div class="tag">[사고약도]</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 보험청구 -->
    <div class="box" style="border-top:0;">
      <div class="row">
        <div class="title-v">보험청구</div>
        <div style="flex:1; padding:4px;">
          위 기재사항이 사실과 다름이 없음을 확인하고, 신속한 사고처리 및 보험금 청구를 위하여 상호 서명날인합니다.
          <table class="sign-table" style="margin-top:4px;">
            <tr>
              <td>A 차량 : (서명)</td>
              <td>B 차량 : (서명)</td>
              <td>보행자 : (서명)</td>
            </tr>
          </table>
        </div>
      </div>
    </div>
  </div>
</body>
</html>'''

    output_path = Path(__file__).parent / "print.html"
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Django 템플릿 print.html 파일이 성공적으로 생성되었습니다: {output_path}")
        print("주요 변경사항:")
        print("1. Django 템플릿 변수 사용 ({{ variable }})")
        print("2. #sheet ID 추가 (JPG 캡처용)")
        print("3. 파손부위 마킹을 Django 템플릿 로직으로 처리")
        print("4. A4 가로 레이아웃 최적화")
        return True
    except Exception as e:
        print(f"파일 생성 오류: {e}")
        return False

if __name__ == "__main__":
    generate_django_template()