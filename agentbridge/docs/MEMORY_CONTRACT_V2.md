# Scratchpad decision / observation / memory contract v2

2026-09-29 작성 / 2026-09-30 완료 · 범위: 계약과 최소 검증. **실제 LLM 성능 실험이나 live Mindustry benchmark 구현이 아니다.**

## 1. Changed files와 보존 경계

- `experiments/memory_sensitive_v2.json`: 버전2 계약, 두 paired-history case, evaluator 전용 utility/정답 참고값.
- `research/memory_contract.py`: public observation projection, 공통 request, pairing 검사, legality-only decision validation, bounded memory v2/store, 단발 provider 경계.
- `research/runner.py`, `research/metrics.py`: 기존 mock runner의 flow milestone/terminal 성공 분리, 미해결 실패 veto, transport 실패 기록.
- `research/condition.py`: legacy reset hook에 실제 context loss가 아니라는 표식 추가.
- `tests/test_memory_contract.py`, `tests/test_terminal_outcomes.py`: 계약·누출·실패 반례 검사. `tests/test_experiment_runner.py`의 기존 metric fixture 1개는 새 terminal/recovery 의미에 맞게 보강.
- `docs/PROGRESS.md`, `docs/ROADMAP.md`, `docs/SCRATCHPAD_EVALUATION.md`, 이 문서: 상태·한계·다음 gate 정리. 직전 승인된 `docs/AUDIT_2026-09-29.md`도 checkpoint에 보존.

기준 checkpoint는 `596ad51`. 시작 시 변경분은 직전 감사의 PROGRESS 수정과 감사 보고서뿐이었다. 기존 `agent/`, `src/`, Gradle 설정, logistics v1 manifest, AUTONOMOUS_DEMO/LOGISTICS_DEMO, GUI/headless 원본 로그·save·배포 JAR는 변경하지 않는다. 기존 agent에 새 정책을 주입하거나 기존 Qwen 호출 방식을 교체하지 않는다.

## 2. Versioned benchmark specification

| 구분 | Logistics v1 | Memory-sensitive v2 |
|---|---|---|
| ID | `autonomous-early-game-logistics-v1` | `memory-sensitive-logistics-v2` |
| 역할 | 정상 실행 smoke / 완전 관측 negative control | 기억 접근이 판단에 영향을 줄 수 있는 계약 microcase |
| 실제 게임 증거 | 과거 GUI/headless 있음 | 없음 |
| executor | 기존 정상 game runtime | `proposal-only-v2`, 명령 제안까지, game 실행 없음 |
| 평가 | mock terminal 오류만 이번 수정 | evaluator-only counterfactual utility, game 성공률 아님 |
| 보존 | 기존 manifest 그대로 | 별도 JSON과 별도 policy module |

v2의 `cases[].histories`, `expected_preference`, `outcome_utility`, history ID는 **evaluator/test 전용**이다. production policy module은 이 JSON을 읽지 않는다. provider에는 오직 명시적 public request를 전달한다. evaluator의 정답은 legality·action 목록·후보 정렬에 쓰지 않는다.

paired request 설정은 model `ollama-cloud/qwen3.5:397b`(reference identifier), generation `contract-only-no-inference`, executor `proposal-only-v2`, action budget4, timeout60초로 같다. 실제 inference generation 설정 적용·budget 집행은 아직 없으며 이것을 runtime 검증이라고 주장하지 않는다. 향후 live driver는 모든 선택(검사·대기 포함)을 같은 예산에 포함하고 남은 시간과 호출 deadline을 실제로 집행해야 한다.

## 3. LLM / Python responsibility

| 영역 | 담당 | 경계 |
|---|---|---|
| subgoal 선택 | LLM | Python phase가 다음 목표를 지정하지 않음 |
| 의미 있는 후보 선호 | LLM | 동일 legality라도 usefulness는 다를 수 있음 |
| 실패 해석 | LLM | 자동 원인 판정·전략 요약을 provider에 추가하지 않음 |
| retry / abandon / alternative / inspect / wait | LLM | 합법적인 선택은 모두 접수 가능; 낮은 utility는 불법이 아님 |
| task transition·recovery | LLM | Python이 자동 대체 경로로 성공을 만들어 주지 않음 |
| tile/candidate 생성·BFS·rotation·비용 | Python | 전략적인 후보 제거·정답 순위 제공 금지. v2는 최소 후보 인터페이스만 구현 |
| schema·현재 자원·unit/command 가능성 | Python | history·scratchpad·expected preference를 validator 입력으로 받지 않음 |
| command 실행·완료 판정 | Python | 기존 정상 게임 방식 유지. v2 live 연결은 후속 작업 |
| 기억 작성/수정 | LLM | Python은 schema·revision·크기만 검사; 사실 정답으로 고치지 않음 |
| utility/outcome 측정 | 독립 evaluator | 정책 결정·자동 복구·오류 메시지로 정답을 전달하지 않음 |

