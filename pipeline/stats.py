"""Numbers for the write-up.

Two kinds:
  1. Facts about all 16,112 open and 88,619 closed issues, counted directly.
  2. Estimates for the whole open backlog from the 1,000 triaged issues.
     Each group (top / security / rest) is weighted by its share of the backlog,
     and the 95% interval uses the standard stratified-sampling variance:
       p = sum_h W_h p_h,   var = sum_h W_h^2 (1 - n_h/N_h) p_h (1 - p_h) / (n_h - 1)
     where W_h = N_h / N. The top group was taken whole, so it adds no sampling error.
"""
import collections, json, math, re
from datetime import datetime, timedelta, timezone

sample_info = json.load(open("data/sample.json"))
N = sample_info["population"]
SIZES = sample_info["strata_sizes"]
rows = [json.loads(l) for l in open("data/triage-1000.jsonl")]
open_issues = [json.loads(l) for l in open("data/raw/open.jsonl")]
closed = [json.loads(l) for l in open("data/raw/closed.jsonl")]
by_number = {i["number"]: i for i in open_issues}
SNAPSHOT = max(i["updated_at"] for i in open_issues)[:10]


def estimate(pred):
    p, var = 0.0, 0.0
    for h, N_h in SIZES.items():
        group = [r for r in rows if r["stratum"] == h]
        n_h = len(group)
        p_h = sum(1 for r in group if pred(r)) / n_h
        W_h = N_h / N
        p += W_h * p_h
        if n_h > 1:
            var += W_h ** 2 * (1 - n_h / N_h) * p_h * (1 - p_h) / (n_h - 1)
    se = math.sqrt(var)
    return {"share": round(p, 4), "low": round(max(0, p - 1.96 * se), 4), "high": round(min(1, p + 1.96 * se), 4),
            "issues": round(N * p), "issues_low": round(N * max(0, p - 1.96 * se)), "issues_high": round(N * min(1, p + 1.96 * se))}


def count(pred, subset=None):
    return sum(1 for r in (subset or rows) if pred(r))


out = {"snapshot": SNAPSHOT, "open": N, "closed": len(closed)}

# --- 1. whole-repo facts ------------------------------------------------------
out["assigned"] = sum(1 for i in open_issues if i["assignees"])
out["unlabeled"] = sum(1 for i in open_issues if not i["labels"])
out["opened_since_sep1"] = sum(1 for i in open_issues if i["created_at"] >= "2026-09-01")
out["upvotes_10_plus"] = sum(1 for i in open_issues if (i["thumbs"] or 0) >= 10)
out["filed_with_claude_signature"] = sum(1 for i in open_issues if re.search(
    r"Filed with Claude Code|Generated with \[?Claude Code|🤖 Generated with", i["body"] or "", re.I))
out["closed_reasons"] = dict(collections.Counter(c["stateReason"] for c in closed))
out["closed_with_stale_label"] = sum(1 for c in closed if "stale" in c["labels"] or "autoclose" in c["labels"])
out["closed_with_duplicate_label"] = sum(1 for c in closed if "duplicate" in c["labels"])

months = collections.Counter(i["created_at"][:7] for i in open_issues) + collections.Counter(c["createdAt"][:7] for c in closed)
closes = collections.Counter((c["closedAt"] or "")[:7] for c in closed)
out["flow_by_month"] = [{"month": m, "opened": months[m], "closed": closes[m]} for m in sorted(months) if m >= "2025-06"]
weeks = collections.Counter()
for i in open_issues:
    weeks[i["created_at"][:10]] += 1
for c in closed:
    weeks[c["createdAt"][:10]] += 1
