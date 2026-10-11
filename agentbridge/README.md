# Time to Think — Mindustry Agent research environment

## 개인 mindustry-lab 포크에서 실행하기

이 폴더는 개인 `Laon030/mindustry-lab:feature/agentbridge-handoff`의 독립 AgentBridge 패키지다.
기존 게임 포크 `Laon030/mindustry`의 인계 commit `f11b8ac480`에서 가져왔으며, 원본 연구 및 개인 게임 포크의 기록은 보존했다.
현재 clone·submodule·검토 절차는 [lab 인계 안내](../docs/AGENTBRIDGE_HANDOFF.md)를 따른다.

아래 명령은 모두 **이 agentbridge 폴더** 기준이다. lab 루트의 기존 플러그인과 자동으로 결합하지 않았으며,
같은 HTTP 포트를 사용하므로 동시에 실행하지 않는다. 하위 `.github/workflows/gradle.yml`은 재현 계약을
보존한 템플릿으로 GitHub Actions에서 자동 실행되지 않는다.

Mindustry v159.7을 이용해 **구조화된 외부 Scratchpad가 Local LLM 기반 장기 자율 agent의 기억·판단·실패 복구에 미치는 영향**을 연구하는 환경이다. 게임을 잘하는 bot 자체가 최종 목적은 아니다.

주 비교는 같은 모델·관측·executor·예산의 `NO_SCRATCHPAD` 대 `STRUCTURED_SCRATCHPAD`다. 연구용 기존 게임 prototype의 OpenCode `ollama-cloud/qwen3.5:397b` 경로는 유지한다. 별도 주말 전투 시연은 로컬 DeepSeek/GLM을 사용하며 scratchpad 연구 결과로 해석하지 않는다.

## Architecture

```text
Mindustry v159.7 ↔ Java AgentBridge ↔ Python Runtime / Deterministic Executor
                                                ↕
                                      LLM + optional Scratchpad
                                                ↕
                                       Independent Evaluator
```

목표 구조다. 기존 logistics live demo와 mock 연구 runner는 별도 실행 경로이며 Memory Contract v2의 live 연결은 없다. Python은 legality/pathfinding/rotation/cost/execution/completion을 담당하고, v2의 목표·선호·복구 전략은 LLM 영역이다.

## 주말 두 모델 전투 시연 (연구 실험과 별도)

저장소 루트의 `3번 AGENT / TEST` 터미널에서 다음 **한 명령**을 실행한다. 기존 6567/8765 서버는 먼저 종료해야 하며, 로컬 Ollama에 DeepSeek Coder 6.7B와 GLM-Edge 4B 모델이 있어야 한다.

```sh
.venv/bin/python scripts/duel_demo.py
```

실행기가 Java 17 Bridge를 빌드하고 새 v159.7 서버·대칭 fixture를 준비한 뒤 `2번 CLIENT`의 `127.0.0.1:6567` 접속을 기다린다. 접속하면 두 모델이 채굴·Duo 건설·유닛 생산·교전을 자동 진행한다. 테스트용 무화면 실행은 명령 뒤에 `--headless`를 붙인다. 로그는 `build/duel-runs/one-command-*/`에 저장되며, 상세한 실험 경계와 검증 결과는 [DUEL_DEMO](docs/DUEL_DEMO.md)에 있다. 실리콘·납은 **경기 전 저장고에 둔 유한 재고**이고, 경기 중 unloader가 빈 공장으로 옮긴다; 원료 채굴·제련까지 자율 수행한 것은 아니다.

다른 머신에서는 JDK 17의 `JAVA_HOME`과 v159.7 서버 파일의 `AGENTBRIDGE_SERVER_JAR`를 지정한다. launcher의 빌드는 offline이므로 먼저 `./gradlew --no-daemon jar`로 의존성을 준비한다. 경로를 설정하지 않으면 과거 개발자의 macOS 경로를 사용한다. 게임 실행 절차와 검증 한계는 [FORK_HANDOFF](docs/FORK_HANDOFF.md)에 있다.

경기 로그는 전장 판정 `observedOutcome`과 실행 종료 `result`를 함께 기록한다. 완료된 승리·무승부는 exit 0, round 제한/timeout/실행 실패는 exit 2다. 예산 초과를 무승부로 세지 않으며, `DRAW_FIGHTERS`는 등록 병력 전멸 판정이다. 관전 `alpha`의 비명령형 좌표 변화만 재추론 비교에서 제외하고, 다른 관측 상태 변화는 계속 검사한다.

## Benchmarks / verification