`decide_once()`에는 전략 fallback이 없다. 잘못된 응답은 실패이며 Python이 다른 후보를 골라 대체하지 않는다. 테스트의 `PublicOnlyProbe`는 정보 차이를 확인하기 위한 투명한 scripted sensitivity witness다. 실제 agent 또는 LLM 성능으로 취급하지 않는다.

## 4. Common observation contract

```json
{
  "tick": 100,
  "resources": {"copper": 60},
  "executor": {"busy": false},
  "candidates": [
    {"id": "site-a", "cost": 20, "legal": true},
    {"id": "site-b", "cost": 20, "legal": true}
  ],
  "visible_events": []
}
```

`observation()`은 허용한 필드만 새 객체에 복사한다. 현재 후보는 최대8개, 환경에 고정된 ID순으로 정렬한다. `phase`, `plan`, `summary`, `previousDecision`, `blocked`, 과거 task/failure, 후보 preference/score와 nested 보조 필드는 전달하지 않는다. 현재 이벤트는 최대6개이며 허용한 sensor predicate와 candidate subject만 통과하고 `observed_tick == tick`이어야 한다. 이전 report를 다음 관측에 자동 재첨부하지 않는다.

단, timestamp만으로 진짜 현재 센서 관측임을 암호학적으로 입증할 수는 없다. 향후 trusted live adapter가 과거 report를 새 timestamp로 포장하지 않아야 한다. 현재 snapshot에 보이지 않는 remote 정보까지 legality 검사 결과로 압축해 보내는 것도 금지한다. 건설 가능성과 종단 물류 유용성을 구분한다.

공통 request는 `contract`, `common_prompt`, `goal`, `settings`, `observation`, `memory_schema`, `scratchpad`로 구성한다. **조건 간 허용되는 유일한 차이는 scratchpad 값**이다. No-memory는 null, structured는 같은 schema의 객체다. instructions·출력 모양·schema 설명은 양쪽에 동일하게 보낸다. `assert_memory_only_difference()`는 모델·prompt·관측·executor·예산 등 다른 차이가 있으면 거절한다.

## 5. Memory-only information과 persistent state inventory

기억 조건만 접근하는 정보는 이전 정찰의 세부 결과, 만료된 실패 report와 시도한 대안, agent가 선택한 하위 목표·판단 이유·미완료 계획이다. 현재 관측에서 직접 보이는 사실이나 진행 중인 명령 상태까지 숨길 필요는 없다. 아래는 저장된 Python 상태의 분류다. 프로그램 상수·파일 경로·스케줄링 시계는 비정책 운영 metadata로 명시한다.

