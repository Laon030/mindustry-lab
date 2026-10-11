# 개인 Mindustry 포크 — AgentBridge 인계

기준일: 2026-10-11 (Asia/Seoul).

> **이 문서는 이전 게임 포크 인계의 보존 기록이다.** 현재 개발 위치는
> `Laon030/mindustry-lab:feature/agentbridge-handoff`의 `agentbridge/`다.
> 새 clone·submodule·test/build 절차는 [현재 lab 인계 안내](../../docs/AGENTBRIDGE_HANDOFF.md)를 따른다.
> 아래 게임 포크 clone 명령은 과거 패키지를 확인할 때만 사용한다.

## 위치와 보존 범위

- 개인 포크: [Laon030/mindustry](https://github.com/Laon030/mindustry), 직접 부모 `time-to-think/mindustry`.
- 작업 브랜치: [`feature/agentbridge-handoff`](https://github.com/Laon030/mindustry/tree/feature/agentbridge-handoff).
- 팀 기준: `develop`의 `e2f588543904bd327a60bd1f8806f085e1dba1d2` (기찬님 PR #1 merge commit).
- 기존 standalone 원본: `Laon030/capstone-project`, checkpoint `06f6f7fbd5f788f8914a92b80121eaaa35d5b8f3`. 연구 기준은 별도 `stage4-agent=37617e0`에 보존되어 있다.
- 원본 Git 추적 파일 102개만 복사했다. 개인 저장소의 Git 이력·비추적 파일·원본 save/logs·모델·서버 JAR·build/runtime 파일은 가져오지 않았다.
- 새 패키지 외의 engine 파일, 상위 Gradle/settings/CI와 기찬님 integration 파일은 수정하지 않는다. 이 패키지는 상위 build에서 자동 실행되지 않는다. 두 runtime은 API·시간 진행·건설/생산 규칙이 다르며 현재 통합된 것이 아니다.
- 이 브랜치만 개인 `origin`에 push한다. 팀·공식 remote push, 팀 PR, `develop` 변경은 이번 인계 범위에 없다.

## 가져온 작업

| 구성 | 검토 범위 |
|---|---|
| `src/agentbridge`, `plugin.json`, Gradle wrapper/config | localhost 관측·명령, Core.app.post, 정상 이동/채굴/BuildPlan 건설/생산/전투 |
| `agent`, `scripts` | 기존 Qwen/OpenCode 경로, 별도 로컬 DeepSeek/GLM duel runner와 fixture |
| `research`, `experiment.py` | scratchpad/조건/지표, Memory Contract v2, mock 연구 runner |
| `tests`, `contracts`, `experiments` | 단위·계약 검증 및 외부 artifact hash/준비 규약 |
| `docs` | 역사적 게임 검증, 미검증 범위, 연구·demo 구분 |

소스 복사 후 바뀐 executable 코드는 `scripts/duel_demo.py`의 **경로 설정**뿐이다. `JAVA_HOME`과 `AGENTBRIDGE_SERVER_JAR` 환경변수를 지원하며 미지정 시 기존 개발 경로를 사용한다. 게임 메커니즘·모델·판단/실행 의미론은 유지한다.

## Clone, 테스트, 빌드

`3번 AGENT / TEST`에서 실행한다. Python은 **CPython 3.13.5**, Java는 **JDK 17**, 게임 API/서버는 **v159.7**이다.

```sh
git clone --branch feature/agentbridge-handoff --single-branch https://github.com/Laon030/mindustry.git
cd mindustry/integrations/mindustry-llm-agent/agentbridge
python3.13 -m venv .venv
.venv/bin/python -m pip install --no-index -r requirements-dev.txt
.venv/bin/python scripts/check_environment.py --python-only
.venv/bin/python -m unittest discover -s tests -q
```

테스트는 서버·Ollama·pip 패키지 없이 실행된다. 정확한 Python 버전이 다르면 환경 확인이 실패한다. 다른 Python/OS 조합은 미검증이다.

JDK 17을 선택한 뒤 plugin 폴더의 wrapper로 빌드한다. macOS 예시:

```sh
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
.venv/bin/python scripts/check_environment.py
./gradlew --no-daemon jar
```

최초 빌드는 Gradle/Mindustry dependency를 다운로드한다. 준비된 cache에서는 `--offline`을 추가할 수 있다. 산출물은 이 폴더의 `build/libs/MindustryAgentBridge.jar`이며, 상위 Mindustry engine build는 실행하지 않는다.

## 선택 사항: 별도 duel 시연

먼저 실제 v159.7 `server-release.jar`, 로컬 Ollama, `deepseek-coder:6.7b-instruct`와 `hf.co/zai-org/glm-edge-4b-chat-gguf:Q4_K_M`을 준비한다. 필요한 서버/artifact의 출처와 hash는 [REPRODUCIBILITY.md](REPRODUCIBILITY.md), `experiments/artifacts.json`에 있다.

`JAVA_HOME`을 위처럼 JDK 17로 선택하고, **자신의 실제 서버 파일 절대 경로**를 환경변수로 지정한다. 예시의 경로를 그대로 사용할 수는 없다.

```sh
export AGENTBRIDGE_SERVER_JAR='/absolute/path/to/v159.7/server-release.jar'
.venv/bin/python scripts/duel_demo.py
```

- 먼저 기존 6567/8765 runtime을 종료한다. 기찬님 integration과 동시 실행하지 않는다. HTTP는 localhost 전용이다.
- launcher는 이 패키지의 `build/duel-runs` 아래 격리 runtime을 만들고 소유 서버를 시작한다. 기존 게임 설치에 plugin을 자동 복사하지 않는다.
- launcher가 `1번 SERVER`를 관리하고, `2번 CLIENT`의 v159.7 게임에서 `127.0.0.1:6567`로 접속한다. `--headless`는 CLIENT 없이 새 경기를 실행한다.
- fixture spawn·유한 silicon/lead 저장고는 경기 전 시험 준비다. 경기 중 채굴·공급·건설·생산·전투는 정상 게임 경로를 사용한다. 원료 채굴·제련까지 자율 수행한 것은 아니다.
- 과거 최신 full match는 headless `DRAW_FIGHTERS`, native `gameOver=false`였다. 최신 GUI 장면, Core 승리, v2 live 연구와 scratchpad 효과는 입증되지 않았다. 이번 인계 테스트/빌드를 새 게임 검증으로 해석하지 않는다.

이 하위 `.github/workflows/gradle.yml`은 standalone 원본의 테스트 계약을 보존한 템플릿이다. 저장소 루트 workflow를 변경하지 않았으므로 이 패키지의 GitHub CI가 자동 실행되는 것은 아니다. 새 CI 연결은 별도 작업이다.

## SourceTree에서의 작업 연결

현재 개발자의 두 클론은 SourceTree bookmark에 등록되어 있다. Mindustry는 `feature/agentbridge-handoff`가 `origin/feature/agentbridge-handoff`를 추적하고, 기본 push 대상은 개인 `origin`이다. 팀/공식 remote의 push URL은 로컬에서 차단되어 있다. 이 설정은 `.git/config`에 있으므로 다른 컴퓨터에서 clone하면 별도로 설정해야 한다.

개발자는 개인 feature branch에서 구현·검증한 뒤 개인 포크에 checkpoint를 저장한다. 팀 integration 계약과 범위가 합의되기 전에는 상위 engine/기찬님 코드를 변경하지 않는다. 지금의 runtime은 독립 package이며 Git 연결 완료를 게임/연구 완료로 해석하지 않는다.

## 다음 검토

기찬님과 각 패키지를 별도로 실행하고 관측·action 접수/완료·시간 진행·실패/승패 정의를 맞춘다. 통합 또는 팀 PR은 그 뒤 별도 합의로 진행한다. 이 개인 포크는 공개되므로 리뷰어가 읽기 위해 collaborator 초대를 받을 필요가 없다.