last30 = [(datetime.fromisoformat(SNAPSHOT) - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(1, 31)]
out["opened_per_day_last30"] = round(sum(weeks[d] for d in last30) / 30)

# --- the stale sweep ---------------------------------------------------------
# The snapshot was taken right after the Nov 6 22:06 UTC run, so the next run is Nov 7 10:06 UTC.
NEXT_RUN = datetime(2026, 11, 7, 10, 6, tzinfo=timezone.utc)
cutoff = (NEXT_RUN - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")


def sweep_skip(i):
    if i.get("locked"):
        return "locked"
    if i["assignees"]:
        return "assigned"
    if "stale" in i["labels"] or "autoclose" in i["labels"]:
        return "already stale"
    if (i["thumbs"] or 0) >= 10:
        return "10+ upvotes"
    return None


oldest_first = sorted(open_issues, key=lambda i: i["updated_at"])
window = oldest_first[:1000]
out["sweep_window"] = dict(collections.Counter(sweep_skip(i) or "can label" for i in window))
idle = [i for i in open_issues if i["updated_at"] < cutoff]
out["sweep_idle_14d"] = len(idle)
out["sweep_idle_labelable"] = sum(1 for i in idle if not sweep_skip(i))
sweep_eligible = {i["number"] for i in idle if not sweep_skip(i)}
# What the fixed query (search) would return: the same rules, with "fewer than 10 reactions of any kind".
out["sweep_fixed_query_matches"] = sum(1 for i in idle if not sweep_skip(i) and (i["reactions"] or 0) < 10)

# Closed issues that went through the stale path (stale/autoclose label, closed as not planned), by label.
went_stale = [c for c in closed if ("stale" in c["labels"] or "autoclose" in c["labels"]) and c["stateReason"] == "NOT_PLANNED"]
out["closed_after_stale_by_label"] = {lab: sum(1 for c in went_stale if lab in c["labels"])
                                      for lab in ("data-loss", "reproduced", "high-priority", "area:security", "has repro")}
popular = [i for i in window if sweep_skip(i) == "10+ upvotes"]
out["window_popular"] = {"count": len(popular), "labeled_bug": sum(1 for i in popular if "bug" in i["labels"]),
                         "quiet_since_before_sep1": sum(1 for i in popular if i["updated_at"] < "2026-09-01")}
went_quiet_last_week = [i for i in open_issues if "2026-10-17T10:06:00Z" <= i["updated_at"] < cutoff and not sweep_skip(i)]
out["going_quiet_per_day"] = round(len(went_quiet_last_week) / 7)

# --- 2. estimates from the 1,000 ---------------------------------------------
DISPOSITIONS = ["already_fixed", "duplicate", "needs_info", "valid_bug", "feature_request", "not_actionable", "stale_unclear"]
popular_in_sample = [r for r in rows if r["number"] in {i["number"] for i in popular}]
out["window_popular"]["in_sample"] = dict(collections.Counter(r["disposition"] for r in popular_in_sample))
out["sample_counts"] = {
    "by_stratum": dict(collections.Counter(r["stratum"] for r in rows)),
    "final_disposition": dict(collections.Counter(r["disposition"] for r in rows)),
    "triage_disposition": dict(collections.Counter(r["triage_disposition"] for r in rows)),
    "closable": count(lambda r: r["closable"]),
    "closable_fixed": count(lambda r: r["closable"] and r["disposition"] == "already_fixed"),
    "closable_duplicate": count(lambda r: r["closable"] and r["disposition"] == "duplicate"),
    "severity": dict(collections.Counter(r["severity"] for r in rows)),
    "security_flagged_by_triage": count(lambda r: r["security_relevant"]),
    "security_verified": count(lambda r: r["security_verified"]),
    "injection_attempts": count(lambda r: r["injection_attempt"]),
    "regressions": count(lambda r: r["regression"]),
    "check_status": {kind: dict(collections.Counter(r["checks"][kind]["status"] for r in rows if kind in r["checks"]))
                     for kind in ("fixed", "duplicate", "security")},
    "by_stratum_disposition": {h: dict(collections.Counter(r["disposition"] for r in rows if r["stratum"] == h)) for h in SIZES},
    "area": dict(collections.Counter(r["area"] for r in rows).most_common()),
}
out["estimates"] = {d: estimate(lambda r, d=d: r["disposition"] == d) for d in DISPOSITIONS}
out["estimates"]["closable_now"] = estimate(lambda r: r["closable"])
out["estimates"]["close_or_redirect"] = estimate(lambda r: r["closable"] or r["disposition"] == "not_actionable")
out["estimates"]["real_open_bug"] = estimate(lambda r: r["disposition"] == "valid_bug")
out["estimates"]["s0_or_s1_bug"] = estimate(lambda r: r["disposition"] == "valid_bug" and r["severity"] in ("S0_critical", "S1_high"))
out["estimates"]["security_verified"] = estimate(lambda r: r["security_verified"])
# Security calls that a checker only marked down, but still at high or medium.
out["estimates"]["security_incl_downgraded"] = estimate(
    lambda r: r["security_relevant"] and (r["security_verified"] or (r["checks"].get("security", {}).get("status") == "rejected"
                                                                     and r["severity"] in ("S0_critical", "S1_high", "S2_medium"))))
out["estimates"]["injection_attempt"] = estimate(lambda r: r["injection_attempt"])

# What a working sweep would close: the sampled issues that are idle and labelable today.
eligible_rows = [r for r in rows if r["number"] in sweep_eligible]
out["sweep_eligible_in_sample"] = {
    "count": len(eligible_rows),
    "disposition": dict(collections.Counter(r["disposition"] for r in eligible_rows)),
    "valid_bug_share": round(count(lambda r: r["disposition"] == "valid_bug", eligible_rows) / max(1, len(eligible_rows)), 3),
    "s0_s1_valid_bugs": [r["number"] for r in eligible_rows if r["disposition"] == "valid_bug" and r["severity"] in ("S0_critical", "S1_high")],
}
# Backlog-wide shares among the issues a working sweep would label (a ratio of two weighted estimates).
eligible_share = estimate(lambda r: r["number"] in sweep_eligible)["share"]
out["sweep_eligible_estimates"] = {
    "share_of_backlog": eligible_share,
    "valid_bug": round(estimate(lambda r: r["number"] in sweep_eligible and r["disposition"] == "valid_bug")["share"] / eligible_share, 3),
    "s0_s1_bug": round(estimate(lambda r: r["number"] in sweep_eligible and r["disposition"] == "valid_bug"
                                and r["severity"] in ("S0_critical", "S1_high"))["share"] / eligible_share, 3),
    "closable": round(estimate(lambda r: r["number"] in sweep_eligible and r["closable"])["share"] / eligible_share, 3),
}

json.dump(out, open("data/stats.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("snapshot", "open", "assigned", "sweep_window", "sweep_idle_labelable")}, indent=None))
print(json.dumps(out["sample_counts"]["final_disposition"]))
for k, v in out["estimates"].items():
    print(f"{k:18} {v['share']:.1%} [{v['low']:.1%}, {v['high']:.1%}] ~{v['issues']} issues")