| 컴포넌트 / 보존 필드 | 분류 | v2 policy로 전달 여부·처리 |
|---|---|---|
| 현재 world snapshot: resources/units/tiles/buildings/rules/tick | environment state | 오직 공개 observation projection |
| `LogisticsBridge.base/state_path`, 일반 Bridge URL/query | executor 설정 | 정책 이력 아님; provider에 경로 미전달 |
| LogisticsRuntime `world`, `future_context`의 world/unit identity | environment/executor | stale 결과 방지용; history label로 쓰지 않음 |
| LogisticsRuntime `bridge/provider/log`, `pool/future` | executor 운영 | prompt 내용 외 공유하지 않음 |
| `safety_margin/task_timeout` | executor 설정 | 조건 간 동일해야 함; 현재 v1에만 존재 |
| `plan`, `sequence`, `build_index` | executor state + 기존 전략 기억 | 실행 중 선택된 task의 기계적 진행만 허용. 자동 선택된 plan 전체를 v2 요약으로 가져오지 않음 |
| `phase`, `maintenance_decided`, `threshold_logged` | v1 agent policy/memory 또는 정책 진행 표식 | v2에 전송 금지. 그대로 쓰면 다음 행동을 노출 |
| `pending_since`, `flow_started`, `builder_parked` | executor/test-protocol state | deadline·fixture 동작; 전략 권고로 쓰지 않음 |
| `flow`, `last_flow_evidence` | completion detector/evaluator 기억 | 완료 사실만 명시된 event로 공개; 누적 증거를 숨은 memory summary로 재전송 금지 |
| `last_flow_log/last_observe_log`, `next_llm`, `counts` | 로그·스케줄·운영 counter | history에 의존한 호출 시점/예산도 paired 비교에서 통제 |
| LogisticsPlan `drill_x/y`, footprint, `ore_tiles`, conveyors, costs, safety margin | 선택된 plan/executor + 과거 환경 정보 | v2 current observation에 자동 추가 금지; 비용·현재 legality만 공개 |
| FlowVerifier `plan`, `baseline_copper/received`, producing/item/core 증가 latch4개 | evaluator state | partial/history 복원 oracle가 될 수 있어 내부 보관 |
| AutonomousRuntime `tasks` | executor state | 진행 중 command만 공개 가능; 완료/실패 archive는 agent memory로 분리 |
| Task `action/payload/status`, `started/last_progress`, `best_distance/best_progress` | executor 상태 | 현재 명령 중복·완료 판단용. 종료 뒤 지속 요약 금지 |
| Task `baseline`, `mining_seen`, `last_resource` | completion detector의 과거 환경 정보 | 현재 command 결과 검사 용도에 한정 |
| AutonomousRuntime `blocked` | 실패 기억+자동 후보 제거 정책 | v2로 가져오면 누출. 현재 불법 여부와 분리 |
| `previous`, `previous_signature`, `context` | agent memory / scheduling / stale identity | previous decision/error는 No-Scratchpad 입력 금지; signature/context는 운영용으로만 |
| `world`, `next_decision`, `last_ask`, `future/pool`, `counts`, `config/bridge/provider/log` | environment/executor 설정·운영 | 의미 있는 history signal이 되지 않도록 정책 입력과 분리 |
| 기존 patrol agent `anchor_x/y`, `target_x/y`, `going_right`, `controlled_unit_id` | scripted policy/executor | 기존 demo만. v2에서 사용하지 않음 |
| continuous resource agent `current_task/current_unit_id` | 마지막 선택/command identity | 기존 demo만. v2에서 사용하지 않음 |
| 일회성 resource/LLM/build/move/observation demo의 locals | 한 실행 snapshot/result/config | 다음 LLM decision에 이어지는 session memory 없음; v2 미사용 |
| 기존 Qwen providers `model/timeout`, locks/process/closed | provider 설정·운영 | stateless 호출; 감춰진 conversation history를 가정하지 않음 |
| MockDecisionProvider `contexts/reset_count/closed/policy` | 테스트 관측 archive/운영/정책 | contexts는 테스트 검사용만; policy 입력에 되먹임 금지 |
| ResearchDecisionAdapter `condition/goal/provider/store` | 조건·공통 goal·명시 agent memory | v1 adapter는 v2의 strategy/관측 경계로 재사용하지 않음 |
| adapter `decision_count/reset_count/context_reset_every/event_sink` | 실행/계측 | hook 횟수와 실제 정보 소실 구분 |
| ScratchpadStore `path/goal` 및 파일 내용 | 명시 agent memory + 설정 | structured만 읽음; No-Scratchpad는 파일 경로도 provider에 전달하지 않음 |
| BenchmarkSpec `data/source/fingerprint` | 환경 계약+evaluator 설정 | 전체를 provider에 보내지 않음. v2 histories/labels 특히 금지 |
| ExperimentRunner `spec/output/provider_factory/provider_config/context_reset_every/base_seed` | evaluator/executor 설정 | 조건 일치 검사, policy hidden input으로 금지 |
| runner episode locals: seed/run ID, observation, counters, construction cost, pending reset, completion/flow flags, adapter | environment/executor/evaluator | 현재 v1 mock용. phase 기반 요약/검증은 v2에 연결하지 않음 |
| MockBackend `spec/seed/step_index/copper/topology_complete/flow_verified/post_completion_replanned/cleaned` | 합성 environment/evaluator | 실제 game 상태 아님; v2 정책 입력으로 재사용 금지 |
| EventLog `path/events/started`, metrics의 사건 목록 | evaluator archive | 읽기 채널을 provider에 주지 않음 |
| v2 `Settings` | 불변 공통 설정 | 두 조건에 동일 |
| v2 `MemoryStoreV2.path/goal` + JSON | 명시 agent memory | caller가 structured 조건에서만 명시적으로 load/update |
| v2 `decide_once`의 request/response/trace | 단일 호출 locals / evaluator 기록 | 인스턴스 history 없음, 매번 fresh provider 생성·close. trace는 다음 요청에 자동 포함하지 않음 |

