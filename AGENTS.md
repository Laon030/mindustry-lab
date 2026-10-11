# Repository workflow

This repository contains the standalone Mindustry LLM RTS agent integration.

## Branches and remotes

- `origin`: the contributor's personal fork; feature branches are pushed here.
- `upstream`: `time-to-think/mindustry-lab`; pull requests and issues belong here.

Do not push directly to `upstream`. Create feature branches from the current
`upstream/develop`, use English commit messages, push to the personal fork, and
open pull requests into `time-to-think/mindustry-lab:develop`.

Do not develop directly on `develop`, rewrite shared branch history, or
force-push shared branches.

## Repository contents

Commit source code, tests, scripts, and documentation only. Do not commit
generated builds, Gradle caches, local model/runtime data, run logs,
credentials, environment files, or agent memory.

## Game and AgentBridge layout

- `game/` is a Git submodule of `time-to-think/mindustry`, pinned to tag
  `v159.7` (commit `c9686eb5d0ae5dd47ee02c40f99f7d5018ccbc8c`).
  Preserve this API baseline; updating the game revision needs compatibility checks.
- `agentbridge/` contains the separate AgentBridge research and duel package.
  Follow its `AGENTS.md` when working there.
- Existing `plugin/`, `client-plugin/`, `mindustry_agent/` and their builds remain
  independent. Do not combine the runtimes without checking their action and
  timing contracts. Both use port 8765, so run only one bridge at a time.
- Read `docs/AGENTBRIDGE_HANDOFF.md` for clone, test, build and review steps.
- Do not develop or push from the game submodule as part of the lab workflow.
  Engine changes use the separate personal engine fork and a team engine PR.
