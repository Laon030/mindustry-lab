# Development rules

- 사용자와 한국어로 소통한다. 실행 터미널 이름은 `1번 SERVER`, `2번 CLIENT`, `3번 AGENT / TEST`로 통일한다.
- 기존 프로젝트를 이어서 개발한다. 변경 전에 Git status/diff/history와 관련 소스를 확인하고 사용자 변경을 보존한다.
- Mindustry API 기준은 `/Users/andrew/capstone/Mindustry-v159.7` (tag `v159.7`)이다. 이 참조 소스는 수정하지 않는다. Java 17을 사용한다.
- 전용 서버는 `/Users/andrew/capstone/MindustryServer/server-release.jar`, 게임 포트는 `6567`, AgentBridge는 `127.0.0.1:8765`이다. HTTP는 localhost 전용으로 유지한다.
- HTTP에서 게임 상태를 읽거나 변경할 때 `Core.app.post(...)`를 통한 게임 메인 스레드 실행을 유지한다.
- 정상 게임 메커니즘을 사용한다: `InputHandler`, `UnitCommand`/stance, `BuildPlan`, builder queue/AI. 즉시 블록 배치, `world.setBlock`, 플러그인의 직접 `Build.beginPlace` 호출로 건설을 대체하지 않는다.
- 코딩 도구와 게임 LLM은 별개다. 기존 `opencode run -m ollama-cloud/qwen3.5:397b` 연동은 요청이나 입증된 필요 없이 교체하지 않는다.
- destructive Git 명령, 사용자 변경 폐기, history rewrite, force push를 금지한다. remote push는 명시적 허가가 필요하다. 검증된 기능은 checkpoint commit을 제안하거나 생성한다.
- 컴파일 성공, 정적 분석, 실제 Mindustry 런타임 검증을 구분한다. HTTP 성공은 명령 접수이며 건설 완료 증거가 아니다. 과거 검증 기록과 이번 세션의 재검증도 구분한다.
- 건설 이동 검증은 `infiniteResources=false`, `instantBuild=false`, 기본 건설 속도에서 진행한다. sandbox 무한 자원은 거리 제한까지 해제한다. 시험용 유닛 spawn은 fixture로 명시한다.
- 의미 있는 milestone마다 `docs/PROGRESS.md`의 결과, 증거, 미검증 항목과 다음 단계를 갱신한다. 관련 없는 리팩터링이나 성급한 multi-agent 확장은 피한다.
