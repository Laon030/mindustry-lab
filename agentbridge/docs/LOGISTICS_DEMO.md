# Autonomous Early-Game Logistics demo

이 절차는 정식 S1/S2 실험 전에 copper bootstrap → mechanical drill → conveyor → Sharded core의 실제 흐름을 확인하는 single-LLM 기술 데모다. 기존 control 데모 절차와 검증 범위는 [AUTONOMOUS_DEMO.md](AUTONOMOUS_DEMO.md), 현재 증거는 [PROGRESS.md](PROGRESS.md)를 따른다.

## 검증된 계약

- Mindustry/AgentBridge/Python/LLM 경계를 유지한다. Qwen은 고수준 intent만 선택하고 좌표·경로·회전·비용·완료 판정은 Python이 담당한다.
- `GET /state?view=logistics-plan`은 계획할 때만 코어 주변 radius 48의 ore, drill 후보와 conveyor cell/rotation mask를 제공한다.
- `GET /state?view=logistics-status`는 1초 관측용이며 정적 계획 격자를 생략하고 core 수량/누적 수령, 건물, drill 생산, conveyor item을 제공한다.
- `POST /action`의 기존 mine/build/move만 사용한다. Drill과 conveyor는 Poly의 정상 BuildPlan 이동·건설로 완성한다.
- 성공은 계획된 topology 완공, Mono의 lead 채굴 격리, copper drill 가동, 계획 conveyor 위 copper 관측, core copper와 누적 copper 수령 증가를 모두 요구한다.

v159.7 기준 mechanical drill은 size 2, tier 2, copper 12이고 copper hardness는 1이다. 기본 conveyor는 size 1, copper 1이다. Runtime은 `12 + conveyor 개수 + safety margin 10`을 이번 계획의 필요 copper로 계산한다.

## 빌드와 배포

`3번 AGENT / TEST`:

```sh
cd /Users/andrew/capstone/MindustryAgentBridge
python3 -m unittest discover -s tests -v
JAVA_HOME=$(/usr/libexec/java_home -v 17) ./gradlew --offline --no-daemon jar
```

`1번 SERVER`를 완전히 종료하고 6567/8765 listener가 없는 것을 확인한 뒤 기존 JAR를 백업하고 `build/libs/MindustryAgentBridge.jar`를 `/Users/andrew/capstone/MindustryServer/config/mods/`에 복사한다. 서버가 실행 중일 때 JAR를 교체하지 않는다.

## 결정적 시작 save 준비

`1번 SERVER`:

```sh
cd /Users/andrew/capstone/MindustryServer
"$(/usr/libexec/java_home -v 17)/bin/java" -jar server-release.jar
```

server console에서 새 Islands sandbox를 연 뒤 rules를 설정한다.

```text
host Islands sandbox
js Vars.state.rules.infiniteResources=false; Vars.state.rules.instantBuild=false; Vars.state.rules.waves=false; Vars.state.rules.waveTimer=false;
```

개발용 headless 실행에서는 same-team Player가 필요하다. 아래 no-op connection Player는 action 권한 fixture일 뿐 production plugin 기능이 아니다. 새 sandbox에서 한 번만 등록하고 Mono/Poly를 대기 명령으로 둔다.

```text
js var hc=extend(NetConnection,"headless-fixture",{send:function(o,r){},close:function(){}}); var hp=Player.create(); hp.name="headless-fixture"; hp.team(Team.sharded); hp.con=hc; hc.player=hp; hc.hasConnected=true; hp.add(); var demoCore=Team.sharded.core(); demoCore.items.clear(); UnitTypes.mono.spawn(demoCore.team,demoCore.x+24,demoCore.y); UnitTypes.poly.spawn(demoCore.team,demoCore.x+40,demoCore.y); var demoMiner=Groups.unit.find(u => u.type==UnitTypes.mono && u.team==demoCore.team); var demoBuilder=Groups.unit.find(u => u.type==UnitTypes.poly && u.team==demoCore.team); InputHandler.setUnitCommand(hp,[demoMiner.id,demoBuilder.id],UnitCommand.moveCommand); hp.remove();
save autonomous-logistics-base
```

임시 Player는 명령 설정 직후 제거한다. 이 save에는 맵, rules, copper/lead 0, Mono/Poly와 시작 command가 고정되고 Player는 포함되지 않는다. 다시 실행할 때는 `load autonomous-logistics-base` 후 headless면 Player/connection fixture만 다시 등록하고, GUI면 실제 CLIENT가 연결될 때까지 기다린다. 동일 save를 쓰더라도 모델 응답과 실시간 unit 궤적이 완전 결정적이라고 주장하지 않는다.

## 실행

GUI 검증에서는 먼저 `2번 CLIENT` v159.7을 `127.0.0.1:6567`에 연결한다. `/state`의 `demo.commandReady=true`를 확인하기 전에는 agent를 시작하지 않는다. Agent 시작 이후 사람이나 server console은 mine/build/move를 보내지 않는다.

`3번 AGENT / TEST`:

```sh
cd /Users/andrew/capstone/MindustryAgentBridge
python3 agent/logistics_agent.py --duration 360
```

기본 로그는 새 `build/demo-runs/logistics-<uuid>.jsonl`에 생성된다. 지정 경로는 새 파일이어야 하며 덮어쓰지 않는다. 터미널의 `ORE SCAN`, `PLAN DRILL`, `PLAN ROUTE`, `COST`, `BOOTSTRAP`, `BUILD`, `VERIFY`, `RESOURCE FLOW`, `COMPLETE`, `REPLAN` 순서를 관찰한다.

GUI에서는 Mono의 copper bootstrap, Poly의 drill 접근과 정상 construction progress, 경로 순서대로 완성되는 conveyor, drill에서 나온 copper item의 이동, core 유입, Mono의 lead 채굴, 완료 뒤 후속 Qwen 판단을 확인한다. 외형만으로 확신하기 어려운 항목은 CLIENT 관측과 live JSON 증거를 함께 기록한다.

## 범위

이 데모는 한 코어 주변 radius 48에서 첫 기능 경로 하나를 찾는다. 전투, unit production, 전력, 복수 생산선, 전역 최적화, multi-agent와 정식 episode 평가/reset harness는 포함하지 않는다.
