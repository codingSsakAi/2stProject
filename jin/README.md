# 자동차보험 추천시스템

AI 기반 자동차보험 추천 및 약관 질의응답 시스템입니다.

## 🚀 주요 기능

- **ML 기반 보험 추천**: 사용자 프로필 분석을 통한 맞춤형 보험사 추천
- **RAG 질의응답**: 보험 약관에 대한 자연어 질의응답
- **실시간 보험료 계산**: CODEF API 연동을 통한 실시간 보험료 계산
- **약관 다운로드**: 보험사별 약관 PDF 다운로드

## 🛠 기술 스택

- **Backend**: Django 4.2.7, Django REST Framework
- **Database**: SQLite (개발), MySQL (프로덕션)
- **ML/AI**: Scikit-learn, Pandas, NumPy
- **RAG/LLM**: OpenAI GPT, LangChain, ChromaDB
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Authentication**: JWT (JSON Web Tokens)

## 📁 프로젝트 구조

```
backend/
├── config/                 # Django 설정
│   ├── settings.py        # 프로젝트 설정
│   ├── urls.py           # 메인 URL 설정
│   └── wsgi.py           # WSGI 설정
├── users/                 # 사용자 관리 앱
│   ├── models.py         # 사용자 모델
│   ├── views.py          # 사용자 API 뷰
│   ├── serializers.py    # 사용자 시리얼라이저
│   └── urls.py           # 사용자 URL
├── insurance/            # 보험 추천 앱
│   ├── models.py         # 보험 관련 모델
│   ├── views.py          # 보험 API 뷰
│   ├── ml_recommender.py # ML 추천 시스템
│   ├── api_service.py    # CODEF API 연동
│   ├── rag_service.py    # RAG 질의응답
│   └── urls.py           # 보험 URL
├── static/               # 정적 파일
│   └── terms/           # 약관 PDF 파일
├── templates/            # HTML 템플릿
│   └── index.html       # 메인 페이지
└── manage.py            # Django 관리 명령어
```

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# Django 설정
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 데이터베이스 설정
USE_SQLITE=True  # 개발환경에서는 True, 프로덕션에서는 False
DB_NAME=insurance_db
DB_USER=root
DB_PASSWORD=0945
DB_HOST=localhost
DB_PORT=3306

# OpenAI 설정
OPENAI_API_KEY=your-openai-api-key-here

# Pinecone 설정 (선택사항)
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=us-east1-gcp
PINECONE_INDEX_NAME=insurance-terms

# CODEF API 설정 (선택사항)
CODEF_CLIENT_ID=your-codef-client-id-here
CODEF_CLIENT_SECRET=your-codef-client-secret-here
CODEF_ACCESS_TOKEN=your-codef-access-token-here

# 기타 설정
LANGUAGE_CODE=ko-kr
TIME_ZONE=Asia/Seoul
```

### 3. 데이터베이스 설정

```bash
# 마이그레이션 생성 및 적용
python manage.py makemigrations
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 4. 서버 실행

```bash
# 개발 서버 실행
python manage.py runserver

# 브라우저에서 http://localhost:8000 접속
```

## 📋 API 엔드포인트

### 사용자 관리

- `POST /api/users/register/` - 회원가입
- `POST /api/users/login/` - 로그인
- `POST /api/users/logout/` - 로그아웃
- `GET /api/users/profile/` - 프로필 조회
- `PUT /api/users/profile/` - 프로필 수정

### 보험 추천

- `POST /api/insurance/recommend/` - 보험 추천
- `GET /api/insurance/recommendations/history/` - 추천 히스토리

### 약관 질의응답

- `POST /api/insurance/chat/` - 약관 질의응답
- `GET /api/insurance/chat/sample-questions/` - 샘플 질문
- `GET /api/insurance/chat/history/` - 채팅 히스토리

### 기타

- `GET /api/insurance/download/<filename>/` - 약관 다운로드
- `POST /api/insurance/initialize-rag/` - RAG 시스템 초기화

## 🔧 개발 가이드

### ML 모델 커스터마이징

`insurance/ml_recommender.py`에서 추천 알고리즘을 수정할 수 있습니다:

```python
# 사용자 특성 추가
def prepare_user_features(self, user_profile):
    features = {
        'age': user_profile.get('age', 30),
        'gender_encoded': 1 if user_profile.get('gender') == 'M' else 0,
        # 추가 특성들...
    }
    return features
```

### RAG 시스템 설정

`insurance/rag_service.py`에서 RAG 설정을 조정할 수 있습니다:

```python
# 청킹 설정
def _split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    # 청크 크기와 오버랩 조정
```

### API 연동

`insurance/api_service.py`에서 CODEF API 연동을 설정할 수 있습니다:

```python
# API 엔드포인트 설정
self.insurance_fee_url = "https://api.codef.io/insurance/each/damoa/insuranceFee"
```

## 🧪 테스트

### API 테스트

```bash
# 회원가입 테스트
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "testpass123",
    "password_confirm": "testpass123",
    "gender": "M",
    "birth_date": "1990-01-01",
    "driving_exp": 5
  }'

# 보험 추천 테스트
curl -X POST http://localhost:8000/api/insurance/recommend/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "gender": "M",
    "birth_date": "1990-01-01",
    "driving_exp": 5,
    "car_year": 2020,
    "annual_mileage": 12000,
    "accident_history": false,
    "budget_range": "medium"
  }'
```

## 📊 데이터베이스 모델

### 사용자 모델 (User)

- `email`: 이메일 (고유)
- `username`: 사용자명
- `gender`: 성별 (M/F)
- `birth_date`: 생년월일
- `driving_exp`: 운전경력 (년)
- `phone_number`: 전화번호
- `address`: 주소

### 보험 관련 모델

- `InsuranceCompany`: 보험사 정보
- `InsuranceProduct`: 보험 상품 정보
- `UserProfile`: 사용자 보험 프로필
- `InsuranceRecommendation`: 보험 추천 결과
- `InsuranceTerms`: 보험 약관 정보
- `ChatHistory`: 약관 질의응답 히스토리

## 🔒 보안

- JWT 토큰 기반 인증
- CORS 설정으로 허용된 도메인만 접근 가능
- 환경변수를 통한 민감한 정보 관리
- SQL Injection 방지를 위한 Django ORM 사용

## 🚀 배포

### 프로덕션 환경 설정

1. `USE_SQLITE=False`로 설정
2. MySQL 데이터베이스 설정
3. `DEBUG=False`로 설정
4. `ALLOWED_HOSTS`에 실제 도메인 추가
5. 정적 파일 수집: `python manage.py collectstatic`

### Docker 배포 (선택사항)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해주세요.

---

**자동차보험 추천시스템** - AI 기반 맞춤형 보험 추천 및 약관 질의응답 플랫폼
