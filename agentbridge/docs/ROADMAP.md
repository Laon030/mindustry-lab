# Mindustry 에이전트 연구 플랫폼 로드맵

갱신: 2026-10-07 · 연구 단계: **재현성·live 연결 전 정합성 검증 완료** · 별도 시연: **Duel Gate 6 안정화 headless 검증 완료**

현재 증거는 [PROGRESS.md](PROGRESS.md), 고정 실험 규약은 [SCRATCHPAD_EVALUATION.md](SCRATCHPAD_EVALUATION.md), 영구 개발 규칙은 [AGENTS.md](../AGENTS.md)를 따른다.

## 별도 duel demonstration 트랙

사용자 승인으로 연구와 분리한 `codex/weekend-duel-demo`에서 두 로컬 모델의 채굴→Duo 건설→유한 저장고 공급→정상 Dagger 생산→실제 교전을 구현하고 headless로 검증했다. 2026-10-07에는 비명령형 관전 alpha의 좌표 guard와 실행 실패/미완료/전장 판정을 보강했다. 최신 full match는 `DRAW_FIGHTERS`이며 native 승리나 전체 GUI acceptance를 주장하지 않는다. 증거·범위는 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.

다음은 같은 fixture의 인간 GUI 확인이다. 그 뒤 Gate 7 vanilla one-tier upgrade를 별도 proof로 진행할 수 있으며, 현재 upgrade/capture는 **NOT_STARTED**다. 아래 연구 로드맵의 gameplay 확장 제한과 model 선택 상태는 연구 트랙에 적용된다. 별도 demo의 로컬 모델 설치나 전투 결과를 scratchpad 연구 검증으로 전용하지 않는다.

## 완료된 gameplay benchmark

Autonomous Early-Game Logistics Vertical Slice는 v159.7에서 완료했다. Deterministic Islands fixture에서 single Qwen 전략 판단과 Python deterministic planner/executor가 Mono copper bootstrap, Poly의 정상 mechanical drill 및 conveyor 건설, drill에서 core까지 연결된 route, 실제 copper 운송과 core 유입, 완료 후 재판단을 수행했다. Headless 360초 run과 사람이 직접 본 v159.7 CLIENT GUI run을 각각 검증했다.

이 결과를 `autonomous-early-game-logistics-v1` benchmark로 동결한다. Mindustry gameplay 기능은 이 연구 단계에서 더 늘리지 않는다. 전투, 방어, unit production, factory, power, advanced logistics, 추가 block 종류와 multi-agent는 현재 범위 밖이다. 과거 multi-agent 비교 구상은 후속 가능성으로만 남기며 이번 연구 질문이나 구현 목표가 아니다.

## 현재 연구 질문과 구조

같은 environment, model, prompt, planner/executor와 예산에서 구조화된 영속 external scratchpad가 없는 조건보다 장기 과제 성공, goal 유지, 실패/context-reset 복구와 추론 효율을 개선하는지 비교한다.

```text
Mindustry v159.7 ↔ AgentBridge ↔ Python runtime ↔ provider(local LLM)
                                         ├─ NO_SCRATCHPAD
                                         └─ STRUCTURED_SCRATCHPAD
                                                   ↓
                                  experiment logs and metrics
```

LLM은 고수준 전략만 선택한다. Python의 좌표, 경로, 비용, action 검증, 실행과 완료 판정은 두 조건에서 동일하다. 최종 local model은 아직 선택하지 않으며 현재 Qwen/OpenCode 연결, mock test provider와 같은 provider interface를 사용한다.

## 단계 — 2026-09-29 감사 및 승인 반영

1. **기존 logistics v1 보존 — 완료.** 과거 GUI/headless 증거는 유지하며 smoke/negative control로 사용한다. manifest 작성은 live 계약 정합성 검증 완료와 다르다.
2. **독립 기술·연구설계 감사 — 완료/승인.** [AUDIT_2026-09-29.md](AUDIT_2026-09-29.md)의 CONDITIONAL GO와 선행 조건을 따른다.
3. **Decision/observation/memory contract v2 — 완료.** [MEMORY_CONTRACT_V2.md](MEMORY_CONTRACT_V2.md): paired-history 두 case, legality와 preference 분리, bounded memory, 누출 방지, terminal 성공 정의와 최소 테스트. 실제 모델 성능 향상은 주장하지 않는다.
4. **재현성·live 연결 전 정합성 — 이번 milestone 완료.** [REPRODUCIBILITY.md](REPRODUCIBILITY.md): Python/Java 환경 및 CI 설정, 실제 API와 v1 manifest 일치, artifact hash/인수 절차, metadata 계약, 격리 checkout 검증. [PRE_LIVE_MAPPING.md](PRE_LIVE_MAPPING.md)에 두 v2 case의 조건부 live mapping과 trusted boundary를 명시했다. Hosted CI·실제 v2 live 동작은 미검증이다.
5. **Trusted adapter conformance — 다음 단일 권장 단계.** recorded/synthetic raw snapshot을 이용해 두 paired history의 public observation bytes, candidate/legality 결과, executor 명령이 memory 외 정보 때문에 달라지지 않는지 검사한다. 새로운 game behavior나 LLM pilot 없이 정보 경계만 구현·검증한다.
6. **Provider/조건/executor live 통합 — 후속.** 기존 구현을 재사용하되 v1 상태기계의 전략 기억을 v2에 그대로 연결하지 않는다. 모델의 선택만 executor가 실행하고 양 조건에서 같은 기계적 도움을 제공한다.
7. **신뢰 가능한 live reset/runner — 후속.** 실제 초기 상태 검증, 실패 포함 결과 보존, 시간 예산·token coverage·완료 근거를 검증한다. 현재 mock의 성공은 이 단계의 증거가 아니다.
8. **Local 모델 및 memory pilot — 후속 승인 범위.** 설치·추론·진짜 context loss 시험은 아직 하지 않았다. Stateless 호출의 reset hook을 기억 소실로 분류하지 않는다.
9. **Logistics 반복 비교 및 분석 — 후속.** pilot 이후 고정 모델·계약·예산·표본 수로 비교한다. Combat/대전은 감사 roadmap의 별도 후속 benchmark이며 지금 구현하지 않는다.

현재 milestone 종료 후 다음 phase를 자동으로 시작하지 않는다. Combat, Human-v-Agent, Agent-v-Agent, Local LLM 설치, 대규모 반복실험은 아직 범위 밖이다.
