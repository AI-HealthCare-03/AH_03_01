# 🤖 만성질환 생활습관 챌린지 웹 서비스

> 고혈압·당뇨 등 만성질환의 발병 가능성을 예측하고, 사용자의 생활습관 데이터를 기반으로 건강 상태를 추적하며, 생활습관 개선 챌린지를 제공하는 AI 기반 만성질환 관리 웹 서비스입니다.

---

## 1. 프로젝트 개요 📝

본 프로젝트는 만성질환 관리에 필요한 **예측 모델링**, **건강 데이터 시각화**, **생활습관 개선 챌린지**, **AI 기반 예방 행동 추천** 기능을 통합한 웹 서비스입니다.

만성질환은 장기간의 생활습관, 건강 상태, 유전적 요인 등이 복합적으로 작용하여 발생합니다. 따라서 단순한 질병 예측에 그치지 않고, 사용자가 자신의 건강 데이터를 지속적으로 확인하고 생활습관을 개선할 수 있도록 돕는 서비스가 필요합니다.

본 서비스는 공개 의료·헬스케어 데이터를 활용하여 만성질환 발병 가능성을 예측하고, 사용자가 입력한 건강/행동 데이터를 기반으로 대시보드와 챌린지를 제공합니다.

---

## 2. 주제 📌

### 만성질환(고혈압·당뇨) 생활습관 챌린지 웹 서비스

사용자의 건강 정보와 생활습관 데이터를 기반으로 만성질환 발병 가능성을 예측하고, 건강 개선을 위한 맞춤형 생활습관 챌린지를 제공하는 서비스입니다.

---

## 3. 주제 선정 배경 🌄

만성질환은 장기간의 관리가 필요한 질환으로, 의료 데이터 기반 예측과 생활습관 개선이 중요한 분야입니다.

특히 고혈압과 당뇨는 식습관, 운동량, 체중, 수면, 음주·흡연 여부 등 생활습관과 밀접한 관련이 있습니다. 따라서 사용자 건강 데이터를 기반으로 위험도를 예측하고, 이를 시각적으로 제공하며, 일상 속에서 실천 가능한 행동 개선 챌린지를 제안하는 서비스가 필요하다고 판단했습니다.

본 프로젝트는 공개 의료 데이터를 활용한 AI 모델 개발부터 웹 서비스 구현, 사용자 대시보드, 챌린지 기능, AI 기반 행동 추천까지 전체 서비스 흐름을 실무 환경과 유사하게 구현하는 것을 목표로 합니다.

---

## 4. 핵심 목표 🎯

- 공개 데이터셋을 활용한 만성질환 발병 가능성 예측 모델 구축
- 사용자 건강/생활습관 데이터 입력 및 관리
- 예측 결과와 건강 데이터 변화 추이를 시각화
- 생활습관 개선을 위한 챌린지 기능 제공
- LLM 기반 맞춤형 예방 행동 추천 기능 구현
- 알림 기능을 통한 지속적인 건강 관리 유도

---

## 5. 주요 기능 ⚒️

| 구분 | 기능명 | 설명 |
|---|---|---|
| 필수 | 만성질환 예측 모델링 | 공개 데이터셋을 활용하여 고혈압·당뇨 등 만성질환 발병 가능성을 예측 |
| 필수 | 만성질환 추적 대시보드 | 사용자 건강/행동 데이터를 시각화하고 예측 결과 변화를 제공 |
| 필수 | 생활습관 챌린지 | 걷기, 물 마시기, 운동 등 생활습관 개선 챌린지 제공 |
| 선택 | LLM 기반 예방 행동 추천 | 사용자 건강/행동 데이터를 기반으로 맞춤형 건강 행동 가이드 생성 |
| 선택 | 이미지 분류 기반 식단 분석 | 사용자의 식단 사진 데이터 입력을 기반으로 음식을 분류하고, 사용자 개인에 따라 부족한 영양소를 분석해주는 시스템 |
| 선택 | 알림 기능 | 건강 데이터 입력, 챌린지 체크, 주요 가이드 확인 알림 제공 |

