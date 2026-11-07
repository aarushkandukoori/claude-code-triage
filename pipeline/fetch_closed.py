"""Pull number/title/close reason/labels for every CLOSED issue (no bodies, to stay small).

GitHub search caps each query at 1,000 results, so we split by creation date
into windows of <= 1,000 closed issues and fetch the windows in parallel.
"""
import json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

OUT = sys.argv[1] if len(sys.argv) > 1 else "data/raw/closed.jsonl"
REPO = "repo:anthropics/claude-code is:issue is:closed"

COUNT_Q = 'query($q: String!) { search(query: $q, type: ISSUE, first: 0) { issueCount } }'
PAGE_Q = """query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { ... on Issue { number title stateReason createdAt closedAt labels(first: 15) { nodes { name } } } }
  }
}"""

def gql(query, **vars):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in vars.items():
        if v is not None:
            args += ["-f", f"{k}={v}"]
    for attempt in range(8):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)["data"]["search"]
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(r.stderr[:300])

def q_for(a, b):
    return f"{REPO} created:{a.isoformat()}..{b.isoformat()}"

def windows(a, b):
    """Split [a, b] into date windows that each hold <= 1,000 closed issues."""
    n = gql(COUNT_Q, q=q_for(a, b))["issueCount"]
    if n <= 1000 or a == b:
        return [(a, b, n)] if n else []
    mid = a + (b - a) // 2
    return windows(a, mid) + windows(mid + timedelta(days=1), b)

def fetch(win):
    a, b, _ = win
    rows, cursor = [], None
    while True:
        p = gql(PAGE_Q, q=q_for(a, b), cursor=cursor)
        for node in p["nodes"]:
            if node:
                node["labels"] = [l["name"] for l in node["labels"]["nodes"]]
                rows.append(node)
        if not p["pageInfo"]["hasNextPage"]:
            return rows
        cursor = p["pageInfo"]["endCursor"]

if __name__ == "__main__":
    wins = windows(date(2025, 1, 1), date.today())
    print(len(wins), "windows,", sum(w[2] for w in wins), "issues expected", flush=True)
    seen = {}
    with ThreadPoolExecutor(6) as pool:
        for rows in pool.map(fetch, wins):
            for r in rows:
                seen[r["number"]] = r
    with open(OUT, "w") as f:
        for n in sorted(seen):
            f.write(json.dumps(seen[n]) + "\n")
    print("done", len(seen), flush=True)
