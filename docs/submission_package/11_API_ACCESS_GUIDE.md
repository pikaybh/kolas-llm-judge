# 시험기관 API 접근·권한·Credential 인계 가이드

- 문서 ID: `KOLAS-DOC-011`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- 현재 official runtime base URL: `https://api.seexr.dev/api`
- 최종 공인시험 base URL: `PENDING — immutable SUT release 확정 시 freeze`
- Official SUT agent: `risk-assessment`

> 시험기관에는 관리자 계정이나 장기 static token을 주지 않는다. 현재 Core 권한모델에서 실질적인 최소권한은 **전용 active 일반 사용자(`Role.USER`) 계정 + 필요한 AI token allowance**이며, 하네스는 email/password로 로그인한 뒤 short-lived access token과 rotating refresh token을 메모리에서만 사용한다.

## 1. 접근 설계 원칙

1. 시험기관 전용 계정을 일반 서비스 사용자와 분리한다.
2. `Role.ADMIN`을 부여하지 않는다.
3. admin RBAC permission을 부여하지 않는다.
4. 시험계정 Saved Instruction은 빈 문자열로 고정한다.
5. 프로젝트를 연결하지 않은 독립 chat session을 사용한다.
6. 시험에 충분한 AI token allowance를 시험기간 동안 확보한다.
7. email/password와 OpenAI API key는 Git/HWP/Issue/run artifact에 저장하지 않는다.
8. 시험 종료 후 refresh/device session을 폐기하고 계정의 계속 사용 여부를 결정한다.
9. 최종 base URL과 server release는 시험 직전 change freeze한다.

## 2. 최소권한 모델

현재 Core에는 KOLAS endpoint만 따로 허용하는 OAuth scope/API-scope 토큰 체계가 없다.

Relevant global guards:

- `JwtAuthGuard`
- `RolesGuard`
- `AdminRbacGuard`
- `AdminMfaStepUpGuard`
- `SubscriptionAccessGuard`

`/agents`의 KOLAS 관련 endpoint는 별도 `@Roles(Role.ADMIN)`을 요구하지 않는다. 따라서 현재 구현에서 시험용 최소권한 계정은 다음과 같다.

| 항목 | 요구값 |
|---|---|
| account status | `active` |
| role | `user` |
| admin role | 없음 |
| admin RBAC | 없음 |
| admin MFA | 불필요/사용하지 않음 |
| project membership | 불필요 |
| Saved Instruction | empty |
| AI token allowance | 시험 전체를 차단하지 않을 충분한 allowance |

### 2.1 AI token entitlement

`POST /agents/{agentId}/runs`는 global `SubscriptionAccessGuard`에서 `assertAiTokenAllowance(userId)`를 수행한다.

따라서 `Role.USER`만 맞아도 충분한 것은 아니다. `tokens_limit`이 유한한 경우 `tokens_used < tokens_limit`이어야 한다. 한도를 소진하면 Core는 `403 AI_TOKEN_LIMIT_EXCEEDED`로 run 생성 자체를 거부한다.

시험 전 다음 authenticated endpoint로 상태를 확인할 수 있다.

```text
GET /users/me/plan
```

응답의 다음 필드를 확인한다.

```text
usage.tokens_used_month
usage.tokens_limit
usage.period_start
usage.period_end
```

최종 시험 시작 전 담당자가 **425-case full run 및 필요한 재시도/재실행을 방해하지 않을 allowance**가 설정되어 있음을 확인한다. 필요한 정확 token 양을 본 문서에서 추정해 숫자로 고정하지 않는다.

## 3. 사용자 데이터 격리

### 3.1 Chat session

`POST /chat/sessions`로 생성한 session은 authenticated `user.sub`에 귀속된다.

Core `ChatService`는 public session을 조회할 때 `publicId + userId`를 함께 조건으로 사용한다. 다른 사용자 session을 동일 ID로 조회할 수 없다.

### 3.2 Agent run