| 항목 | 상태 |
|---|---|
| Logistics v1 | **VERIFIED — 과거 headless + human GUI:** Mono 채굴, Poly 정상 이동·BuildPlan 건설, drill→conveyor→core 물류. smoke/negative control |
| Memory-sensitive v2 | **VERIFIED — contract/unit:** 같은 관측·다른 history 두 사례, 누출 검사, bounded memory, terminal 판정 |
| 연구 runtime 전체 | **PARTIALLY VERIFIED:** provider/scratchpad/mock runner. live memory 통합은 별도 |
| v2 live gameplay / scratchpad 성능 개선 | **NOT VERIFIED** |
| 주말 별도 Local LLM 전투 demo | **VERIFIED_HEADLESS:** 두 로컬 모델의 한 명령 채굴·건설·경기 중 저장고 공급·공장 생산·교전; 이 버전의 GUI는 미검증 |
| 연구용 multi-agent·scratchpad 전투 | **NOT VERIFIED**, 현재 범위 밖 |

CI·단위 테스트 성공은 실제 게임 동작이나 기억 성능 향상의 증거가 아니다.

## Requirements

- **CPython 3.13.5**, `.python-version`에 고정. 다른 patch/minor는 미검증이며 3.9 호환성을 주장하지 않는다.
- Python runtime/tests/helpers는 **표준 라이브러리만 사용**한다. pip 패키지 없음.
- **JDK17**, Mindustry **v159.7**, Gradle wrapper **9.4.1**. 현재 로컬 검증은 Temurin17.0.20.
- 최초 Java build에 Gradle/Mindustry dependency 다운로드가 필요하다. wrapper·dependency SHA-256을 기록했다.
- 게임에는 별도 server/save/JAR가 필요하다. 테스트·mock에는 불필요하다. [재현·artifact 안내](docs/REPRODUCIBILITY.md)를 따른다.

## Development / test

checkout root에서 Python3.13.5로 실행한다. 터미널은 `1번 SERVER`, `2번 CLIENT`, `3번 AGENT / TEST`로 구분한다.

`3번 AGENT / TEST`:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --no-index -r requirements-dev.txt
.venv/bin/python scripts/check_environment.py --python-only
.venv/bin/python -m compileall -q agent research scripts tests experiment.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python experiment.py --scenario logistics --condition no_scratchpad --runs 1 --provider mock --output build/smoke-no-memory
.venv/bin/python experiment.py --scenario logistics --condition structured_scratchpad --runs 1 --provider mock --output build/smoke-memory
```

output 경로는 새 경로여야 한다. 기존 디렉터리는 덮어쓰지 않고 거절한다. `experiment.py`는 **항상 mock backend**다. `--provider qwen`도 실제 게임 연결을 뜻하지 않으며 비용이 발생할 수 있어 재현 명령에 사용하지 않는다. v2는 별도 contract 테스트로만 검증한다.

macOS Java17 선택:

```sh
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
.venv/bin/python scripts/check_environment.py
./gradlew --no-daemon jar
```

Linux/CI도 `JAVA_HOME`을 JDK17로 지정한다. 산출물은 checkout 이름과 무관하게 `build/libs/MindustryAgentBridge.jar`다. cache가 준비된 뒤에만 `--offline`을 사용할 수 있다. 위 연구 재현 명령은 배포·서버 시작을 자동 수행하지 않으며, 별도 주말 시연 명령만 격리 서버를 시작한다.

```sh
.venv/bin/python scripts/verify_artifacts.py --root artifacts
.venv/bin/python scripts/validate_metadata.py contracts/experiment_metadata.example.json
```

외부 artifact가 없으면 첫 명령은 missing 목록과 exit2를 반환한다. 두 번째는 **미실행 template의 형식**만 검사한다.

## 문서

- [현재 lab 포크 인계 / 재현 절차](../docs/AGENTBRIDGE_HANDOFF.md)
- [팀원 상호 검토 / 브랜치·실행 방식·협의안](docs/TEAM_REVIEW.md)
- [PROGRESS](docs/PROGRESS.md), [ROADMAP](docs/ROADMAP.md)
- [독립 감사](docs/AUDIT_2026-09-29.md), [Memory Contract v2](docs/MEMORY_CONTRACT_V2.md)
- [재현성 / artifact / metadata](docs/REPRODUCIBILITY.md)
- [현재 AgentBridge API](docs/AGENTBRIDGE_API.md)
- [v2 live mapping / trusted adapter 설계](docs/PRE_LIVE_MAPPING.md)
- [과거 GUI 검증 logistics demo](docs/LOGISTICS_DEMO.md), [control demo](docs/AUTONOMOUS_DEMO.md)

HTTP는 `127.0.0.1:8765` 전용이다. `/state`는 ground truth를 포함하므로 v2 provider에 그대로 넘길 수 없다. `/action` 성공은 명령 접수이며 실제 완공은 관측으로 확인한다.
