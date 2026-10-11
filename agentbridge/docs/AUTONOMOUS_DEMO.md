# Autonomous single-LLM vertical slice

이 데모는 정식 S1/S2 평가 전에 지속적인 observe → reason → act → verify → replan을 검증한다. 실제 검증 상태와 실행 증거는 [PROGRESS.md](PROGRESS.md)를 확인한다. 게임 결정 모델은 기존 `ollama-cloud/qwen3.5:397b`이며 Codex와 별개다.

## 실행

기존 agent 프로세스가 같은 유닛을 조종하지 않도록 종료한다. 새 sandbox를 사용할 때는 기존 게임을 저장한다. 최신 JAR를 Java 17로 빌드하고 전용 서버가 정지한 상태에서 백업 후 배포한다.

`1번 SERVER` (shell):

```sh
cd /Users/andrew/capstone/MindustryServer
"$(/usr/libexec/java_home -v 17)/bin/java" -jar server-release.jar
```

새 데모용 server console (이미 다른 게임을 host 중이면 먼저 저장하고 `stop`):

```text
host Islands sandbox
js Vars.state.rules.infiniteResources=false; Vars.state.rules.instantBuild=false; Vars.state.rules.waves=false; Vars.state.rules.waveTimer=false;
```

`2번 CLIENT`: v159.7로 `127.0.0.1:6567`에 접속한다. 실제 같은 팀 플레이어가 있어야 기존 action API를 사용할 수 있다. 기본 Sharded 팀을 사용한다.

`1번 SERVER`: agent를 시작하기 전에 시험 유닛을 한 번만 준비한다. 이는 데모 fixture이며 생산 기능 검증이 아니다. 기존 Mono/Poly가 있으면 중복 생성하지 않는다.

```text
js var demoCore=Vars.state.rules.defaultTeam.core(); if(!Groups.unit.contains(u => u.type==UnitTypes.mono && u.team==demoCore.team)) UnitTypes.mono.spawn(demoCore.team,demoCore.x+24,demoCore.y); if(!Groups.unit.contains(u => u.type==UnitTypes.poly && u.team==demoCore.team)) UnitTypes.poly.spawn(demoCore.team,demoCore.x+40,demoCore.y);
js var demoPlayer=Groups.player.find(p => p.team()==demoCore.team); var demoMiner=Groups.unit.find(u => u.type==UnitTypes.mono && u.team==demoCore.team); InputHandler.setUnitCommand(demoPlayer,[demoMiner.id],UnitCommand.moveCommand);
```

마지막 줄은 agent 시작 전 fixture를 대기 상태로 만드는 정상 command 전환이다. 먼저 접속한 같은 팀 Player가 없으면 실행하지 않는다. Mono의 기본 auto-mining이 LLM 판단 전에 자원을 채워, 그 성과를 LLM 채굴로 오인하는 것을 방지한다. agent 시작 이후에는 실행하지 않는다.

`3번 AGENT / TEST`:

```sh
cd /Users/andrew/capstone/MindustryAgentBridge
python3 agent/autonomous_llm_agent.py --duration 300
# 계속 실행은 --duration 없이 실행; Ctrl+C로 종료
```

실행 이후 사람은 mine/move/build를 보내지 않는다. Python은 실제 ID를 자동 선택하고 Qwen의 구조화된 역할/후보 선택만 검증해 전달한다. 같은 역할 유닛이 여러 개면 가장 작은 ID를 선택한다. 유닛이 교체되면 이전 ID를 전제로 한 LLM 응답을 폐기한다.

기본 설정: 관측 1초, 판단 완료 후 8초 간격(사건 재계획은 최소 5초 간격), copper reserve 50, lead reserve 10, 작업 구역 내 conveyor 총 3개. 이 값들은 기술 데모 파라미터이며 연구 결론이 아니다. `--poll-interval`, `--decision-interval`, `--llm-timeout`, `--copper-reserve`, `--lead-reserve`, `--max-conveyors`로 조절한다. `--help`에 전체 옵션이 있다.

기본 작업 구역은 첫 코어 기준 `(-38,+7)` 타일 중심, radius 2이다. Islands 데모에 맞춘 작은 구역이며 범용 base planner가 아니다. 다른 맵은 `--area TILE_X TILE_Y --radius 2`로 작업 구역을 지정한다. 타일은 비어 있고 v159.7 `Build.validPlace`를 통과한 경우만 후보가 된다. 후보가 없으면 건설을 강행하지 않는다. 기존 conveyor도 총 개수에 포함하므로 이미 3개라면 새 건설 없이 자원 관리를 계속한다.

## 관측·행동·완료 의미