기존 runtime의 위 정책 상태를 삭제하거나 리팩터링하지 않았다. **v1은 그대로 보존하고 v2에서 사용하지 않는 방식으로 누출을 차단했다.** 향후 live 통합 때 이 표를 기준으로 어떤 상태를 노출할지 다시 검증해야 한다. Java 게임 내부 누적 state도 environment/evaluator에 속하며, remote ground truth를 제한 없이 주는 현재 v1 `/state`를 v2 compliant라고 주장하지 않는다.

## 6. Two same-observation / different-history cases

각 case는 history2개가 **byte-equivalent public current request**(memory 제외)에 도달한다. 서로 다른 history ID·phase·oracle를 raw input에 넣어도 projection 이후 같다.

| Case | 공통 현재 관측 | History A → 적절한 선호 | History B → 적절한 선호 |
|---|---|---|---|
| `survey_preference` | tick100, copper60, idle, 같은 비용20·legality true인 site-a/b, 현재 report 없음 | 이전 정찰: a는 copper4타일, b는1 → a 선택 | 이전 정찰: a는1, b는4 → b 선택 |
| `failure_recovery` | tick100, copper60, idle, 같은 비용20의 route-a/b 명령 합법, 현재 report 없음 | a 실패는 builder interruption, outlet 확인됨; b는 느린 대안 → a 재시도 | a 실패는 blueprint outlet 단절, 같은 명령 반복은 해결 못 함; b는 작동 → b 대안 선택 |

두 번째 사례에서 개별 건설 명령의 합법성은 end-to-end delivery 성공을 뜻하지 않는다. 재시도·대안·검사·대기·포기는 모두 합법이다. executor가 이미 올바른 전체 경로를 재계산해 자동 수리하면 이 case는 무효가 된다. 향후 live 구현에서는 명시적으로 선택된 blueprint 실행과 새 경로 요청을 구분해야 한다.

utility는 작성자가 정한 진단값이다. 선호 target을 선택하는 여러 intent alias는 같은 점수로 취급해 문구를 정답으로 강제하지 않는다. 현재 관측만 사용하는 하나의 고정 선택이 paired history 양쪽에서 동시에 최적일 수 없음을 모든 허용 선택에 대해 검사한다. 이는 기억 정보의 식별 가능성 증거이지 실제 최적 game strategy의 증거가 아니다.

`inspect`는 즉시 utility0이지만 합법이고, 기억이 없는 agent에게 합리적인 선택일 수 있다. 후속 정찰로 성공할 가능성을 부정하지 않는다. 이 milestone은 전체 episode memory 필요성이나 LLM의 성능 향상을 입증하지 않는다.

## 7. Scratchpad schema

```json
{
  "schema_version": 2,
  "revision": 0,
  "goal": "fixed benchmark goal",
  "selected_subgoal": "recover copper delivery",
  "relevant_events": [
    {"subject": "route-a", "predicate": "trial_failure", "value": "builder interruption", "observed_tick": 40}
  ],
  "completed_milestones": ["survey completed"],
  "failures": [
    {"target": "route-a", "cause": "builder interruption", "attempted_alternatives": ["route-b"]}
  ],
  "unresolved_information": ["current remote flow unknown"],
  "next_intended_step": "consider retry or inspect"
}
```

실제 goal은 `research.memory_contract.GOAL`의 고정 문자열이며 위의 `fixed benchmark goal`은 설명용 축약이다.

Canonical UTF-8 JSON 전체는 4096 bytes 이하, revision은 음이 아닌 정수로 갱신마다 +1이다. event6개, milestone6개, unresolved6개, failure4개, 각 failure의 alternative4개까지 허용한다. 본문160자, identifier32자 이내이며 event value는 bounded scalar다. 임의 key, raw message/role/content 목록, 중첩 history object는 거절한다. 모델이 짧은 문자열에 부적절한 내용을 넣는 것까지 schema가 의미적으로 판단하지는 않는다.

