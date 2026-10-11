# 재현성 및 live 연결 전 계약

갱신: 2026-10-01. 이 문서는 `2d77541299cf6f83f15b2df26d62643c15d20f29`에서 시작한 재현성 milestone의 결과다. 새 게임 실행이나 LLM 추론 결과가 아니다. 기존 logistics v1의 GUI/headless 증거와 Memory Contract v2의 단위 계약은 별도로 유지한다.

## 고정 환경과 3번 AGENT / TEST 절차

현재 확인한 Python 실행 파일은 `/opt/anaconda3/bin/python3`의 **CPython 3.13.5**다. `.python-version`은 이 정확한 버전을 지정한다. 3.13의 다른 patch 및 Python 3.9 지원을 주장하지 않는다. Python runtime, 연구 코드, 테스트 및 검증 helper에는 제3자 pip 패키지가 없으므로 `requirements-dev.txt`는 비어 있는 의존성 선언이며 설치는 network 없이 가능하다. 이 방법은 Python interpreter 자체를 제공하지 않는다.

checkout root에서 `python3.13`이 해당 버전인지 확인한 다음 다음 명령을 실행한다.

```sh
python3.13 --version
python3.13 -m venv .venv
.venv/bin/python -m pip install --no-index -r requirements-dev.txt
.venv/bin/python scripts/check_environment.py --python-only
.venv/bin/python -m compileall -q agent research scripts tests experiment.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_metadata.py contracts/experiment_metadata.example.json
```

macOS에서는 `export JAVA_HOME="$(/usr/libexec/java_home -v 17)"` 후 다음을 실행한다. Linux/CI에서도 JDK 17을 `JAVA_HOME`으로 지정한다.

```sh
.venv/bin/python scripts/check_environment.py
./gradlew --no-daemon jar
```

Gradle wrapper는 9.4.1이며 배포 ZIP의 SHA-256은 `gradle/wrapper/gradle-wrapper.properties`에, compile dependency `Anuken:Mindustry:v159.7`의 SHA-256은 `gradle/verification-metadata.xml`에 고정했다. 첫 Java build에는 wrapper와 dependency를 받을 network가 필요하다. 캐시가 준비된 뒤에는 `./gradlew --offline --no-daemon jar`가 가능하다. `settings.gradle`은 checkout 디렉터리 이름과 무관하게 `build/libs/MindustryAgentBridge.jar`를 만든다. Java 서버 JAR와 save는 이 build에 필요하지 않다.

연구용 mock smoke는 새 output 디렉터리를 지정한다. 두 조건은 모두 `experiment.py`의 deterministic mock backend를 사용하며 실제 게임 서버나 LLM 연결 증거가 아니다.

```sh
.venv/bin/python experiment.py --scenario logistics --condition no_scratchpad --runs 1 --provider mock --output build/smoke-no-memory
.venv/bin/python experiment.py --scenario logistics --condition structured_scratchpad --runs 1 --provider mock --output build/smoke-memory
```

GitHub Actions의 `buildJar`와 `pythonContracts`는 각각 Java 17 JAR와 Python 3.13.5 compileall/전체 unittest를 검사한다. CI 설정을 로컬에서 동일한 명령으로 확인했지만 **GitHub hosted CI run은 수행되지 않았다**. CI 통과도 Mindustry runtime 검증을 대신하지 않는다. Python 패키지 cache는 의존성 목록이 비어 있어 사용하지 않는다.

## 외부 artifact 인수 및 검증

Git에는 benchmark/spec, API inventory, metadata contract와 검증 script가 있다. 정확한 save, 과거 배포 JAR, dedicated server JAR, 원본 GUI/headless 로그 및 compile dependency binary는 Git에 넣지 않았다. `experiments/artifacts.json`이 각 파일의 역할, Git 포함 여부, 원본 인수/생성 방법, bundle 내 상대 경로와 expected SHA-256을 기록한다. **원본 로그는 재실행으로 동일한 바이트를 만들 수 없다.** save를 데모 절차로 새로 구성해도 역사적 save와 같다고 할 수 없다.