run 생성 시 Core가 session을 다시 `sessionId + userId` 기준으로 확인하고, run에도 `userId`가 저장된다.

`GET /agents/runs/{runId}/events`는 stream 시작 전에 `getOwnedRun(runId, userId)`를 호출한다. run owner가 아니면 `403 Forbidden`이다.

따라서 시험기관 전용 사용자 계정을 쓰면 해당 계정의 시험 session/run이 다른 일반 사용자와 논리적으로 분리된다.

## 4. Credential 종류와 저장 위치

### 4.1 SEEXR credential

공식 시험 권장:

```text
SEEXR_EMAIL=<secure channel>
SEEXR_PASSWORD=<secure channel>
```

하네스는 이 값을 이용해 로그인하고 access/refresh token을 런타임 메모리에만 유지한다.

`SEEXR_API_TOKEN` static token 방식은 smoke/development 편의용으로는 가능하지만, 장시간 공식시험에서 access token 만료 후 스스로 갱신할 수 없으므로 권장하지 않는다.

### 4.2 OpenAI Judge credential

```text
OPENAI_API_KEY=<secure channel>
```

Judge credential은 SEEXR SUT 계정과 별개다.

### 4.3 절대 저장하지 않는 위치

다음에는 실제 secret을 넣지 않는다.

- Git
- GitHub Issue
- HWP/HWPX
- Markdown 제출본문
- `manifest.json`
- `run_seal.json`
- `summary.json`
- screenshot
- 메신저 평문

문서에는 `[별도 보안채널 제공]` 또는 environment variable name만 기록한다.

## 5. 인증 lifecycle

현재 Core effective 설정(2026-10-11 Green):

| 항목 | 값 |
|---|---|
| JWT access lifetime | `15m` |
| JWT refresh lifetime | `7d` |
| refresh rotation | 사용 시 기존 refresh token revoke 후 새 token 발급 |
| login account status | `active` required |
| admin MFA | admin only; 시험계정은 admin 사용 금지 |

이 TTL은 현재 `.env.local`과 코드 기본값이 일치한 값이다. 최종 공인시험 release가 다른 environment를 사용하면 실제 effective value를 다시 기록한다.

### 5.1 하네스의 401 recovery

하네스는 authenticated request에서 401이 발생하면:

1. 현재 refresh token으로 `POST /auth/refresh` 시도
2. 성공하면 새 access/refresh token으로 교체
3. refresh 실패 시 email/password로 `POST /auth/login` 재시도
4. concurrent 401에서는 lock을 사용하여 중복 refresh rotation을 방지

따라서 공식시험은 renewable account credential이 필요하다.

## 6. Credential 회수 / revoke

시험 종료·담당자 변경·credential 노출 의심 시 다음 순서로 회수할 수 있다.

### A. 현재 login/device session 종료

```text
POST /auth/logout
```

현재 refresh token 또는 연결된 device session을 revoke한다.

### B. 특정 device session 강제 종료

```text
GET    /auth/devices
DELETE /auth/devices/{deviceSessionId}
```

### C. 계정 전체 비활성

관리/운영 절차를 통해 시험계정 상태를 `inactive`로 변경하거나 계정 탈퇴 처리하면 login/refresh가 차단되고 모든 device session을 폐기할 수 있다.

`DELETE /auth/me`는 사용자 스스로 account를 inactive 처리하고 모든 device session을 revoke하는 endpoint지만, 공식기관 계정 폐기정책은 운영자가 별도로 승인한 절차를 따른다.

### D. OpenAI key

OpenAI credential은 provider 측 project/key 관리화면에서 별도 rotate/revoke한다. SEEXR logout과 연동되지 않는다.

## 7. Current / Final base URL

현재 frozen evaluator runtime:

```text
https://api.seexr.dev/api
```

