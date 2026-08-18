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
- [x] **[P2] 동일응답 연속반복(straightlining) 지표 부재**
  - 완료(2라운드): 문항별 `seq`(실제 표시 순서, 클라이언트가 이미 추적하던 `currentIndex`) 저장 추가. `response_quality()`가 `seq` 기준 정렬 후 `max_same_answer_streak` 계산. 기존 저장된 응답(seq 없음)은 안전하게 None으로 저하.

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

- [x] **[P3] 결과 리포트가 전략게임 지표를 전혀 보여주지 않음**
  - 완료(2라운드, 범위 확장 승인됨): `reports/views.py`/`candidate_detail.html`에 `game_slug == 'expedition-investment'`일 때만 적용되는 전용 블록 추가(final_total/exploration_rate/learning_rate/loss_stay_rate/reversal_adaptation/outcome_variance/loss_chasing_index). 다른 8개 게임은 기존 accuracy/avg_rt_ms/n_trials 블록 그대로 유지 — 회귀 테스트로 고정. 성향파악 섹션에도 extreme_response_rate/fast_response_rate/max_same_answer_streak 노출.

## 2라운드에서 추가로 발견·수정한 항목 (코드 품질/예외상황)

- [x] **[P1] 비객체 JSON 바디로 500 크래시** — `submit_response`(traits), `submit_result`(games, 9개 게임 공유), `expedition_round` 모두 `payload.get(...)`을 `payload`가 dict인지 확인 없이 호출해, JSON 배열/스칼라 바디가 오면 처리되지 않은 AttributeError로 500이 났다. `isinstance(payload, dict)` 가드 추가. `submit_result`는 공유 파일이지만 정상 요청 동작은 전혀 바뀌지 않는 순수 방어적 수정.
- [x] **[P1] 리포트에서 0 값이 "-"(데이터 없음)으로 오인 표시** — Django `default` 필터는 0/0.0을 falsy로 취급한다. `exploration_rate: 0`이나 `loss_chasing_index: 0` 같은 실제 값이 "데이터 없음"과 구분되지 않았다. `default_if_none`으로 교체(성향파악 종합점수 포함).
- [x] **[코드 품질] 시행 횟수 매직넘버 중복** — 클라이언트 `N_TRIALS=100`과 서버 `EXPEDITION_TRIALS=100`이 따로 존재해 둘이 어긋나면 조기 종료되거나 101번째 요청이 400을 받는 구조였다. 서버가 매 라운드 응답에 `done` 플래그를 내려주고 클라이언트는 그것만 보고 멈추도록 변경 — 중복 상수 제거.
- [x] **[예외상황 테스트] 새로고침 시나리오** — expedition-investment 중간에 새로고침하면 서버 세션의 라운드 카운터가 되돌아가는지 회귀 테스트로 고정(`test_reloading_play_page_resets_round_progress`).

## 완료 조건 (전체)
- [x] 성향파악 P0=0, P1=0(승인 후), 승인된 P2 완료
- [x] 전략게임 P0=0, P1=0(승인 후), 승인된 P2 완료
- [x] 관련 테스트 전체 PASS(전체 96개), 기존 기능 regression 없음

1·2라운드에서 발견된 P0/P1/P2 항목 모두 처리 완료(straightlining 지표, 리포트
노출 포함 — 2라운드에서 범위 확장 승인됨). 다음 라운드 후보:

1. (장기 개선 원칙 5~8차 관점: 사용성/예외상황/테스트 부족 영역/코드 품질) 추가 재검토
2. `games/models.py`의 `GameResult.game_slug` 기본값이 `'go-nogo'`인데 현재 catalog에는 해당 슬러그의 게임이 없음 — 다른 8개 게임에도 걸쳐 있는 모델 레벨 이슈라 이번 범위(전략게임 단독) 밖. 수정하려면 Migration 검토 필요(AGENTS.md 7장 승인 대상).
