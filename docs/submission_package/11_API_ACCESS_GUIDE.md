# 시험기관 재현 API 사용법 — SEEXR 운영 서버

- 문서 ID: KOLAS-DOC-011
- 개정: 2026-10-27 / 시험기관 협의용
- **시험대상:** SEEXR Blue 운영 서비스, `https://api.seexr.co.kr/api`
- **인증:** SEEXR가 시험기관에 별도로 제공하는 API 키(`SEEXR_API_KEY`)만 사용
- **Judge:** 별도로 제공되는 OpenAI API 키(`OPENAI_API_KEY`)
- 이 문서는 **시험기관의 키 발급 절차를 설명하지 않는다.** 인증정보를 수령한 뒤 사용하는 절차만 다룬다.

## 1. 제공 자료와 준비

시험기관은 SEEXR가 전달한 (1) 실행 패키지, (2) GT 425 시나리오/843 기준 위험요인, (3) SEEXR 시험용 API 키, (4) Judge용 OpenAI 키를 준비한다. 두 키는 외부 제출 문서, 저장소, 검사 로그에 기재하지 않는다.

실제 시험 대상 서버는 **Blue 운영 API**로 단일화한다. 시험기관은 이 운영 환경 외의 서버에 접속하지 않는다. Blue용 인증 기능의 정식 배포 및 키 준비가 확인되지 않은 동안은 **시험 미개시** 상태이다.

키를 받은 뒤 패키지의 `.env`에 다음 이름으로 지정한다.

```dotenv
SEEXR_API_KEY=<SEEXR에서 전달한 운영 시험용 API 키>
OPENAI_API_KEY=<Judge 호출용 OpenAI API 키>
```

하네스는 SEEXR 요청마다 HTTP `x-api-key` 헤더를 전송한다.

## 2. 실행 순서

```bash
# 패키지 루트에서 실행 (Python 3.12+, uv 설치 후)
cp .env.example .env
# .env에 실제 SEEXR_API_KEY, OPENAI_API_KEY 지정
uv sync --frozen
uv run --env-file .env kolas-llm-judge doctor --official
```

`doctor --official`은 로컬 파일/설정의 사전 검증용이다. 이후 시험기관 담당자가 **읽기 전용 연결 확인**을 수행한다.

```bash
uv run --env-file .env kolas-llm-judge doctor --official --live
```

`--live`는 실제 서비스 인증 및 계획 상태를 확인하지만 위험성평가 425건을 생성하지 않는다. 정상 연결이 확인된 뒤 실행 비용·반복횟수·측정 지표·분모가 승인되면 아래 본시험을 수행한다.

```bash
uv run --env-file .env kolas-llm-judge official-live
```

**주의:** 마지막 명령은 실제 SEEXR 위험성평가 및 OpenAI Judge 호출을 수행해 비용을 발생시키므로 승인 없이 실행하지 않는다.

## 3. HTTPS 내부 호출 흐름

| 순서 | 방법·경로 | 역할 |
|---|---|---|
| 1 | GET /agents | 읽기 전용 접속 점검 |
| 2 | GET /instructions/me | 시험계정에 별도 사용자 지시가 없는지 점검 |
| 3 | GET /users/me/plan | 시험 실행 가능 할당량 확인 |
| 4 | POST /chat/sessions | 시나리오별 독립 세션 생성 |
| 5 | POST /agents/risk-assessment/runs | `clientRequestId`가 있는 위험성평가 실행 |
| 6 | GET /agents/runs/{runId}/events?after=N | SSE 결과 수신·재연결 |

모든 URL은 상단의 `https://api.seexr.co.kr/api`에 위 경로를 이어 붙인 것이다. 하나의 키는 발급된 시험계정에 귀속되며, 권한/상태/만료/철회 및 사용량 정책은 서버에서 검증된다.

## 4. 오류 및 보완

- `401`: 전달받은 키와 Blue 운영 환경의 일치·만료·폐기 상태 확인. 실패 시 로그인 등 다른 방식으로 자동 우회하지 않는다.
- `403`: 허용하지 않는 경로/키 권한/AI 사용량 제한 확인.
- `404`: run ID·세션 소유자·시험 환경 확인.
- SSE 연결 중단: 마지막 durable sequence부터 복구하고 로그에 재연결 횟수를 남긴다.
- 본시험 평가 불가 사례: SUT 미완료와 Judge/전송 인프라 장애를 분리 기록한다.

## 5. 시험 전 확정할 사항

본 문서의 **Blue URL은 시험 대상으로 제안하는 단일 환경**이다. 시험기관은 실제 시험 전에 SEEXR 담당자로부터 Blue API 키 유효성, 해당 기능의 Blue 배포 완료, 모델/서비스 릴리스, Judge 사용 비용, 반복 횟수, 공식 측정방법 및 분모 확정을 확인받는다.

해당 확인이 끝나기 전까지 `official-live`의 성적을 공인시험 결과로 표시하지 않는다.
