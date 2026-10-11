# AgentBridge 실제 API inventory

2026-09-30에 v1 API를 기록했고, 2026-10-01에 별도 주말 duel demo context 두 개를 추가했다. v1 `/state`·`/action`의 request/response 의미론은 유지한다. `contracts/agentbridge_api.json`은 현재 기계 판독 inventory와 Java source hash를 기록하며 OpenAPI validator는 아니다.

## Transport / thread / identity

Plugin은 `127.0.0.1:8765`에 bind한다. game port는6567. `HttpServer.setExecutor(null)`이며 상태 캡처/action parsing·조작은 `Core.app.post(...)`로 main thread에 예약한다. handler는 latch를 최대5초 기다린다. **timeout은 예약된 작업을 취소하지 않는다.** 불확실한 action을 무조건 재전송하면 안 된다.

기존 v1 관측은 `rules.defaultTeam` 기준이고 `/action`은 지정 unit 팀의 첫 Player를 찾는다. 이 두 endpoint에는 caller identity·팀 권한·fog·ownership session·action/task ID가 없다. localhost가 다중 agent 권한 격리를 의미하지 않는다.

등록 endpoint는 기존 `/state`, `/action`과 duel demo 전용 `/duel/state`, `/duel/action`, `/duel/control`이다. Java HTTP context가 prefix match하므로 접미 path도 handler로 갈 수 있지만 지원 API로 간주하지 않는다. `/units`, `/buildings`, `/tasks/{task_id}`는 미구현이다.

## GET /state

query 없음 또는 두 방식 중 하나:

| query | 조건 |
|---|---|
| tileX/tileY/radius | x/y는 함께, 음이 아닌 integer. radius1..6, 기본2. radius만도 가능 |
| view | logistics-plan 또는 logistics-status. 좌표/radius와 혼합 불가 |

중복/unknown query와 잘못된 형식은400. map 밖 좌표는 캡처 중 실패하므로200 error가 될 수 있다. active/waiting/capture error/timeout은 모두HTTP200이다. 다른 method는405/빈 body. code만으로 정상 관측 판정 금지.

| response | schema |
|---|---|
| waiting | `{status:"waiting", message:string}` |
| error/timeout | `{error:string}` |
| active | `wave/tick:int,team:string,resources:{copper:int,lead:int},cores:Core[],units:Unit[],demo:Demo,logistics?:Logistics` |
| Core | `x/y:tileInt,health/maxHealth:number` |
| Unit | `id:int,type:string,x/y:worldNumber,health:number,activity:Activity` |
| Activity | `commandable:bool,command:string,canBuild:bool,buildRange:number,mineResource?:string,mineResources:string[],mining:bool,item:string,itemAmount:int,planCount:int,plans:Plan[]` |
| Plan | `tileX/tileY:int,block:string,rotation:int,breaking:bool,progress:number`; 최대8개. planCount는 전체 queue |
| Demo | `worldId:string,commandReady:bool,infiniteResources:bool,instantBuild:bool,conveyorCopperCost:int,ores:{copper:bool,lead:bool},area:Area` |
| Area | core가 있으면 `tileX/tileY/radius:int`, 항상 `tiles:Tile[]`. 기본 중심 core 왼쪽38/up7(map 제한) |
| Tile | `id:"x:y",tileX/tileY:int,block/team:string,rotation:int,constructing?:string,progress?:number,buildRotations:int[]` |

Demo는 최대169타일. 빈 타일만 conveyor `Build.validPlace` rotation을 제공한다. ores와 mineResources는 **전역 indexer**를 사용하며 현재 unit 시야가 아니다.

## Logistics view

active response에 logistics 추가. core가 없으면 `{}`. 양쪽 view 모두 core 중심radius48 건물을 읽는다. **status도 remote 생산/건물/item을 제공하므로 partial observation이 아니다.**

| 필드 | schema |
|---|---|
| bounds | minX/maxX/minY/maxY:int |
| core | tileX/tileY/size/copper/receivedCopper:int, footprint:[[x,y],...] |
| content.drill | name:string,size:int,requirements:{item:cost},tier:int,drillTime:number,copperHardness:int |
| content.conveyor | name:string,size:int,requirements:{item:cost} |
| buildings[] | tileX/tileY/size/rotation/copper:int, block/team:string |
| 건설 중 추가 | constructing:string,progress:number |
| drill 추가 | dominantItem:string,dominantTiles:int,progress/warmup/lastDrillSpeed:number |
| conveyor 추가 | itemCount:int |
| oreTiles (plan만) | [[x,y],...], copper drop |
| drillCandidates (plan만) | {tileX,tileY,oreItem,oreTiles,footprint}[], valid placement + copper dominant |
| conveyorCells (plan만) | [[x,y,rotationMask],...], 유효 rotation mask가0 아닌 cell |

