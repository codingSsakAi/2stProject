# 자동차 보험 추천 챗봇 시스템

## 프로젝트 개요
로그인한 사용자에게 **자동차 보험 추천 및 약관 상담이 가능한 챗봇**을 개발합니다.  
PDF 약관 → 텍스트 변환 → Upstage Embedding → Pinecone 저장 → RAG 기반 OpenAI API 챗봇 연결의 일련 과정을 포함합니다.

## 주요 기능
- **회원가입/로그인**: 사용자 프로필 및 보험 관련 정보 저장
- **PDF 약관 처리**: 다중 PDF 업로드, 병합, 텍스트 변환
- **RAG 챗봇**: 약관 질의응답 및 보험 상담
- **보험 추천**: 사용자 옵션 기반 맞춤형 보험 추천
- **ML 통계**: 연령대, 성별, 차량 크기별 추천 트렌드
- **카카오톡 스타일 UI**: 모바일/PC 반응형 지원

## 기술 스택
- **Backend**: Django 5.2.5, Django REST Framework
- **Database**: MySQL, Pinecone (벡터 DB)
- **AI**: OpenAI API, Upstage Embedding, LangChain
- **Frontend**: Bootstrap, jQuery
- **OCR**: EasyOCR
- **PDF**: PyPDF2

## 설치 방법

### 1. 환경 설정
```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env` 파일을 생성하고 다음 정보를 입력하세요:
```env
# Django 설정
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 데이터베이스 설정 (MySQL)
DB_NAME=insurance_chatbot
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

# OpenAI API 설정
OPENAI_API_KEY=your-openai-api-key-here

# Pinecone 설정
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=your-pinecone-environment-here
PINECONE_INDEX_NAME=insurance-documents

# Upstage Embedding API 설정
UPSTAGE_API_KEY=your-upstage-api-key-here
```

### 3. 데이터베이스 설정
```bash
# MySQL 데이터베이스 생성
mysql -u root -p
CREATE DATABASE insurance_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Django 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser
```

### 4. 서버 실행
```bash
python manage.py runserver
```

## 프로젝트 구조
```
2stProject-2/
├── accounts/                 # 사용자 계정 및 프로필 관리
├── chatbot/                  # 챗봇 및 문서 처리
├── insurance_chatbot/        # Django 프로젝트 설정
├── static/                   # 정적 파일 (CSS, JS, 이미지)
├── media/                    # 업로드된 파일
├── data/                     # PDF 및 텍스트 파일
├── doc/                      # 프로젝트 문서
├── .env                      # 환경변수
├── requirements.txt          # Python 의존성
└── README.md                 # 프로젝트 설명
```

## 개발 단계
1. ✅ **기본 프로젝트 셋업** - Django, MySQL, 환경변수 설정
2. 🔄 **회원가입/로그인/관리자 계정 생성** - 진행중
3. ⏳ **PDF 업로드 → 병합 → TXT 변환**
4. ⏳ **Embedding → Pinecone 업로드**
5. ⏳ **RAG 챗봇 구현**
6. ⏳ **보험 추천 로직 연결**
7. ⏳ **추천 내역 DB 저장 및 마이페이지**
8. ⏳ **ML 통계 및 시각화**
9. ⏳ **UI/UX 개선 (카톡 스타일)**
10. ⏳ **음성 인식 기능 추가**

## 사용법

### 관리자 기능
- Django Admin (`/admin/`)에서 사용자, 문서, 추천 내역 관리
- PDF 약관 업로드 및 처리 상태 모니터링
- Mock 데이터 설정으로 보험료 계산 로직 테스트

### 사용자 기능
- 회원가입 시 보험 추천에 필요한 정보 입력
- 챗봇을 통한 약관 상담 및 보험 추천
- 마이페이지에서 추천 내역 및 설정 관리

## 라이선스
이 프로젝트는 교육 및 연구 목적으로 개발되었습니다.

## 기여
프로젝트 개선을 위한 제안이나 버그 리포트는 언제든 환영합니다.
