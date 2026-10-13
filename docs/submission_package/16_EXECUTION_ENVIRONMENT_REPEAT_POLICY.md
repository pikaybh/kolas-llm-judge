# 실행환경 및 반복시험 신규생성·세션·캐시 정책

- 문서 ID: `KOLAS-DOC-016`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-13`
- Evidence IDs: `EV-ENV-20261013`, `EV-REPEAT-POLICY-20261013`
- 관련 문서: `02_SYSTEM_UNDER_TEST.md`, `10_REPRODUCIBILITY_GUIDE.md`, `11_API_ACCESS_GUIDE.md`

## 1. 목적

시험기관 요청 중 다음 항목을 한 곳에서 명확히 답한다.

- SW/HW 환경 정보
- 반복마다 시스템 결과를 새로 생성하는지 여부
- cache/session 초기화 및 동일 입력 적용 방법

## 2. 2026-10-13 실험/감사 host 환경

| 항목 | 확인값 |
|---|---|
| OS | Ubuntu 24.04.3 LTS |
| Kernel | 7.0.0-30-generic |
| Architecture | x86_64 |
| CPU | Intel(R) Xeon(R) Silver 4410Y |
| CPU topology | 1 socket / 12 cores / 2 threads per core |
| Logical CPU | 24 |
| RAM | 269,942,763,520 bytes, 약 251 GiB |
| Virtualization | `systemd-detect-virt = none` |
| Local NVIDIA GPU | audit host에서 미검출 |
| Python | 3.12.3 |
| uv | 0.8.5 |
| Node.js | v23.11.1 |
| npm | 11.10.1 |

SUT의 생성 LLM 및 evaluator Judge는 외부 provider API를 호출하므로 local GPU가 시험 하네스 실행의 필수조건은 아니다.

본 표는 **2026-10-13 audit host 기록**이며 최종 공인 endpoint가 변경되면 시험 직전에 다시 수집하여 final manifest에 고정한다.

## 3. 공식 repeat의 신규 run 생성

사용자가 실행하는 공식 CLI는:

```bash
uv run kolas-llm-judge official-live
```

이다.

CLI는 기존 `run_id`를 입력받는 옵션을 노출하지 않는다. `official_live.py`는 `make_official_run_id()`를 통해 다음 형식의 새 run ID를 만든다.

```text
<UTC YYYYMMDDTHHMMSSZ>-official-live-<8-hex random suffix>
```

각 실행은 별도 `runs/<RUN_ID>/` 디렉터리를 사용한다.

따라서 full repeat 1과 repeat 2를 각각 정상적인 `official-live` 명령으로 수행하면 **서로 다른 run directory와 신규 SUT 결과**를 생성한다.

## 4. case별 신규 SEEXR session

`SeexrSutClient.run_case()`는 fresh SUT 실행 시 각 scenario에 대해:

1. `POST /chat/sessions`로 새 session 생성
2. 해당 session에 `POST /agents/risk-assessment/runs` 생성
3. SSE event stream에서 terminal content 수집

순서로 동작한다.

따라서 fresh official run의 각 case는 새 SEEXR chat session을 사용한다.

## 5. checkpoint reuse 범위

평가 하네스는 장시간 실행 복구를 위해 **같은 run directory 내부**에 있는 완료 checkpoint를 재사용할 수 있다.

이 기능은 한 번의 장시간 run이 중단된 뒤 동일 run을 복구하는 목적이다.

공인 반복시험 간에는 다음 규칙을 적용한다.

> 반복 1회는 신규 official run ID로 시작한다. 서로 다른 full repeat 간에는 이전 repeat의 `sut.json`, `parsed.json`, `binary_judge.json`, `result.json` 등 case checkpoint를 재사용하지 않는다.

## 6. retry와 신규 repeat의 구분

각 SUT 요청의 `clientRequestId`는:

```text
evaluation_run_id + case_id
```

에 대한 UUIDv5로 결정적으로 생성한다.

- 같은 run/case의 transient create-run retry: 동일 `clientRequestId` 재사용
- 다른 official repeat: `evaluation_run_id`가 다르므로 다른 `clientRequestId`

같은 retry ID 사용은 network retry 중 중복 run 생성을 방지하는 idempotency 조치이며 이전 full repeat output을 재사용하는 동작이 아니다.

## 7. 동일 입력 조건

반복시험에서는 다음 identity를 동일하게 유지한다.

- GT version/hash
- `scenarios_v1.jsonl` hash와 case order
- SUT release/config
- model identifiers/effective environment
- RA/Law snapshot identity
- test-account Saved Instruction empty 상태
- Judge model/config
- Judge prompt/rubric
- parser/metric code
- timeout/retry/failure policy

run ID 자체는 각 반복을 구분하기 위해 의도적으로 다르다.

## 8. application cache 감사

2026-10-13 Core, Agents, RA API tracked source에서 다음 application-level response/result cache 구현 지표를 검색했다.

- `CacheModule`
- `cache-manager`
- Redis/redis
- memoize/memoized
- LRU/lru-cache

해당 SUT 결과를 이전 요청에서 꺼내 반환하는 구현은 확인되지 않았다.

따라서 현재 확인 범위에서는 SEEXR application-level **위험성평가 output cache를 사용하지 않는다**고 기록한다.

## 9. provider-side input/prompt caching

외부 model provider는 동일한 input prefix의 처리비용 최적화를 위해 input/prompt caching을 적용할 수 있다. 과거 AJQG response metadata에서도 cached-token 정보가 관찰될 수 있다.

이는 이전 generated output 자체를 재사용하는 output/result cache와 구분한다.

제출 표현:

> 각 official repeat는 신규 run/session에서 SUT와 Judge를 다시 호출하여 결과를 생성한다. SEEXR application에서 이전 위험성평가 output을 반환하는 result cache는 사용하지 않는다. 외부 provider의 input/prompt caching이 발생할 수 있으나 prior generated output 재사용과는 별개이며, provider가 노출하는 경우 response metadata로 기록한다.

## 10. Timeout / Retry

기존 공식 runtime candidate:

- SUT timeout: 180 s
- SUT max retries: 3
- exponential backoff: 0.5 s 기반, bounded
- SSE reconnect: 최대 3회
- Judge timeout: 180 s
- Judge SDK max retries: 3

상세 규칙은 `01_TEST_METHOD.md`와 `11_API_ACCESS_GUIDE.md`를 따른다.
