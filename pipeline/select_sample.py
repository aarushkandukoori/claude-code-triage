"""Pick the 1,000 issues to triage, in three groups (strata).

  top      - the 150 most-upvoted open issues (all of them)
  security - a random 250 of the open issues that look security-ish
             (label area:security or data-loss, or a security word in the title)
  rest     - a random 600 of everything else

Each issue gets a weight = (issues in its group) / (issues we picked from that group),
so the 1,000 can be scaled back up to estimate the whole backlog.
"""
import json, random, re

SEED = 20261106
N_TOP, N_SEC, N_REST = 150, 250, 600

SEC_LABELS = {"area:security", "data-loss"}
SEC_WORDS = re.compile(
    r"\b(security|vulnerab\w*|cve|credential\w*|secrets?|api[ -]?keys?|tokens? (?:leak|expos)\w*|leak\w*|privacy|"
    r"private data|exfiltrat\w*|prompt[- ]injection|injection|bypass\w*|deny rules?|denylist|sandbox escape|"
    r"escap\w+ (?:the )?sandbox|rm -rf|deleted|deletes|deleting|data loss|lost (?:my|all|work|data|files)|wiped|"
    r"destroy\w*|overwr\w+|force[- ]push\w*|git reset --hard|malicious|unauthori[sz]ed|"
    r"without (?:permission|consent|asking|approval)|email address\w*|user-agent|telemetry)\b", re.I)

def looks_security(issue):
    return bool(SEC_LABELS & set(issue["labels"])) or bool(SEC_WORDS.search(issue["title"] or ""))

issues = [json.loads(line) for line in open("data/raw/open.jsonl")]
by_thumbs = sorted(issues, key=lambda i: (-(i["thumbs"] or 0), i["number"]))
top = by_thumbs[:N_TOP]
top_ids = {i["number"] for i in top}
security = [i for i in issues if i["number"] not in top_ids and looks_security(i)]
rest = [i for i in issues if i["number"] not in top_ids and not looks_security(i)]

rng = random.Random(SEED)
picked = {
    "top": top,
    "security": rng.sample(sorted(security, key=lambda i: i["number"]), N_SEC),
    "rest": rng.sample(sorted(rest, key=lambda i: i["number"]), N_REST),
}
sizes = {"top": len(top), "security": len(security), "rest": len(rest)}

sample = []
for stratum, group in picked.items():
    weight = sizes[stratum] / len(group)
    for i in group:
        sample.append({"number": i["number"], "stratum": stratum, "weight": weight})
sample.sort(key=lambda s: s["number"])

json.dump({"seed": SEED, "population": len(issues), "strata_sizes": sizes,
           "picked": {k: len(v) for k, v in picked.items()}, "sample": sample},
          open("data/sample.json", "w"), indent=1)
print(sizes, {k: len(v) for k, v in picked.items()}, len(sample))