---

## 6. 상세 기능 설명

### 6.1 만성질환 예측 모델링

사용자의 건강 데이터를 기반으로 만성질환 발병 가능성을 예측하는 기능.

활용 가능한 데이터 예시:

- Kaggle 공개 헬스케어 데이터셋
- AIHub 의료/건강 관련 데이터셋
- HuggingFace 공개 모델 및 데이터셋
- 고혈압, 당뇨, 심혈관 질환 관련 공개 데이터

예측 모델은 사용자의 건강 지표를 입력받아 질환 발병 가능성을 확률 형태로 제공.

예상 입력 데이터 예시:

- 나이
- 성별
- 키
- 몸무게
- BMI
- 혈압
- 혈당
- 흡연 여부
- 음주 여부
- 운동 빈도
- 수면 시간
- 가족력
- 식습관 관련 정보

예상 출력 예시:

```json
{
  "disease": "diabetes",
  "risk_score": 0.72,
  "risk_level": "High",
  "message": "당뇨(/고혈압) 발병 가능성이 높은 편입니다. 병원에 내원하여 검진을 꼭 받아보세요!"
}
```

### 6.2 만성질환 추적 대시보드

### 6.3 생활습관 챌린지

---

## 7. 주요 특징 

- **FastAPI Framework**: 고성능 비동기 API 서버 구현.
- **AI Worker**: 모델 추론 및 학습 작업을 API 서버와 분리하여 처리.
- **UV Package Manager**: 매우 빠른 의존성 설치 및 가상환경 관리.
- **Tortoise ORM**: 비동기 방식의 데이터베이스 모델링 및 쿼리 관리.
- **Docker-Compose**: MySQL, Redis, Nginx를 포함한 전체 서비스 스택을 한 번에 실행.
- **CI/CD Scripts**: 코드 포맷팅(Ruff), 타입 체크(Mypy), 테스트(Pytest)를 위한 자동화 스크립트 제공.

---

## 8. 프로젝트 구조 📂 

```text
.
├── ai_worker/          # AI 모델 추론 및 학습 관련 코드 (Worker)
│   ├── core/           # 워커 설정 및 로거
│   ├── models/         # AI 모델 파일 보관 (PyTorch 등)
│   ├── tasks/          # 실제 처리할 작업 정의
│   └── main.py         # 워커 진입점
├── app/                # FastAPI 서버 코드
│   ├── apis/           # API 라우터 (v1 버전 관리)
│   ├── core/           # 서버 설정 (pydantic-settings), DB 설정, JWT, Validator 등 핵심 기능
│   ├── dtos/           # 데이터 전송 객체 (Pydantic models)
│   ├── models/         # DB 테이블 정의
│   ├── services/       # 비즈니스 로직
│   └── main.py         # FastAPI 애플리케이션 진입점
├── envs/               # 환경 변수 설정 파일 (.env)
├── infra/              # 인프라 설정 관련 디렉터리
│   ├── docker/         # Docker Compose 설정 (운영용)
│   └── nginx/          # Nginx 설정 파일 (리버스 프록시)
├── scripts/            # 배포 및 CI용 쉘 스크립트
├── docker-compose.yml  # 로컬 개발용 서비스 실행 설정
└── pyproject.toml      # uv 기반 의존성 관리 설정
```

---

## ⚙️ 사전 준비 사항

