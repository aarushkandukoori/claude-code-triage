"""Run sandboxed Claude readers over batch files, several at a time.

Each reader is a headless `claude -p` session that can only Read/Grep/Glob inside
data/reader (no shell, no web, no MCP, no settings files, permission prompts denied).
It gets one batch in its prompt and must answer in a fixed JSON shape.

    python3 pipeline/run_readers.py triage            # all triage batches
    python3 pipeline/run_readers.py verify            # all verify batches
    python3 pipeline/run_readers.py triage b000 b001  # just these
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READER_DIR = os.path.join(ROOT, "data", "reader")
# CLAUDE_BIN overrides; otherwise use the account-failover wrapper when it exists, else `claude` on PATH.
_WRAPPER = os.path.expanduser("~/Projects/claude-failover/bin/claude-failover")
CLAUDE = os.environ.get("CLAUDE_BIN") or (_WRAPPER if os.path.exists(_WRAPPER) else "claude")
WORKERS = 6
MODEL = "claude-opus-5-5"

ENUMS = {
    "kind": ["bug", "feature_request", "question", "docs", "not_claude_code", "spam_or_empty"],
    "area": ["tui", "cli", "permissions", "sandbox", "hooks", "mcp", "plugins_skills", "agents_subagents",
             "ide_extensions", "desktop_app", "web_cloud", "auth_account", "cost_usage_limits", "model_behavior",
             "tools_bash_edit", "git_github", "installation_update", "networking_proxy", "performance_memory",
             "windows_wsl", "api_providers", "settings_config", "context_memory", "other"],
    "platform": ["macos", "windows", "linux", "wsl", "all", "unknown"],
    "severity": ["S0_critical", "S1_high", "S2_medium", "S3_low", "none"],
    "security_type": ["none", "credential_exposure", "permission_bypass", "sandbox_escape", "prompt_injection",
                      "data_exfiltration_privacy", "destructive_action", "supply_chain", "other"],
    "disposition": ["already_fixed", "duplicate", "needs_info", "valid_bug", "feature_request",
                    "not_actionable", "stale_unclear"],
    "confidence": ["high", "medium", "low"],
}

TRIAGE_ITEM = {
    "type": "object",
    "properties": {
        "number": {"type": "integer"},
        "summary": {"type": "string"},
        "kind": {"type": "string", "enum": ENUMS["kind"]},
        "area": {"type": "string", "enum": ENUMS["area"]},
        "platform": {"type": "string", "enum": ENUMS["platform"]},
        "severity": {"type": "string", "enum": ENUMS["severity"]},
        "security": {"type": "object", "properties": {
            "relevant": {"type": "boolean"},
            "type": {"type": "string", "enum": ENUMS["security_type"]},
            "why": {"type": "string"}}, "required": ["relevant", "type", "why"]},
        "has_repro": {"type": "boolean"},
        "regression": {"type": "boolean"},
        "disposition": {"type": "string", "enum": ENUMS["disposition"]},
        "duplicate_of": {"type": ["integer", "null"]},
        "fixed_in": {"type": ["string", "null"]},
        "evidence": {"type": "string"},
        "confidence": {"type": "string", "enum": ENUMS["confidence"]},
        "next_action": {"type": "string"},
        "injection_attempt": {"type": "boolean"},
    },
    "required": ["number", "summary", "kind", "area", "platform", "severity", "security", "has_repro", "regression",
                 "disposition", "duplicate_of", "fixed_in", "evidence", "confidence", "next_action", "injection_attempt"],
}

VERIFY_ITEM = {
    "type": "object",
    "properties": {
        "claim_id": {"type": "string"},
        "verdict": {"type": "string", "enum": ["supported", "refuted", "uncertain"]},
        "reason": {"type": "string"},
        "corrected_disposition": {"type": "string", "enum": ENUMS["disposition"] + ["keep"]},
        "corrected_severity": {"type": "string", "enum": ENUMS["severity"] + ["keep"]},
    },
    "required": ["claim_id", "verdict", "reason", "corrected_disposition", "corrected_severity"],
}

STAGES = {
    "triage": {"prompt": "triage.md", "batches": "batches", "out": "triage",
               "schema": {"type": "object", "properties": {"results": {"type": "array", "items": TRIAGE_ITEM}},
                          "required": ["results"]}},
    "verify": {"prompt": "verify.md", "batches": "verify", "out": "verify",
               "schema": {"type": "object", "properties": {"results": {"type": "array", "items": VERIFY_ITEM}},
                          "required": ["results"]}},
}


def expected_ids(stage, text):
    import re
    if stage == "triage":
        return [int(n) for n in re.findall(r"^## Issue #(\d+):", text, re.M)]
    return re.findall(r"^### Claim (\S+)", text, re.M)


def run_one(stage, name):
    cfg = STAGES[stage]
    out_path = os.path.join(ROOT, "data", "out", cfg["out"], name + ".json")
    if os.path.exists(out_path):
        return name, "skip"
    batch = open(os.path.join(READER_DIR, cfg["batches"], name + ".md")).read()
    ids = expected_ids(stage, batch)
    template = open(os.path.join(ROOT, "pipeline", "prompts", cfg["prompt"])).read()
    meta = json.load(open(os.path.join(ROOT, "data", "batch_meta.json")))
    prompt = (template.replace("{today}", date.today().isoformat())
              .replace("{latest}", meta["latest"]).replace("{latest_date}", meta["latest_date"])
              .replace("{count}", str(len(ids))).replace("{batch}", batch))
    cmd = [CLAUDE, "-p", "--model", MODEL, "--restricted", "--strict-mcp-config",
           "--tools", "Read,Grep,Glob", "--permission-mode", "dontAsk", "--no-session-persistence",
           "--output-format", "json", "--json-schema", json.dumps(cfg["schema"])]
    for attempt in range(1, 4):
        t0 = time.time()
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=READER_DIR, timeout=3600)
        try:
            d = json.loads(r.stdout)
            results = d["structured_output"]["results"]
            got = [x["number"] if stage == "triage" else x["claim_id"] for x in results]
            if sorted(map(str, got)) != sorted(map(str, ids)):
                raise ValueError(f"ids mismatch: missing {set(map(str, ids)) - set(map(str, got))}")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            json.dump({"batch": name, "results": results, "cost_usd": d.get("total_cost_usd"),
                       "turns": d.get("num_turns"), "seconds": round(time.time() - t0),
                       "denials": d.get("permission_denials")}, open(out_path, "w"), indent=1)
            return name, f"ok in {round(time.time() - t0)}s, {d.get('num_turns')} turns"
        except Exception as e:  # bad JSON, error result, or wrong ids: try again
            err = f"attempt {attempt}: {type(e).__name__}: {str(e)[:200]} | stderr: {r.stderr[-300:]} | stdout: {r.stdout[-300:]}"
            print(f"[{name}] {err}", flush=True)
            time.sleep(20 * attempt)
    return name, "FAILED"


if __name__ == "__main__":
    stage = sys.argv[1]
    names = sys.argv[2:] or sorted(p[:-3] for p in os.listdir(os.path.join(READER_DIR, STAGES[stage]["batches"]))
                                   if p.endswith(".md"))
    print(f"{stage}: {len(names)} batches, {WORKERS} at a time", flush=True)
    done = 0
    with ThreadPoolExecutor(WORKERS) as pool:
        for name, status in pool.map(lambda n: run_one(stage, n), names):
            done += 1
            print(f"[{done}/{len(names)}] {name}: {status}", flush=True)
