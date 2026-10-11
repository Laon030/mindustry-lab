# Scratchpad Evaluation 연구 규약

작성: 2026-09-11 · 상태: harness 단위 테스트 및 deterministic mock smoke 검증 완료, 실제 Mindustry/Qwen 반복 실험 미실행

2026-10-01 정정: 이 문서는 **logistics v1 smoke/negative-control 및 기존 mock harness**의 규약이다. 기억 연구용 현재 계약은 [MEMORY_CONTRACT_V2.md](MEMORY_CONTRACT_V2.md)와 별도 `experiments/memory_sensitive_v2.json`을 따른다. 기존 runtime에 연구 adapter가 live로 연결됐다는 의미가 아니다. 아래 구조도는 통합 목표 구조이며 현재 runner backend는 mock으로 고정되어 있다. v1 manifest의 미구현 endpoint/active field 표기는 [API inventory](AGENTBRIDGE_API.md)에 맞춰 바로잡았지만, normalized fixture snapshot과 raw live `/state`의 차이 및 live runner 미연결은 남아 있다.

## 연구 질문

같은 Mindustry 환경, 관측, action whitelist, deterministic planner/executor, 모델, 전략 prompt, 제한 시간과 action budget에서 **구조화된 영속 external scratchpad만 추가했을 때** local LLM agent의 장기 과제 성공, goal 유지, 실패 복구와 추론 효율이 개선되는가를 측정한다. Autonomous Early-Game Logistics Vertical Slice를 고정 benchmark로 사용하며 게임 기능은 더 추가하지 않는다.

```text
Mindustry v159.7 ↔ AgentBridge ↔ Python LogisticsRuntime/planner ↔ DecisionProvider
                                                           ├─ NO_SCRATCHPAD
                                                           └─ STRUCTURED_SCRATCHPAD ↔ scratchpad.json
                                      experiment runner → JSONL → metrics.json
```

LLM은 `continue_bootstrap`, `establish_copper_logistics`, `wait`, `reconsider` 중 전략 intent만 선택한다. Python은 좌표, drill 후보, conveyor route/rotation, 비용, action 검증, 정상 BuildPlan 실행과 완료 판정을 계속 담당한다.

## 고정 benchmark

기계 판독 원본은 [`experiments/logistics_benchmark.json`](../experiments/logistics_benchmark.json)이다. 다음 항목을 benchmark version 1에서 고정한다.

- Mindustry v159.7, Islands, `infiniteResources=false`, `instantBuild=false`, build speed 1.0.
- save 원본은 `/Users/andrew/capstone/MindustryServer/config/saves/autonomous-logistics-base.msav`; portable bundle 경로는 `artifacts/autonomous-logistics-base.msav`, SHA-256 `1a70fe390341fa4fed62b189053838a750762266d01f31606a159dfc24eabc4f`.
- 초기 core copper/lead 0, Mono 1, Poly 1과 검증된 core footprint.
- AgentBridge의 제한 관측과 기존 mine/build/move action, runtime의 wait.
- `agent/logistics_planner.py`와 `agent/logistics_agent.py`의 GUI 검증 당시 동작(`a5dd369`).
- 목표: copper bootstrap, 정상 mechanical drill 및 core까지 연결된 conveyor 완공, 실제 copper core 유입 확인, 완료 후 재판단.
- 성공 판정: bootstrap 관측, drill 완공, 연결 route 완공, flow 이후 core copper 증가, 완료 후 재판단이 모두 있어야 한다.
- episode timeout 360초, action budget 80, construction safety margin copper 10, context reset 간격 2 strategic decisions.

Save를 load했다는 사실만으로 동일 초기 상태라 판정하지 않는다. 각 run은 시작 snapshot의 map, wave, 네 자원, Mono/Poly 수, rules와 core footprint를 manifest와 비교해야 한다. Live runner는 reset 후 이 검사를 통과하기 전 agent를 시작할 수 없다.

## 비교 조건

