"""One-command v159.7 duel demo: server, finite supply, two local LLMs, combat.

Run from the repository: python3 scripts/duel_demo.py
Use --headless for a self-contained runtime check without a CLIENT.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from duel.auto_match import AUTO_MODELS, match_exit_code, run_match  # noqa: E402
from duel.coordinator import DuelBridge, DuelCoordinator  # noqa: E402
from duel.unified import UnifiedOllamaProvider  # noqa: E402


JAVA_HOME = Path(os.environ.get(
    "JAVA_HOME", "/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home"
)).expanduser().resolve()
SERVER_JAR = Path(os.environ.get(
    "AGENTBRIDGE_SERVER_JAR", "/Users/andrew/capstone/MindustryServer/server-release.jar"
)).expanduser().resolve()
BRIDGE_JAR = ROOT / "build/libs/MindustryAgentBridge.jar"
FIXTURES = ("duel_gate5_fixture.console", "duel_gate6_inmatch_supply.console",
            "duel_event_listeners.console")
BASE = "http://127.0.0.1:8765"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def listening(port):
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def get_json(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def wait_until(predicate, description, server=None, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if server is not None and server.poll() is not None:
            raise RuntimeError(f"1번 SERVER exited during {description}: {server.returncode}")
        try:
            value = predicate()
            if value:
                return value
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for {description}")


def console(server, line):
    if server.poll() is not None:
        raise RuntimeError("1번 SERVER exited")
    server.stdin.write(line + "\n")
    server.stdin.flush()


def clean_log(path):
    return ANSI.sub("", path.read_text(errors="replace"))


def run_fixture(server, log, filename, marker):
    for line in (ROOT / "scripts" / filename).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line.startswith("js "):
            console(server, line)
    wait_until(lambda: marker in clean_log(log), marker, server)


def valid_fixture(state, *, initial=True):
    if ((initial and state.get("tick") != 0)
            or state.get("paused") is not True or state.get("gameOver")):
        return False
    if set(state.get("teams", {})) != {"sharded", "crux"}:
        return False
    for team in state["teams"].values():
        if (len(team["cores"]) != 1 or team["resources"]["copper"] != 0
                or team["economy"]["nearbyCopperOreTiles"] != 25
                or team["economy"]["duoSite"]["status"] != "empty"
                or sum(unit["type"] == "mono" for unit in team["units"]) != 1
                or sum(unit["type"] == "poly" for unit in team["units"]) != 1
                or any(unit["type"] not in ({"mono", "poly"} if initial
                                            else {"mono", "poly", "alpha"})
                       for unit in team["units"])):
            return False
        factory = team["production"]["factory"]
        supply = factory.get("supply", {})
        if (factory["status"] != "idle"
                or factory["stock"] != {"silicon": 0, "lead": 0}
                or supply.get("routeReady") is not True
                or supply.get("stock") != {"silicon": 10, "lead": 10}):
            return False
    return True


def client_connected(server, log):
    before = clean_log(log).count("Players:")
    console(server, "players")
    def players():
        lines = [line for line in clean_log(log).splitlines() if "Players:" in line]
        if len(lines) <= before:
            return False
        return bool(re.search(r"Players:\s*[1-9]", lines[-1]))
    return wait_until(players, "CLIENT player count", server, seconds=3)


def stop_owned_server(server):
    if server.poll() is None:
        try:
            console(server, "exit")
            server.wait(timeout=5)
        except (BrokenPipeError, TimeoutError, subprocess.TimeoutExpired):
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


def wait_for_client_inspection():
    try:
        input("1번 SERVER: CLIENT에서 결과를 본 뒤 Enter를 누르면 서버를 종료합니다. ")
    except EOFError:
        print(f"1번 SERVER: 입력 채널이 없어 서버를 유지합니다. 종료: kill -INT {os.getpid()}",
              flush=True)
        while True:
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true",
                        help="start the match immediately and stop the owned server afterward")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--client-timeout", type=int, default=600)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 20 or args.client_timeout < 1:
        parser.error("rounds must be 1-20 and client-timeout must be positive")
    if not JAVA_HOME.joinpath("bin/java").is_file() or not SERVER_JAR.is_file():
        parser.error("Java 17 or v159.7 server JAR is missing; set JAVA_HOME and AGENTBRIDGE_SERVER_JAR")
    if listening(6567) or listening(8765):
        parser.error("6567/8765 is already in use; stop the existing 1번 SERVER first")
    if not listening(11434):
        parser.error("Local Ollama is not listening on 127.0.0.1:11434")
    available = {model["name"] for model in get_json("http://127.0.0.1:11434/api/tags")["models"]}
    if not set(AUTO_MODELS.values()) <= available:
        parser.error(f"Missing local Ollama models: {set(AUTO_MODELS.values()) - available}")

    run_dir = ROOT / "build/duel-runs" / (time.strftime("one-command-%Y%m%d-%H%M%S-")
                                          + uuid4().hex[:6])
    run_dir.mkdir(parents=True)
    if not args.skip_build:
        print("3번 AGENT / TEST: Java 17 JAR build", flush=True)
        environment = {**os.environ, "JAVA_HOME": str(JAVA_HOME)}
        with (run_dir / "build.log").open("w") as output:
            build = subprocess.run(["./gradlew", "jar", "--offline"], cwd=ROOT,
                                   env=environment, stdout=output, stderr=subprocess.STDOUT)
        if build.returncode:
            raise RuntimeError(f"JAR build failed: {run_dir / 'build.log'}")
    if not BRIDGE_JAR.is_file():
        raise FileNotFoundError(BRIDGE_JAR)

    runtime = run_dir / "runtime"
    (runtime / "config/mods").mkdir(parents=True)
    (runtime / "home").mkdir()
    shutil.copy2(BRIDGE_JAR, runtime / "config/mods/MindustryAgentBridge.jar")
    server_log = run_dir / "server.log"
    server = None
    try:
        with server_log.open("w") as output:
            server = subprocess.Popen(
                [str(JAVA_HOME / "bin/java"), f"-Duser.home={runtime / 'home'}",
                 "-jar", str(SERVER_JAR)], cwd=runtime, stdin=subprocess.PIPE,
                stdout=output, stderr=subprocess.STDOUT, text=True, bufsize=1)
            print(f"1번 SERVER: {server_log}", flush=True)
            wait_until(lambda: listening(8765), "AgentBridge listener", server, seconds=45)
            for line in ("config autoPause off", "config allowCustomClients true",
                         "host Islands sandbox", "pause on"):
                console(server, line)
            wait_until(lambda: listening(6567), "game port 6567", server, seconds=45)
            run_fixture(server, server_log, FIXTURES[0], "G5_READY")
            run_fixture(server, server_log, FIXTURES[1], "DEMO_SUPPLY_READY team=crux")
            run_fixture(server, server_log, FIXTURES[2], "DEMO_COMBAT_LISTENERS_READY")
            state = wait_until(lambda: (state if valid_fixture(state) else None)
                               if (state := get_json(BASE + "/duel/state")) else None,
                               "paused two-team finite-supply fixture", server, seconds=15)
            (run_dir / "initial-state.json").write_text(json.dumps(state, indent=2))
            print(f"1번 SERVER: fixture ready, world={state['worldId']}, tick=0", flush=True)
            if not args.headless:
                print("2번 CLIENT: v159.7 CLIENT에서 127.0.0.1:6567 접속; 접속 확인 후 자동 시작", flush=True)
                wait_until(lambda: client_connected(server, server_log),
                           "v159.7 CLIENT connection", server, seconds=args.client_timeout)
                joined = get_json(BASE + "/duel/state")
                (run_dir / "post-client-state.json").write_text(json.dumps(joined, indent=2))
                if joined.get("worldId") != state["worldId"] or not valid_fixture(joined, initial=False):
                    raise RuntimeError("Fixture changed before CLIENT was ready")
            print("3번 AGENT / TEST: DeepSeek vs GLM autonomous match", flush=True)
            coordinator = DuelCoordinator(DuelBridge(), AUTO_MODELS["A"], AUTO_MODELS["B"])
            providers = {side: UnifiedOllamaProvider(model) for side, model in AUTO_MODELS.items()}
            result = run_match(coordinator, providers, log=run_dir / "match.jsonl",
                               max_rounds=args.rounds)
            final = get_json(BASE + "/duel/state")
            (run_dir / "final-state.json").write_text(json.dumps(final, indent=2))
            (run_dir / "result.json").write_text(json.dumps({"result": result,
                "worldId": state["worldId"], "bridgeJarSha256": sha256(BRIDGE_JAR),
                "fixtures": {name: sha256(ROOT / "scripts" / name) for name in FIXTURES}}, indent=2))
            print(f"3번 AGENT / TEST: {result['result']}, evidence={run_dir}", flush=True)
            if not args.headless:
                wait_for_client_inspection()
            return match_exit_code(result)
    finally:
        if server is not None:
            stop_owned_server(server)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f"시연 준비/실행 실패: {error}", file=sys.stderr)
        raise SystemExit(1)