Goal/형식/크기/revision은 Python이 검증하지만 기억의 진위는 검증하지 않는다. **stale/incorrect scratchpad도 schema가 맞으면 허용한다.** No-memory/올바른 memory/반대 history에서 온 잘못된 memory를 구분해 검사한다. 정오 label은 provider에 전달하지 않는다. 원자적 저장은 기존 store의 I/O만 재사용하며 v1 schema는 변경하지 않는다.

## 8. No-Scratchpad leakage prevention

검증한 경계는 다음과 같다.

1. request 함수는 history/case/oracle를 별도 인자로 받지 않고 current snapshot의 허용 필드와 명시적 memory만 사용한다.
2. Python phase·summary·previousDecision·blocked·실패 이력·후보 score에 canary를 넣어도 public request는 달라지지 않는다.
3. history에 따른 후보 순서를 뒤집어도 ID순으로 정규화한다. 과거 event와 알 수 없는 summary predicate는 거절한다.
4. validator는 memory를 읽지 않고 두 history에서 양쪽 전략·wait/abandon을 모두 허용한다. 전략적으로 열등한 선택도 허용한다.
5. provider에는 deep copy를 전달한다. 입력을 변조해도 다음 호출과 기록을 바꾸지 못한다. 새 provider instance는 호출 후 close한다.
6. No-memory에서 반환한 scratchpad가 null이 아니면 거절한다. 외부 session을 재사용하지 않는지는 향후 transport 통합 테스트에서 검증해야 한다.
7. `assert_memory_only_difference`는 모델/생성 설정/prompt/관측/executor/action budget/timeout/schema 차이를 거절한다.

테스트의 `PublicOnlyProbe`는 숨은 oracle 정답을 읽지 않고 공개 입력 차이에 반응한다. 규칙을 작성한 진단용 probe이므로 결과를 LLM의 추론·기억 능력으로 부르지 않는다.

## 9. Corrected success / failure / context semantics

기존 mock runner의 `flowVerified`는 **milestone**으로 변경했다. 후속 판단이 성공해 `postCompletionReplanned`가 된 뒤에만 completion을 기록한다. `task_success`는 후속 판단을 마친 completion, 그 뒤의 유일한 성공 terminal, 미해결 goal loss/failure/invalid action이 없음을 모두 요구한다. terminal 뒤에는 cleanup만 허용한다. 성공이 아니면 completion time은 null이다.

회복을 인정하려면 원래 event가 `recoverable=true`이고 `recovery(resolved=true, trigger_seq=...)`가 실제 선행 실패를 참조해야 한다. 무관한 reset이나 다음 유효 JSON만으로 goal loss를 취소하지 않는다. 실제 회복 여부는 독립 evaluator가 판단해야 한다.

감사 반례인 `bootstrap → establish → wait(flow) → reconsider(실패)`는 flow milestone을 남기지만 task success=false가 된다. provider transport의 OSError도 failure terminal과 metrics/summary를 남긴다.

v2에서 합법적인 wait/inspect/abandon 자체는 goal loss가 아니다. 목적 미달로 종료하면 unsatisfied objective, 예산 소진은 timeout/budget, schema 위반은 invalid, provider 장애는 infrastructure failure로 구분한다. v1 mock의 phase 기반 validator는 negative control의 기존 동작으로 남겨 두고 v2에 사용하지 않는다.

**Context reset:** stateless provider에는 지울 대화 이력이 없다. v2는 매 판단 fresh request이며 `context_loss=false`다. 기존 `context_reset` event명과 count는 호환용으로 남기되 `semantics=boundary_hook_only`, `context_loss=false`를 붙이고 복구를 허위 집계하지 않는다. 추가 지표 `actual_context_loss_count`는 이번에 0이다. 진짜 context-loss 평가는 보존했던 history를 실제로 제거하는 transport/프로세스 경계를 검증한 경우에만 수행한다.

새 outcome contract version은2다. 오래된 mock 로그에 terminal 증거가 없으면 새 metrics는 보수적으로 false를 반환한다. 과거 GUI/headless 로그와 사용자의 관찰 사실을 수정하는 것은 아니다.

## 10. Tests passed와 재현

`3번 AGENT / TEST`에서 Python3.13.5를 사용한다. 기본 Python3.9 호환성은 이번 수정 범위가 아니다.

```sh
/opt/anaconda3/bin/python3 -m unittest discover -s tests -v
```