| 조건 | 모델에 전달되는 동적 기억 | context reset 이후 유지 |
| --- | --- | --- |
| `NO_SCRATCHPAD` | 현재 관측만 | 없음 |
| `STRUCTURED_SCRATCHPAD` | 현재 관측 + 아래 외부 JSON | 검증된 외부 JSON만 reload |
| `RECENT_HISTORY` | 후속 ablation 후보 | 아직 구현/실행하지 않음 |

두 주조건 모두 같은 goal과 공통 전략 지시문을 사용한다. Structured 조건에만 scratchpad 입력과 완전 갱신 출력 형식이 추가된다. Provider 내부 대화 history, 이전 Python observation, 숨은 요약은 no-scratchpad 조건에 넘기지 않는다.

## Scratchpad schema와 갱신

```json
{
  "schema_version": 1,
  "revision": 0,
  "goal": "immutable benchmark goal",
  "current_subgoal": "one compact subgoal",
  "known_state": {},
  "plan": [],
  "completed": [],
  "failures": [],
  "next_step": "one concrete next step",
  "confidence": 0.5
}
```

전체 canonical JSON은 4096 bytes 이하이다. `known_state`는 최대 16개 scalar, `plan`/`completed`/`failures`는 각각 최대 8개 문자열이다. Goal은 benchmark goal에서 바꿀 수 없고 revision은 정확히 1씩 증가해야 한다. 모델은 부분 patch가 아니라 완전한 다음 객체를 명시적으로 반환한다. Python은 decision과 scratchpad schema를 모두 검증한 뒤 임시 파일 write, `fsync`, atomic replace 순서로 저장한다. 실패한 갱신은 기존 파일을 보존하고 해당 decision을 거절한다.

## Context reset

고정 decision 간격에 provider의 `reset_context()` hook을 호출한다. 현재 OpenCode는 매번 새 stateless 요청이므로 이 hook은 이력을 제거하지 않는다. 기존 event명은 유지하지만 `context_loss=false`, `semantics=boundary_hook_only`를 기록한다. Structured 조건의 파일 reload와 실제 대화 이력 소실은 다른 사건이다. `actual_context_loss_count`는 실제 loss 표식이 있는 경우만 세며, 이번 mock 실행에는 해당 사건이 없다.

Unit tests는 no-scratchpad context에 과거 관측이 없는지, 같은 프로세스에서 adapter를 재생성한 뒤 structured scratchpad가 reload되는지, goal 변조·revision 건너뛰기·크기 초과를 거절하며 파일을 보존하는지 확인한다. 실제 프로세스 재기동 검증은 하지 않았다.

## Provider 계약

모든 provider는 다음 경계를 구현한다.

```text
decide(context) -> ProviderResponse(payload, usage, latency_seconds)
reset_context()
close()
```

현재 `ollama-cloud/qwen3.5:397b` OpenCode prototype은 이 경계 안에서 유지되고 project config, tools, sharing을 차단한다. 기존 runtime-tested `LogisticsDecisionProvider`용 adapter도 보존한다. Deterministic mock provider는 harness/test 전용이다. 후속 local provider는 같은 계약을 구현하되 최종 모델은 속도, context 길이, JSON 준수율과 로컬 하드웨어 pilot 근거가 생긴 뒤 선택한다.

## Episode runner와 산출물

현재 CLI smoke 실행 예시는 다음과 같다.

```sh
python3 experiment.py --scenario logistics --condition no_scratchpad --runs 2 --provider mock
python3 experiment.py --scenario logistics --condition structured_scratchpad --runs 2 --provider mock
```

각 run은 별도 directory에 `metadata.json`, `events.jsonl`, `metrics.json`을 쓰고 condition별 `summary.json`을 만든다. Metadata에는 benchmark/save fingerprint, v159.7, planner/executor commit, condition, provider/model 설정, prompt version, seed, timeout, action budget과 context-reset 간격을 기록한다. 매 episode는 `reset → fixture 검증 → observe → decide → validate → act → observe/complete → cleanup` 순서다.