원본 관리자로부터 받은 파일을 새 checkout의 `artifacts/` 아래 manifest의 `bundle_path`대로 배치한다. 기존 운영 server의 save/JAR를 덮어쓰거나 서버에 자동 배포할 필요가 없다. 예를 들어 과거 fixture는 `artifacts/autonomous-logistics-base.msav`, 과거 JAR는 `artifacts/MindustryAgentBridge.jar`, 원본 로그는 `artifacts/logs/`에 둔다. 이 디렉터리는 Git ignore 대상이다. 로컬의 현 원본 경로는 dedicated server의 `config/saves/`, `config/mods/`, repo의 `build/demo-runs/`에 분산되어 있으므로 배포 가능한 공개 다운로드 경로가 있다는 뜻이 아니다. v159.7 dedicated server JAR와 Gradle compile dependency는 manifest의 출처 설명을 참고할 수 있으나, binary hash 일치를 별도로 확인해야 한다.

```sh
.venv/bin/python scripts/verify_artifacts.py --root artifacts
.venv/bin/python scripts/verify_artifacts.py --root artifacts --only logistics-save
```

helper는 **읽기 전용** SHA-256 확인이다. 모두 일치하면 exit 0, 하나라도 없고 mismatch가 없으면 exit 2, mismatch/읽기 실패면 exit 1이다. `--only`는 필요한 artifact만 좁혀 확인한다. 이 helper는 download, restore, overwrite, deploy를 수행하지 않는다. 전체 일치는 artifact 무결성 증거이며 save load, GUI 재현 또는 로그의 진실성 독립 검증은 아니다.

이번 격리 검증에서는 bundle이 없는 상태의 10개 항목 모두 `missing`을 확인하고, 로컬 원본을 임시 checkout의 ignore된 `artifacts/`에 **복사**한 후 10개 모두 expected hash와 일치함을 확인했다. 원본 save/JAR/로그의 바이트는 수정하지 않았다.

## Manifest와 실제 실행 계약

실제 Java API는 [AgentBridge API inventory](AGENTBRIDGE_API.md) 및 `contracts/agentbridge_api.json`을 따른다. `/state` GET과 `/action` POST만 있다. 이전 logistics v1 manifest의 `/units`, `/buildings`, `/tasks/{task_id}`는 미구현이어서 제거했다. `wait`는 Python 내부 intent다. `/action`의 200은 command 접수이고 task completion은 후속 관측 판정이다.

`experiments/logistics_benchmark.json`은 **benchmark version 1**을 보존하면서 fixture 경로를 portable bundle 경로로 바꾸고, 실제 endpoint/필드·plan/status view를 명시했다. fixture hash, goal, success criterion, 숫자 budget은 바꾸지 않았다. 이 manifest는 v1 smoke/negative control이다. `BenchmarkSpec.verify_initial_state()`가 검사하는 map, full rules, 네 자원, unitCounts, core footprint는 **normalized mock/fixture snapshot** 형식이다. raw `/state`가 모두 제공한다고 주장하지 않는다. 따라서 실제 save reset을 검증할 live adapter는 아직 없다.

| 값 | 현재 의미 / 집행 범위 |
|---|---|
| v1 `action_budget=80` | mock에서 synthetic mine/build command를 센다. wait 제외. 기존 live `LogisticsRuntime`에 이 manifest 숫자가 자동 적용되지는 않는다. |
| v1 `timeout_seconds=360` | mock은 blocking call 사이에서 검사한다. hard cancellation이 아니다. 기존 live는 별도 `--duration`을 쓴다. |
| v1 `context_reset_every_decisions=2` | stateless provider의 boundary hook. 실제 대화 맥락 소실이라고 부르지 않는다. |
| v1 seed | mock metadata에 기록하는 값이다. 게임 RNG/model에 적용된 seed가 아니다. |
| v2 `action_budget=4`, `timeout_seconds=60` | `experiments/memory_sensitive_v2.json`의 microcase **계약 값**이다. live 집행이 확인되지 않았고 v1 단위와 직접 비교하지 않는다. |
| v2 model/executor | model ID는 비교 조건의 동일성 표기이며 inference 실행 증거가 아니다. `proposal-only-v2`는 실제 live executor 버전이 아니다. |

`agent/logistics_planner.py`와 `agent/logistics_agent.py` 및 `verified_commit=a5dd369`은 과거 GUI 검증된 v1 경로를 가리킨다. `experiment.py`는 `MockLogisticsBackend`를 쓰므로 이 경로를 실행하지 않는다. v2 원본 JSON/모듈과 paired-history 보장은 바꾸지 않았다.

