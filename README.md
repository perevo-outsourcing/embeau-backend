# EMBEAU API

색채 심리 상담 연구용 백엔드 API

## 기술 스택

- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL + asyncpg
- **Auth**: JWT (python-jose)
- **ML**: PyTorch (BiSeNet, DenseNet121) - GPU 추론
- **AI**: OpenAI GPT-4o-mini, LangChain RAG
- **Package Manager**: uv

## 프로젝트 구조

```
backend/
├── src/embeau_api/
│   ├── api/v1/           # API 라우터
│   ├── ml/               # PyTorch 모델 (NEW)
│   │   ├── face_parsing/ # BiSeNet 얼굴 세그멘테이션
│   │   └── model_loader.py
│   ├── models/           # SQLAlchemy 모델
│   ├── schemas/          # Pydantic 스키마
│   ├── services/         # 비즈니스 로직
│   ├── core/             # 보안, 로깅, 예외처리
│   └── db/               # 데이터베이스 설정
├── models/               # 모델 가중치 (다운로드 필요)
│   ├── 79999_iter.pth              # BiSeNet
│   └── best_densenet121_rafdb.pth  # DenseNet121
└── data/                 # 정적 데이터 (color.pdf 등)
```

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/auth/login` | 로그인 |
| POST | `/api/auth/logout` | 로그아웃 |
| GET | `/api/auth/profile` | 프로필 조회 |
| POST | `/api/color/analyze` | 이미지 분석 (퍼스널컬러) |
| GET | `/api/color/result` | 분석 결과 조회 |
| GET | `/api/color/daily-healing` | 오늘의 힐링컬러 |
| POST | `/api/emotion/analyze` | 감정 분석 |
| GET | `/api/emotion/history` | 감정 기록 조회 |
| GET | `/api/emotion/weekly-insight` | 주간 인사이트 |
| GET | `/api/recommendations` | 추천 조회 |
| POST | `/api/feedback` | 피드백 제출 |
| GET | `/api/reports/weekly` | 주간 PDF 리포트 |

## 서버 설정 가이드 (Ubuntu + A5000 GPU)

### 1. PostgreSQL 설치 및 설정

```bash
# PostgreSQL 설치
sudo apt update
sudo apt install postgresql postgresql-contrib

# DB 및 사용자 생성
sudo -u postgres psql
CREATE USER embeau WITH PASSWORD 'embeau';
CREATE DATABASE embeau OWNER embeau;
\q
```

### 2. uv 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### 3. 의존성 설치

```bash
cd /path/to/embeau/backend
uv sync
```

### 4. 모델 가중치 다운로드

Google Drive에서 다운로드: https://drive.google.com/drive/folders/1FLY0526bDTU4sxk6JbvAbCJ1jvsAywA1

```bash
mkdir -p models
# 다운로드 후 models/ 폴더에 배치:
# - models/79999_iter.pth (BiSeNet)
# - models/best_densenet121_rafdb.pth (DenseNet121)
```

### 5. 환경 설정

```bash
cp .env.example .env
nano .env
```

필수 설정:
```bash
DATABASE_URL=postgresql+asyncpg://embeau:embeau@localhost:5432/embeau
SECRET_KEY=your-secret-key-change-in-production
OPENAI_API_KEY=your-openai-api-key
USE_LOCAL_MODELS=true
```

### 6. 데이터베이스 초기화

```bash
uv run python -m embeau_api.db.init_db
```

### 7. 서버 실행

```bash
# 개발 모드
uv run uvicorn embeau_api.main:app --host 0.0.0.0 --port 8000 --reload

# 프로덕션 모드
uv run uvicorn embeau_api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 테스트 계정

- Email: `test@test.com`
- Participant ID: `testtest`

## 프론트엔드 연동

프론트엔드 `.env.local`:
```
NEXT_PUBLIC_API_URL=http://your-server-ip:8000/api
```

## ML 모델 정보

### BiSeNet (Face Parsing)
- 용도: 얼굴 세그멘테이션, 피부 영역 추출
- 클래스: 19개 (피부, 눈, 코, 입 등)
- 가중치: `models/79999_iter.pth`

### DenseNet121 (Emotion Recognition)
- 용도: 얼굴 감정 인식
- 클래스: 7개 (surprise, fear, disgust, happy, sad, angry, neutral)
- 학습: RAF-DB 데이터셋
- 가중치: `models/best_densenet121_rafdb.pth`

### GPU 요구사항
- CUDA 지원 GPU 권장 (A5000x4 최적)
- CPU 폴백 지원 (느림)

## 연구용 로깅

모든 사용자 행동이 `research_logs.jsonl`에 기록됨:
- 로그인/로그아웃
- 컬러 분석 요청/결과
- 감정 분석
- 추천 조회
- 피드백 제출

## 환경 변수 참조

| 변수 | 설명 | 기본값 |
|------|------|--------|
| DATABASE_URL | PostgreSQL 연결 | postgresql+asyncpg://embeau:embeau@localhost:5432/embeau |
| SECRET_KEY | JWT 시크릿 | (필수 변경) |
| OPENAI_API_KEY | OpenAI API 키 | (필수) |
| USE_LOCAL_MODELS | 로컬 ML 모델 사용 | true |
| BISENET_WEIGHTS | BiSeNet 가중치 경로 | models/79999_iter.pth |
| EMOTION_MODEL_WEIGHTS | DenseNet121 가중치 경로 | models/best_densenet121_rafdb.pth |
