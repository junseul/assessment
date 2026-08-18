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

- [ ] **[P2] 일관성/극단응답 지표 없음**
  - 현재 문제: 동일 응답 반복, 극단값(1/5) 비율, 응답 변경 등 지시문 3장이 요구하는 지표가 전혀 계산되지 않음.
  - 개선 이유: 사회적 바람직성 편향·무성의 응답 탐지 근거 부재.
  - 수정 범위: `traits/survey_definition.py`에 `score_answers` 부가 지표 함수 추가(신규 API 계약 변경 아님 — 서버 내부 계산이므로 승인 불필요, 단 리포트 노출은 `reports` 공통 템플릿이라 범위 밖).
  - 완료 조건: 함수 단위 테스트로 극단응답/무성의 응답 시나리오 검증(지시문 9장 시뮬레이션).

## 전략게임 (expedition-investment)

- [x] **[P1] 페이오프 테이블이 클라이언트 JS에 그대로 노출됨 — 측정 타당성 붕괴 위험**
  - 현재 문제: `expedition_investment.html`의 `decks = {A:{winAmt:100, lossProb:0.5, lossAmt:250}, ...}`와 `REVERSAL_INDEX=50`이 브라우저에 그대로 전송된다. 개발자도구로 페이지 소스를 보면 각 지역의 정확한 손실확률·금액과 반전 시점을 즉시 알 수 있어, "확률은 알려드리지 않는다"는 게임 전제가 깨지고 위험선호·손실회피·탐색행동 측정이 무의미해진다.
  - 개선 이유: 지시문 2장 "특정 답변으로 쉽게 결과를 조작할 수 있는가"에 정면으로 해당하는 가장 심각한 공략 가능성 문제.
  - 수정 범위: `games/views.py`(신규 라운드 판정 API), `games/templates/games/expedition_investment.html`(클라이언트는 선택만 전송, 결과는 서버 응답으로 받음), `games/tests.py`.
  - 측정 목적: 실제 확률 구조를 모르는 상태에서의 탐색/위험선택 행동을 정확히 측정.
  - 완료 조건: 페이지 소스·네트워크 탭 어디에도 확률/손실액/반전 시점이 노출되지 않음. 기존 summary 지표(exploration_rate, learning_rate 등) 계산 결과가 서버 권위 데이터 기준으로 동일하게 산출됨.
  - 테스트 방법: 신규 엔드포인트 단위테스트 + 기존 `ExpeditionInvestmentTests` 회귀.
  - 완료: `games:expedition_round` 엔드포인트 추가, 클라이언트는 선택만 전송하고 서버가 세션 상태로 손익/반전을 판정. `winAmt`/`lossProb`/`lossAmt` 문자열이 렌더링된 페이지에 더 이상 존재하지 않음(회귀 테스트로 고정).

- [ ] **[P2] 손실회피/위험선호 개별 지표 부재**
  - 현재 문제: `learning_rate`, `exploration_rate`, `loss_stay_rate`, `reversal_adaptation`은 있지만, "손실 후 더 위험한 선택을 하는가(손실추격)", "고손실분산 덱 선호 비율(위험선호)" 같은 직접적인 위험태도 지표가 없음.
  - 수정 범위: `expedition_investment.html`의 `on_finish` 요약 계산부만(신규 API 아님, 기존 summary 필드에 항목 추가는 API 계약 확장이라 하위호환 유지 시 승인 불필요 — 단 위 P1과 함께 처리 권장).
  - 완료 조건: `high_variance_choice_rate`, `post_loss_risk_shift` 등 신규 지표가 summary에 추가되고 값이 합리적 범위(0~1 또는 상관 방향)로 산출.

- [ ] **[P3] 결과 리포트가 전략게임 지표를 전혀 보여주지 않음** (구현 안 함, 후보만 기록)
  - 현재 문제: `reports/candidate_detail.html`의 게임 섹션은 `accuracy`/`avg_rt_ms`/`n_trials`만 렌더링. expedition-investment의 실제 요약 지표(exploration_rate 등)는 화면에 노출되지 않음.
  - 범위 문제: `reports/candidate_detail.html`은 9개 게임이 공유하는 템플릿이라 작업 범위(전략게임 단독) 밖의 공통 파일. 수정하려면 다른 8개 게임 렌더링에 영향이 없는지 별도 검토 필요.
  - 처리: 이번 라운드는 구현하지 않고 후보로만 기록. 사용자가 범위 확장을 승인하면 진행.

## 완료 조건 (전체)
- 성향파악 P0=0, P1=0(승인 후), 승인된 P2 완료
- 전략게임 P0=0, P1=0(승인 후), 승인된 P2 완료
- 관련 테스트 전체 PASS, 기존 기능 regression 없음