## Experiment metadata contract

`contracts/experiment_metadata.json`은 schema version 1의 **필수 field 목록과 타입/범위/enum 계약**이다. 각 field는 `{status, value, source}`로 표현한다. `known`에는 실제 값과 출처가 필요하고 `unknown`/`unavailable`/`not_applicable`에는 `value:null`과 그 이유를 `source`에 적는다. `contracts/experiment_metadata.example.json`의 모든 unknown은 **미실행 양식**이다.

계약은 benchmark ID/version, Git commit 및 dirty 상태, Mindustry/Python/Java 버전, Bridge JAR·save·prompt hash, model ID 및 정확한 revision, provider/runtime ID·버전, temperature/top_p/max tokens/thinking, memory condition 및 scratchpad schema, timeout 값과 집행 방식, action/decision budget 및 단위, seed와 적용 범위, episode/run ID, executor·observation contract version, 실제 context loss 여부를 요구한다. 현재 provider가 주지 않는 revision/digest를 추측해 채우지 않는다. `scripts/validate_metadata.py`는 구조와 값 형식만 검사한다. 기존 runner는 이 envelope를 아직 생성하지 않으므로 **live run metadata 충족은 미검증**이다.

## 격리된 fresh-checkout simulation 결과

임시 디렉터리 `renamed-checkout`에 현재 Git 가시 파일과 미커밋 milestone 수정본을 복사해 기존 checkout/worktree와 분리했다. 이는 당시 pending 변경을 포함한 **source snapshot 재현**이지, 원격에 이미 올라간 clean commit에서의 clone 검증은 아니다. `.git`, `.venv`, `build`, 원본 artifact는 처음에 포함하지 않았다. CPython 3.13.5 interpreter는 이 host에서 가져왔고 새 venv에는 system site packages를 넣지 않았다.

| 검사 | 결과 |
|---|---|
| `pip install --no-index -r requirements-dev.txt` | 성공, 설치할 외부 패키지 없음 |
| 환경 검사/compileall | 성공 |
| 전체 unittest | **70/70 성공** (기존 61 + 신규 9) |
| metadata example 형식 검증 | 성공; 실행값 증거는 아님 |
| bundle 없이 artifact 검사 | 예상대로 exit 2 / 10개 missing |
| 두 조건 mock smoke 각 1 run | 성공; research/game outcome이 아님 |
| 외부 원본 10개 복사 뒤 hash 검사 | 10/10 일치 |
| 빈 Gradle cache + Java 17 build | 성공. Gradle 9.4.1/compile dependency 다운로드 포함 |
| 새 hash metadata로 offline `clean jar` | 성공. 산출 JAR SHA-256 `60c79393e5cddf855e5baf570537198cf21387c119f14f479ae94769ffbe5def` |

로컬 historical deployed JAR와 임시 checkout 새 build JAR의 SHA-256이 같았다. 이것은 이 host의 build 재현 결과이지 모든 OS의 bit-for-bit 재현 보장은 아니다. 전체 live reset, 서버 실행, 클라이언트 GUI, LLM 선택, v2의 실제 성능은 이번 milestone에서 확인하지 않았다.

## Remote backup 경계

시작 branch는 `stage4-agent`, base HEAD는 `2d77541`, fetch한 `origin/stage4-agent`는 `82b3ce7`이었다. 시작 시 branch가 remote보다 **10 commits 앞섰고 0 behind**였다. `origin/master`는 `6bb236d`, local `master`는 `fdeb005`였으며 remote master의 별도 `docs/PROJECT_DIRECTION.md` commit은 이번 branch에 없다. 다른 두 worktree는 `82b3ce7`에 머물러 있어 변경하지 않았다.

이번 local checkpoint 뒤 원격 branch가 그대로라면 `stage4-agent`를 **non-force push로 fast-forward**할 수 있다. push는 수행하지 않는다. 원격 master와 문서 commit의 통합 여부는 별도 검토 대상이며 **stage4-agent 백업을 위해 merge/rebase가 선행될 필요는 없다**. 실제 push 직전에는 remote ref를 다시 확인해야 한다.
