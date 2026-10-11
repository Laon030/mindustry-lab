# Memory Contract v2 → live mapping / trusted boundary

2026-09-30 · **설계만, 구현·live validation 없음.** paired-history, memory-only checker, legality-only validator,4096-byte bound, revision, raw-history 거절, terminal/context-loss 의미를 변경하지 않는다.

판정: 두 case는 v159.7 정상 메커니즘과 **조건부로 양립 가능한 설계**다. 현재 LogisticsRuntime을 그대로 연결하면 사례가 붕괴하지만, Bridge 전면 재설계가 필요하다는 증거는 없다. 기존 v1과 별도의 trusted adapter·선택된 과업만 수행하는 executor 경계를 검증해야 한다.

## A. survey_preference

| 정보 계층 | 실제 게임 대응 / 접근 규칙 |
|---|---|
| Environment ground truth | size2 drill footprint copper1/4타일, dominant item, terrain·건설가능성·운송 경로·실제 생산. 두 world에서 a/b 밀도 교대 |
| Current public observation | 같은 tick·자원·idle, 같은 비용/legality의 a/b, 현재 local sensor만. 고정 site anchor ID와 canonical 정렬. 지난 ore count·remote production 제외 |
| Memory-only history | 과거 unit이 site 정찰 반경에 들어갔을 때 관측한 ore 수·시각·불확실성. 획득 시점에는 양 조건에 같은 정보, 이후 structured만 모델이 쓴 기억을 읽음 |
| Executor-only state | anchor→좌표, 선택된 footprint·경로·rotation·cost·진행 queue·timeout. 후보 우열을 고르거나 기억된 순위로 후보 제거 금지 |
| Evaluator-only state | 전체 ore, 비교 조건, 누적 생산/수령, inspect 이동시간/비용, case/history label. 정책으로 utility/정답을 돌려주지 않음 |

근거: 참조 v159.7 `core/src/mindustry/world/blocks/production/Drill.java`의 countOre/dominantItems/updateTile은 ore 수를 progress/speed에 반영한다. 실제 산출은 warmup·막힘에도 좌우되므로 microcase utility4/1을 실제 처리량 비율로 주장하지 않는다. 경로 길이·비용·초기 자원 등을 맞춘 fixture와 실제 처리량 검사는 후속 과제다.

Partial observation은 **조작 unit 기준 사전 고정 sensor footprint**로 정의한다. 현재 Bridge에 자동 fog 기능이 있다는 뜻도, 인간 GUI와 같다는 뜻도 아니다. site는 정찰 때 보이고 decision 시 unit은 core-local에 있어 안 보여야 한다. 사전 지도에도 ore 세부 정보를 넣지 않는다. `/state?view=logistics-plan`의 oreTiles/drillCandidates.oreTiles, status의 remote 생산·건물, demo 전역 ores를 그대로 넘기면 현재 상태만으로 답이 나와 case가 무효다.

재정찰 `inspect`는 합법이다. 정상 move로 site에 접근한 뒤 **그 획득 tick의** sensor snapshot을 받는다. inspect 판단1회, 실제 command 수, simulation ticks, 이동거리, inference token·wall-time을 구분해 측정한다. 무료 remote HTTP 재조회로 정찰을 대체하지 않는다. no-memory도 다시 정찰해 성공할 수 있고 기억의 효과는 성공률보다 비용 차이일 수 있다.

legality=true가 ore 최소 존재를 드러내는 것은 공통 계약에 명시하지만 rich site만 candidate로 내보내면 안 된다. adapter는 후보 geometry를 계산할 수 있어도 preference를 선택하지 않는다.

## B. failure_recovery

| 정보 계층 | 실제 게임 대응 / 접근 규칙 |
|---|---|
| Environment ground truth | a의 각 타일은 합법이나 outlet이 단절된 blueprint/world, 또는 outlet은 연결됐지만 정상 move/stop으로 builder가 중단됐던 world. b는 작동 대안 |
| Current public observation | 동일 core-local idle·자원·후보 비용/legality. remote outlet과 과거 queue/실패 원인 제외. tick/ID/위치/현재 command/예산의 차이도 통제 |
| Memory-only history | trial 당시 command 중단·queue·관측한 outlet/item 흐름·시각과 시도한 대안. transient/structural 해석은 LLM |
| Executor-only state | 선택된 정확한 blueprint 좌표/rotation·현재 queue/progress·완료 baseline·중복 방지. retry는 같은 과업 재실행, 자동 대체 경로가 아님 |
| Evaluator-only state | 전체 topology·원인·delivery·두 대안 utility·injection schedule·history label. “retry가 정답” 요약 제공 금지 |

정상 메커니즘 후보: Poly에 정상 move/stop command로 건설을 중단하고 정상 build로 재개한다. 구조적 실패는 개별 placement는 합법이나 conveyor outlet 방향/연결 대상이 core까지 이어지지 않게 한다. 참조 `Conveyor.java`의 front/next/acceptItem은 배치 가능성과 종단 delivery가 다름을 뒷받침한다. 직접 damage·teleport·setBlock injection은 제안하지 않는다.

