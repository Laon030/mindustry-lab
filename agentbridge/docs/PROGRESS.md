# Project checkpoint

Updated: 2026-10-11 (Asia/Seoul)

## 2026-10-11 lab 이전 — 게임/AI 저장소 분리

- 현재 개발 위치는 `Laon030/mindustry-lab:feature/agentbridge-handoff`의 `agentbridge/`다. 개인 게임 포크의 `f11b8ac480`를 보존하고 Git 추적 소스만 옮겼다. 기존 팀 implementation과 게임 submodule은 독립 유지한다.
- 현재 실행·clone·검토 안내는 [lab 인계 문서](../../docs/AGENTBRIDGE_HANDOFF.md)를 따른다. 이 단계는 폴더·문서·Git 연결 변경이며 Java/Python 행동과 Qwen/OpenCode 연동은 변경하지 않는다.
- 이번 이전의 새 검증 결과는 lab 루트 [진행 기록](../../docs/PROGRESS.md)에 남긴다. 아래 게임 포크 인계 기록은 이전 단계의 증거다.

## 2026-10-11 SourceTree와 개인 포크 작업 연결 완료

- **VERIFIED — 로컬 설정:** 공식 Atlassian 배포의 SourceTree 4.2.19를 설치했고 checksum·개발자 서명·macOS 공증 검사를 통과했다. 앱 실행과 `browser.plist`의 BAR/Mindustry 두 클론 bookmark 경로를 확인했다. Bitbucket 저장소 연결은 이 GitHub 작업에 필요하지 않다.
- 처음 single-branch clone의 `origin` fetch 범위가 `develop`만 포함해 업로드한 feature branch를 SourceTree가 원격 추적할 수 없었다. `feature/agentbridge-handoff`를 fetch 범위에 추가하고, 같은 이름의 `origin` branch를 tracking하도록 설정했다. 변경 전 개인 remote SHA를 확인했고 연결 후 local/remote **0 ahead / 0 behind**를 확인했다.
- 두 클론에 local `remote.pushDefault=origin`, `push.default=simple`을 설정했다. `upstream`과 `canonical` push URL은 계속 `DISABLED`다. 이 단계는 Git 연결/문서 정리이며 source/runtime/API 변경은 없다. 앞선 121개 Python 테스트와 Java 17 빌드 결과를 유지하며 이번 단계에서 새 게임 검증을 수행하지 않았다.
- 작업 방식은 팀 정보를 fetch → 별도 개인 feature branch에서 구현/검증 → checkpoint commit → 개인 origin push → 상호 검토 순서다. 자동 팀 merge·팀 PR·DM 발송은 이번 범위 밖이다. 현재 demo GUI/native Core 승패 및 연구 live v2의 미검증 상태는 그대로다.

## 2026-10-11 개인 Mindustry 포크의 독립 AgentBridge 인계

- **범위/출처:** 사용자가 개인 포크에만 업로드하도록 허가했다. 팀 `develop=e2f588543904bd327a60bd1f8806f085e1dba1d2`에서 `feature/agentbridge-handoff`를 만들고, 원본 `Laon030/capstone-project=06f6f7fbd5f788f8914a92b80121eaaa35d5b8f3`의 Git 추적 파일 102개를 `integrations/mindustry-llm-agent/agentbridge`로 복사했다. 기존 원본 checkout과 연구 branch는 보존한다.
- **격리:** 새로운 패키지 밖의 engine/Gradle/settings/CI 및 기찬님 integration 파일은 수정하지 않는다. 상위 build에 자동 등록하지 않는다. 개인 `origin=Laon030/mindustry`만 push 대상이며 로컬 `upstream`과 `canonical`의 push URL은 `DISABLED`로 설정했다. 팀 PR과 develop push는 이번 범위 밖이다.
- **IMPLEMENTED — 실행 경로 준비:** demo launcher에 `JAVA_HOME`과 `AGENTBRIDGE_SERVER_JAR` 환경변수 override를 추가했다. 미지정 시 기존 경로를 유지한다. 정상 게임 실행·기존 Qwen 경로·duel 모델·Memory Contract는 변경하지 않았다. README와 [FORK_HANDOFF.md](FORK_HANDOFF.md)에 하위 폴더 기준 clone/test/build, 최초 dependency 준비, 포트 충돌, fixture·검증 한계와 nested CI 템플릿의 비활성 상태를 설명했다.
- **VERIFIED_TEST — 이번 세션:** 독립 클론의 패키지 위치에서 CPython 3.13.5 전체 단위 테스트 **121/121 OK**. 환경/metadata 확인, compileall과 경로 override·missing-path preflight smoke도 통과했다. 오류 주입 테스트의 출력은 실제 서버 장애가 아니다. 게임/모델/server는 시작하지 않았다. 원본 Java 파일의 기존 trailing whitespace는 API source hash와 원본 byte 보존을 위해 유지했고, 그 항목만 제외한 staged whitespace 검사를 통과했다.
- **VERIFIED_BUILD — 이번 세션:** Java 17 Gradle offline `jar` 빌드 성공. 최종 폴더 `/Users/andrew/capstone/mindustry-laon`에서도 재빌드 성공; JAR SHA-256 `a5e99016d802f0aef5897096e9c9f06e7bfd3a078d253ebe617dde720da53912`. 빌드 성공은 실제 게임 재검증이 아니다.
- **제외/한계:** .git 이력, 원본 save/logs, runtime/build 파일, 서버 JAR, 모델과 인증정보는 snapshot에서 제외했다. 기본 HTTP는 localhost 전용이다. 최신 GUI, native Core 승패, v2 live 통합과 scratchpad 성능 효과는 이번에도 미검증이다.
- 먼저 이미 있는 개인 BAR 포크 `Laon030/Beyond-All-Reason`를 `/Users/andrew/capstone/Beyond-All-Reason`에 소스 작업용 sparse clone으로 준비한 뒤 이 인계를 재개했다. BAR 게임 실행용 대용량 자산은 내려받지 않았고 소스 변경/push는 수행하지 않았다.
- **VERIFIED_REMOTE:** 최초 패키지 commit `daa1e1fd95e1ad9cddbb5734fc236ea42189f31e`를 개인 `origin`의 `feature/agentbridge-handoff`에 push하고 `git ls-remote`로 확인했다. 개인 `develop=e2f5885`는 그대로이며, 기준 대비 103개 추가 파일 모두 새 패키지 안에 있다. 이 후속 기록도 같은 개인 작업 브랜치에만 반영한다. 팀 PR은 생성하지 않았다.
- 다음 단계: 기찬님과 각 runtime을 독립 실행·교차 검토한 뒤 통합 계약을 협의한다.

## 2026-10-08 개인 GitHub backup 및 상호 검토 준비

