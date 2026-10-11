# 기찬님과 상호 검토하기 위한 안내

**2026-10-11 lab 이전:** 현재 검토·실행 위치는 개인 `Laon030/mindustry-lab:feature/agentbridge-handoff`의 `agentbridge/`다.
멘토의 게임/AI 저장소 분리 규칙을 적용했으며, 게임은 lab의 `game/` submodule에서 v159.7로 고정한다.
[현재 lab 인계 안내](../../docs/AGENTBRIDGE_HANDOFF.md)를 먼저 읽는다. 아래의 게임 포크/비공개 원본 정보는 이전 단계의 기록이다.

**2026-10-11 포크 인계 업데이트:** 현재 실행 패키지는 `Laon030/mindustry:feature/agentbridge-handoff`의 `integrations/mindustry-llm-agent/agentbridge`에 있다. 최신 팀 `develop=e2f5885`는 기찬님 PR #1의 merge commit이다. 아래 10/08의 비공개 저장소·미병합 PR 설명은 당시 기록이며, 현재 공유·실행은 [FORK_HANDOFF.md](FORK_HANDOFF.md)를 따른다. 개인 포크는 공개되어 별도 collaborator 초대 없이 읽을 수 있다.

기준일: 2026-10-08 (Asia/Seoul). `Mindustry` 채팅의 기존 연구/별도 demo 범위와 아래 GitHub 소스를 확인했다. 역할 분담과 통합 방식은 **협의 제안**이며 팀 합의로 확정된 내용이 아니다.

## 검토 대상과 저장소

