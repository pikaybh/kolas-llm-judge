# KOLAS 최종 HWP/HWPX 편집·인수인계 명세

- 문서 ID: `KOLAS-HWP-SPEC-001`
- 목적: Markdown만 전달받은 다른 에이전트가 기술 내용을 임의 해석하지 않고 공문형 HWP/HWPX 제출본을 제작할 수 있도록 하는 편집 계약

## 1. 우선순위

1. 시험기관이 제공한 공식 양식/작성요령이 있으면 그것을 최우선으로 따른다.
2. 기관 양식이 없거나 일부 항목만 규정되어 있으면 이 명세를 기본값으로 사용한다.
3. Markdown의 기술 내용과 HWP 디자인이 충돌하면 **기술 내용과 version/hash 값을 보존**한다.
4. 미확정 필드는 추측해서 채우지 않는다.

## 2. 문서 패키지 권장 구성

### 본문 공문

- 문서번호: `{{OFFICIAL_DOCUMENT_NUMBER}}`
- 시행일자: `{{ISSUE_DATE}}`
- 수신: `{{RECIPIENT_ORGANIZATION}}`
- 참조: `{{REFERENCE_RECIPIENT}}`
- 제목: `SEEXR 위험성평가 AI KOLAS 시험 재현성 및 측정시스템 제출자료`
- 발신기관: `{{SENDER_ORGANIZATION}}`
- 담당/검토/승인: `{{AUTHOR}} / {{REVIEWER}} / {{APPROVER}}`

본문은 짧은 송부 공문으로 구성하고, 기술 상세는 **붙임/별첨 보고서**로 분리하는 것을 기본안으로 한다.

### 붙임 권장안

1. 붙임 1. 시험방법 및 시험대상 시스템 명세서
2. 붙임 2. 모델·추론 고정 설정 명세서
3. 붙임 3. Ground Truth 구축·출처·전문가 검증 보고서
4. 붙임 4. 측정시스템(Evaluator/Judge) 명세 및 적격성 검증 보고서
5. 붙임 5. 시험 재현 절차 및 API 접속 가이드
6. 붙임 6. 버전·무결성·변경통제 명세서
7. 붙임 7. 제출 파일 및 전자자료 목록

기관 요구에 따라 하나의 통합 기술보고서로 합칠 수 있으나, Markdown 원본의 문서 ID와 traceability는 유지한다.

## 3. Markdown → HWP 변환 계약

각 Markdown 문서는 최종적으로 다음 metadata를 가져야 한다.

```text
문서 ID:
제목:
버전:
상태: DRAFT | REVIEW | APPROVED | FROZEN
작성자:
검토자:
승인자:
기준일:
관련 Git commit/tag:
관련 GT/evaluator version:
```

HWP 작성 에이전트는 다음 규칙을 따른다.

- Markdown H1은 별첨 문서 제목 또는 장 제목으로 변환한다.
- H2는 `1.`, `2.` 수준의 장 제목으로 변환한다.
- H3는 `가.`, `나.` 또는 `1.1`, `1.2` 중 기관 양식에 맞는 체계를 사용한다.
- 코드블록의 명령/API 예시는 본문 고정폭 스타일 또는 별첨 표로 변환한다.
- Markdown table은 HWP 표로 재작성하되 행/열 의미를 변경하지 않는다.
- 체크박스는 **작업관리용**이므로 최종 HWP 본문에는 원칙적으로 포함하지 않는다. 단, 제출 체크리스트가 요구되는 경우 별도 부록으로 이동한다.
- 파일경로, commit SHA, checksum, model ID는 줄임표로 생략하지 않는다.
- `{{PLACEHOLDER}}`는 실제 확정 증적이 있을 때만 치환한다. 없으면 `[미확정]`으로 표시하고 최종 승인 전에 차단한다.
- `[별도 보안채널 제공]` 표기는 credential 값을 본문에 넣지 않고 그대로 유지한다.
- 내부 대화체, 메모, TODO 설명은 최종 문장으로 정리된 본문이 별도로 없는 한 제출본에 넣지 않는다.

## 4. 표와 증적 표현

핵심 값은 서술문에만 두지 말고 표로 반복하여 사람이 빠르게 대조할 수 있게 한다.

### 필수 표