- **VERIFIED_REMOTE — 개인 backup:** `Mindustry` 채팅과 Git 상태·이력·remote를 확인했다. 개인 계정은 `Laon030`, `0803leesj`는 이메일 앞부분이다. 사용자가 기존 비공개 `Laon030/capstone-project`로 push를 명시적으로 허가했다. 연구 `stage4-agent=37617e0803c521c2d9a33a428d0f6270891fe4d0`와 별도 demo `codex/weekend-duel-demo=837363146e6b2a3ea7fb030edf12d11e1f708e52`를 force 없이 push했고, `git ls-remote origin`으로 두 remote SHA를 확인했다. 이 후속 문서 기록 전의 backup SHA이며, `master`와 다른 두 worktree는 보존했다.
- **VERIFIED_TEST — 이번 세션:** `/opt/anaconda3/bin/python3.13 -m unittest discover -s tests -q` **121/121 OK**, `git diff --check` 통과. 이번 작업은 문서 정리이며 새 Java build·실제 게임·모델·GUI 재검증은 수행하지 않았다. 10/07 headless 결과는 과거 증거로 유지한다.
- **VERIFIED_READ — 협업 상대:** 기찬님 `qrc4723/mindustry:feature/mindustry-llm-agent`의 head `c4b068829cf8c96f3a8f7c20e24748e85763fe07` 및 팀의 열린 PR #1을 확인했다. 팀 `develop` 병합으로 취급하지 않는다. API·실시간 판단·RTS 건설/훈련 규칙이 이 저장소와 달라 무작정 병합하지 않는다. 기찬님 integration의 실제 실행은 이번 세션에서 검증하지 않았다.
- [TEAM_REVIEW.md](TEAM_REVIEW.md)에 branch별 검토 범위, clone/test 절차, 다른 머신의 절대 경로 제약, 팀 fork/feature/PR 규칙, 공통 계약·작은 역할 분담 제안과 미발송 DM 초안을 정리했다. 현재 개인 저장소는 비공개이며 `qrc4723` 접근 권한은 없으므로 링크만으로 검토할 수 없다. 역할·실험 규칙·통합 방식은 아직 팀 합의가 아니다.
- **검토 준비:** 개인 저장소에 [draft PR #1](https://github.com/Laon030/capstone-project/pull/1)을 생성했다(`codex/weekend-duel-demo` → `stage4-agent`). 비교·댓글용 검토 대상으로 준비했으며 병합하지 않았다. 비공개 저장소의 collaborator 초대는 쓰기 권한까지 포함하는 범위를 사용자에게 확인 중이며, 현재 초대·DM 발송은 수행하지 않았다.
- 다음 단계: 저장소 접근 방식 확정, 기찬님과 실행 규칙·API/완료·승패 기준 협의 후 각자 작은 feature를 구현·교차 검토한다. 기존 연구 live v2, 최신 demo GUI, native Core 승패와 upgrade/capture의 미검증 상태는 그대로다.

## 2026-10-07 Duel Gate 6 후속 안정화 — 관전 좌표 guard와 종료 판정

- **현재 checkpoint/범위:** `fe5c3c0`의 clean working tree에서 이어갔다. 이전 duel 서버·agent는 종료되어 있었고 localhost Ollama만 실행 중이었다. 기존 logistics v1, Memory Contract v2, 연구 runner와 Java 게임 소스는 변경하지 않았다. 이번 범위는 demo 안정화이며 Gate 7 upgrade와 Gate 8 capture는 **NOT_STARTED**다.
- **IMPLEMENTED:** `agent/duel/auto_match.py`의 `DUEL_PAUSED_DECISION_GUARD_V1`은 모델 관측/명령 대상에 쓰이지 않는 **비명령형 alpha의 x/y만** 비교에서 제외한다. 나머지 유닛·건물·자원·체력·명령 가능 여부·tick·world 변경은 계속 차단한다. 무시한 좌표 경로를 별도 로그로 남긴다. 실제 접수되고 정상 실행된 공격만 fighter 결과의 근거가 되며, 오류가 있는 실행은 `INFRA_FAILURE` 또는 `TIMEOUT`으로 종료한다. `observedOutcome`은 실제로 얻은 전장 판정과 실행 실패를 분리하고, 최종 관측을 못 읽으면 판정·tick·scoreboard를 미확인으로 남긴다. `scripts/duel_demo.py`도 같은 exit-code 규칙을 사용한다.
- **VERIFIED_TEST:** 기존 108개를 유지하고 13개 테스트를 추가해 `/opt/anaconda3/bin/python3.13 -m unittest discover -s tests -q` **121/121 OK**. 관전 좌표 허용 외에 11종 관련 상태 변화 차단, 부분 명령 실패, provider/command timeout, 연결 소실, pause 실패, world 교체, 오류와 동시에 관측된 Core 승리의 과대 판정을 검사했다. Java 17 offline `jar`는 **BUILD SUCCESSFUL / UP-TO-DATE**, JAR SHA-256은 기존 `a5e99016d802f0aef5897096e9c9f06e7bfd3a078d253ebe617dde720da53912`다. compileall/diff check도 통과했다. 오류 주입 단위 테스트는 실제 서버 장애 발생 증거로 해석하지 않는다.
- **VERIFIED_HEADLESS — 새 full match:** `/opt/anaconda3/bin/python3.13 scripts/duel_demo.py --headless`가 world `8577f5b6-4716-4392-b270-2c50764b987e`에서 네 라운드 모두 첫 시도로 `MINE/MINE → PRODUCE/BUILD → BUILD/PRODUCE → ATTACK_0/ATTACK_0`을 실행했다. 양측 copper 0→125(건설 지출 후), Duo 2개 완성, 유한 silicon/lead 저장고 10/10→0/0, factory Dagger 234/240의 실제 출현·피해·사망을 확인했다. tick 4845에 `DRAW_FIGHTERS`, `failure=null`, `finalObservationVerified=true`, `gameOver=false`, exit 0. 원본 증거: `build/duel-runs/one-command-20261007-172057-a47a2c/{build.log,match.jsonl,server.log,initial-state.json,final-state.json,result.json}`.
- **VERIFIED_HEADLESS — guard 양성/음성 검사:** `scripts/duel_guard_probe.py`는 실제 두 모델의 선택을 30초 보류하여 paused 좌표 주입 창을 만든다. 최종 수동적 alpha fixture의 raw snapshot은 x/y 외 모든 필드가 같았고, 첫 시도에서 두 `MINE` 명령을 접수했다. alpha가 비명령형·150 HP로 유지되고 양 Core 1100 HP, copper 40/40을 확인했다. 의도적인 1-round 제한은 `TIMEOUT / round_limit`, exit 2로 끝났다. 별도 commandable-alpha 좌표 변경은 `stale_snapshot → INFRA_FAILURE`, 명령 없이 exit 2로 차단됐다. 증거: `build/duel-runs/observer-guard-20261007-172346-13a61d/{server.log,held-match.jsonl,passive-match.jsonl,passive-initial-state.json,passive-drift-state.json,passive-final-state.json}`. 초기 진단의 늦은 주입과 공격하는 FlyingAI fixture는 성공 증거로 사용하지 않으며 [DUEL_DEMO.md](DUEL_DEMO.md)에 한계를 기록했다.
- **NOT_VERIFIED / 다음 단계:** 이번 세션은 GUI 없이 진행했다. 실제 CLIENT에서 새 guard의 무재시도 동작, 최신 end-to-end GUI 장면별 확인, native Core 승패, 실리콘 제련/납 채굴은 미검증이다. 현재 자재 공급은 여전히 경기 전 유한 저장고→경기 중 정상 unloader→factory다. 다음은 같은 fixture의 인간 GUI 확인이며, Gate 7은 그 뒤 별도 vanilla upgrade proof로 진행한다. 상세 변경 파일·실행 절차·hash·잔여 confound는 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.

## 2026-10-04 One-command CLIENT join and server-lifetime repair

- **IMPLEMENTED + VERIFIED_TEST:** `scripts/duel_demo.py` now accepts only the CLIENT's additional player `alpha` unit in the post-join fixture check while still requiring the original Mono/Poly, two Cores, empty Duo/factory, and untouched finite supply. The launcher records `post-client-state.json`. A closed launcher input channel now keeps the server alive for inspection instead of raising `EOFError`. Four focused regression tests were added in `tests/test_duel_demo_launcher.py`; `/opt/anaconda3/bin/python3.13 -m unittest discover -s tests -q` passed **108/108**, compileall and `git diff --check` passed.
- **VERIFIED_HEADLESS / CLIENT connected:** `/opt/anaconda3/bin/python3.13 scripts/duel_demo.py --skip-build` started the v159.7 Java 17 server; `server.log` recorded the CLIENT connection and the joined state showed only an additional Crux `alpha` at tick 0. Without manual game commands, DeepSeek/GLM selected `MINE/MINE → PRODUCE/BUILD → BUILD/PRODUCE → ATTACK_0/ATTACK_0`. The live state recorded both Duo complete, finite silicon/lead reserves 10/10→0/0, factory Daggers 240/246, then normal damage and both `DEMO_DESTROY` events. Result: `DRAW_FIGHTERS`, `gameOver=false`, full-health Cores. Evidence: `build/duel-runs/one-command-20261004-100333-048f47/{match.jsonl,server.log,initial-state.json,post-client-state.json,final-state.json,result.json}`.
- **PARTIALLY_VERIFIED:** This run exposed a separate launcher lifetime error after the match: the noninteractive tool input closed, `input()` raised `EOFError`, and `finally` shut down the server before extended CLIENT inspection. The match result and logs were saved before that error. The input-channel fix passed a regression test and the next live run confirmed server persistence. CLIENT connection by itself does not establish GUI-visible mining, supply transfer, construction, production, or combat.
- **VERIFIED_HEADLESS — repaired live replay:** A fresh `/opt/anaconda3/bin/python3.13 scripts/duel_demo.py --skip-build` run in `build/duel-runs/one-command-20261004-101217-0d1cfa/` completed four automatic rounds in world `0ce030b7-8743-4d90-bf46-682cb197b795`: `MINE/MINE → PRODUCE/BUILD → BUILD/PRODUCE → ATTACK_0/ATTACK_0`, with safe retries for spectator `alpha` coordinate drift. Both Duo sites completed, finite silicon/lead reserves went 10/10→0/0, factory Daggers 236/242 appeared, and normal damage plus both destroy events produced `DRAW_FIGHTERS` at tick 4859 (`gameOver=false`). After the result, `6567` remained LISTEN and `/duel/state` still returned the same paused world; the server-lifetime fix is therefore **VERIFIED_HEADLESS**. The user's scene-specific GUI report is pending, so these game actions are **NOT_VERIFIED_GUI** in this run.

## 2026-10-04 Weekend duel demo — bounded two-model autonomous match

- **IMPLEMENTED + VERIFIED_TEST / 한 명령 시연:** `scripts/duel_demo.py`가 Java 17 JAR 빌드, 독립 v159.7 서버, 동일한 두 팀 fixture, CLIENT 접속 대기, 두 로컬 모델 경기와 결과 로그를 한 명령으로 관리한다. 새 공급 fixture는 공장 재고 0/0·유한 저장고 silicon/lead 10/10으로 시작하며, 모델이 `PRODUCE`를 고른 뒤 정상 unloader가 경기 중 아이템을 옮긴다. `stale_snapshot`은 원인 필드 경로를 기록하고 명령 없이 최대 두 번 새 판단을 시도한다. 전체 Python **104/104**와 Java 17 offline JAR 빌드 통과; 자세한 변경 파일·명령·로그는 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.
- **VERIFIED_HEADLESS:** 실제 `python3.13 scripts/duel_demo.py --headless --skip-build` 한 명령이 새 world `b620c921-3003-47bb-9956-c55b7444841b`에서 A/B `MINE/MINE→PRODUCE/BUILD→BUILD/PRODUCE→ATTACK_0/ATTACK_0`을 자동 실행했다. 양쪽 저장고 silicon/lead 10/10→0/0, 두 공장 Dagger 234/240가 실제 live roster에 출현, Duo 2개 완성, 정상 피해·양측 사망, `DRAW_FIGHTERS`/`gameOver=false`를 확인했다. 최초 출구가 unloader에 막힌 실패 시도는 정상 출구를 서쪽으로 돌려 해결했으며 성공으로 세지 않았다. 이 새 공급 버전의 CLIENT 화면과 원료 자율 채굴·제련은 **NOT_VERIFIED**.
- **PARTIALLY_VERIFIED — 기본 GUI 명령 preflight:** `scripts/duel_demo.py --client-timeout 5`는 Java build→새 paused fixture→CLIENT 접속 대기까지 실행하고, 의도적으로 짧은 timeout 뒤 agent를 시작하지 않고 소유 서버를 종료했다. 따라서 한 명령 GUI 준비와 안전 종료는 확인했지만 실제 CLIENT 접속 시 자동 시작 및 화면 장면은 **NOT_VERIFIED_GUI**다.
- **CLIENT 재시연 / PARTIALLY_VERIFIED:** 사용자가 재접속했고 `players=1`을 확인한 새 월드 `5eb78284-f753-4073-af41-e76b78768905`에서 같은 runner를 실행했다. 첫 프로세스는 두 라운드 `PRODUCE/MINE→MINE/BUILD` 뒤 세 번째 판단의 `stale_snapshot` 안전 검사에서 명령 없이 중단했다; 현재 상태를 재확인한 후 같은 paused 월드의 별도 프로세스로 `BUILD/PRODUCE→ATTACK_0/ATTACK_0`을 이어 최종 `DRAW_FIGHTERS`, `gameOver=false`를 얻었다. Dagger 587/638의 정상 공장 생성·피해·사망은 서버 이벤트로 **VERIFIED_HEADLESS**이고, 원인 미확정인 snapshot 변화와 프로세스 재시작 때문에 이 재시연을 무중단 단일 프로세스 성공으로 기록하지 않는다. CLIENT 화면의 장면별 사용자 확인은 아직 **NOT_VERIFIED_GUI**이며 로그·hash는 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.
- **CLIENT-connected replay, GUI 판정 대기:** 사용자가 v159.7 CLIENT 접속 완료를 알렸고 서버도 02:27:41 `andrew has connected`를 기록했다. 별도의 수동 mine/build/move 명령 없이 같은 `auto_match`를 새 paused world `46cf512d-41bd-46af-8fae-6c2d89c6da4c`에서 실행했다. 서버/agent는 4라운드 `PRODUCE/MINE→MINE/BUILD→BUILD/PRODUCE→ATTACK_0/ATTACK_0`, 실제 Dagger 513/524 생산·피해·양측 제거, 최종 `DRAW_FIGHTERS`/`gameOver=false`를 기록했다. **VERIFIED_HEADLESS**이며 CLIENT가 접속했다는 사실만으로 화면에서 각 동작을 봤다고 분류하지 않는다. 사용자의 장면별 시각 확인은 현재 **NOT_VERIFIED_GUI**. 원본 로그와 명령·해시는 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.
- **IMPLEMENTED + VERIFIED_TEST:** `agent/duel/auto_match.py`와 `unified.py`가 한 paused world의 동일 snapshot에서 DeepSeek Coder 6.7B(A)와 GLM-Edge 4B(B)를 병렬 호출하고, 모델이 고른 MINE/BUILD/PRODUCE/ATTACK/DEFEND/WAIT를 기존 정상 게임 명령으로 변환하며, 라운드마다 자동 pause/advance/re-observe한다. `/duel/control`은 localhost 및 main game thread에서 현재 world ID를 확인한다. provider 오류 시 자동 WAIT로 대체하지 않고 명령 없이 중단하도록 자체 검토 후 고쳤다. 기존 Qwen 경로와 research/logistics 코드는 유지했다. 전체 test/build 결과와 변경 파일은 [DUEL_DEMO.md](DUEL_DEMO.md)의 autonomous match 절에 있다.
- **VERIFIED_HEADLESS:** 새 대칭 two-core world `b5ecb988-e2d2-40b6-8418-e6a0d66b8b68`에서 단일 `-m duel.auto_match` 프로세스가 별도의 phase operator 호출 없이 네 번 판단했다: A `PRODUCE→MINE→BUILD→ATTACK_0`, B `MINE→BUILD→PRODUCE→ATTACK_0`. 두 Core 구리 0→105/145, 두 Duo 완료, `ground-factory`의 Sharded Dagger 439/Crux Dagger 450 생성, 피해와 양측 `UnitDestroyEvent`가 기록됐다. tick 4866에 양측 Dagger 0, Core HP 1100/1100, `gameOver=false`, **DRAW_FIGHTERS**다. 원본 JSONL·server event·최종 state 및 SHA-256은 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.
- **PARTIALLY_VERIFIED / NOT_VERIFIED:** 한 프로세스의 end-to-end headless phase 전환과 정상 게임 실행은 확인했으나, 인간 CLIENT에서 이 새 run을 보지 않았고 winner/native game-over는 없다. 모델에는 목표와 경제/전투별 좁은 선택지가 주어지며, 초기 Mono/Poly, factory/solar/silicon/lead는 pre-match fixture다. 따라서 일반 전략 능력, 완전한 자원 경제, scratchpad 효과, GUI 데모를 입증하지 않는다. 다음은 같은 fixture의 인간 GUI 확인이고, upgrade/capture는 아직 시작하지 않았다.

## 2026-10-03 Weekend duel demo — same-world chain and fighter result correction

- **VERIFIED_TEST:** `gate4_probe.check`의 fixture 승패가 Mono/Poly 생존자까지 세던 오류를 Dagger 전투 병력 기준으로 고쳤다. worker가 남은 양측 Dagger 전멸 사례 회귀 테스트를 추가해 전체 Python **97/97** 통과, `git diff --check` 성공. Java/게임 코드는 Gate 6 checkpoint `8266d82` 이후 변경하지 않았다.
- **VERIFIED_HEADLESS / PARTIALLY_VERIFIED:** 새 월드 `ea84ab65-6e6e-41ba-ae09-10e72bcc9e8f`에서 두 로컬 모델이 동일 snapshot별로 `MINE→BUILD→PRODUCE→ATTACK`을 각각 선택했다. 양 Core 구리 0→120 뒤 Duo 정상 건설로 85/85, pre-match factory 재고 silicon/lead 10/10→0/0, 실제 생성 Dagger 307/308, 정상 교전 뒤 양 Dagger 소멸을 확인했다. tick 10653의 fighter-force 판정은 **DRAW**, `gameOver=false`, 두 Core HP 1100이다. 각 phase는 같은 게임 월드에서 이어졌지만 operator가 pause/resume과 광부 정지를 조정하고 다음 provider 호출 시점을 선택했다. 원본 command, log path, SHA-256 및 자세한 경계는 [DUEL_DEMO.md](DUEL_DEMO.md)의 “Same-world” 절에 있다.
- **NOT_VERIFIED:** 무중단 자율 판단 루프, 모델 자체의 경제→생산→전투 전환 결정, 실제 winner/native game-over, 이 실행의 CLIENT GUI, 일괄 배치된 silicon/lead의 자율 확보, upgrade/capture. 다음 우선순위는 제한된 단일 cross-phase decision contract와 round controller의 실제 경기 검증이며, 그 다음 인간 GUI 확인이다.

## 2026-10-02 Weekend duel demo — Gate 6 vanilla Dagger production

- **IMPLEMENTED + VERIFIED_TEST:** 대칭 `/duel/state`에 factory 위치·상태·실제 recipe 재고·진행도·전력 상태를 넣었다. 팀/후보/비용을 검증한 좁은 `produce` 명령은 게임의 `InputHandler.tileConfig(..., UnitTypes.dagger)`로 실제 `ground-factory` 계획을 설정한다. DeepSeek-R1 1.5B와 GLM-Edge 1.5B가 동일 paused snapshot에서 각각 `PRODUCE`/`WAIT`를 고르는 probe와 팀 격리 테스트를 추가했다. Java 17 `./gradlew jar --offline` 성공, Python **96/96** 통과, compileall/diff check 성공. 테스트 JAR SHA-256 `73d47a43f9f6ab3cdb457061927531871f8118536651aaa9fcfc0963544882eb`.
- **VERIFIED_HEADLESS:** 새 v159.7 월드 `530d42e0-a3b2-4c85-9dd0-13cb580a7dba`에 양 팀 동일한 *경기 전 fixture*로 idle factory, 인접 solar panel, silicon 10/lead 10을 준비했다. 위조된 상대 factory 좌표는 HTTP 400으로 거절됐다. `PYTHONPATH=agent /opt/anaconda3/bin/python3.13 -m duel.gate6_probe round --log build/duel-runs/gate6-local.jsonl`에서 두 로컬 모델 모두 `PRODUCE`를 선택했고 각 팀 정상 factory 설정이 수락됐다. `pause off` 후 tick 680의 양쪽 progress는 679/900·power 1/1·Dagger 0/0이었다. 서버 `UnitCreateEvent`는 Sharded Dagger 225와 Crux Dagger 226을 각 factory에서 기록했고, tick 1280의 실제 stock은 양쪽 silicon/lead 0/0, live Dagger는 1/1이었다. 후속 `gate6_probe observe`는 tick 2203에서 두 Dagger 생존을 기록했다. 원본 `build/duel-runs/gate6-local.jsonl` SHA-256 `5899bbf76bce05dfb440a06ed7f83be6c7cbbc2287e97f748a6cd23da39ae11e`, `build/duel-runs/gate6-server.log` SHA-256 `059093becd4a34f1f5c4182e1fe0eb5880a0f79b01bdffaa034960f79f0c1d98` (Git ignored). 상세 command와 changed files는 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.
- **PARTIALLY_VERIFIED / NOT_VERIFIED:** 실제 아이템 소비·전력 사용·유닛 생성은 headless로 확인했다. 다만 silicon/lead와 발전/공장은 경기 전 fixture이고, Gate 5 채굴·건설에서 Gate 6 생산까지 이어지는 연속 autonomous episode는 아직 검증하지 않았다. 이 실행의 CLIENT 화면, 생산 이후 LLM 전투 전환, two-core native 승패, 업그레이드는 **NOT_VERIFIED**. 다음에는 같은 월드의 생산 유닛으로 모델 선택 전투를 확인하고, 이어서 연속 경기 루프를 검증한다.

## 2026-10-02 Weekend duel demo — Gate 5 two-team economy/build

- **IMPLEMENTED + VERIFIED_TEST:** 별도 `/duel/state`에 양 팀 동일 형태의 25-tile 구리 광맥·Core 상대 `duo` 후보·건물 상태를 넣고, `/duel/action`에 팀 검증을 거친 Mono 구리 채굴과 Poly 정상 `BuildPlan` 건설을 제한적으로 추가했다. Python coordinator는 소유권·정확한 후보·자원 비용을 검증하며 `MINE`/`BUILD`/`WAIT` 전략 선택은 실제 로컬 DeepSeek-R1 1.5B/GLM-Edge 1.5B의 출력에 남겼다. Java 17 offline JAR build 성공, Python **93/93** 통과, compileall/diff check 성공. 기존 `/action` logistics와 Memory Contract v2는 변경하지 않았다.
- **VERIFIED_HEADLESS:** v159.7 서버의 한 월드 `767c4a94-823d-46d0-9cfb-f807ff1eb36c`에서 두 Core, 동일 33×33 로컬 지형/구리 광맥 25개, 각 팀 Mono/Poly, Core 구리 0/0으로 시작했다. 두 로컬 모델이 같은 paused snapshot에서 각각 `MINE`을 선택했고 실제 Core 구리는 양쪽 모두 0→40→60으로 증가했다. 별도 후속 판단에서 GLM과 DeepSeek가 각각 `BUILD`를 선택한 후 Crux `(151,132)`와 Sharded `(151,52)`에 `duo`가 정상 완성됐고 두 Core 구리는 각각 60→25, Poly queue는 1→0이었다. `infiniteResources=false`, `instantBuild=false`, `waves=false`; in-match 즉시 블록 배치나 유닛 spawn 없음. `build/duel-runs/gate5-symmetric-local.jsonl` SHA-256 `2d1bcb279d137b0213c47a0cc8bcce38b6800378d85580e912f92d58e187d301`; `gate5-symmetric-server.log` SHA-256 `b6c608b548413592f47feb55fce8959bf4b7b77b1d2d01ada7b8ebc86580a19b` (Git ignored). 정확한 실행 절차와 실패한 초기 시도는 [DUEL_DEMO.md](DUEL_DEMO.md)에 있다.
- **PARTIALLY_VERIFIED:** 같은 월드의 모델 선택→자원→건설은 이어졌지만, 모델 1.5B가 처음 비용 충족 후에도 반복 `MINE`을 선택하여 짧은 예시 프롬프트가 필요했다. 각 round는 병렬 추론·동일 snapshot 검증이지만 전체 episode는 test operator가 pause/resume·채굴 중단을 조정했다. 지속 autonomous match loop와 두 모델의 전략 품질은 입증되지 않았다.
- **NOT_VERIFIED:** 이 Gate의 CLIENT 시각 확인, factory를 통한 유닛 생산, duo ammo/방어 효용, native core 파괴 승패, end-to-end GUI 경기, 업그레이드. 다음 Gate는 v159.7 실제 factory recipe/power/item 소비를 따르는 Gate 6이다.

## 2026-10-02 Weekend duel demo — Gate 3/4 small local model proof

- 사용자가 DeepSeek와 GLM을 별도 팀 모델로 쓰고 로컬 모델 크기로 낮추도록 요청했다. OpenCode에 등록된 [DeepSeek-V4-Flash](https://ollama.com/library/deepseek-v4-flash)/[GLM-5.3-Flash](https://ollama.com/library/glm-5.3-flash)는 각각 전체 약 304B/321B라 로컬 크기 요구에 맞지 않는다. 16GB RAM 호스트의 localhost Ollama에 실제 로컬 [DeepSeek-R1 1.5B](https://ollama.com/library/deepseek-r1) (ID `e0979632db5a`, 1.1GB)와 공식 [Z.ai GLM-Edge 1.5B GGUF](https://huggingface.co/zai-org/glm-edge-1.5b-chat-gguf) (ID `ecab014058c4`, 980MB)를 설치했다. `ollama list`와 `lsof`에서 두 모델과 127.0.0.1:11434 listener를 확인했다. API 키는 필요하지 않으며 게임 관측은 localhost Ollama에만 전달했다.
- **IMPLEMENTED + VERIFIED_TEST:** 기존 Qwen/OpenCode 경로를 유지하면서 `DuelOllamaProvider`, LLM이 적 Dagger slot을 고르는 strict JSON 계약, 같은 paused snapshot에서 두 모델을 병렬 호출한 뒤 관측이 그대로일 때만 양 팀 명령을 내리는 Gate 4 probe를 추가했다. 기존 Gate 3 probe도 `--provider ollama`를 지원한다. 소형 DeepSeek가 한 차례 빈 JSON, 한 차례 누락된 필드를 반환했고 반대 팀 관측에서는 공격 slot을 null로 반환했다. 이후 관측에 따른 합법 출력 schema를 적용했다. Python이 임의 target을 고르지 않는다. 이전부터 손상된 HP가 새 전투 증거가 되지 않도록 사전 HP baseline도 추가했다. 전체 unittest **89/89 통과**, `compileall -q agent/duel`과 `git diff --check` 성공.
- **VERIFIED_HEADLESS — Gate 3:** `PYTHONPATH=agent /opt/anaconda3/bin/python3.13 -m duel.gate3_probe prepare --provider ollama --model deepseek-r1:1.5b --log build/duel-runs/gate3-local.jsonl`에서 실제 DeepSeek 모델 ID, 224 prompt/462 output tokens, `ATTACK`/slot0, 양 팀 정상 attack 명령 접수를 기록했다. `pause off` 후 같은 probe의 `check`가 tick 0→2211, Sharded roster `[263,264]`, Crux roster `[]`, fixture winner Sharded를 관측했다. 원본 최종 `/duel/state`에는 A unit 263 HP 42/150, unit 264 HP 150/150, Crux `units=[]`, `gameOver=false`. 로그 `gate3-local.jsonl` SHA-256 `26f7b5f1867684334ed1d245a9ec04c3126f7ff2ba08d881e6994bd2002e954a`; 최종 상태 `gate3-final-state.json` SHA-256 `932136d16665f1c6ad3dc23fea5be41da640cf0fc1749d1aa75f7d693d7e1f3d`.
- **VERIFIED_HEADLESS — Gate 4:** 동일 서버에서 `stop`/`host Islands sandbox`로 새 world를 열고 paused fixture에 Sharded Dagger 2기(306,307)와 Crux Dagger 1기(308)를 150 HP로 생성했다. 초기 상태 `build/duel-runs/gate4-initial-state.json`에는 worldId `0995ab21-d6e0-4b8d-8610-204983eb4346`, tick 1073, 2-vs-1 roster가 있다. `PYTHONPATH=agent /opt/anaconda3/bin/python3.13 -m duel.gate4_probe prepare --log build/duel-runs/gate4-local.jsonl`에서 두 **서로 다른 실제 모델**이 같은 paused 관측을 병렬 호출받아 각자 `ATTACK`/slot0을 반환했고, A→unit308, B→unit306 명령이 정상 접수됐다. `pause off` 후 `check`는 tick 3390, A `[306,307]`(HP 42/150, 150/150), B `[]`, fixture winner Sharded를 기록했다. 서버 콘솔도 Crux unit 308 `isAdded=false`, HP -3을 확인했다. `gate4-local.jsonl` SHA-256 `807e83d3a69146aabc77c61fcdeae5a6fd38824ae31abc23c0ae2fd363cc6893`; 초기/최종 원본 상태 SHA-256은 [DUEL_DEMO.md](DUEL_DEMO.md)에 기록했다.
- **NOT_VERIFIED:** 이 2-vs-1 built-in Islands fixture에는 Crux Core가 없고 엔진 `gameOver=false`다. 이번 Gate 3/4 실행의 GUI 확인, 균형 잡힌 two-core PvP 승패, 여러 판단 라운드의 지속 경기, 경제·건설·생산은 확인하지 않았다. 기존 Gate 1의 HUMAN GUI 유닛 전투 확인은 유효하지만 이번 두 모델 실행의 GUI 증거로 전용하지 않는다. 다음 단계는 대칭 two-core fixture와 경제/건설 Gate 5이며 아직 구현하지 않았다.

## 2026-10-01 Weekend duel demo — Gate 3 preflight, cloud call blocked

- **IMPLEMENTED + VERIFIED_TEST:** 기존 `ollama-cloud/qwen3.5:397b` 후보용 tool-free Duel provider, strict `ATTACK/DEFEND/WAIT` JSON, 기계적 intent 실행과 scripted B probe를 `agent/duel/`에 추가했다. raw unit ID·좌표·자원·worldId 없이 병력 수·체력 비율·Core 존재 여부만 모델에 전달하도록 제한하고 누출 방지 테스트를 추가했다. 전체 unittest **82/82 통과**, compileall 성공. 게임/전투 Java 코드는 변경하지 않았다.
- **NOT_VERIFIED — live LLM:** `opencode models ollama-cloud`는 Qwen ID 등을 목록에 표시했으나 실제 inference는 수행되지 않았다. `gate3_probe prepare` 실행은 자동 승인 검토에서 **프로세스 생성 전 두 차례 거절**됐다. 첫 거절은 로컬 게임 상태의 외부 전송, 요약 축소 후 두 번째 거절은 집계 게임 상태도 외부 cloud에 보낼 구체적 승인 부재를 이유로 들었다. 우회하지 않았다. 현재 Gate 3 fixture는 tick0/paused/Dagger 3기 full HP이고 명령 미발행이다. 사용자에게 표시된 집계 payload의 cloud 전송 승인을 받아야 실제 Gate 3을 검증할 수 있다. 자세한 경계는 [DUEL_DEMO.md](DUEL_DEMO.md).

## 2026-10-01 Weekend duel demo — Gate 2 coordinator/ownership

- Gate 1 GUI/headless 유닛 전투 증거를 `6f3b827`에 checkpoint했다. 이어서 기존 v1 API를 유지한 별도 `/duel/state`, `/duel/action` 및 `agent/duel/`의 두 독립 `AgentSession`/`DuelCoordinator`를 구현했다. 공통 omniscient snapshot에서 대칭 own/enemy view를 만들고 매 관측마다 live commandable unit roster를 교체한다.
- **VERIFIED_TEST:** 새 unit/contract tests에서 A/B 세션 분리, 서로 다른 model ID 조건, 양쪽 상대 unit ID 거절, 팀 위조 거절, dead/despawned roster 제거, 중복 ID 거절을 검사했다. Java 17 `./gradlew jar --offline` 빌드와 Python compileall이 성공했고 전체 unittest **76/76 통과**.
- **VERIFIED_HEADLESS:** 새 JAR을 올린 실제 v159.7 서버의 `/duel/state`가 Sharded/Crux roster를 같은 worldId/tick으로 반환했다. `gate2_probe prepare`가 상대 ID 명령 2건을 Python에서 거절하고 양쪽 자기 팀 공격 명령을 접수했다(A/B counter 각각1). 위조된 team/unit 조합은 Java에서도 HTTP400. 정상 게임 전투 후 `check`는 A=[208,210], B=[]를 관측했고 서버 콘솔은 B unit 209가 `Groups.unit`에서 제거됐음을 확인했다. 근거: `build/duel-runs/gate2-live.jsonl`, `gate2-ownership-reject.http`, `gate2-server.log` (Git ignored), 세부 SHA-256은 [DUEL_DEMO.md](DUEL_DEMO.md)에 기록.
- **경계:** Java의 `team` 필드는 인증된 caller ID가 아니다. Python coordinator의 A/B 소유권 검사와 Java의 unit-team 검증은 controlled localhost demo용이며 완전한 보안 설계가 아니다. 기존 연구용 관측/runner·logistics v1 의미론을 변경하지 않았다. 두 LLM 실행, GUI에서 새 endpoint 동작, 대칭 two-core/native game-over, 경제·건설·생산은 **NOT_VERIFIED**. 다음은 Gate 3 LLM A vs scripted B.

## 2026-10-01 Weekend duel demo — Gate 1 combat proof

- 별도 `codex/weekend-duel-demo` branch에서 주말 시연 milestone을 시작했다. 기존 logistics v1 및 Memory Contract v2의 코드와 의미론은 변경하지 않았다. 상세 범위와 게이트 상태는 [DUEL_DEMO.md](DUEL_DEMO.md)에 기록한다.
- **VERIFIED_HEADLESS:** Java 17/v159.7 dedicated server의 실제 `InputHandler.commandUnits` 공격 명령으로 Sharded/Crux Dagger가 이동·교전했다. `UnitDamageEvent`와 `UnitDestroyEvent`가 발생했다. Crux Dagger는 `Groups.unit`에서 제거됐고 등록 병력 생존 수 A=2/B=0으로 fixture-level Sharded 승리를 계산했다. 이전 2-vs-2 상호 전멸은 무승부로 분류한다. 전투 중 HP 수정·순간이동·강제 kill은 하지 않았다. 원본 서버 로그 복사본: `build/duel-runs/gate1-headless.log` (Git ignored), 핵심 `G1_ORDERS`/`G1_DAMAGE`/`G1_DESTROY`/`G1_RESULT`.
- **VERIFIED — fixture/lifecycle 원인:** 내장 `Islands`에는 Crux core가 없어 기본 variable unit cap에서 Crux unit이 즉시 제거된다. 양 팀 unit이 실제로 유지되도록 **시합 시작 전 fixture**에서 `unitCapVariable=false`, `unitCap=10`을 설정했다. 별도의 `pvpAutoPause` 규칙도 headless 틱 진행을 막고 있어 해제했다.
- **VERIFIED_GUI — 유닛 전투:** 6567 수신, 8765 `/state` 응답, 2-vs-1 Dagger fixture에서 사용자가 v159.7 CLIENT로 이동·발사/교전·1기 사망·화면상 사라짐을 직접 확인했다. 대칭 two-core PvP match/native game-over는 확인하지 않았다.
- **GUI handshake blocker 및 설정 수정:** 사용자의 pinned source-built CLIENT 접속은 `customClient`로 거절됐다. 현재 서버 `version`은 build 159.7/Java 17.0.20이고, 새 격리 런타임의 `allowCustomClients=false`가 원인이었다. 과거 프로젝트 서버 로그에는 `true`가 기록돼 있으나 새 임시 `config/settings.bin`으로 승계되지 않았다. 재시작 없이 `config allowCustomClients true`로 변경했고 동일 fixture가 tick 0/paused/3 units added 상태임을 확인했다. 설정 수정은 **VERIFIED_TEST**, 재접속 성공과 GUI 전투는 아직 **NOT_VERIFIED**다. 원본 로그: `build/duel-runs/gate1-gui-handshake.log` (Git ignored).
- **VERIFIED_HEADLESS — 재접속/대기 화면 진단:** 이후 서버에서 CLIENT 접속을 확인했다. CLIENT의 “상대 플레이어를 기다리는 중” 표시는 내장 Islands의 활성 Core 팀이 하나인 PvP fixture가 paused일 때 뜨는 HUD 조건이었다. `pvpAutoPause=false` 상태에서 `pause off`로 화면 대기를 풀었고 tick 522까지 Dagger 3기의 초기 위치/체력 유지, `gameOver=false`를 확인했다. 공격 명령은 아직 내리지 않았으며 사용자의 실제 화면 확인 전까지 **VERIFIED_GUI는 아님**.
- **Gate 1 PASS — VERIFIED_HEADLESS + VERIFIED_GUI 유닛 전투:** 사용자가 전장과 유닛을 본 뒤 정상 공격 명령을 내렸다. 서버 로그 `build/duel-runs/gate1-gui-combat.log`에는 양측 피해, Crux unit 210 `UnitDestroyEvent`, 그룹 제거, 등록 병력 A=2/B=0 판정이 남았다. 사용자는 별도 답변에서 **이동·발사/교전·1기 사망·화면상 사라짐 모두 직접 확인**했다. 엔진 `gameOver=false`이므로 승자는 fixture-level 판정이다. 이 2-vs-1 전투의 승리를 균형 잡힌 two-core duel이나 엔진 `GameOverEvent`로 해석하지 않는다.
- 팀 저장소 `time-to-think/mindustry`의 공개 head/history를 확인했으나 보고된 terrain/capture·prompt·spawn/despawn 작업을 찾지 못했다. 현재 공개 branch는 상류 Mindustry 이력으로 보여 아무 코드도 가져오지 않았다.
- **NOT VERIFIED:** 대칭 두-core PvP map/native game-over, end-to-end dual-agent match, 두 모델 동시성, 경제·건설·생산·업그레이드. 현재 GUI/헤드리스 유닛 전투 성공을 전체 duel 성공으로 확대하지 않는다.

## Long-term direction / current gate

- 현재 연구 목표는 같은 관측·모델·executor·예산에서 `NO_SCRATCHPAD`와 `STRUCTURED_SCRATCHPAD`를 공정하게 비교하는 것이다. 기존 logistics v1은 smoke/negative control로 보존하고, 기억에 민감한 계약은 별도 v2로 분리한다.
- 개발 순서와 범위는 [ROADMAP.md](ROADMAP.md), 조건·schema·지표 규약은 [SCRATCHPAD_EVALUATION.md](SCRATCHPAD_EVALUATION.md)를 따른다.
- 현재 위치: **Autonomous Early-Game Logistics Vertical Slice**의 과거 헤드리스 기능 검증과 실제 v159.7 CLIENT 인간 시각 검증은 유효하다. Provider/scratchpad/metric/mock runner는 부분 구현·단위 검증 단계이며, 실제 게임에서 scratchpad 효과를 검증한 상태가 아니다.
- 현재 gate: **재현성·live 연결 전 계약 정합성 milestone 완료**. [MEMORY_CONTRACT_V2.md](MEMORY_CONTRACT_V2.md)의 v2 보장은 그대로 유지했고, [REPRODUCIBILITY.md](REPRODUCIBILITY.md)에 실행 환경·artifact·검증 수준을 기록했다. 다음 phase는 아직 시작하지 않았다.

## 2026-10-01 Reproducibility & Pre-Live Contract Alignment

- 기준 checkpoint `2d77541299cf6f83f15b2df26d62643c15d20f29`, branch `stage4-agent`. 시작 시 Git staged 변경 없음, remote `origin/stage4-agent=82b3ce7` 대비 10 ahead/0 behind. 기존 두 다른 worktree, Java/agent/research gameplay 소스, `experiments/memory_sensitive_v2.json`, 과거 save/JAR/로그는 변경하지 않았다.
- **VERIFIED — 환경/빌드:** CPython 3.13.5로 새 격리 venv를 만들고 network 없이 빈 pip 의존성 선언을 처리했다. JDK Temurin 17.0.20, Gradle 9.4.1, `Anuken:Mindustry:v159.7`로 빈 Gradle cache에서 Java build가 성공했다. Gradle wrapper/compile dependency hash를 고정했다. 다른 Python/OS 조합은 검증하지 않았다.
- **VERIFIED — 테스트:** 기존 61개를 유지하고 환경/API/manifest/artifact/metadata 계약 9개를 더해 **70/70 통과**. 두 조건의 1-run mock smoke, compileall, metadata 형식 검증도 임시 checkout에서 성공했다. Java 17 cold build와 dependency hash 검증을 적용한 offline `clean jar`도 성공했고 새 JAR는 기존 배포 JAR와 SHA-256 `60c79393e5cddf855e5baf570537198cf21387c119f14f479ae94769ffbe5def`로 같았다. GitHub hosted CI는 실행되지 않았다.
- **VERIFIED — API/manifest:** 실제 Bridge endpoint는 GET `/state`, POST `/action`뿐이다. v1 manifest의 미구현 `/units`, `/buildings`, `/tasks/{task_id}`를 제거하고 view/active 필드와 Python 내부 `wait`를 구분했다. fixture 검사에 필요한 map/full rules/four resources/unitCounts는 현재 raw `/state`에 모두 없음을 명시했다. 기존 v1 goal·fixture hash·budget 숫자와 v2 spec을 유지했다. 360초/80회는 mock에서만 부분 집행되고 기존 live demo 예산과 동일한 계약이 아님을 기록했다.
- **VERIFIED — artifact 정합성:** 원본 관리자가 보유한 save, historical JAR, server JAR, 로그 6개 및 compile dependency 1개를 manifest의 총 10개 항목으로 기록했다. bundle 없음 → 10 missing/exit 2; 원본을 임시 경로에 복사한 뒤 → 10/10 hash 일치/exit 0. helper는 읽기 전용이다. 원본의 Git 배포나 새 게임 재실행은 하지 않았다.
- **VERIFIED — 문서 계약:** README를 연구 프로젝트 기준으로 교체하고 field-status metadata 계약/검증 helper를 추가했다. 알려지지 않은 model revision/생성값은 null 및 이유로 남긴다. 실제 runner는 이 완전한 envelope를 아직 생성하지 않는다.
- **PARTIALLY VERIFIED — v2 live feasibility:** `survey_preference`는 과거 실제 ore 정찰과 현재 unit-local sensor를 분리하면 조건부 구현 가능하다. `failure_recovery`는 builder interruption과 remote outlet 단절을 정상 메커니즘으로 구분할 수 있으나 동일 current observation을 가진 paired fixture를 실제 게임에서 아직 구성하지 않았다. [PRE_LIVE_MAPPING.md](PRE_LIVE_MAPPING.md)에 ground truth/public/history/executor/evaluator 경계와 누출 공격을 설계했다. Bridge 전면 재설계가 필요하다는 증거는 없지만 trusted adapter와 별도 executor 경계의 구현·검증이 필요하다.
- **NOT VERIFIED:** GitHub hosted CI, 공개 artifact 인수 경로, live save reset/초기상태 검증, v2 adapter의 public bytes 동등성, live LLM inference/게임 success, scratchpad 성능 효과, 실제 context loss. 과거 v1 GUI/headless 성과를 이번 세션의 게임 재검증으로 해석하지 않는다.
- 다음 단일 milestone 권장: recorded/synthetic Bridge snapshot으로 trusted observation adapter의 **same-public-observation / no-leakage conformance**를 검증한다. 실제 v2 gameplay 연결과 LLM pilot은 그 다음 별도 단계다.

## 2026-09-30 Memory-sensitive contract v2 milestone

- 시작 checkpoint `596ad51`, 시작 미커밋 변경은 직전 감사 보고서와 PROGRESS뿐이었다. 이 문서들을 보존했다. `agent/`, Java Bridge, v159.7 설정, 기존 logistics v1 manifest, GUI/headless 원본 기록과 demo 절차는 변경하지 않았다.
- **VERIFIED — CONTRACT/UNIT:** `experiments/memory_sensitive_v2.json`에 동일 current observation/상이한 history의 두 case를 명시했다. 이전 정찰 결과에 따른 site-a/b 선호, 이전 실패 원인에 따른 route-a 재시도/route-b 대안 선택이다. 두 case 각각 history2개를 가진다.
- Public request는 조건 사이에서 scratchpad 값만 다르다. 모델·공통 prompt·관측·executor·budget·timeout 차이는 pair checker가 거절한다. validator는 history/정답/memory를 보지 않으며 전략적으로 열등해도 합법적인 양쪽 선택을 허용한다.
- **VERIFIED — 정보 경계:** Python phase/summary/previousDecision/blocked/후보 score 누출 canary 제거, 후보 순서 정규화, 과거 event와 임의 summary predicate 거절, provider mutation 격리, no-memory의 암묵적 scratchpad 반환 거절을 검사했다. None/correct/incorrect memory를 구분하며 잘못된 기억도 schema가 맞으면 통과한다.
- Bounded memory v2는 goal, selected subgoal, relevant events, completed milestones, failures/attempted alternatives, unresolved information, next step을 저장한다. 전체4096 bytes와 필드별 한도·revision·atomic 저장을 검증했다. raw history 구조는 허용하지 않는다.
- **VERIFIED — 평가 반례 수정:** 기존 mock runner에서 flow는 milestone이고 후속 판단까지 성공해야 completion이다. 성공 terminal·후속 판단 증거·미해결 실패 부재를 모두 요구한다. 감사의 `bootstrap → establish → wait → reconsider` 반례는 이제 실패로 집계된다. transport OSError도 metrics/summary를 남긴다.
- Stateless boundary hook은 `context_loss=false`로 기록하며 실제 복구처럼 세지 않는다. `actual_context_loss_count=0`. 실제 이력 제거·프로세스 재기동을 검증했다는 뜻이 아니다.
- **VERIFIED — TEST:** Python3.13.5에서 기존38개 + 신규23개, **61/61 통과**. 기존 metric fixture1개는 성공 terminal과 명시적 recovery 의미에 맞게 보강했고 삭제/skip하지 않았다. 결과: `build/contract-v2/tests.txt`; 진단 자료: `build/contract-v2/evidence.json` (ignored, 테스트로 재생성 가능).
- **PARTIALLY VERIFIED:** memory가 의미 있는 독립변수가 될 수 있는 최소 계약과 정적 persistent-state 감사. 진단용 scripted policy·수작업 memory/utility를 사용했으며 실제 모델 능력을 측정하지 않았다.
- **NOT VERIFIED:** LLM의 기억 작성/활용 효과, v2 live 관측/게임 실행, 실제 시간 예산 집행, 장기 episode, local inference, combat/대전. 이번에는 서버·LLM을 시작하거나 모델을 설치하지 않았다.
- 남은 confounds: live adapter가 정보 경계를 지키는지, memory token/latency 증가, 재정찰의 정보 가치, 손으로 정한 utility의 게임 대응. Mock의 엄격한 timeout·전체 metric 정확성과 artifact 재현성은 후속 범위다.
- 다음 권장 milestone: 감사 Phase C의 **재현성 및 live 연결 전 계약 정합성 정리**. README/Python/CI·manifest 실제 API·fixture 복원과 두 v2 case의 live 대응 가능성을 확인한 뒤 provider/executor 통합을 별도 승인받는다.

## 2026-09-29 Audit — 구현 및 실험 주장 재분류

- 코드·Git·문서·기존 로그·v159.7 참조 API·외부 1차 자료를 감사했다. 이번에는 게임/LLM을 실행하지 않았으며 gameplay 코드, 설정, checkpoint를 변경하지 않았다. 아래 결과는 과거 GUI/headless 성공의 재실행이 아니다.
- **VERIFIED — 현재 Git/파일:** 시작 작업 트리는 clean, HEAD `596ad51`, `stage4-agent`는 실제 remote의 `82b3ce7`보다 9 commits 앞선다. 로컬 master는 `fdeb005`지만 실제 remote master는 `6bb236d`로 cached ref와 달랐다. fetch/merge/push하지 않았으므로 실제 remote master와의 ancestry는 미확정이다. 기존 로그·fixture hash와 build/deployed JAR 동일성을 확인했다.
- **VERIFIED — 이번 단위 테스트:** Python 3.13.5에서 38개 통과. 기본 Python 3.9.6에서는 union type annotation 평가로 module import 오류 4건이 발생했다. 실행 환경 명시가 필요하다. 결과는 `build/audit-20260929/tests*.txt`에 보존했다.
- **PARTIALLY VERIFIED — 연구 framework:** `experiment.py`는 provider 선택과 무관하게 mock backend를 사용한다. ResearchDecisionAdapter는 실제 logistics entrypoint에 연결되지 않았다. manifest의 일부 endpoint/관측 필드는 현재 Bridge와 다르므로 frozen manifest 자체를 live 실행 계약 검증으로 해석하면 안 된다.
- **RISK — 지표 정확성:** 작은 mock 진단에서 후속 판단 실패 뒤에도 `task_success=true`, provider transport 예외 시 metrics/summary 누락, blocking 호출의 episode timeout 초과를 확인했다. 일부 token usage만 보고된 경우 coverage 없이 합계로 표시된다. 진단은 `build/audit-20260929/probes.json`에 보존했으며 새 게임 실험 캠페인은 아니다.
- **RISK — 연구 책임 경계:** 현재 Python이 물류 후보·경로·연속 건설·자원 보충·일부 복구를 수행한다. 물류 GUI 실행은 360초 동안 LLM 판단 3회이며, MAINTAIN에서 후속 판단 1회 후 관측만 계속한다. “후속 판단 확인”은 유지하지만 “지속적 전략 재계획/장기 기억 검증”으로 확대하지 않는다.
- **NOT VERIFIED:** 실제 Local LLM 실행, scratchpad의 게임 성능 효과, 의미 있는 context-reset 처치, live episode 반복, combat, dual-agent. 현재 OpenCode reset hook은 매 호출 stateless 요청이므로 no-op이며, adapter reload 테스트를 실제 프로세스 재시작 검증으로 부르지 않는다.
- **BLOCKER — 향후 대전:** observation은 defaultTeam 기준이고 action은 대상 unit 팀의 Player를 찾아 실행한다. caller identity/팀 권한·ownership·fog 격리가 없어 두 agent 대전 평가 전에 보완해야 한다.
- 기존 functional logistics GUI/headless 증거는 보존한다. 감사 결론은 전면 재작성이 아니라 연구용 정책/기억/평가 경계의 선행 정리다. Combat/Human-v-Agent/Agent-v-Agent는 보고서의 설계 제안이며 구현하지 않았다.

## Repository reconstruction

- Branch: `stage4-agent`, tracking `origin/stage4-agent`.
- Implementation checkpoint: `8a4ac47` — Add persistent autonomous LLM vertical slice.
- Stage 10 runtime-fix checkpoint: `21f0d92` — Verify Stage 10 building and restore builder command after move.
- Previous milestone: `802e2ca` — Stage 9: add runtime-tested LLM-controlled mining agent.
- `master` stops at movement demo `fdeb005`. Two other worktrees also point to Stage 10; do not alter them.
- Reference checkout reports tag `v159.7` and is clean. Dedicated server JAR reports build `159.7`.

## Architecture and files

Mindustry dedicated server ↔ Java AgentBridge HTTP/JSON ↔ external Python agent ↔ decision layer.

- `AgentBridgePlugin` starts localhost HTTP. `StateHttpServer` and `ActionHttpHandler` dispatch game access through `Core.app.post` and wait up to 5 seconds.
- `/state`: 기존 상태와 함께 `units[].activity` 및 bounded `demo` 관측을 제공한다. 선택적 `tileX`/`tileY`, radius 1–6으로 최대 169타일만 읽는다.
- `/action`: move via `InputHandler.commandUnits`; mine via mine command/item stance; build via validation followed by `unit.addBuild(new BuildPlan(...), true)`.
- `agent/agent.py`: observe; `demo_move.py`: one move; `autonomous_agent.py`: Dagger patrol; `resource_agent.py` / `continuous_resource_agent.py`: resource balancing.
- `agent/build_test.py`: submit one conveyor BuildPlan for an explicitly chosen tile, select a unique Poly, and record positions/resources. Uses a 7-second HTTP timeout. Does not claim completion from observations without tile evidence.
- `llm_decision_test.py`: observation → Qwen JSON; `llm_game_agent.py`: validate mine/copper/lead decision → action. Runtime model remains `ollama-cloud/qwen3.5:397b` via OpenCode CLI.
- `agent/autonomous_llm_agent.py`: 1초 관측과 비동기 Qwen 판단을 분리하고, 엄격한 Python 검증 뒤 mine/build/move/wait를 공통 루프로 실행·모니터링·재계획한다. 기존 agent 파일은 교체하지 않았다.
- `/state?view=logistics-plan`: 코어 기준 radius 48의 copper ore, v159.7 `Build.validPlace`를 통과한 mechanical-drill 후보와 conveyor cell/회전 mask, 기존 건물, 실제 콘텐츠 비용을 계획 시 한 번 제공한다. `/state?view=logistics-status`는 정적 계획 격자를 빼고 코어 수령량, drill 동작과 conveyor item 상태를 주기적으로 제공한다.
- `agent/logistics_planner.py`: drill 후보 선택, BFS conveyor 경로·회전 계산, 비용 및 topology/flow 판정을 담당한다. `agent/logistics_agent.py`: Qwen의 고수준 intent와 PLAN→DECIDE→BOOTSTRAP→BUILD→VERIFY_FLOW→MAINTAIN 상태 흐름을 연결한다.
- `experiments/logistics_benchmark.json`: 검증된 v159.7 fixture와 goal/success/budget을 동결한다. `research/`: provider 경계, memory condition, bounded scratchpad, runner와 metric 계산을 포함한다. `experiment.py`는 현재 deterministic mock smoke runner를 제공한다.

## Verification status

| Stages | Evidence / status |
| --- | --- |
| 1–3: state, Python observation, movement | Historical runtime-tested per handoff; Stage 1/3 commit subjects explicitly say runtime-tested. Server log records client sessions and Dagger spawn. Not replayed in this session yet. |
| 4–7: patrol, mining, resource selection/balancing | Historical runtime-tested per handoff; Stage 5 commit explicitly says runtime-tested. Source implements all stages; logs show Mono sessions. Logs alone do not prove each agent outcome. |
| 8–9: Qwen decision and mining action | Historical runtime-tested per handoff; Stage 9 commit explicitly says runtime-tested. No new model request performed. |
| 10: build | Java 17 compile/jar, v159.7 서버 로딩, no-player 거절, server-only Player를 사용한 헤드리스 완공을 확인했다. move→build 정체를 최소 수정한 뒤 실제 네트워크 client에서도 Poly 이동, 정상 BuildPlan 건설 과정과 블록 완성을 사람이 확인했다. |
| Autonomous control vertical slice | 2026-09-08 헤드리스 300.669초와 2026-09-09 실제 client 연결 300.105초 실행에서 Qwen mine/build/wait 판단, 실제 Mono 채굴과 코어 자원 변화, Poly 이동·정상 건설·블록 완성, 완료 후 재판단을 확인했다. 이는 제어 루프와 건설 메커니즘 검증이다. 생산 지점→Core 물류 달성 검증은 아니다. |
| Autonomous Early-Game Logistics Vertical Slice | **VERIFIED — HEADLESS:** 2026-09-09 360.649초 실행에서 bootstrap, drill/conveyor 정상 완공, 격리된 자동 copper flow와 후속 재판단을 확인했다. **VERIFIED — HUMAN GUI:** 같은 deterministic fixture의 360.249초 실제 v159.7 CLIENT 실행에서 사용자가 Mono bootstrap, Poly 이동·정상 drill/conveyor 건설, 연결 경로, conveyor item 이동, core 유입과 무인 후속 실행을 직접 확인했다. |

## Caveats

- `build.gradle` inherited `mindustryVersion = "latest"`; changed to `"v159.7"` on 2026-09-08. Resolved artifact metadata reports 159.7 and its content matches the previous cached dependency.
- A same-team player must be in `Groups.player` for all actions. 헤드리스 검증에는 no-op `NetConnection`을 가진 server-only Player fixture를 사용했고, 실제 end-to-end 시각 검증은 v159.7 CLIENT 연결로 완료했다.
- Poly defaults to rebuild command (`BuilderAI`). The reproduced move→build stall is fixed: build selects supported rebuild command, preserves queued plans during switching, and clears hold-position. Verified in actual headless game.
- Sandbox's global `infiniteResources=true` also bypasses build range (`BuilderComp`). Turn it off to prove travel and resource consumption. Keep `instantBuild=false` and default build multipliers.
- 물류 계획 관측은 코어 주변 radius 48로 제한되고 계획 시에만 읽는다. 이는 Islands 기술 데모용 planner이며 범용 전체 맵 planner나 정식 episode schema는 아니다.
- mine milestone은 matching mining을 관측한 뒤 발생한 코어 재고 증가를 요구하지만, 여러 생산원이 있는 환경에서 그 증가를 특정 Mono에 엄밀히 귀속하는 평가 지표는 아니다.
- 실제 네트워크 client 화면에서 Mono 채굴, 자원 변화, Poly 이동, 정상 건설 과정, 블록 완성과 후속 동작을 확인했다. LLM이 별도 `move`를 선택한 실행은 아니며, 관찰한 Poly 이동은 BuildPlan의 정상 접근이다.
- 2026-09-09의 이전 bounded control demo 위치는 광물 생산 시설과 Core를 연결하는 경로가 아니었다. 아래 새 logistics headless 실행의 증거와 혼동하지 않는다.
- 서버 `/state`와 build event는 완성 block을 `conveyor`, team `sharded`, rotation 0으로 기록했다. 사용자는 CLIENT 화면만으로 설치된 블록이 의도한 conveyor인지 확신할 수 없었다고 보고했다. 따라서 GUI 증거만으로 블록 외형/종류를 확정했다고 기록하지 않는다.
- 당시 README는 upstream template이었다. 2026-10-01 이 milestone에서 교체했다. 현재 research runner의 mock backend는 harness 검증용이며 live Mindustry reset driver는 아직 연결되지 않았다.

## 당시 제안된 다음 milestone (2026-09-09 기록)

- Frozen save load, 초기 snapshot 검증, action identity, run 종료와 cleanup을 한 episode 경계로 묶는 live reset driver를 추가한다.
- 두 조건의 실제 Qwen/local LLM pilot은 live reset 검증 뒤 소수만 실행한다. 대규모 cloud 반복이나 최종 모델 선택은 하지 않는다.
- combat, defense, factories, power, 추가 block, advanced logistics와 multi-agent는 연구상 필요가 입증되기 전까지 추가하지 않는다.

## 2026-09-09 Autonomous Early-Game Logistics headless verification

- 실행 파일: `build/demo-runs/logistics-headless-20260909-verified.jsonl` (Git ignored), SHA-256 `095592cf09b0f107c9b866dc775f0fac7c18f5139948c4246545a28f0d7fcb86`. 해당 서버 시작 구간은 `build/demo-runs/logistics-headless-20260909-server.log`, SHA-256 `36186dfad9abdee484456bf6ce2352be5240237323734310e66ad57d6979d995`로 보존했다.
- 환경: v159.7 Islands sandbox, 초기 copper/lead 0, Mono 209, Poly 210, `infiniteResources=false`, `instantBuild=false`, waves/timer off, 기본 비용·건설 속도. no-op `NetConnection`을 가진 same-team server-only Player는 headless action 권한 fixture이며 실제 네트워크 client는 없었다. Agent 시작 뒤 console에서 mine/build/move를 보내지 않았다.
- 360.649초 동안 관측 358회, Qwen 고수준 판단 3회, action 15회, 실제 완성 block 12개, flow completion 1회를 기록했고 최종 phase는 `MAINTAIN`, runtime error는 0건이었다. Qwen은 `continue_bootstrap` → `establish_copper_logistics` → 완성 후 `wait`를 선택했다.
- 실제 계획: copper ore를 덮는 mechanical drill anchor `(164,42)`, footprint `(164..165,42..43)`, copper ore 1타일. BFS 경로는 `(163,43)`에서 `(161,51)`까지 연결된 conveyor 11개이며 마지막 tile은 core footprint `(158..160,51..53)`를 향한다. 계획된 block/team/rotation 전부를 live state에서 다시 확인했다.
- v159.7 실제 비용은 mechanical drill copper 12, conveyor copper 1×11, construction 23이며 명시적 safety margin 10을 더한 bootstrap 기준은 33이었다. Agent는 copper 40을 관측한 뒤 두 번째 Qwen 판단을 요청했고, 응답 대기 중 정상 채굴이 계속되어 건설 시작 시 재고는 더 증가했다.
- 유량 기준선은 Poly를 기존 `move` action으로 코어에 대기시키고 Mono의 유일한 선택 stance와 실제 채굴이 lead인 상태에서 잡았다. 기준선 copper 66/누적 수령 2 이후 drill의 `dominantItem=copper`, `lastDrillSpeed>0`, 계획 conveyor 위 copper, core copper 67 및 누적 수령 증가가 차례로 관측되어 `COMPLETE`가 기록됐다. 실행 종료 후 독립 상태 읽기는 Mono lead 채굴 중, drill warmup 1.0, core copper 92/누적 수령 28이었다.
- 첫 75초 개발 실행은 copper→lead 전환 시 v159.7 item stance가 배타적이지 않아 `/state`가 `mineResource` 중복 키를 만든 문제를 발견했다. `ActionHandler`가 이전 item stance를 정상 `InputHandler.setUnitStance(..., false)`로 해제하도록 수정하고, 관측도 중복 키를 만들지 않게 한 뒤 새 sandbox에서 위 성공 실행을 완료했다.
- **헤드리스에서 검증:** drill placement 유효성, drill→conveyor→core topology, 정상 BuildPlan 완공, Mono copper 비채굴 격리, drill 생산, conveyor item 관측, 자동 copper의 core 유입, 완료 후 재판단과 수분간 유지.
- **아직 GUI에서 미검증:** 새 계획의 실제 drill 외형·건설 animation, 11개 conveyor 경로의 시각적 연결과 item 이동. 이전 GUI run은 이 항목의 증거로 사용하지 않는다.

## GUI verification fixture ready

- `1번 SERVER`에 `config/saves/autonomous-logistics-base.msav`를 생성했다. SHA-256은 `1a70fe390341fa4fed62b189053838a750762266d01f31606a159dfc24eabc4f`다.
- 저장 직후 live 상태는 copper/lead 0, Mono 238과 Poly 239 모두 `move`, build plan 0, 기존 건물은 Sharded core 1개뿐이었다. `infiniteResources=false`, `instantBuild=false`, 6567/8765 LISTEN을 확인했다.
- 임시 server-only Player는 시작 command 설정 직후 제거해 `commandReady=false`다. 실제 v159.7 CLIENT가 연결되기 전에는 `agent/logistics_agent.py`를 시작하지 않는다.

## 2026-09-11 Autonomous Early-Game Logistics human GUI verification

- **VERIFIED — HUMAN GUI.** 사용자가 실제 v159.7 CLIENT에서 같은 autonomous logistics 실행을 직접 관찰했다. 사람은 agent 시작 뒤 mine/build/move 명령을 보내지 않았다.
- 직접 확인 항목: Mono bootstrap mining, Poly의 build area 접근, 정상 BuildPlan mechanical drill 건설, conveyor 경로 건설, drill에서 core 방향으로 연결된 배치, conveyor 위 copper item 이동, copper의 core 유입, 완료 후 runtime의 무인 지속 동작.
- 같은 실행의 agent 로그: `build/demo-runs/logistics-gui-20260909.jsonl` (Git ignored), SHA-256 `754c47e72a2ed3323821a2d9281f0cf374524c7416705874169c2e10e60b8577`. Runtime 360.249초, Qwen intent `continue_bootstrap` → `establish_copper_logistics` → `wait`, action 9회, 실제 완성 block 6개, flow completion 1회, 오류 0건, 최종 phase `MAINTAIN`.
- 같은 실행의 서버 로그: `build/demo-runs/logistics-gui-20260909-server.log` (Git ignored), SHA-256 `078cca83964faf346993d7cc44444257c892f7b4ad932316db38a0c78b0c1943`. Poly 239의 mechanical drill `(151,53)`과 conveyor `(153..157,53)` 각각에 대한 정상 build begin/end를 기록했다.
- 시스템 유량 증거: Mono 238은 flow 측정 중 lead만 선택해 실제 채굴했고, 기준선 core copper 63/누적 수령 1 이후 drill 생산, 계획 conveyor 위 copper, core copper와 누적 수령 증가가 순차 관측됐다. 360초 종료 뒤 독립 상태는 core copper 90/누적 수령 28, drill warmup 1.0이었다.
- 결론: 이 milestone은 headless와 human GUI 양쪽에서 완료했다. 위 관찰은 현재 copper 물류 benchmark에 한정하며 범용 base building, 다른 block/자원, combat, production 또는 multi-agent 성능을 입증하지 않는다.

## 2026-09-09 GUI visual verification

- 실제 v159.7 CLIENT 사용자 `andrew`가 `127.0.0.1:6567`에 연결했고, 같은 팀 Player로 `commandReady=true`인 상태에서 실행했다. server-only Player는 실행에 사용하지 않았다.
- 실행 파일: `build/demo-runs/gui-vertical-slice-20260909.jsonl` (Git ignored), SHA-256 `79baa0d104f867bd73e58e79d2f4e71b73144db2013b1ab795203f64ab33d834`.
- 환경: Islands sandbox, copper 200, lead 0, Mono 208, Poly 209, `infiniteResources=false`, `instantBuild=false`, waves/timer off, 기본 build 속도. 300.105초 동안 관측 299회, LLM 판단 8회, 접수 action 4회, mine milestone 1회, build completion 3회를 기록했고 runtime error는 없었다.
- 시스템 로그는 `(121,59)`, `(121,60)`, `(121,61)`에 sharded conveyor rotation 0 완성과 copper 200→197 소비를 기록했다. 완료 뒤 Qwen은 3회 `wait`를 선택하며 관측을 계속했다.
- **GUI에서 확인:** Mono의 실제 채굴, Core 자원 변화, Poly의 실제 접근 이동, 정상 건설 과정과 블록 완성, 건설 이후 후속 동작.
- **GUI/기능으로 확인하지 못함:** 올바른 drill placement, drill→conveyor→core의 연결된 물류망, conveyor를 통한 실제 자원 운송, 자동 생산 자원의 Core 유입. 설치된 블록의 시각적 종류도 사용자에게 명확하지 않았다.
- 결론: autonomous observation/replanning, mining, legitimate Poly movement, legitimate BuildPlan construction, actual block completion과 completion 이후 판단은 검증했다. Functional logistics 성공으로 분류하지 않는다.

## Latest continuous runtime evidence

- 실행 파일: `build/demo-runs/vertical-slice-20260908-mining-build.jsonl` (Git ignored), SHA-256 `9963d1b0bbec7df6debe4ed70e8faa8d925b1a71c3d16d6da04a1929bdba790d`.
- 명령: `python3 agent/autonomous_llm_agent.py --duration 300 --lead-reserve 50 --log build/demo-runs/vertical-slice-20260908-mining-build.jsonl`.
- 환경: Islands sandbox, v159.7 dedicated server, `infiniteResources=false`, `instantBuild=false`, waves/timer off, 기본 build 속도. 같은 팀 server-only Player와 Mono/Poly를 fixture로 등록했으며 네트워크 client는 연결하지 않았다.
- 시작 상태: tick 2579, copper 200, lead 0, Mono 215는 move/idle, Poly 216은 rebuild, 작업 구역 conveyor 0개, `commandReady=true`.
- 로그: 637줄, 관측 299회, LLM 판단 8회, 접수된 게임 action 4회, mine milestone 1회, build completion 3회, 검증 거절 1회. 종료까지 300.669초 실행했다.
- 순서 증거: mine 판단/접수 → matching mining 관측 및 새 lead 증가로 mine 완료 → reserve 미달 build 제안 거절 → lead 60에서 새 build 판단/접수 → 실제 conveyor 완료 → 후속 build/replan/wait 판단.
- 완성 타일: `(121,59)`, `(121,60)`, `(121,61)`, 모두 `conveyor`, sharded, rotation 0. Copper는 각 정상 건설에서 200→199→198→197로 감소했다.
- 첫 build 판단 시 Poly와 목표 거리는 약 348.9 world units로 build range 220 밖이었다. server event의 build begin 시 거리는 약 215.9였으므로 BuildPlan이 Poly를 정상 범위 안으로 이동시킨 뒤 건설했다.
- agent 종료 직후 읽은 상태는 copper 197, lead 640, conveyor 3개였고 Mono는 lead 채굴 중이었다. 이후 읽기에서는 lead 700으로 계속 증가했다.
- 최종 실행 중 사람이나 console이 mine/move/build action을 보내지 않았다. 이전 retry와 Mono의 시작 전 자동 채굴은 이 증거에서 제외했다.

## Runtime commands

`3번 AGENT / TEST` — build, tests, runtime:

```sh
cd /Users/andrew/capstone/MindustryAgentBridge
JAVA_HOME=$(/usr/libexec/java_home -v 17) ./gradlew --offline --no-daemon jar
python3 -m unittest discover -s tests -v
python3 agent/autonomous_llm_agent.py --duration 300
```

Deploy only while the server is stopped; preserve the old JAR outside `config/mods` before copying `build/libs/MindustryAgentBridge.jar` into `/Users/andrew/capstone/MindustryServer/config/mods/`.

`1번 SERVER` — start in the dedicated runtime directory:

```sh
cd /Users/andrew/capstone/MindustryServer
"$(/usr/libexec/java_home -v 17)/bin/java" -jar server-release.jar
```

Server console (not shell):

```text
host Islands sandbox
js Vars.state.rules.infiniteResources = false; Vars.state.rules.instantBuild = false; Vars.state.rules.waves = false; Vars.state.rules.waveTimer = false;
status
```

Use `exit` to shut down before JAR replacement; `stop` only stops hosting. Fixture 준비와 검증 항목은 [AUTONOMOUS_DEMO.md](AUTONOMOUS_DEMO.md)를 따른다.

`2번 CLIENT` — connect the existing v159.7 client to `127.0.0.1:6567`. Do not edit the pinned source. Historical launch command (Gradle writes generated build outputs; no source edits):

```sh
cd /Users/andrew/capstone/Mindustry-v159.7
JAVA_HOME=$(/usr/libexec/java_home -v 17) ./gradlew desktop:run
```

If a source-built client is rejected as `customClient`, inspect the existing `allowCustomClients` setting before changing it.

## 2026-09-11 Scratchpad Evaluation framework

- **VERIFIED — UNIT/DETERMINISTIC MOCK:** `experiments/logistics_benchmark.json`에 v159.7 Islands save SHA-256, 초기 자원/Mono/Poly, observation/action, 검증된 planner/runtime, 목표, 성공 기준, 360초 timeout과 action budget 80을 동결했다.
- `DecisionProvider.decide(context)` 경계로 기존 Qwen/OpenCode 연결, 기존 `LogisticsDecisionProvider` adapter와 deterministic mock을 분리했다. OpenCode provider는 기존처럼 project config, 도구와 sharing을 차단하며 최종 local model은 선택하지 않았다.
- `NO_SCRATCHPAD`와 `STRUCTURED_SCRATCHPAD`를 같은 runtime adapter에 연결했다. Structured 조건은 4096-byte 고정 schema, 불변 goal, 연속 revision과 atomic file replace를 강제하고 context reset/adapter 재시작 뒤 디스크에서 reload한다. No-scratchpad 조건은 현재 관측 외의 이전 observation을 provider context에 넣지 않는다.
- `experiment.py`는 condition/run별 metadata, JSONL, metrics, summary를 생성하고 deterministic mock episode마다 reset, fixture 검증, decide/validate/action/complete, cleanup을 수행한다. 두 조건 각 2-run unit test와 별도 CLI smoke에서 성공, context reset, cleanup, fairness metadata 일치를 확인했다.
- task success/time, LLM/action/invalid/redundant 수, goal loss/recovery, resource efficiency, provider token/latency, scratchpad bytes와 context-reset recovery latency의 운영 정의와 계산 테스트를 추가했다.
- **NOT VERIFIED:** 실제 Mindustry save reset을 반복 episode 경계로 묶는 live reset driver, 실제 Qwen/local LLM을 사용한 두 조건 pilot, scratchpad 성능 효과, 최종 local model과 본실험 run 수. Mock 결과는 research outcome이나 game runtime 증거가 아니다.
- 당시 다음 단계로 frozen fixture용 live reset driver와 소수 pilot을 제안했다. **2026-09-29 감사에서 이 순서를 재검토했다:** 먼저 연구용 decision/observation/memory 계약을 확정해야 한다. 기존 `docs/SCRATCHPAD_EVALUATION.md`와 `docs/ROADMAP.md`의 세부 실행 규약은 감사 보고서의 한계·제안과 함께 읽어야 하며, 다음 구현은 승인 대기 상태다.

## Experiment history

- 2026-08-19–20: historical state/movement/mining/agent/Qwen progression in Git and handoff. Dedicated log contains client sessions and Dagger/Mono spawns; no build-completion trace found.
- 2026-08-26: Stage 10 committed as `82b3ce7`; deployment JAR also exposes `handleBuildAction` despite its earlier filesystem timestamp. Timestamp is not proof of runtime verification.
- 2026-09-08: reconstructed branch/diffs/tree/source/history and pinned runtime/source version. Initial deployed JAR SHA-256: `a184cc54b0afbe46e463975cfe5d295c7c5154c93b5fb3648760c2e66cca6e4a`. Fresh Java 17 Gradle compile/jar succeeded; pinned-source static analysis confirmed Poly BuilderAI path and sandbox range caveat.
- 2026-09-08: pinned Gradle dependency, rebuilt, backed up/deployed JAR, started Java 17 server on Islands sandbox, and configured finite normal construction. A no-player build correctly returned HTTP 400; this was rejection-path evidence only.
- 2026-09-08: created `docs/ROADMAP.md` with eight phases, S1/S2/S3 candidates, minimum interface, metric/fairness proposals and explicit scope boundaries.
- 2026-09-08 vertical slice: latest user instruction superseded approval wait. With a server-only test Player added to `Groups.player` (no network client, no block mutation), existing build moved Poly 208 from ~925 world units into range 220 and completed conveyor `(121,59)`, team sharded, rotation 0, copper 200→199, queue empty. Begin/end occurred in the same tick: this cheap conveyor can finish within one ordinary builder update; distinct event ticks are NOT required. Human visual/network client verification remains separate.
- Reproduced move→build defect: Poly at ~528 distance kept `command=move`, `plans=1`, target `(122,59)=air` after 8 seconds despite HTTP 200. Minimal fix selects the supported normal rebuild command, preserves queued plans across the command switch, and disables hold-position before adding the plan. Fix compiled on Java 17 and verified after loading the same stalled save: Poly resumed motion, `(122,59)` became sharded conveyor, copper 199→198, command=rebuild, plans=0.
- 2026-09-08 continuous run: verified the LLM-selected mine → observed result → validated build → actual completion → later replanning chain described above. The 15 Python tests and Java 17 offline JAR build passed after the final implementation changes.
- Server lifecycle caveat observed: console `exit` can leave the existing HTTP listener alive. Shut down the owned process with Ctrl+C after save/exit when 8765 remains bound. No lifecycle redesign was included.