하지만 `seexr.dev`는 Green development/pre-release 환경이다. 최종 공인시험에서 그대로 사용할지, dedicated KOLAS deployment 또는 clean tagged production endpoint를 사용할지는 Phase 2 final SUT freeze에서 결정해야 한다.

**공식 시험 시작 후 base URL을 변경하지 않는다.**

변경 시 다음을 다시 수행한다.

- SUT version/source fingerprint freeze
- endpoint/auth preflight
- test account entitlement 확인
- Saved Instruction empty 확인
- AJQG
- 필요 시 clean-room drill

## 8. KOLAS harness가 사용하는 endpoint

Base URL 뒤의 path:

| Method | Path | 목적 | 인증 |
|---|---|---|---|
| POST | `/auth/login` | access/refresh token 발급 | public credential exchange |
| POST | `/auth/refresh` | rotating refresh | refresh token |
| GET | `/agents` | `risk-assessment` agent 활성 확인 | Bearer |
| GET | `/users/me/plan` | token allowance 사전 확인 | Bearer |
| POST | `/chat/sessions` | 시험 case용 session 생성 | Bearer |
| POST | `/agents/risk-assessment/runs` | durable 위험성평가 run 생성 | Bearer + AI allowance |
| GET | `/agents/runs/{runId}/events?after={sequence}` | SSE result/replay | Bearer + run ownership |
| POST | `/auth/logout` | refresh/device session revoke | Bearer/cookie context |

본 시험에는 admin endpoint, 결제 endpoint, user-management endpoint가 필요하지 않다.

## 9. 인증 예시

실제 credential은 예시에 넣지 않는다.

### 9.1 Login request

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "<TEST_ACCOUNT_EMAIL>",
  "password": "<TEST_ACCOUNT_PASSWORD>"
}
```

응답에서 일반 사용자 계정은 access/refresh token을 받을 수 있다. 실제 token 문자열을 실행기 로그/HWP에 복사하지 않는다.

### 9.2 Bearer request

```http
GET /api/agents
Authorization: Bearer <ACCESS_TOKEN>
```

### 9.3 Session create

```http
POST /api/chat/sessions
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json

{
  "agentId": "risk-assessment"
}
```

실제 하네스는 반환된 public session ID를 다음 run 요청에 사용한다.

### 9.4 Risk run create — 구조 예시

```http
POST /api/agents/risk-assessment/runs
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json