- 시험대상 시스템 버전표
- repository/commit SHA 표
- 모델 및 추론 파라미터 표
- GT 버전/건수/hash 표
- GT source type 및 provenance coverage 표
- 전문가 자격/역할 표
- 전문가 검증 결과/일치도 통계 표
- evaluator 모델/config/prompt/schema version 표
- 재현 실행환경 표
- API endpoint/권한 표
- 제출 파일/checksum 표
- 변경이력 표

각 표에는 `표 N. <제목>`을 부여한다.

## 5. 그림

필요할 경우 다음 그림을 우선 사용한다.

- `Scenario → SUT → Generated Hazards → Evaluator → GT Match → Metric` 측정 흐름
- 제출 패키지 디렉토리 구조
- version/integrity chain

그림은 장식용이 아니라 재현 절차 이해에 도움이 될 때만 사용한다.

## 6. 문체

- 공적·검증 가능한 서술을 사용한다.
- `대략`, `아마`, `~인 것 같다` 같은 표현을 사용하지 않는다.
- 추정값을 확정값처럼 쓰지 않는다.
- 시험기관 요구사항과 SEEXR 내부 품질관리 기준을 혼동하지 않는다.
- 과거 내부 성능평가 수치와 공식 KOLAS 시험 수치를 명확히 구분한다.
- 제품 UI 명칭(`Sol`, `Fast` 등)과 API model identifier를 구분해서 표기한다.

## 7. 권장 본문 구조

### 공문 본문

1. 송부 목적
2. 제출자료 목록
3. 재현시험을 위한 별도 credential 전달 안내
4. 담당자/문의처
5. 붙임 목록

### 통합 기술보고서가 필요한 경우

1. 목적 및 적용범위
2. 용어 및 정의
3. 시험대상 시스템
4. 시험방법 및 평가 지표
5. AI 모델 및 추론 고정 설정
6. Ground Truth 구성 및 출처
7. 전문가 검증 절차 및 신뢰성 분석
8. Evaluator/Judge 구성 및 적격성 검증
9. 시험 재현 절차
10. API 접속 및 권한
11. 버전·무결성 관리
12. 변경통제
13. 제출자료 목록
14. 결론 및 확인

## 8. HWP 생성 전 차단 조건

다음 항목 중 하나라도 충족되면 `APPROVED` 최종본으로 만들지 않는다.

- `{{PLACEHOLDER}}`가 남아 있으나 미확정 목록에 기록되지 않음
- model identifier 또는 핵심 inference 설정이 코드/API와 대조되지 않음
- GT canonical file/hash가 확정되지 않음
- 전문가 검증이 완료되지 않았는데 완료된 것처럼 서술됨
- evaluator version/prompt가 고정되지 않음
- API credential 자체가 문서에 평문으로 들어감
- repository SHA가 실제 제출 package와 다름
- integrity manifest와 파일 내용이 불일치함

## 9. 최종 HWP QA 체크리스트

- [ ] 기관 양식 적용 여부 확인
- [ ] 문서번호/수신/발신/일자 확인
- [ ] 작성/검토/승인 정보 확인
- [ ] 붙임 번호와 본문 참조 일치
- [ ] 표/그림 번호 연속성 확인
- [ ] 모든 version/hash 대조
- [ ] 모든 수치가 근거 evidence와 일치
- [ ] 미확정 placeholder 0건 확인 또는 공식 미확정 처리
- [ ] secret 평문 노출 0건 확인
- [ ] 표가 페이지 밖으로 잘리지 않음
- [ ] 페이지 번호/머리말/꼬리말 일관성 확인
- [ ] PDF preview와 HWP 내용 일치 확인
- [ ] 최종 HWP/HWPX 및 PDF hash 기록

## 10. HWP 에이전트에게 전달할 최소 입력

HWP 생성 작업을 다른 에이전트에게 인계할 때 다음을 함께 준다.

1. `docs/kolas/` 전체
2. freeze된 GT 또는 GT의 제공 가능한 사본
3. version/integrity manifest
4. 필요한 표/그림 원본
5. 기관이 제공한 HWP 양식 또는 작성요령
6. 최종 승인된 조직명/수신처/담당자 등 행정정보
7. 실제 secret을 제외한 API 접속 정보

이 일곱 항목이 없다면 HWP 에이전트는 기술값을 추정하지 않고 누락 목록을 반환해야 한다.
