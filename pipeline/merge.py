"""Combine the triage calls with the two verifier lenses into one final row per issue.

For each checked call (fixed / duplicate / security) the two verdicts give a status:
  confirmed   - both lenses say supported
  likely      - one says supported, the other uncertain
  rejected    - at least one lens refuted it
  unverified  - neither lens supported it (both uncertain)

Only confirmed or likely "already fixed" and "duplicate" calls count as closable.
A rejected call takes the refuting verifier's suggested disposition (or valid_bug).
"""
import csv, glob, json, os

SEVERITY_ORDER = ["none", "S3_low", "S2_medium", "S1_high", "S0_critical"]

sample = {s["number"]: s for s in json.load(open("data/sample.json"))["sample"]}
meta = json.load(open("data/batch_meta.json"))["issues"]
open_issues = {}
for line in open("data/raw/open.jsonl"):
    i = json.loads(line)
    open_issues[i["number"]] = i

triage = {}
for path in sorted(glob.glob("data/out/triage/b*.json")):
    for r in json.load(open(path))["results"]:
        triage[r["number"]] = r

verdicts = {}  # (number, kind) -> {"A": result, "B": result}
for path in sorted(glob.glob("data/out/verify/v*.json")):
    for v in json.load(open(path))["results"]:
        number, kind, lens = v["claim_id"].split("-")
        verdicts.setdefault((int(number), kind), {})[lens] = v


def status(pair):
    got = [pair.get("A", {}).get("verdict"), pair.get("B", {}).get("verdict")]
    if "refuted" in got:
        return "rejected"
    if got.count("supported") == 2:
        return "confirmed"
    if "supported" in got:
        return "likely"
    return "unverified"


def refuter(pair):
    """The first lens that refuted the call (lens A before lens B)."""
    for lens in ("A", "B"):
        if pair.get(lens, {}).get("verdict") == "refuted":
            return pair[lens]
    return None


rows = []
for number, r in sorted(triage.items()):
    row = dict(r)
    row["security_relevant"] = r["security"]["relevant"]
    row["security_type"] = r["security"]["type"]
    row["security_why"] = r["security"]["why"]
    del row["security"]
    row["triage_disposition"] = r["disposition"]
    row["triage_severity"] = r["severity"]
    row["checks"] = {}

    kind = {"already_fixed": "fixed", "duplicate": "duplicate"}.get(r["disposition"])
    if kind and (number, kind) in verdicts:
        pair = verdicts[(number, kind)]
        row["checks"][kind] = {"status": status(pair), "A": pair.get("A", {}).get("reason"), "B": pair.get("B", {}).get("reason")}
        if status(pair) == "rejected":
            fix = refuter(pair)["corrected_disposition"]
            row["disposition"] = fix if fix not in ("keep", r["disposition"]) else "valid_bug"
            if row["disposition"] != "duplicate":
                row["duplicate_of"] = None
            if row["disposition"] != "already_fixed":
                row["fixed_in"] = None

    if (number, "security") in verdicts:
        pair = verdicts[(number, "security")]
        s = status(pair)
        row["checks"]["security"] = {"status": s, "A": pair.get("A", {}).get("reason"), "B": pair.get("B", {}).get("reason")}
        if s == "rejected":
            corrected = refuter(pair)["corrected_severity"]
            if corrected == "keep":  # refuted but no new level given: step down one
                corrected = SEVERITY_ORDER[max(0, SEVERITY_ORDER.index(r["severity"]) - 1)]
            row["severity"] = corrected
    # A security call counts only if neither verifier refuted it.
    row["security_verified"] = row["checks"].get("security", {}).get("status") in ("confirmed", "likely")

    row["closable"] = (row["disposition"] in ("already_fixed", "duplicate")
                       and row["checks"].get(kind or "", {}).get("status") in ("confirmed", "likely"))
    i = open_issues[number]
    row.update({
        "title": i["title"], "url": f"https://github.com/anthropics/claude-code/issues/{number}",
        "opened": i["created_at"][:10], "last_activity": i["updated_at"][:10], "upvotes": i["thumbs"] or 0,
        "comments": i["comments"], "labels": i["labels"],
        "stratum": sample[number]["stratum"], "weight": sample[number]["weight"],
        "reported_version": meta[str(number)]["reported_version"], "version_source": meta[str(number)]["version_source"],
    })
    rows.append(row)

# Full rows stay local. The published rows drop the pipeline's notes on open security reports
# (repro hints for bypasses and leaks), keeping only the title, the link and the call.
SENSITIVE = {"credential_exposure", "permission_bypass", "sandbox_escape", "prompt_injection",
             "data_exfiltration_privacy", "supply_chain", "other"}


def public(row):
    if not (row["security_relevant"] and row["security_type"] in SENSITIVE):
        return row
    out = dict(row, summary="Security report. Details withheld here; see the issue.", evidence="",
               next_action="Route to the security team.", security_why="")
    out["checks"] = {k: {"status": c["status"], "A": None, "B": None} for k, c in row["checks"].items()}
    return out


os.makedirs("data/private", exist_ok=True)
with open("data/private/triage-1000-full.jsonl", "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")
rows = [public(row) for row in rows]
with open("data/triage-1000.jsonl", "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

columns = ["number", "title", "url", "stratum", "weight", "opened", "last_activity", "upvotes", "comments",
           "reported_version", "kind", "area", "platform", "disposition", "triage_disposition", "closable",
           "duplicate_of", "fixed_in", "severity", "triage_severity", "security_relevant", "security_verified", "security_type",
           "confidence", "has_repro", "regression", "injection_attempt", "summary", "evidence", "next_action"]
with open("data/triage-1000.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

print(len(rows), "rows;", sum(r["closable"] for r in rows), "closable;",
      sum(1 for r in rows for c in r["checks"].values() if c["status"] == "rejected"), "calls rejected by verifiers")