- 기존 `/state` 필드를 유지하며 `units[].activity`와 `demo`만 추가한다. `/state?tileX=X&tileY=Y&radius=R`의 radius는 1–6, 최대 169타일이다. 기본은 25타일이며 유닛별 계획은 최대 8개와 전체 개수를 반환한다.
- `activity`: commandability/현재 command, mine 대상·실제 mining·운반 자원, build 가능 여부/범위·계획. `demo`: world ID, 같은 팀 명령 주체 존재, 자원 rules, 광석 존재, conveyor 비용, 제한 구역 타일·블록/팀/회전·공사 진행·유효 회전 후보.
- `mine`: Mono의 선택 자원과 실제 mining을 관측한 뒤, 일치하는 작업 중 새 코어 재고 증가를 확인하면 자원 증가 milestone을 완료 처리한다. 작업 실행이 관측되기 전에 발생한 재고 증가만으로는 완료 처리하지 않는다. 정상 mine command 자체는 계속 동작한다. 다른 생산원이 있는 게임에서 증가량의 엄밀한 유닛별 귀속을 제공하는 평가 지표는 아니다.
- `build`: Poly의 정상 rebuild command와 BuildPlan을 사용한다. Python은 실제 목표 타일의 완성 block, team, rotation이 모두 일치해야 완료 처리한다. HTTP 200은 COMMAND ACCEPTED만 의미한다.
- `move`: miner/builder의 `core` 또는 `work-area`라는 명명된 위치만 선택 가능하며 15 world units 안 도착을 확인한다. 건설을 위한 이동은 BuildPlan이 수행하므로 별도 move를 강제로 시연하지 않는다.
- `wait`: HTTP mutation 없이 관측을 계속한다.
- Qwen은 독립된 임시 작업 디렉터리, `--pure`, 모든 도구 permission deny, 결정 전용 agent 설정으로 실행한다. shell=False subprocess argument 목록을 사용한다. 모델에게 직접 게임 명령/도구 실행을 허용하지 않는다.
- JSON 중복 키/NaN/추가 필드/지원 밖 행동/임의 좌표/없어진 역할/자원 부족/변경된 타일/이미 진행 중인 건설은 Python 검증에서 거절한다. LLM 대기 중에도 빠른 관측을 유지하며 world/역할 변경과 오래된 응답을 검사한다.
- POST 통신이 끊기면 접수 여부를 uncertain으로 추적하고 실제 결과를 먼저 확인한다. 동일 건설을 곧바로 재전송하지 않는다. 작업이 장시간 진전 없으면 실패로 기록하고 재계획한다.

## 로그와 시각 확인

터미널에 `[OBSERVE]`, `[ASK LLM]`, `[LLM DECISION]`, `[VALIDATE]`, `[ACT]`, `[MONITOR]`, `[COMPLETE]`, `[ERROR]`를 표시한다. 원본 JSONL은 `build/demo-runs/<run-id>.jsonl`에 보존한다. `--log PATH`는 새 파일만 생성하며 덮어쓰지 않는다.

클라이언트에서 확인할 내용:

1. LLM mine 판단 이후 Mono의 실제 채굴과 자원 증가.
2. LLM build 판단 이후 Poly의 이동 및 정상 conveyor 완성.
3. 같은 건설의 `[COMPLETE]` 이후에도 관측과 다음 LLM 판단이 이어지는지.
4. 수분간 진행 중 사람이 action을 보내지 않았는지.

Conveyor는 비용이 작아 정상 규칙에서도 한 builder update 안에 완성될 수 있다. 애니메이션을 길게 보려고 건설 속도나 자원 규칙을 바꾸지 않는다. 시작/완료 event가 같은 tick이라는 이유만으로 instant placement로 판단하지 않는다.

OpenCode가 내보내는 token usage와 reportedCost는 로그에 남기지만 reportedCost=0을 실제 무료 과금의 증거로 간주하지 않는다. 인프라 호출·지연과 게임 진행 시간은 서로 구분한다.

## 개발 검증과 제한

```sh
python3 -m unittest discover -s tests -v
JAVA_HOME=$(/usr/libexec/java_home -v 17) ./gradlew --offline --no-daemon jar
```

Headless 서버 통합 테스트에서는 GUI 대기 없이 기존 API 경로를 검증하기 위해 서버 내부 Player fixture를 `Groups.player`에 등록할 수 있다. 실제 네트워크 client 접속과 다르며 반드시 기록한다. production plugin에는 자동 fixture 생성이나 no-player 우회가 없다. fixture는 테스트 종료 시 제거한다.

게임 action은 runtime 종료 후에도 진행될 수 있다. 재시작 전 현재 작업과 구역 내 기존 conveyor를 확인한다. 이 데모에는 attack, unit production, multi-agent, 대규모 reset/evaluation framework가 없다.