receivedCopper는 `Vars.state.stats.coreItemCount`이며 team별 item 출처 추적으로 가정하지 않는다. buildings에는 fog/team filter가 없다. raw `/state`에는 map name·네 자원 전체·build speed·normalized unitCounts·fixture형 core가 모두 있지 않다. `BenchmarkSpec.verify_initial_state()`는 normalized mock/fixture snapshot 검사이며 raw API validator가 아니다.

## POST /action

공통 request는 `action:string,unitId:int`.

| action | 추가 필수 필드 | 정상 실행 |
|---|---|---|
| move | x/y:float world coordinates | InputHandler.commandUnits |
| mine | resource:string | mine command+item stance. 이름 copper/lead/titanium/thorium 인식; 실제 unit tier/ore 검사 |
| build | block:string,tileX/tileY:int,rotation:int(0..3) | content/placement 검사, rebuild command, 정상 BuildPlan queue |

성공 response는 `success:true`와 action/unitId/요청별 해당 필드, HTTP200이다. 거절/예외/timeout은 `success:false,error:string,action?:string`, HTTP400. method 위반은405 `{error:"Method not allowed"}`. fallback error에는 success가 없을 수 있다. wait는 Python 내부 동작이다. 서버 build whitelist는 conveyor/drill로 제한되지 않고 content와 placement 조건을 검사한다. 재료 확보·목표 도달·완공을 응답이 보증하지 않는다.

현재 parser는 key/colon/quote/숫자 문자열 추출 방식이다. duplicate/extra key·malformed JSON을 엄격히 거절한다고 주장하지 않는다. body 크기 제한, finite float/좌표 범위, epoch/idempotency 계약도 없다. 이번에는 behavior hardening 없이 문서를 정합화했다.

## Duel demo extension (isolated from v1)

`GET /duel/state`는 `DUEL_DEMO_OMNISCIENT_V0` 계약으로 동일 tick에서 sharded/crux의 resource(copper/lead), core, live unit 목록을 대칭적으로 제공한다. `worldId`, `tick`, `paused`, `gameOver`도 포함한다. `commandable`은 `CommandAI` 여부이며 죽거나 제거된 unit은 roster에서 빠진다. 이것은 **완전 관측 demo**이며 인간 시야/fog 또는 연구용 v2 public observation이 아니다.

`POST /duel/action`은 `team`, `action`, `unitIds`와 move의 `x/y` 또는 attack의 `targetUnitId`를 받는다. 서버는 모든 대상 unit이 live·commandable·요청 team 소속인지 한 번에 검증하고, `InputHandler.commandUnits` 정상 명령을 호출한다. 상대 팀 unit ID가 섞이면 전체 batch를 거절한다. 이 endpoint의 `team`은 HTTP caller identity가 아니므로 Java만으로 agent 인증을 제공하지 않는다. Python `DuelCoordinator`가 Agent A/B와 팀을 고정하고 매 관측마다 roster를 갱신한 뒤 payload를 검증한다. controlled localhost demo 경계다. 응답의 `accepted=true`는 명령 접수이며 이동 완료나 공격 결과를 의미하지 않는다.

`POST /duel/control`은 `worldId`와 boolean `paused`로 현재 월드의 라운드 시간을 제어한다. 요청 월드가 다르거나 게임이 없으면 400이고, 적용된 pause 상태와 tick을 반환한다. localhost 데모 runner 전용이며 클라이언트가 보는 시간도 멈춘다.

주말 한 명령 시연의 `production.factory.supply`는 공장 옆 팀 소유 `vault`와 `unloader`가 정상 연결된 경우에만 `routeReady=true`와 저장고의 실리콘·납 재고를 노출한다. `produce`는 공장 자체 재고 또는 그 유한 저장고 재고가 recipe를 충족해야 설정 가능하다. 설정 후 실제 아이템 이동·소비·유닛 생성은 게임 틱의 unloader와 `UnitFactory`가 수행하며, HTTP 수락은 생산 완료가 아니다. 이는 `DUEL_DEMO_OMNISCIENT_V0`의 통제된 데모 관측이지 연구용 public observation이 아니다.

세 endpoint 모두 게임 접근을 `Core.app.post`로 실행하고 5초 후 timeout을 반환한다. timeout은 명령 취소를 뜻하지 않는다. 이 확장은 기존 logistics v1 및 Memory Contract v2 endpoint/runner 의미론을 변경하지 않는다.

## Completion

HTTP는 command acceptance. Task 객체와 completion은 Python 내부다. block/team/rotation과 실제 완성 타일, mining activity/자원 변화, topology/flow 등 별도 관측 증거가 필요하다. task_id나 `/tasks` polling은 없다. v2 public observation은 raw API의 별칭이 아니라 trusted adapter가 향후 만드는 별도 계약이다.
