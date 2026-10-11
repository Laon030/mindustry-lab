import json
import re
import subprocess
import urllib.request

STATE_URL = "http://127.0.0.1:8765/state"
MODEL = "ollama-cloud/qwen3.5:397b"


def get_state():
    with urllib.request.urlopen(STATE_URL, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


state = get_state()

resources = state.get("resources", {})
copper = resources.get("copper", 0)
lead = resources.get("lead", 0)

prompt = f"""
You are controlling a resource-mining agent in Mindustry.

Current game state:
- copper: {copper}
- lead: {lead}

Available actions:
- mine copper
- mine lead

Choose which resource should be mined next.
Prefer balancing resources by mining the resource with the lower current amount.

Return ONLY valid JSON in exactly this format:
{{"action":"mine","resource":"copper","reason":"short explanation"}}

The resource must be either "copper" or "lead".
"""

print("[OBSERVE]")
print(f"  Copper = {copper}")
print(f"  Lead   = {lead}")

print("\n[ASK LLM]")
print(f"  Model = {MODEL}")

result = subprocess.run(
    ["opencode", "run", "-m", MODEL, prompt],
    capture_output=True,
    text=True,
    timeout=120
)

output = result.stdout

# OpenCode may include status text and Markdown fences.
# Extract the first JSON object from its output.
match = re.search(r'\{.*?\}', output, re.DOTALL)

if not match:
    print("\n[RAW LLM OUTPUT]")
    print(output)
    raise SystemExit("[ERROR] Could not find JSON in LLM response.")

decision = json.loads(match.group(0))

print("\n[LLM DECISION]")
print(json.dumps(decision, indent=2))

print("\n[NOTE]")
print("No game action was executed. This test only checks Mindustry -> Python -> LLM.")