{
  "sessionId": "<PUBLIC_SESSION_ID>",
  "clientRequestId": "<UUID>",
  "message": "<CASE_MESSAGE>",
  "context": {
    "riskAssessmentMethod": "빈도강도법 5x4",
    "modelMode": "fast",
    "reasoningStyle": "balanced"
  }
}
```

`clientRequestId`는 UUID 형식이어야 하며, 하네스는 동일 run/case retry에서 같은 값을 재사용한다.

### 9.5 SSE

```http
GET /api/agents/runs/<RUN_ID>/events?after=<LAST_SEQUENCE>
Authorization: Bearer <ACCESS_TOKEN>
Accept: text/event-stream
```

SSE 재접속 시 마지막 sequence 이후부터 durable event replay를 요청한다.

## 10. Timeout / retry / rate limit

Official harness 현재값:

- request/SSE timeout: `180 s`
- max retries: `3`
- 총 create attempt 최대: `4`
- retry backoff: `0.5 → 1.0 → 2.0 s` (현재 세 번의 retry)
- retryable HTTP: `408, 425, 429, 500, 502, 503, 504`
- retryable transport: timeout / transport error

### 10.1 Core throttle

Green 환경 2026-10-11 effective config:

- `@nestjs/throttler` `6.5.0`
- global `THROTTLE_LIMIT=100`
- global `THROTTLE_TTL=60`
- v6.5.0 TTL unit은 milliseconds이므로 global window는 현재 코드상 `60 ms`
- `/auth/login`: explicit `10 / 60,000 ms`
- `/auth/refresh`: explicit `20 / 60,000 ms`

Global `60 ms`는 의도 여부와 별개로 **현재 effective configuration을 있는 그대로 기록한 것**이다. 최종 공인 endpoint에서는 throttle config도 release manifest와 함께 재확인한다.

429 응답은 하네스의 retryable status에 포함된다.

## 11. 오류 처리

| 상태/상황 | 처리 |
|---|---|
| 400 | 입력/계약 오류, 자동 retry 대상 아님 |
| 401 | refresh → 필요 시 login recovery |
| 403 `AI_TOKEN_LIMIT_EXCEEDED` | account entitlement 문제; 자동 transient retry로 해결하지 않음 |
| 403 run/session ownership | account/session mismatch; 시험 중단 및 설정 확인 |
| 408/425 | bounded retry |
| 429 | bounded retry + backoff |
| 500/502/503/504 | bounded retry |
| network timeout/transport | bounded retry |
| SSE disconnect | 마지막 sequence 이후 reconnect/replay |
| terminal `run-failed` / `run-cancelled` | reconnect하지 않고 SUT failure 기록 |

### 11.1 Official preflight account-state gate

2026-10-11 evaluator revision부터 `doctor --live --official --require-ready`는 인증 후 다음을 자동 검사한다.

- `GET /instructions/me` → normalized Saved Instruction이 empty인지 확인; 원문은 출력/저장하지 않고 SHA-256만 기록
- `GET /users/me/plan` → `tokens_used_month` / `tokens_limit`로 AI token allowance 확인

현재 내부 rehearsal 계정은 allowance는 사용 가능하지만 Saved Instruction이 NON_EMPTY이므로 official preflight에서 FAIL한다. 해당 계정의 instruction 내용은 본 패키지에 기록하지 않는다. 최종 시험에는 별도 empty-instruction 계정을 provisioning한다.

## 12. 시험기관 계정 provisioning checklist

운영 담당자가 secret을 제외한 체크 결과만 서명/기록한다.

- [ ] 기관/담당자 확정
- [ ] 전용 계정 생성
- [ ] `status=active`
- [ ] `role=user`
- [ ] admin/RBAC 권한 없음
- [ ] Saved Instruction empty 확인 — official live preflight 자동검사
- [ ] project 연결 없음 또는 시험에 영향 없는 상태 확인
- [ ] `/users/me/plan`에서 AI token allowance 확인 — official live preflight 자동검사
- [ ] access/refresh TTL 확인
- [ ] final base URL 확인
- [ ] `GET /agents`에서 `risk-assessment` 활성 확인
- [ ] `doctor --live --official --require-ready` PASS
- [ ] 시험 종료 시 revoke 책임자/시점 기록

비밀번호, access token, refresh token, OpenAI API key 자체는 체크리스트에 기입하지 않는다.

## 13. Change-freeze notification

다음 변경은 시험기관에 통지하고 재preflight/requalification 여부를 판단한다.

- base URL / TLS / reverse proxy 변경
- Core/Agents commit 변경
- auth TTL 또는 refresh policy 변경
- role/guard/entitlement 정책 변경
- test account role/status/entitlement 변경
- Saved Instruction 변경
- SUT model/workflow/runtime 변경
- RA/Law stateful dependency snapshot 변경

시험 시작 후 발견된 임의 변경은 가능한 한 즉시 중단하고 run validity를 재평가한다.

## 14. 현재 미완료

2026-10-11 현재 다음은 문서만으로 완료할 수 없는 실제 기관 인계 항목이다.

1. 시험기관 담당자/전용 계정 실제 생성
2. 시험기간에 충분한 entitlement 실제 부여
3. 시험 직전 Saved Instruction empty 확인
4. final immutable SUT endpoint/base URL 결정
5. credential 안전 전달 및 수신확인
6. 시험 종료 후 revoke 실행 기록

따라서 Phase 7은 접근모델·권한·인증·회수 절차는 정의 완료했으나 실제 기관 credential handoff는 `PENDING`이다.
