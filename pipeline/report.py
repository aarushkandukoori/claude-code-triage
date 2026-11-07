"""Two lists a maintainer could act on: issues to close now, and serious bugs at risk of being closed for silence."""
import json, re

rows = [json.loads(l) for l in open("data/triage-1000.jsonl")]
open_issues = {}
for line in open("data/raw/open.jsonl"):
    i = json.loads(line)
    open_issues[i["number"]] = i
CUTOFF = "2026-10-24T10:06:00Z"  # 14 days before the next sweep run (Nov 7, 10:06 UTC)


def cell(text):
    return (text or "").replace("|", "\\|").replace("\n", " ")


def link(n):
    return f"[#{n}](https://github.com/anthropics/claude-code/issues/{n})"


def vkey(v):
    """Sort CLI versions numerically; anything else (e.g. a desktop app version) goes last."""
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else (9999,)


closable = [r for r in rows if r["closable"]]
fixed = sorted((r for r in closable if r["disposition"] == "already_fixed"), key=lambda r: (vkey(r["fixed_in"]), r["number"]))
dups = sorted((r for r in closable if r["disposition"] == "duplicate"), key=lambda r: (r["duplicate_of"], r["number"]))

lines = [
    "# Issues that can be closed now",
    "",
    f"{len(closable)} of the 1,000 triaged issues. Each call was made by one reader and then checked by two separate readers",
    "(one checking the evidence, one trying to prove it wrong). \"confirmed\" means both agreed; \"likely\" means one agreed",
    "and the other was unsure. Snapshot: evening of Nov 6, 2026.",
    "",
    f"## Already fixed in a later release ({len(fixed)})",
    "",
    "| Issue | Title | Fixed in | Evidence | Check |",
    "|---|---|---|---|---|",
]
lines += [f"| {link(r['number'])} | {cell(r['title'])} | {r['fixed_in']} | {cell(r['evidence'])} | {r['checks']['fixed']['status']} |"
          for r in fixed]
lines += ["", f"## Duplicates ({len(dups)})", "", "| Issue | Title | Duplicate of | Evidence | Check |", "|---|---|---|---|---|"]
lines += [f"| {link(r['number'])} | {cell(r['title'])} | {link(r['duplicate_of'])} | {cell(r['evidence'])} | {r['checks']['duplicate']['status']} |"
          for r in dups]
open("report/closable.md", "w").write("\n".join(lines) + "\n")

# Serious bugs and where they stand with the stale sweep.
def sweep_status(n):
    i = open_issues[n]
    if "stale" in i["labels"] or "autoclose" in i["labels"]:
        return "labeled stale now"
    if i["assignees"] or i.get("locked") or (i["thumbs"] or 0) >= 10:
        return "protected"
    return "next for a working sweep" if i["updated_at"] < CUTOFF else "active"

serious = [r for r in rows if r["severity"] in ("S0_critical", "S1_high")
           and r["disposition"] in ("valid_bug", "needs_info", "stale_unclear")
           and (r["checks"].get("security", {}).get("status") != "rejected")]
order = {"labeled stale now": 0, "next for a working sweep": 1, "active": 2, "protected": 3}
serious.sort(key=lambda r: (order[sweep_status(r["number"])], r["severity"] != "S0_critical", -r["upvotes"]))
lines = [
    "# Serious bugs and the stale sweep",
    "",
    f"{len(serious)} issues from the sample rated high or critical that are still open bugs. \"labeled stale now\" will be",
    "closed in 14 days unless someone comments. \"next for a working sweep\" has been quiet for 14+ days and would be",
    "labeled by a sweep that could reach it. \"protected\" has 10+ upvotes or an assignee.",
    "",
    "| Issue | Severity | Sweep status | Upvotes | Summary |",
    "|---|---|---|---|---|",
]
lines += [f"| {link(r['number'])} | {r['severity'].split('_')[0]} | {sweep_status(r['number'])} | {r['upvotes']} | {cell(r['summary'])} |"
          for r in serious]
open("report/serious-bugs.md", "w").write("\n".join(lines) + "\n")
from collections import Counter
print(len(fixed), "fixed,", len(dups), "duplicates;", len(serious), "serious:", Counter(sweep_status(r["number"]) for r in serious))
