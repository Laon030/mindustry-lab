# Repository workflow

This repository contains the standalone Mindustry LLM RTS agent integration.

## Branches and remotes

- `origin`: the contributor's personal fork; feature branches are pushed here.
- `upstream`: `time-to-think/mindustry-llm-agent`; pull requests and issues belong here.

Do not push directly to `upstream`. Create feature branches from the current
`upstream/develop`, use English commit messages, push to the personal fork, and
open pull requests into `time-to-think/mindustry-llm-agent:develop`.

Do not develop directly on `develop`, rewrite shared branch history, or
force-push shared branches.

## Repository contents

Commit source code, tests, scripts, and documentation only. Do not commit
generated builds, Gradle caches, local model/runtime data, run logs,
credentials, environment files, or agent memory.
