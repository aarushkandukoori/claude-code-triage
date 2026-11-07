"""Fetch the comment threads for the sampled issues (first 100 + last 100 when longer)."""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

OPEN = {json.loads(l)["number"]: json.loads(l) for l in open("data/raw/open.jsonl")}
sample = json.load(open("data/sample.json"))["sample"]
FIELDS = '[.[] | {user: .user.login, type: .user.type, assoc: .author_association, created_at, body}]'

def get(path):
    for _ in range(5):
        r = subprocess.run(["gh", "api", path, "--jq", FIELDS], capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
    print("FAILED", path, r.stderr[:200], file=sys.stderr)
    return []

def comments(number):
    n = OPEN[number]["comments"]
    if n == 0:
        return number, []
    first = get(f"repos/anthropics/claude-code/issues/{number}/comments?per_page=100&page=1")
    if n > 100:
        last_page = (n + 99) // 100
        tail = get(f"repos/anthropics/claude-code/issues/{number}/comments?per_page=100&page={last_page}")
        seen = {(c["user"], c["created_at"]) for c in first}
        first += [c for c in tail if (c["user"], c["created_at"]) not in seen]
    return number, first

with ThreadPoolExecutor(8) as pool:
    out = dict(pool.map(comments, [s["number"] for s in sample]))
json.dump(out, open("data/raw/comments.json", "w"))
print(len(out), "issues,", sum(len(v) for v in out.values()), "comments")
