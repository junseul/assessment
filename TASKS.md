# TASKS — 성향파악 / 전략게임 장기 개선

작업 범위: `traits`(성향파악), `games` 앱 중 `expedition-investment`(전략게임) 슬러그만.
다른 게임, 로그인/회원관리, 공통 UI, 인증, DB 구조, 배포는 수정 대상 아님.

## 성향파악 (traits)

- [x] **[P1] 문항별 응답시간·타임아웃 여부가 전혀 저장되지 않음**
  - 현재 문제: `survey_detail.html`이 문항마다 6~8초 제한시간을 이미 재고 있는데(`deadline`, `currentLimitMs`), 서버로는 `{q001: 3, q002: 5, ...}` 최종 값만 전송한다. 응답시간, 타임아웃(무응답) 여부, 제한시간 자체가 유실됨.
  - 개선 이유: 지시문 3장 "데이터" 항목(문항별 응답, 응답시간, 극단값/일관성 지표)의 최소 전제 조건. 응답시간 없이는 무성의 응답·비정상적으로 빠른 응답을 탐지할 방법이 없음.
  - 수정 범위: `traits/templates/traits/survey_detail.html`(payload에 문항별 rt_ms/timed_out 포함), `traits/views.py`(`submit_response` 검증 로직), `traits/models.py`는 그대로(JSONField라 스키마 변경 불필요), `traits/survey_definition.py`(`score_answers`가 `{value, rt_ms}` 형태를 읽도록).
  - 측정 목적: 응답 신뢰성(반응시간 이상치, 극단응답 탐지) 데이터 확보.
  - 완료 조건: SurveyResponse.answers에 문항별 rt_ms 저장, 기존 score_answers 정상 동작, 기존 테스트 통과.
  - 테스트 방법: `traits/tests.py`에 rt_ms 포함 payload 회귀 테스트 추가.
  - **API 요청 구조 변경(AGENTS.md 7장) → 사용자 승인 필요. 구현계획 별도 제시.**

- [x] **[P2] 타임아웃(무응답)이 유효 응답과 동일하게 조용히 수용됨**
  - 완료: 위 P1과 함께 처리됨. `score_answers`가 도메인별 `timed_out` 카운트를 반환. `reports` 쪽 노출은 공통 템플릿이라 범위 밖 — 후보로 남김.

- [x] **[P2] 일관성/극단응답 지표 없음**
  - 완료: `response_quality()` 추가 — `extreme_response_rate`, `avg_rt_ms`, `fast_response_rate`(<1.5초 응답 비율). 지시문 9장 시뮬레이션(전항 최고점/최저점/중간값/무작위/비정상 속응답) 테스트로 검증.
  - 보류: 동일응답 연속반복(straightlining) 지표는 구현하지 않음 — Postgres jsonb는 JSON 객체의 key 순서를 보존한다는 보장이 없어, 저장된 `answers` dict만으로는 실제 응답 순서를 신뢰할 수 없음. 순서를 신뢰성 있게 확보하려면 문항별 순번을 별도로 저장해야 하며, 이는 또 다른 API 요청 구조 변경(승인 필요)이라 이번 라운드에서는 후보로만 남김.

## 전략게임 (expedition-investment)

- [x] **[P1] 페이오프 테이블이 클라이언트 JS에 그대로 노출됨 — 측정 타당성 붕괴 위험**
  - 현재 문제: `expedition_investment.html`의 `decks = {A:{winAmt:100, lossProb:0.5, lossAmt:250}, ...}`와 `REVERSAL_INDEX=50`이 브라우저에 그대로 전송된다. 개발자도구로 페이지 소스를 보면 각 지역의 정확한 손실확률·금액과 반전 시점을 즉시 알 수 있어, "확률은 알려드리지 않는다"는 게임 전제가 깨지고 위험선호·손실회피·탐색행동 측정이 무의미해진다.
  - 개선 이유: 지시문 2장 "특정 답변으로 쉽게 결과를 조작할 수 있는가"에 정면으로 해당하는 가장 심각한 공략 가능성 문제.
  - 수정 범위: `games/views.py`(신규 라운드 판정 API), `games/templates/games/expedition_investment.html`(클라이언트는 선택만 전송, 결과는 서버 응답으로 받음), `games/tests.py`.
  - 측정 목적: 실제 확률 구조를 모르는 상태에서의 탐색/위험선택 행동을 정확히 측정.
  - 완료 조건: 페이지 소스·네트워크 탭 어디에도 확률/손실액/반전 시점이 노출되지 않음. 기존 summary 지표(exploration_rate, learning_rate 등) 계산 결과가 서버 권위 데이터 기준으로 동일하게 산출됨.
  - 테스트 방법: 신규 엔드포인트 단위테스트 + 기존 `ExpeditionInvestmentTests` 회귀.
  - 완료: `games:expedition_round` 엔드포인트 추가, 클라이언트는 선택만 전송하고 서버가 세션 상태로 손익/반전을 판정. `winAmt`/`lossProb`/`lossAmt` 문자열이 렌더링된 페이지에 더 이상 존재하지 않음(회귀 테스트로 고정).

- [x] **[P2] 손실회피/위험선호 개별 지표 부재**
  - 완료: `outcome_variance`(실현된 시행 결과의 분산 — 위험선호 대리지표), `loss_chasing_index`(손실 직후 시행의 평균 절대변동폭 − 전체 평균 절대변동폭 — 손실추격 대리지표) 추가. 페이오프 테이블이 서버로 옮겨졌으므로 확률 자체가 아니라 실현된 `amount`만으로 계산.

- [ ] **[P3] 결과 리포트가 전략게임 지표를 전혀 보여주지 않음** (구현 안 함, 후보만 기록)
  - 현재 문제: `reports/candidate_detail.html`의 게임 섹션은 `accuracy`/`avg_rt_ms`/`n_trials`만 렌더링. expedition-investment의 실제 요약 지표(exploration_rate 등)는 화면에 노출되지 않음.
  - 범위 문제: `reports/candidate_detail.html`은 9개 게임이 공유하는 템플릿이라 작업 범위(전략게임 단독) 밖의 공통 파일. 수정하려면 다른 8개 게임 렌더링에 영향이 없는지 별도 검토 필요.
  - 처리: 이번 라운드는 구현하지 않고 후보로만 기록. 사용자가 범위 확장을 승인하면 진행.

## 완료 조건 (전체)
- [x] 성향파악 P0=0, P1=0(승인 후), 승인된 P2 완료
- [x] 전략게임 P0=0, P1=0(승인 후), 승인된 P2 완료
- [x] 관련 테스트 전체 PASS(전체 83개), 기존 기능 regression 없음

이번 라운드에서 발견된 모든 P0/P1/P2 항목 처리 완료. 남은 항목은 모두
범위 확장(다른 게임 공유 템플릿 수정) 또는 추가 API 승인이 필요해 후보로만
기록. 다음 라운드에서 다룰 후보:

1. `reports/candidate_detail.html` — 전략게임 지표 노출 (공통 템플릿, 범위 확장 필요)
2. 성향파악 응답 순서 기반 straightlining 지표 (문항 순번 저장을 위한 API 구조 변경 필요)
3. (장기 개선 원칙 3~8차 관점: 게임 밸런스/사용성/예외상황/테스트 부족 영역/코드 품질) 재검토는 다음 라운드에서 계속