현재 mock backend는 이 lifecycle, 파일 형식과 metric 재계산을 검증하기 위한 deterministic state machine이다. `test_mode=true`가 항상 기록되며 실제 게임 성공이나 scratchpad 효과의 증거가 아니다. 실제 반복 실험을 시작하기 전에 1번 SERVER save load와 fixture snapshot 검증, 2번 CLIENT 또는 정당한 server-side action identity, 3번 AGENT / TEST의 run 종료 및 다음 reset을 한 episode 경계로 묶는 live reset driver를 연결하고 소수 pilot으로 검증해야 한다.

## 지표의 운영 정의

| 지표 | JSONL에서 계산하는 규칙 |
| --- | --- |
| `task_success` | 후속 판단 완료 표식이 있는 completion 뒤 유일한 성공 terminal이 있고 미해결 failure/goal loss/invalid action이 없을 때만 true. flow만으로 성공 아님 |
| `completion_time_seconds` | 성공 episode의 후속 판단까지 마친 completion 시각. 실패는 null |
| `llm_decision_count` | schema와 goal/action validator를 통과한 `llm_decision(valid=true)` 수 |
| `action_count` | AgentBridge가 접수한 game action 수. runtime의 내부 wait는 제외 |
| `invalid_action_count` | JSON/schema/whitelist/stale 또는 기계 검증에서 거절된 proposal 수 |
| `redundant_action_count` | 관측 version 변화나 task 완료 전에 같은 정규화 action을 같은 대상에 다시 접수한 수 |
| `goal_loss_count` | 현재 상태 변화로 정당화되지 않으며 고정 benchmark goal과 모순되어 validator가 분류한 proposal 수 |
| `recovery_count/rate` | goal loss, recoverable failure 또는 context reset 뒤 다음 유효한 goal-consistent decision 수 / 해당 trigger 수 |
| `resource_efficiency` | 성공에 필요한 drill/route에 소비된 copper / episode 전체 construction copper 소비. 소비가 없으면 null |
| `token_usage` | provider가 보고한 input/output token 합. 제공하지 않으면 null이며 문자열 길이로 대체하지 않음 |
| `decision_latency_seconds` | 관측 context 제출부터 validated response까지의 평균과 nearest-rank p95 |
| `scratchpad_size_bytes` | 각 유효 갱신 뒤 canonical UTF-8 JSON 크기의 평균/최대. no-scratchpad는 0 |
| `context_reset_recovery_latency_seconds` | 실제 context loss 표식의 event를 참조하는 recovery만 집계. stateless hook은 제외 |

2026-09-30 outcome contract v2에서 회복은 선행 recoverable event를 명시적으로 참조하고 `resolved=true`여야 terminal 성공의 실패 veto를 해제할 수 있다. v1 mock의 goal-loss 정책, redundancy/resource-efficiency/token coverage 등 다른 지표 한계는 감사 보고서에 남아 있으며 기억 효과 판단에 사용하지 않는다. 새 성공 정의를 충족할 terminal 증거가 없는 과거 mock 로그는 새 계산에서 보수적으로 실패 처리한다. 과거 실제 게임/GUI 검증 기록을 수정하지 않는다.

Infrastructure failure는 fixture/reset/server/provider transport 실패처럼 agent 판단 전에 발생한 실패다. Agent failure는 유효한 환경에서 잘못된 판단, invalid action 누적, goal loss, action budget 또는 timeout이다. 제외 규칙과 실패 run을 보존하며 성공 run으로 대체하지 않는다.

## 공정성 규약

조건 사이에서 benchmark fingerprint, save hash, 초기 snapshot, v159.7, AgentBridge JAR, Python planner/executor, 전략 goal/prompt version, provider/model/생성 설정, timeout, action budget, context-reset schedule, seed schedule와 실행 순서를 고정한다. 달라지는 것은 외부 memory 조건과 이를 표현하는 최소 입력/출력 schema뿐이다. 조건별 run 순서는 교차하고 모든 호출, 오류와 cleanup을 보존한다.

Mock smoke 결과로 연구 가설을 판정하지 않는다. 대규모 cloud 반복을 실행하기 전에 두 조건 각각 소수 live pilot에서 reset 재현성, token/latency 보고, context reset과 성공 판정을 확인하고, 그 증거로 본실험 run 수와 최종 local model을 정한다.