변경 전 기준38개가 통과했다. 변경 후 기존38개와 새 contract/outcome tests를 모두 실행한다. 기존 metric 테스트1개의 fixture는 명시적인 회복 event와 성공 terminal을 가진 정상 성공 예로 보강했다. 테스트 삭제·skip·assertion 약화는 없으며, 잘못된 옛 성공 정의는 새 negative tests로 거절한다.

결과는 `build/contract-v2/tests.txt`, 진단 trace는 `build/contract-v2/evidence.json`이다. ignored 파일이지만 테스트와 case JSON에서 재생성할 수 있다. 최종 통과 개수는 PROGRESS에 기록한다.

## 11. VERIFIED / PARTIALLY VERIFIED / NOT VERIFIED

| 분류 | 범위 |
|---|---|
| VERIFIED — contract/unit | 동일 현재 관측의 paired history2쌍, private label 격리, memory-only 차이, 양쪽 전략 합법성, bounded 저장, none/correct/incorrect 입력, 성공 반례 거절, stateless 용어 정리 |
| PARTIALLY VERIFIED | memory를 독립변수로 조작 가능한 최소 구조. state inventory는 정적 감사. store reload는 같은 프로세스에서 객체 재생성으로 검사 |
| NOT VERIFIED | 실제 LLM의 유용한 기억 작성, game에서 v2 관측/행동/복구, local inference, 성능 개선, 장기 episode, 진짜 context-loss 복구 |

## 12. Adversarial review / remaining confounds

| 공격적인 질문 | 검사·결과 | 남은 한계 |
|---|---|---|
| Scratchpad 없이도 Python state에서 답이 나오지 않는가 | paired public inputs 완전 일치. 모든 허용 고정 선택을 열거했을 때 양쪽 history에서 동시에 최적인 선택 없음 | live observation이 계약을 지키는지 미검증 |
| 후보 순서·phase·score·실패 summary가 답을 누출하지 않는가 | canary 제거·ID순 정규화·과거 event 거절 | adapter가 과거 정보를 현재 sensor로 위장하면 타입만으로 탐지 불가 |
| validator가 잘못된 memory를 고치지 않는가 | 반대 history의 기억과 열등한 choice를 허용 | LLM의 허위 기억 판별 능력 미측정 |
| Structured만 모델/prompt/executor를 강화하지 않았는가 | scratchpad 외 차이를 pair checker가 거절 | memory의 추가 token·latency는 처치 비용으로 남음 |
| 시험 policy에 정답을 심지 않았는가 | test-only probe를 명시, private label을 입력하지 않음 | 규칙 기반 probe 성공은 LLM 결과가 아님. memory fixture도 evaluator 작성이라 기억 작성 능력 미검증 |
| memory에 다음 정답을 그대로 쓴 것은 아닌가 | 관측 사실만 입력, expected preference 비공개 | 짧은 사례이며 추론은 단순함. 일반화 증거 아님 |
| 기존 runtime의 phase를 몰래 사용하지 않는가 | v2 module은 legacy runtime/runner/planner를 import하지 않음 | 실게임 연결 시 재감사 필수 |
| 성공 flag만 먼저 세우지 않는가 | completion/terminal/미해결 실패를 분리 검사 | evaluator가 거짓 completion을 만들면 타입만으로 방지 불가. live 결과 근거 필요 |

남은 항목: 현재 mock timeout은 blocking provider를 중간 취소하는 엄격한 deadline이 아니다. token coverage·resource efficiency·recovery rate의 전체 감사 개선과 provider 생성/cleanup 예외의 완전한 episode 처리는 범위 밖이다. v2 budget은 계약이며 실제 시간·게임 비용 집행은 미검증이다. v1 manifest의 미구현 endpoint와 artifact 이식성도 다음 재현성 milestone에 남긴다.

## 13. Checkpoint

commit hash는 최종 보고와 Git 이력을 참조한다. 이 문서는 같은 commit에 포함하므로 자기 자신의 hash를 삽입하지 않는다. remote push는 하지 않는다.

## 14. Next recommended milestone

**재현성과 live 연결 전 계약 정합성 정리.** 감사 Phase C에 따라 README/Python 환경/CI, manifest와 실제 API의 일치, fixture·artifact 복원을 정리한다. v2 partial observation을 어떤 정보원으로 만들 수 있는지 확인하고 두 case의 live 대응 가능성을 명시한다. 이후 승인받아 provider/executor 통합으로 진행한다. 이번 완료 후 다음 phase를 자동 시작하지 않는다.
