# Repository workflow

This repository contains the standalone Mindustry LLM RTS agent and training
code. The Mindustry game source is included as a submodule at `mindustry/`.

## Branches and remotes

- `origin`: the contributor's personal fork; feature branches are pushed here.
- `upstream`: `time-to-think/mindustry-lab`; pull requests and issues belong here.

Do not push directly to `upstream`. Create feature branches from the current
`upstream/develop`, use English commit messages, push to the personal fork, and
open pull requests into `time-to-think/mindustry-lab:develop`.

Do not develop directly on `develop`, rewrite shared branch history, or
force-push shared branches.

## Repository contents

Keep the game submodule pointed at a reviewed commit of
`time-to-think/mindustry:develop`. Change the game core in the game repository
and update the submodule pointer here after that change is merged. Keep agent,
plugin, training, and evaluation code in this repository.

Commit source code, tests, scripts, and documentation only. Do not commit
generated builds, Gradle caches, local model/runtime data, run logs,
credentials, environment files, or agent memory.
