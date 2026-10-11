# 개인 mindustry-lab — AgentBridge 인계

기준일: 2026-10-11 (Asia/Seoul).

## 위치와 협업 규칙

- 개인 origin: https://github.com/Laon030/mindustry-lab
- 팀 upstream / PR 대상: https://github.com/time-to-think/mindustry-lab 의 `develop`
- 개인 브랜치: `feature/agentbridge-handoff`
- lab 기준 commit: `1d274c3039646bed6b3f3497cd4c1314c024b221`
- 이 머신의 작업 폴더: `/Users/andrew/capstone/mindustry-lab-laon`
- 게임 submodule: `game/`, URL `https://github.com/time-to-think/mindustry.git`,
  tag `v159.7`, commit `c9686eb5d0ae5dd47ee02c40f99f7d5018ccbc8c`.

개인 feature branch에서 작업하고 개인 origin에 push한 뒤 상호 검토한다.
팀 develop 직접 push와 force push는 하지 않는다. 팀/공식 최신 게임 동기화는
지정 maintainer의 engine PR로 진행한다. 이 lab의 게임 revision은 플러그인 API
기준에 맞춘 고정값이며, 현재 팀 develop의 최신 commit을 뜻하지 않는다.

## 보존한 코드와 실행 경계

`agentbridge/`는 개인 게임 포크 `f11b8ac4802d870ec7d9d4745ff386b1f973b047`에서
Git 추적 파일 103개를 가져온 패키지다. 출발 원본은
`Laon030/capstone-project=06f6f7fbd5f788f8914a92b80121eaaa35d5b8f3`이고,
연구 checkpoint는 별도 `stage4-agent=37617e0`에 보존되어 있다.

게임 포크 기록과 standalone 원본은 삭제하지 않았다. lab의 기존 Java/Python
소스, root Gradle/settings, 테스트는 덮어쓰지 않는다. 이번 이전은 문서·폴더·Git
연결을 바꾸며 AgentBridge의 Java/Python 동작과 Qwen/OpenCode 연결을 유지한다.

두 runtime은 **동시 실행하지 않는다**. 기존 팀 bridge와 AgentBridge는 둘 다
localhost `8765`를 사용하며 상태·action·시간 진행·건설 계약이 다르다.
AgentBridge는 정상 이동/채굴/BuildPlan 건설을 사용한다. 저장소를 함께 둔 것을
같은 어댑터로 비교 가능한 상태라고 해석하지 않는다.

## Clone 및 submodule

`3번 AGENT / TEST`에서:

```sh
git clone --branch feature/agentbridge-handoff --recurse-submodules https://github.com/Laon030/mindustry-lab.git
cd mindustry-lab
git submodule status
git remote add upstream https://github.com/time-to-think/mindustry-lab.git
git remote set-url --push upstream DISABLED
git config remote.pushDefault origin
git config push.default simple
git -C game remote set-url --push origin DISABLED
```

이미 clone한 경우 `git submodule update --init --recursive`로 기록된 game commit을
가져온다. `git submodule update --remote`로 임의 최신 버전을 선택하지 않는다.
게임 자체를 수정하려면 별도 개인 engine 포크와 feature branch를 사용한다.

## AgentBridge 테스트 및 빌드

**CPython 3.13.5 / Java 17 / Mindustry v159.7** 기준이다.
명령은 lab 루트가 아닌 `agentbridge/`에서 실행한다.

```sh
cd agentbridge
python3.13 -m venv .venv
.venv/bin/python scripts/check_environment.py --python-only
.venv/bin/python -m unittest discover -s tests -q
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
./gradlew --no-daemon jar
```

Python tests는 표준 라이브러리만 사용하며 서버·모델을 실행하지 않는다.
macOS 이외 환경에서는 자신의 JDK 17 경로를 `JAVA_HOME`으로 지정한다.
최초 빌드는 의존성 다운로드가 필요하고 이후 준비된 cache에서만 `--offline`을
사용할 수 있다. 출력은 `agentbridge/build/libs/MindustryAgentBridge.jar`다.
게임 submodule은 버전 고정 및 API 참조용이며 여기서 engine build를 자동 실행하지 않는다.

lab 루트의 기존 팀 패키지는 별도로 검증한다:

```sh
cd ..
python3.13 -m unittest discover -s tests -q
./gradlew --no-daemon jar spectatorJar
```

## 별도 게임 시연

AgentBridge의 [실행 안내](../agentbridge/README.md)와
[재현 artifact 규약](../agentbridge/docs/REPRODUCIBILITY.md)을 따른다.
v159.7 server JAR와 기존 Ollama 모델은 외부 runtime이며 Git에 올리지 않는다.
이 머신의 서버는 `/Users/andrew/capstone/MindustryServer/server-release.jar`다.

`3번 AGENT / TEST`의 `agentbridge/`에서:

```sh
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
export AGENTBRIDGE_SERVER_JAR='/absolute/path/to/v159.7/server-release.jar'
.venv/bin/python scripts/duel_demo.py
```

자신의 실제 서버 경로를 지정한다. 기존 게임 포트 `6567`과 HTTP `8765`를 사용하는
runtime은 먼저 종료한다. launcher는 소유하는 격리 서버만 관리하고 기존 서버
설치에 plugin을 덮어쓰지 않는다. `1번 SERVER`, `2번 CLIENT`, `3번 AGENT / TEST`
터미널 구분을 유지하며 CLIENT는 `127.0.0.1:6567`로 접속한다.

## 검토 순서와 미검증 범위

1. 서로의 패키지를 별도로 실행하며 관측 / 명령 접수 / 행동 완료 계약을 비교한다.
2. 건설 시간·자원·fixture·모델·승패 조건을 맞춘 뒤 동일 조건 실험을 준비한다.
3. 필요한 기능만 작은 feature branch와 팀 lab PR로 제안한다.

이전 10/07 duel 증거는 headless `DRAW_FIGHTERS`, `gameOver=false`였다.
이번 이전의 테스트·컴파일은 새 실제 게임/GUI 검증 또는 scratchpad 성능 개선
증거가 아니다. 최신 GUI, native Core 승리, 연구 live v2는 별도 검증이 남아 있다.
하위 `.github/workflows`는 원본 계약 보존 템플릿이며 root CI를 추가하지 않았다.
팀 PR, merge 또는 기찬님 DM은 자동으로 수행하지 않는다.

## 기찬님께 보낼 협의 초안 (미발송)

> 기찬님, 멘토님 규칙에 맞춰 팀 mindustry-lab을 제 계정으로 포크하고,
> 제 AgentBridge 코드는 별도 agentbridge 폴더에 정리했습니다.
> 게임은 팀 mindustry를 submodule로 연결해 v159.7로 고정했어요.
> https://github.com/Laon030/mindustry-lab/tree/feature/agentbridge-handoff
> 기존 기찬님 코드는 건드리지 않았고, 서로의 프로그램은 별도로 실행하도록 했습니다.
> 먼저 관측/명령/행동 완료 API와 건설 시간·자원·승패 기준을 비교해보고,
> 공통 실험 조건과 각자 맡을 구현 범위를 맞춰보면 좋겠습니다.
