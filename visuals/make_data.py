"""Write the data files the three widgets read, from the merged triage and the stats."""
import json, os, random, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
import stats  # noqa: E402  (loads data and defines estimate())

rows = stats.rows
OUT = "visuals/data"
os.makedirs(OUT, exist_ok=True)


def group(r):
    if r["closable"]:
        return "close"
    return {"valid_bug": "bug", "already_fixed": "bug", "duplicate": "bug", "feature_request": "feature",
            "needs_info": "ask", "stale_unclear": "ask", "not_actionable": "noact"}[r["disposition"]]


def short(text, limit):
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\s*[\u2014\u2013]\s*", " - ", text)  # the author's no-em-dash rule
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "..."


# --- waffle -----------------------------------------------------------------
waffle = {
    "issues": [{"n": r["number"], "t": r["title"] if len(r["title"]) <= 110 else r["title"][:110].rsplit(" ", 1)[0] + "...", "g": group(r), "d": r["disposition"],
                "sev": r["severity"], "s": r["stratum"], "sum": short(r["summary"], 220),
                "act": short(r["next_action"], 160),
                "chk": next((c["status"] for k, c in r["checks"].items() if k in ("fixed", "duplicate")), None),
                "up": r["upvotes"]} for r in rows],
    "strata": {"top": {"label": "150 most-upvoted", "picked": 150, "of": stats.SIZES["top"]},
               "security": {"label": "security-flavored", "picked": 250, "of": stats.SIZES["security"]},
               "rest": {"label": "random", "picked": 600, "of": stats.SIZES["rest"]}},
    "estimate": {g: stats.estimate(lambda r, g=g: group(r) == g) for g in ("bug", "feature", "close", "ask", "noact")},
    "population": stats.N,
}
json.dump(waffle, open(f"{OUT}/backlog-waffle.json", "w"), ensure_ascii=False)

# --- sweep window --------------------------------------------------------------
CODE = {"10+ upvotes": "up", "assigned": "as", "already stale": "st", "locked": "lk", None: "ok"}
window = [CODE[stats.sweep_skip(i)] for i in stats.window]
sweep = {
    "window": window,
    "counts": {c: window.count(c) for c in ("up", "as", "st", "lk", "ok")},
    "logged_runs": [{"when": "Nov 6, 22:06 UTC", "labeled": 64}, {"when": "Nov 6, 10:06 UTC", "labeled": 71},
                    {"when": "Nov 5, 22:05 UTC", "labeled": 69}],
    "waiting": 8000,  # GitHub search count for the fixed query, Nov 6 2026 20:31 EST (snapshot sim: 8,003)
    "opened_per_day": stats.out["opened_per_day_last30"],
    "going_quiet_per_day": stats.out["going_quiet_per_day"],
    "cap": 300,  # MAX_STALE_LABELS_PER_RUN in the patch
}
json.dump(sweep, open(f"{OUT}/sweep-window.json", "w"))

# --- card deck ------------------------------------------------------------------
PRIVATE = re.compile(r"@|https?://|token|password|secret|api[ _-]?key|sk-|ghp_|\b\d{6,}\b", re.I)


def usable(r):
    text = r["title"] + " " + r["summary"] + " " + r["evidence"]
    return (not r["injection_attempt"] and not r["security_relevant"] and r["severity"] != "S0_critical"
            and len(r["title"]) <= 140 and not PRIVATE.search(text))


def why(r):
    evidence = r["evidence"]
    if r["disposition"] == "already_fixed":
        lead = "" if evidence.startswith(r["fixed_in"] or "?") else f"Fixed in {r['fixed_in']}. "
        return short(lead + evidence, 200)
    if r["disposition"] == "duplicate":
        lead = "" if f"#{r['duplicate_of']}" in evidence[:40] else f"Same problem as #{r['duplicate_of']}. "
        return short(lead + evidence, 200)
    return short(evidence, 200)


def bare_title(r):
    """Titles that are only a template tag, like "[GitHub integration]" or "[FEATURE]"."""
    return re.fullmatch(r"\s*(\[[^\]]*\]\s*)+", r["title"]) is not None


rng = random.Random(11)
deck = []
picks = {
    "close": [r for r in rows if r["closable"] and all(c["status"] == "confirmed" for c in r["checks"].values())],
    "bug": [r for r in rows if r["disposition"] == "valid_bug" and r["confidence"] == "high" and not r["checks"]],
    "feature": [r for r in rows if r["disposition"] == "feature_request" and r["confidence"] == "high"],
    "ask": [r for r in rows if r["disposition"] in ("needs_info", "stale_unclear") and r["confidence"] in ("high", "medium")],
    "noact": [r for r in rows if r["disposition"] == "not_actionable" and r["confidence"] == "high"],
}
quota = {"close": 10, "bug": 9, "feature": 6, "ask": 6, "noact": 6}
for bucket, pool in picks.items():
    pool = sorted((r for r in pool if usable(r)), key=lambda r: r["number"])
    bare = [r for r in pool if bare_title(r)]
    pool = [r for r in pool if not bare_title(r)] + bare[:1]  # at most one empty template report per bucket
    for r in rng.sample(pool, min(quota[bucket], len(pool))):
        deck.append({"n": r["number"], "t": r["title"], "sum": short(r["summary"], 200), "bucket": bucket,
                     "why": why(r), "up": r["upvotes"], "opened": r["opened"],
                     "checked": bucket == "close"})
json.dump({"cards": deck}, open(f"{OUT}/sort-the-issues.json", "w"), ensure_ascii=False)

print({k: len(v) for k, v in picks.items()}, "deck", len(deck), {b: sum(c["bucket"] == b for c in deck) for b in quota})
print("waffle groups", {g: sum(1 for i in waffle["issues"] if i["g"] == g) for g in waffle["estimate"]})
print("sweep", sweep["counts"], "opened/day", sweep["opened_per_day"])