- **Python**: 3.13 이상 (로컬 개발 환경용)
- **UV**: Python 패키지 매니저 ([설치 가이드](https://github.com/astral-sh/uv))
- **Docker & Docker-Compose**: 전체 서비스 실행용

---

## 🛠️ 설치 및 설정

### 1. 가상환경 구축 및 의존성 설치

`uv`를 사용하여 프로젝트에 필요한 패키지를 설치합니다.

```bash
# 의존성 설치 (가상환경 자동 생성)
uv sync

# 특정 그룹의 의존성만 설치하려는 경우
uv sync --group app  # API 서버용
uv sync --group ai   # AI 워커용
```

### 2. 환경 변수 설정

`envs/` 디렉토리에 있는 예시 파일을 복사하여 `.env` 파일을 생성합니다.
- 로컬용 
    ```bash
    cp envs/example.local.env envs/.local.env
    ```
- 배포용 
    ```bash
    cp envs/example.prod.env envs/.prod.env
    ```

생성된 `env` 파일 내의 환경변수들은 프로젝트 상황에 맞게 수정하세요.

---

## 🏃 실행 방법

### 1. 로컬 및 개발 환경

#### Docker Compose로 전체 스택 실행

모든 서비스(API, Worker, DB, Redis, Nginx)를 한 번에 실행합니다.

```bash
docker-compose up -d --build
```

실행 후 다음 주소로 접속 가능합니다:
- **API 서버**: [http://localhost/api/docs](http://localhost/api/docs) (Swagger UI)
- **Nginx**: 80 포트를 통해 API 서버로 요청을 전달합니다.

#### 로컬에서 개별 실행 (개발용)

**FastAPI 서버 실행:**
```bash
uv run uvicorn app.main:app --reload
# or
docker compose up -d --build app
```

**AI Worker 실행:**
```bash
uv run python -m ai_worker.main
# or
docker compose up -d --build ai_worker
```

### 2. EC2 배포 환경 (Production)

제공된 쉘 스크립트를 사용하여 AWS EC2 환경에 이미지를 빌드, 푸시 및 배포할 수 있습니다.

#### 사전 준비
- EC2 인스턴스 (Ubuntu 권장)
- SSH 키 페어 (`~/.ssh/` 경로에 위치)
- 도커 허브(Docker Hub) 계정 및 Personal Access Token
- 배포용 환경 변수 설정 (`envs/.prod.env`)
- 도메인 구매 (Gabia, GoDaddy, AWS Route53 등)

#### 자동 배포 스크립트 실행
`scripts/deployment.sh`는 도커 이미지 빌드, 레포지토리 푸시, EC2 접속 및 컨테이너 실행 과정을 자동화합니다.

```bash
chmod +x scripts/deployment.sh
./scripts/deployment.sh
```
스크립트 실행 시 다음 정보를 입력해야 합니다:
1. 도커 허브 계정 정보 (Username, PAT)
2. 이미지를 업로드할 레포지토리 이름
3. 배포할 서비스 선택 (FastAPI, AI-Worker) 및 버전(Tag)
4. SSH 키 파일명 및 EC2 IP 주소
5. https 사용여부
   - 5-1. https인 경우 도메인 추가 입력  

#### SSL(HTTPS) 설정 (Certbot)
도메인을 연결하고 HTTPS를 적용하려면 `scripts/certbot.sh`를 사용합니다.

```bash
chmod +x scripts/certbot.sh
./scripts/certbot.sh
```
1. 도메인 주소 및 이메일 입력
2. SSH 키 파일명 및 EC2 IP 주소 입력
3. Let's Encrypt를 통한 인증서 발급 및 Nginx 설정 자동 갱신 적용

---

## 🧪 테스트 및 품질 관리

제공된 스크립트를 사용하여 코드의 품질을 검증할 수 있습니다.

```bash
# 테스트 실행
./scripts/ci/run_test.sh

# 코드 포맷팅 확인 (Ruff)
./scripts/ci/code_fommatting.sh

# 정적 타입 검사 (Mypy)
./scripts/ci/check_mypy.sh
```

---

## 📝 개발 가이드

- **API 추가**: `app/apis/v1/` 아래에 새로운 라우터 파일을 생성하고 `app/apis/v1/__init__.py`에 등록하세요.
- **DB 모델 추가**: `app/models/`에 Tortoise 모델을 정의하고 `app/db/databases.py`의 `MODELS` 리스트에 추가하세요.
- **AI 로직 추가**: `ai_worker/tasks/`에 새로운 처리 로직을 작성하고 `ai_worker/main.py`에서 호출하도록 구성하세요.
