# Repository layout

`mindustry-lab` owns the capstone agent, bridge plugin, experiments, tests, and
documentation. The `mindustry/` directory is a Git submodule of
[`time-to-think/mindustry`](https://github.com/time-to-think/mindustry), pinned to
a reviewed commit on its `develop` branch. Generated game binaries and local
run logs do not belong in either repository.

Clone both repositories with:

```sh
git clone --recurse-submodules https://github.com/time-to-think/mindustry-lab.git
```

For an existing clone, run `git submodule update --init --recursive`.

Change the Mindustry game source in a personal fork of `time-to-think/mindustry`
and open a pull request into its `develop` branch. After that change is merged,
update the `mindustry/` submodule pointer in a separate `mindustry-lab` pull
request. Agent logic, bridge-plugin code, training, and evaluation changes go
directly through `mindustry-lab` pull requests.

The current bridge build and local server scripts still target the official
Mindustry v159.7 release. Adding the submodule does not switch their runtime or
dependency version. Align and test those versions before running the bridge
against a different game build.