같은 current observation은 같은 전체 world를 뜻하지 않는다. remote topology는 다를 수 있다. trial 뒤 필요하면 정상 deconstruction/이동으로 공통 local readiness를 만들되 비용·tick·자원·unit 상태를 paired protocol에서 맞춰야 한다. **정확한 matched fixture를 아직 runtime으로 만들거나 입증하지 않았다.** 정상 절차로 만들 수 없으면 범위를 넓히지 말고 architecture review로 돌린다.

실패 evidence는 trial acquisition snapshot에서 양쪽에 주고 이후 자동 archive로 재전달하지 않는다. Python이 “일시적이므로 재시도하라”라고 쓰면 전략 leakage다. 실제 command/queue 변화, 관측 당시 outlet/완공 타일 같은 bounded 사실을 제공하고 모델이 해석한다. 현재 unit 상태에 원인이 남아 있다면 같은 observation 조건을 충족하지 못한 것으로 판정한다.

현재 v1 `choose_plan`과 자동 PLAN 복귀/재경로를 붙이면 case가 붕괴한다. 새 경계에서는 **선택된 blueprint만 실행**하고 새 경로 요청/선택은 LLM에 남겨야 한다. Python의 요청받은 경로 계산 자체는 계속 허용된다. 기존 v1을 고칠 필요 없이 별도 executor 경계로 가능한지 후속 검증한다. blueprint 내용을 provider에 모두 재첨부해 remote 단절 정보를 노출하는 것도 금지한다.

## Trusted live adapter boundary

```text
Ground Truth → Trusted Adapter → Public Projection → optional Scratchpad
 → LLM → Legality Validator → Deterministic Executor → Mindustry
                                                    ↓
                                             Independent Evaluator
```

| 경계 | 읽기 | 보존 가능 정보 | provider 전달 | evaluator-only / leakage 위험 |
|---|---|---|---|---|
| Ground truth collector | main-thread raw snapshot | tick/epoch/snapshot ID, 제한된 계측 buffer | 직접 전달 금지 | 전역 ore/remote 건물/수령 누적 |
| Trusted adapter | 현재 snapshot·고정 sensor/identity config | 현재 센서 계산·전달 중 snapshot, 전략 이력 없음 | 같은 acquisition tick의 허용 사실 | 과거 event 재타임스탬핑 |
| Public projection | 허용 typed fields | 요청 생성 중만 | 고정ID순 후보·현재 사실 | label/utility/ranking 차단 |
| Memory store | 모델 작성 bounded JSON | structured만 파일 | structured만 read, no-memory=null | 진위 label 비공개 |
| LLM transport | 공통 prompt/settings/current facts/memory | fresh request, 독립 session | 명시된 context만 | file/tool/log/API 우회 접근 금지 |
| Legality validator | 현재 권한·비용·명령 가능성 | 현재 검증 상태 | 실행 가능성의 최소 결과 | hidden topology를 viability로 누출 금지 |
| Executor | 선택된 plan·현재 queue | 현재 과업 진행/중복 방지/시간 | 현재 실행 상태·새 결과 | 이전 실패를 보고 대안 자동 선택 금지 |
| Completion detector | 현재 선택 과업·필요 baseline | 누적 증거 latch | 확인된 완료 event 일회 | 과거 evidence 전체를 summary로 반복하면 기억 대행 |
| Evaluator | 전체 ground truth/public trace | 전체 episode·utility·outcome | 정책 feedback 없음 | private history·반사실 결과 |

## 공격별 방어와 후속 acceptance

1. **과거 failure를 현재로 포장:** observed_tick은 획득 snapshot에 고정. 늦은 event를 새 tick으로 바꾸지 않는다. 놓친 event는 양 조건에 동일한 전달 규칙 적용. 현재 계약은 current tick과 다른 event를 거절한다.
2. **Legality oracle:** 두 history에서 후보 membership·legality·error schema가 같아야 한다. remote 원인이 달라졌다는 이유로 후보 제거/상세 오류 반복 제공 금지. 실제 새로운 실행 중 관측한 실패는 새 정보다.
3. **후보 순위:** 고정 environment ID/canonical sort. planner best-first 결과를 그대로 전달하지 않음.
4. **Executor 자동 복구:** 같은 current observation+같은 command에는 같은 command sequence. 과거 실패 cache로 target을 바꾸면 위반.
5. **Completion 누출:** current task 결과와 episode oracle 분리. no-memory에 과거 milestone/flow baseline을 반복 첨부하지 않음.

현재 API는 full map/rules를 모두 노출하지 않으며 authorization·timeout race도 남아 있다. 같은 프로세스의 객체 분리만으로 arbitrary file/tool 접근을 막을 수 없으므로 실제 transport 도구 차단과 입력 trace 감사가 필요하다.

**다음 통합 gate:** 먼저 recorded/synthetic raw snapshot 기반 trusted-adapter conformance를 구현하여 public bytes·legality·executor 선택이 memory 외 요소로 달라지지 않는지 검사한다. 이 설계 문서가 live gameplay 성공 또는 utility 현실성을 입증하지는 않는다.
