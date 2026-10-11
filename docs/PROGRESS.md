# lab 이전 진행 기록

Updated: 2026-10-11 (Asia/Seoul)

## 개인 fork 및 분리된 패키지 준비

- 개인 `Laon030/mindustry-lab`을 팀 `time-to-think/mindustry-lab`에서 fork/clone했다. 최신 팀 lab `develop=1d274c3`에서 `feature/agentbridge-handoff`를 만들었고, 개인 origin을 기본 push 대상으로 지정했다. 팀 upstream push는 로컬에서 차단한다.
- 기존 팀 implementation은 보존하며 103개 Git 추적 AgentBridge 파일만 독립 `agentbridge/`에 가져왔다. 실제 Java/Python 동작, 모델, 정상 게임 메커니즘은 변경하지 않는다.
- 팀 게임을 `game/` submodule로 연결하고 v159.7의 `c9686eb5d0ae5dd47ee02c40f99f7d5018ccbc8c`에 고정한다. 최신 팀 develop과 구분하며 API 기준 참조 소스는 변경하지 않는다.
- root AGENTS의 변경 전 주소를 현재 lab 주소로 고치고 README / 인계 문서에 clone·테스트·build·포트 충돌·runtime 계약 차이를 기록했다.
- 검증 결과는 수행 후 아래에 기록한다. 테스트와 컴파일을 실제 게임/GUI 성공으로 취급하지 않는다.

## 이번 세션 검증 및 SourceTree 연결

- **VERIFIED_TEST:** `agentbridge/.venv`를 CPython 3.13.5로 새로 만들었다. 환경 확인, AgentBridge **121/121** 테스트, compileall, metadata 계약 검사를 통과했다. root의 기존 팀 Python 테스트도 **87/87** 통과했다. 테스트 출력의 실패/timeout 상태는 의도적인 오류 주입이며 실제 게임 실행 기록이 아니다.
- **VERIFIED_BUILD:** Java 17에서 root `jar spectatorJar`와 `agentbridge/`의 offline `jar` 모두 BUILD SUCCESSFUL이다. AgentBridge JAR SHA-256은 `a5e99016d802f0aef5897096e9c9f06e7bfd3a078d253ebe617dde720da53912`로 이전 검증본과 같다. root bridge는 `3691c0b432398c0b52f2212e519e634501ac68f10931f12be8d2369e2ed4fc8c`, spectator는 `52ccd960892938c551fa6b844b4c8c69fc2dfe4ca71c02130a27bde633f17fa9`다. JAR는 Git에서 제외한다.
- **VERIFIED_SOURCE:** 가져온 103개 파일 중 변경된 것은 README와 인계/진행/팀 검토 문서 4개뿐이다. Java/Python 실행 소스는 동일하다. 기존 lab 실행 소스·Gradle/settings·테스트도 그대로 유지한다. 게임 submodule은 clean이며 기록된 gitlink는 v159.7 commit이다.
- **VERIFIED_CONFIG:** `stree`로 새 lab 폴더를 열었고 SourceTree bookmark 설정에서 `/Users/andrew/capstone/mindustry-lab-laon` 등록을 확인했다. 앱의 개별 버튼 동작을 직접 클릭하여 검증한 것은 아니다.
- **NOT_VERIFIED_RUNTIME:** 이번 세션에 게임·모델·GUI를 실행하지 않았다. 게임 본체 build도 수행하지 않았다. API 기준 소스 checkout 및 plugin build 성공과 구분한다. 기존 최신 duel GUI / native Core 승리 / live 연구 v2 검증은 남아 있다.

- **VERIFIED_REVIEW:** staged 110개 경로는 새 AgentBridge 패키지, 문서/규칙/ignore 및 game gitlink에 한정된다. 기존 팀 실행 소스는 변경하지 않았고 credential-pattern scan은 0건이다. 원본 Java의 trailing whitespace 21개는 소스 동일성/계약 hash를 보존하기 위해 유지했다. 해당 기존 공백만 제외한 diff check는 통과했다.

## 개인 포크 업로드 및 새 clone 검증

- **VERIFIED_REMOTE:** checkpoint `905e31c8e7650c184f46e169322e106f9da8b323`를 개인 `origin/feature/agentbridge-handoff`에 push했다. GitHub API에서 개인 fork parent=`time-to-think/mindustry-lab`을 확인했고 `git ls-remote`로 업로드 SHA 및 개인 develop=`1d274c3` 보존을 확인했다. 팀 저장소에 push/PR/merge하지 않았다.
- **VERIFIED_CLONE:** 개인 GitHub feature branch를 별도 임시 디렉터리에 depth=1로 새 clone하고 `git submodule update --init --depth=1 --filter=blob:none`를 실행했다. 팀 URL에서 game=`c9686eb5d0ae5dd47ee02c40f99f7d5018ccbc8c`를 정상 checkout했고 AgentBridge 소스 존재 및 clean 상태를 확인했다. 증거 폴더는 `/private/tmp/mindustry-lab-clone-check-j754qk83/checkout`이다. 이는 clone 재현 검증이며 새 게임 실행이나 전체 engine build가 아니다.
- 이 후속 기록도 같은 개인 feature branch에만 반영한다. 개인 원본과 이전 engine fork 기록은 보존한다. 새 개발 위치는 `/Users/andrew/capstone/mindustry-lab-laon`; AgentBridge 작업/테스트 폴더는 그 아래 `agentbridge/`다.
- 기찬님께 보낼 협의 초안은 [인계 안내](AGENTBRIDGE_HANDOFF.md)에 저장했으며 발송하지 않았다. 다음은 서로의 실행 계약과 실험 조건을 맞추는 리뷰이며 팀 merge와 실제 GUI 검증은 별도 단계다.
