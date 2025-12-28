# 🤱DearBelly🤱

태아와 산모를 위한 맞춤형 관리 서비스, 디어벨리의 FastAPI Server Repository 입니다.

---

## ⭐ERD⭐

![ERD](https://github.com/user-attachments/assets/3f9a8294-7e3c-4d5b-a56d-6d38dda217da)

---

## ⭐Architecture⭐

![Architecture](https://github.com/user-attachments/assets/10e088dd-89c5-40fc-8001-379fb8fb7ea5)

---

## 📁 프로젝트 구조 📁
```angular2html
app/
├── api/
│   └── endpoints/
│       └── __init__.py          # 라우터 모음
├── core/                        # 공통 설정 및 유틸리티 (config, logging 등)
├── models/
│   └── models/                  # CV BaseModel
├── schemas/
│   ├── __init__.py
│   └── job.py                   # 요청/응답 스키마 (작업 단위)
├── services/
│   ├── __init__.py
│   ├── openai_service.py        # OpenAI 연동 로직
│   ├── predictor_service.py     # CV 모델기반 예측/추론 로직
│   └── s3_service.py            # AWS S3 연동 로직(Presigned URL 다운)
├── worker/
│   ├── __init__.py
│   ├── redis_client.py          # Redis 연결 및 클라이언트
│   ├── tasks.py                 # 비동기 작업 정의
│   └── worker.py                # 워커 엔트리포인트
├── __init__.py
└── main.py                      # FastAPI 애플리케이션 엔트리포인트
deployment/
│
├── deploy.sh                    # 배포 스크립트
├── docker-compose.yml           # 기본 실행 구성
├── docker-compose.monit         # 모니터링 포함 실행 구성
├── nginx.conf                   # Nginx 설정
├── prometheus.yml               # Prometheus 설정
├── prometheus-rule.yml          # Prometheus rule 설정
└── generate_review.py           # 유틸/실행 스크립트
```

---

# Tech Stack

- **Python / FastAPI**
- **Redis** (Queue/Worker)
- **OpenAI API** (생성/요약 등)
- **AWS S3** (파일 저장)
- **Nginx** (Reverse Proxy)
- **Docker / Docker Compose**
- **Prometheus** (Monitoring)

---
# 📝 Git Commit Convention 📝

DearBelly Spring Server Git 커밋 메시지 작성 규칙

## 커밋 메시지 형식

```angular2html
<type>(<scope>): <subject>
```
> 예시 : feat(member): 회원가입 API 구현 <br>
> 이슈 번호를 커밋/PR 메시지에 포함하면, GitHub에서 자동으로 `(#4)` 형식으로 링크되어 작업 추적이 쉬워집니다.

---

## Type 목록

| Type       | 설명 |
|------------|------|
| `feat`     | 새로운 기능 추가 |
| `fix`      | 버그 수정 |
| `refactor` | 기능 변화 없는 리팩토링 |
| `del`      | 불필요한 코드 삭제 |
| `test`     | 테스트 코드 추가/수정 |
| `docs`     | 문서 작성 또는 수정 |
| `chore`    | 빌드, 설정, CI, 기타 유지관리 |

---

# 📝 Branch Naming Convention 📝

## 브랜치 네이밍 컨벤션

```angular2html
<type>/<작업-설명>-<이슈번호>
```
- main: 배포 가능한 안정적인 코드
- develop: 개발 브랜치
- `type`: feat, fix, refactor 등
- `작업-설명`: 소문자-케밥케이스(kebab-case)로 작성
- `이슈번호`: GitHub 이슈 번호 연결용
> 예시: `feat/social-login-4`

---
