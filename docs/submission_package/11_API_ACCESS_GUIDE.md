# 시험기관 API 접근·권한·Credential 인계 가이드 — 2026-10-26 개정

- 문서 ID: `KOLAS-DOC-011`
- 개정: `0.2-api-key` / 시험기관 협의용
- 현재 고정 official runtime: `https://api.seexr.dev/api` (Green)
- 계획된 Blue production: `https://api.seexr.co.kr/api` (Blue API Key 지원 소스의 별도 배포·검증 후 사용)
- 시험 에이전트: `risk-assessment` (임의 다른 agent로의 권한 확대 금지)

> **개정 핵심:** 일반 계정 이메일·비밀번호나 단기 JWT를 시험기관에 배포하는 대신, 가능한 한 **발급·철회 가능한 SEEXR API Key**를 권장한다. 현재 Core 개발판은 외부 평가용 `x-api-key` 인증 경로를 제한적으로 지원하도록 수정되었다. 코드 검증이 완료되어도 Blue 운영 배포와 시험기관 승인 전에는 'Blue 사용 가능'으로 표시하지 않는다.

## 1. 시험기관 credential 제공 절차

1. 실제 시험 대상 환경(현재 Green, 운영시험으로 이행할 때 Blue)에서 전용 일반 사용자 계정이 `active`인지 확인한다.
2. API 키 발급 엔드포인트 `POST /api/api-keys`에 로그인한 JWT로 접근하여 키를 생성한다. 키 생성은 JWT가 필요하며, 키 자체로 다른 키를 발급할 수 없다.
3. 가능한 경우 `permissions: ["risk-assessment:run"]`을 지정한다. 권한을 생략한 기존 키도 **서버가 허용하는 아래의 여섯 시험 API 경로만** 사용할 수 있다.
4. 발급 시 1회 표시되는 `sk-...` 원문을 사용자 승인 보안채널로 시험기관에 전달한다. 이후 키 원문 조회는 허용하지 않고 폐기·재발급한다.
5. `OPENAI_API_KEY`는 Judge 전용으로 별도 관리하며 SEEXR 키와 혼용하지 않는다.

예시 환경변수(실제 비밀값 기록 금지):

```dotenv
SEEXR_API_KEY=<secure-channel>
OPENAI_API_KEY=<secure-channel>
```

하네스 `SutConfig.from_env()`는 `SEEXR_API_KEY`를 최우선으로 선택하고 각 HTTPS 요청에 `x-api-key`를 첨부한다. 401 발생 시 비밀번호 로그인으로 우회하지 않는다. 토큰값은 manifest·개별 case 기록에 저장하지 않는다.

## 2. HTTP API 호출 순서

**현재 official runtime의 URL은 Green으로 고정**되어 있다. Blue에서 실제 시험하려면 시험기관과 대상 release/fingerprint를 다시 확정한 뒤 config 및 hash를 함께 갱신한다. 환경변수 `SEEXR_API_BASE_URL`만 변경해도 official runtime의 대상은 바뀌지 않는다.

| 순서 | Endpoint | 목적 |
|---|---|---|
| 1 | `GET /agents` | 연결 및 에이전트 목록 read-only 확인 |
| 2 | `GET /instructions/me` | 시험용 지시사항이 비어있는지 확인 |
| 3 | `GET /users/me/plan` | 시험계정 AI 토큰 사용량·허용량 확인 |
| 4 | `POST /chat/sessions` | case별 독립 session 생성 |
| 5 | `POST /agents/risk-assessment/runs` | `clientRequestId`로 중복 없이 실행 요청 |
| 6 | `GET /agents/runs/{runId}/events?after=N` | SSE로 생성결과·종료상태 수신 및 재연결 |

이외의 users/admin/files/project 변경/다른 agent API에는 발급 키로 접근할 수 없다. 현장 서비스의 JWT/Cookie 인증 경로는 종전대로 유지한다.

개념적인 curl 확인(가상 키 예시, 실제 값 출력 금지):

```bash
# API 키가 환경변수로 설정돼 있는 경우에만:
curl -sS -H "x-api-key: $SEEXR_API_KEY" \
  "https://api.seexr.dev/api/agents"
```

## 3. 사용자 귀속과 운영 정책

- API 키는 발급 사용자의 `userId`에 귀속된다.
- 사용자 상태가 `active`가 아니거나 키가 만료/폐기되면 인증되지 않는다.
- 요청별 사용자 역할은 반드시 `user`로 제한되어 관리자로 승격할 수 없다.
- Session과 Run은 키 소유자의 `userId`로 생성·조회된다.
- 기존 `SubscriptionAccessGuard`의 `assertAiTokenAllowance`와 SSE의 run 소유권 확인을 우회하지 않는다.
- 키 사용량 및 마지막 사용 시각은 서버에서 갱신된다. 이 기록과 시험 run별 request ID를 연결하여 추적한다.
- 일괄 실행 후 키 폐기, 계정 사용내역 감사, 로그 보존 범위는 시험기관과 합의한다.

## 4. 오류 처리 및 제한

| 상태 | 해석/조치 |
|---|---|
| 401 Invalid API key | 키 환경·원문·활성 상태를 확인; JWT로 묵시적 fallback 금지 |
| 403 API key not permitted | 시험 외 엔드포인트 접근이므로 요청 경로 확인 |
| 403 lacks risk-assessment:run | 발급된 명시 permissions를 확인하고 재발급 |
| 403 AI_TOKEN_LIMIT_EXCEEDED | 서버 entitlement / 시험 예산·허용량 조정 필요 |
| 404 Run not owned/not found | session/run 소유자 및 환경 혼동 여부 확인 |
| SSE 중단 | 마지막 durable sequence 이후 재연결; SUT 실패와 인프라 실패 구분 |

인증 자체를 점검하는 read-only 명령과 실제 AI 실행 명령은 다르므로 시험기관은 의도하지 않은 유료 본시험을 실행하지 않는다.

## 5. 기존 계정 방식의 호환성

과거 패키지는 `SEEXR_EMAIL`+`SEEXR_PASSWORD` 로그인과 access/refresh JWT 갱신 방식이었다. **기능 호환을 위해 남겨두되 외부 시험기관 전달 방식의 기본값으로 권장하지 않는다.** `SEEXR_API_TOKEN`은 유효기간이 짧은 JWT이므로 장기 official run에 단독 사용하지 않는다.

## 6. 시험 전 확인·승인

- [ ] Green 인증 및 SSE 경로 검증, CI/단위시험
- [ ] 시험대상 환경에서 단건 실 API 연결 검증(비용 동의 후)
- [ ] Blue 적용 여부, 운영 URI·release SHA·권한 검증
- [ ] 시험기관 시험방법/분모/Judge validation/반복회수 승인
- [ ] 비용 부담·보안 전달 경로·키 폐기 담당자 확인

**참조:** `15_METHOD_VALIDITY_AND_API_KEY.md`; `01_TEST_METHOD.md`; `10_REPRODUCIBILITY_GUIDE.md`.