- 개인 GitHub 계정은 **Laon030**이다. `0803leesj`는 연결된 이메일의 앞부분이다.
- 개인 저장소: [Laon030/capstone-project](https://github.com/Laon030/capstone-project). 비공개이며, 확인 시점에 `qrc4723`의 접근 권한은 없었다. 링크 전달만으로 접근할 수 없다.
- 연구 기준: [`stage4-agent`](https://github.com/Laon030/capstone-project/tree/stage4-agent), checkpoint `37617e0`. Logistics v1과 Memory Contract v2/재현성 작업을 보존한다. v2 live 연결과 scratchpad 성능 효과는 미검증이다.
- 별도 전투 demo: [`codex/weekend-duel-demo`](https://github.com/Laon030/capstone-project/tree/codex/weekend-duel-demo), 구현 checkpoint `f8fa679`. 이 안내를 포함하는 후속 문서 commit은 gameplay 변경이 없다.
- 상호 검토용 [개인 저장소 draft PR #1](https://github.com/Laon030/capstone-project/pull/1): demo를 보존된 연구 기준과 비교한다. 병합 여부는 미합의이며 댓글·diff 검토에 사용한다.
- 기찬님 작업: [팀 PR #1 — Add Mindustry LLM agent integration](https://github.com/time-to-think/mindustry/pull/1), `qrc4723/mindustry:feature/mindustry-llm-agent`, 확인 head `c4b068829cf8c96f3a8f7c20e24748e85763fe07`. 아직 열린 PR이며 팀 `develop`에 병합된 것으로 취급하지 않는다.

## 실제로 다른 부분

| 항목 | 이 저장소의 전투 demo | 기찬님 PR #1의 integration |
|---|---|---|
| 코드 형태 | Mindustry v159.7 Java plugin + Python runner | Mindustry engine fork의 `integrations/mindustry-llm-agent` |
| API | `/state`, `/action`; demo `/duel/state`, `/duel/action`, `/duel/control` | `/v1/state`, `/v1/action` |
| 판단 시간 | 같은 paused snapshot에서 두 모델 판단 후 advance/re-observe | 게임이 계속 흐르며 각 프로세스 응답 즉시 적용 |
| 모델 | 로컬 DeepSeek Coder 6.7B / GLM-Edge 4B; 기존 연구 Qwen 경로 별도 보존 | README 기준 cloud GLM / DeepSeek |
| 건설·생산 | 정상 BuildPlan/builder 이동·건설, 정상 factory 생산, 경기 중 unloader 공급 | RTS 모드의 비용·시간 기반 건설/훈련 queue와 완료 시 배치·생성 |
| 경기 판정 | 현재 full match는 `DRAW_FIGHTERS`, native `gameOver=false` | README 기준 Core 파괴 승리; 거점은 보너스 |
| 검증 | 이번 세션 Python 121/121; 10/07 실제 headless 증거는 과거 기록 | PR의 테스트·빌드 기록 및 현재 CI 성공; 여기서 실제 실행하지 않음 |

기찬님 방식의 tile 배치/유닛 생성은 이 저장소의 정상 게임 실행 계약과 다르다. 합의 없이 executor를 가져오거나 두 결과를 같은 실험 조건으로 비교하지 않는다. CI의 엔진 테스트·desktop build 성공도 integration의 Python 테스트나 실제 경기 성공을 대신하지 않는다.

## 먼저 실행·검토할 순서

접근 권한이 있는 계정으로 clone한다. 터미널은 `3번 AGENT / TEST`를 사용한다.

```sh
git clone https://github.com/Laon030/capstone-project.git
cd capstone-project
git switch codex/weekend-duel-demo
python3.13 -m venv .venv
.venv/bin/python -m pip install --no-index -r requirements-dev.txt
.venv/bin/python scripts/check_environment.py --python-only
.venv/bin/python -m unittest discover -s tests -q
```

- 기준 Python은 **3.13.5**, Java는 **17**, 게임은 **v159.7**이다. 단위 테스트에는 서버·모델이 필요 없다.
- 먼저 [현재 API](AGENTBRIDGE_API.md), [전투 demo](DUEL_DEMO.md), [진행 기록](PROGRESS.md), [연구 재현성](REPRODUCIBILITY.md)을 읽는다. 연구 검토는 별도 checkout의 `stage4-agent`에서 진행한다.
- `scripts/duel_demo.py`의 Java/server 경로는 현재 개발자 macOS 환경의 절대 경로다. 다른 컴퓨터에서 그대로 실행된다고 보장하지 않는다. 서버 JAR·모델·fixture와 경로 준비를 확인한 뒤 각자 환경의 실행 절차를 정한다.
- 실제 게임은 HTTP `127.0.0.1:8765`, 게임 `6567`을 사용한다. 기존 실행과 포트가 겹치지 않게 한다. `1번 SERVER`, `2번 CLIENT`, `3번 AGENT / TEST`로 구분하고 참조 게임 소스는 수정하지 않는다.
- 공유 Git에는 credential, 모델 가중치, server JAR, save, 원본 runtime 로그를 추가하지 않는다. 필요한 증거는 검토한 작은 발췌·hash·환경 정보를 별도로 준비한다.

## 협의해서 정할 최소 항목

1. **이번 목표:** 정상 vanilla 메커니즘을 입증하는 시연인가, RTS 규칙을 정의한 시연인가? 연구 평가 조건은 시연과 분리한다.
2. **공통 계약:** 관측 tick/world/team, action 접수/실행/완료/실패의 구분, timeout·승패 정의를 먼저 맞춘다. API를 통일하기 전에는 각자의 runner로 실행한다.
3. **검토 결과:** 각자 실행한 commit·환경·명령, 예상/실제 결과, 미검증 GUI·Core 승패 등을 기록한다. 단순 HTTP 200은 건설 완료 증거가 아니다.
4. **작은 분담 제안:** 승준은 정상 실행·completion/실패 증거와 최신 GUI 확인을, 기찬님은 RTS terrain/capture·전술 loop와 로그를 담당하고 상대 계약/API를 교차 검토한다. 실제 분담은 대화에서 정한다.
5. **다음 구현:** 각자 한 가지 작은 변경을 자신의 feature branch에서 구현하고 먼저 PR로 검토한다. 현재 demo의 upgrade/capture는 미시작이며 이번 안내가 구현 착수 승인을 뜻하지 않는다.

## 팀 Git 사용 규칙

기찬님 feature branch의 [AGENTS.md](https://github.com/qrc4723/mindustry/blob/feature/mindustry-llm-agent/AGENTS.md)를 확인했다. 엔진 작업은 개인 engine fork를 `origin`, `time-to-think/mindustry`를 `upstream`, Anuken을 읽기 전용 `canonical`로 두고, 최신 팀 `develop`에서 `feature/<topic>`를 만들어 English commit → 개인 fork push → 팀 `develop` 대상 PR 순서로 진행한다. 팀 `develop` 직접 push와 shared branch force push는 하지 않는다.

이 저장소는 **플러그인 저장소**이며 현재 `upstream`은 `Anuken/MindustryPluginTemplate`이다. 이를 팀 engine 저장소로 바꾸거나 별개의 Git history를 그대로 병합하지 않는다. 엔진 통합이 합의되면 별도 개인 engine fork/checkout에서 작은 adapter 또는 필요한 파일만 검토하여 PR로 제안한다. 이번 개인 저장소 backup은 팀 merge가 아니다.

## DM 초안

> 기찬님, Mindustry 작업 서로 한번 검토해보면 좋을 것 같아서 제 진행분을 개인 GitHub에 정리했어요. 연구 기준은 `stage4-agent`, 전투 시연은 `codex/weekend-duel-demo`에 나눠뒀고, 실행 방법과 검증/미검증 항목도 적어뒀습니다.
>
> 저장소: https://github.com/Laon030/capstone-project
> 검토 안내: https://github.com/Laon030/capstone-project/blob/codex/weekend-duel-demo/docs/TEAM_REVIEW.md
> 검토 PR: https://github.com/Laon030/capstone-project/pull/1
>
> 기찬님 PR #1도 확인했는데, 제 쪽은 정상 게임 건설·공장 생산 기반이고 기찬님 쪽은 실시간 RTS queue 방식이라, 우선 이번 시연에서 사용할 규칙과 action 완료/승패 기준을 맞추면 좋겠어요. 각자 코드를 먼저 실행해보고 작은 변경 단위로 서로 리뷰하는 방식은 어떨까요?
>
> 저는 정상 실행·완료/실패 관측과 GUI 확인 쪽, 기찬님은 terrain/capture·전술 loop 쪽을 맡는 안을 생각했는데 기찬님 의견이 궁금합니다. 제 저장소가 비공개라 접근 권한부터 준비할게요.

이 문서는 DM 초안이며 발송 기록이 아니다. 저장소 접근 권한이 준비된 뒤 링크를 전달한다.
