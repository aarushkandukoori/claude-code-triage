# Facts sheet (every number the post may use, with its source)

Snapshot: open issues pulled 2026-11-06 ~19:30-19:40 EST (2026-11-07 ~00:30 UTC), right after the Nov 6 22:06 UTC sweep run. Closed issues pulled the same evening.

## Whole repo (counted directly; data/raw/open.jsonl, closed.jsonl; pipeline/stats.py)
- Open issues: 16,112. Assigned: 294 (1.8%). Unassigned: 15,818 (98.2%).
- Open issues with no labels at all: 248 (1.5%), so 98.5% carry at least one label.
- Opened since Sep 1, 2026 and still open: 12,973 (80.5%).
- New issues per day, average of the last 30 days (open + closed by creation date): 255.
- Open issues with 10+ upvotes: 1,256.
- Closed issues: 88,619. Close reasons: NOT_PLANNED 50,798 (57%), DUPLICATE 22,792 (26%), COMPLETED 15,029 (17%).
- Closed issues carrying a stale or autoclose label: 40,693.
- Open issues titled only "[GitHub integration]": 511 (658 start with it).
- CHANGELOG.md: 437 version headings, 8,814 bullet lines. Latest release 2.1.319 (2026-11-06).
- Monthly opened vs closed (2026): Jan 6,000/6,844; Feb 7,074/7,345; Mar 11,339/8,771; Apr 13,074/10,743; May 9,029/11,226; Jun 8,082/7,814; Jul 10,020/5,062; Aug 7,972/6,837; Sep 7,361/8,708; Oct 7,847/5,454.

## Anthropic's bots (upstream/*.yml, scripts/*.ts in anthropics/claude-code)
- claude-issue-triage.yml: runs Claude Code (claude-sonnet-5-5) on every new issue and comment; only adds/removes labels; never comments. Duplicates only against OPEN issues.
- claude-dedupe-issues.yml: on every new issue, Claude searches for up to 3 duplicates and comments; auto-close-duplicates.yml closes after 3 days.
- sweep.yml + scripts/sweep.ts: twice daily (10:06, 22:06 UTC). Marks stale after 14 days idle; closes stale/autoclose 14 days later as not planned. Skips assigned, locked, already-stale, 10+ upvotes. Scans only 10 pages x 100 issues, oldest-updated first.

## The sweep window (snapshot after the Nov 6 22:06 UTC run; issues only)
- Window of 1,000: {'locked': 1, 'assigned': 186, '10+ upvotes': 599, 'already stale': 155, 'can label': 59}.  941 of 1,000 are always skipped.
- Run logs: Nov 5 22:05 UTC labeled 69 (closed 54); Nov 6 10:06 UTC labeled 71 (closed 88); Nov 6 22:06 UTC labeled 64 (closed 73). Runs 42118507950, 42200120211, 42302084908. Nov 4 10:07 run failed (timeout).
- With pull requests included (what a token with PR access sees): the first 1,000 = 555 PRs + 286 10+upvote + 88 assigned + 70 stale + 1 locked = 0 labelable; dry run of the original script with my token labels 0.
- Idle 14+ days as of the next run (Nov 7 10:06 UTC, cutoff Oct 24 10:06 UTC): 9,387 open issues; 8,008 meet every labeling rule; the fixed search query matches 8,003 (5 differ because reactions:<10 counts all reaction kinds).
- Fixed sweep (patch): search query + MAX_STALE_LABELS_PER_RUN = 300, 2 s between writes (GitHub allows about 500 content-creating requests an hour). 600 a day against about 237 issues going quiet a day: today's ~8,000 take about three weeks (8,000 / 363 = 22 days). Not run live (search secondary rate limit on my token); live search count for the query = 8,000.
- Weighted share of the backlog a working sweep would label: 51.6%. Among those: real bugs 40.0%, high/critical real bugs 2.9%, closable now 11.7%.
- Labels vs the stale path, whole repo: data-loss open 175 (27 already stale, 88 next for a fixed sweep; 324 closed by the stale path); high-priority open 23 (1 stale, 8 next; 77 closed by stale); reproduced open 248 (1 stale, 149 next; 200 closed by stale); area:security open 724 (154 stale, 370 next; 1,346 closed by stale); has repro open 3,620 (530 stale, 1,644 next; 10,015 closed by stale).
- Examples closed by the stale bot (its comment says closing for now, inactive for too long): #88605 'Exit cleanup recursively deletes $HOME instead of session directory' (high-priority, data-loss; closed 2026-10-13; no changelog fix found); #86667 guard bypass via 'cmd /c rd' then destructive command (high-priority, security, data-loss; closed 2026-10-03; FIXED in 2.1.283 on 2026-09-25, a week earlier); #84224 auto-updater clobbers another npm install (reproduced by a maintainer 2026-08-25 on 2.1.233; closed 2026-10-24; no changelog fix found).

## The 1,000 (data/triage-1000.jsonl; stratified sample, seed 20261106)
- Strata: top 150 by upvotes (all 150 of 150); security-flavored 250 of 1,574; random 600 of 14,388.
- First-pass calls: valid_bug 349, feature_request 220, duplicate 174, not_actionable 131, needs_info 58, already_fixed 37, stale_unclear 31.
- Verification (two separate sessions per call, opposite lenses): fixed {'rejected': 9, 'confirmed': 21, 'likely': 5, 'unverified': 2}; duplicate {'confirmed': 83, 'rejected': 57, 'likely': 14, 'unverified': 20}; security {'confirmed': 31, 'rejected': 49, 'likely': 5, 'unverified': 1}. 115 of 297 calls rejected (39%).
- Final: {'valid_bug': 408, 'feature_request': 224, 'duplicate': 117, 'stale_unclear': 31, 'not_actionable': 133, 'already_fixed': 28, 'needs_info': 59}. Closable now (both checks agree or one agrees + one unsure): 123 (26 fixed, 97 duplicates).
- Severity (final): {'S2_medium': 368, 'none': 319, 'S1_high': 66, 'S3_low': 238, 'S0_critical': 9}. Regressions (says it worked before): 123.
- Security: first pass flagged 86; 36 survived both checks (17 destructive actions/data loss, 9 permission bypass, 3 supply chain, 2 privacy, 1 prompt injection, 1 credential exposure, 3 other). 9 rated critical (8 verified), all data loss, all with 0 upvotes.
- Text addressed to AI agents: 2 issues (#3301, #14202), both commenters asking an agent to fix the bug. Nothing malicious found.
- Top 150 by upvotes: {'valid_bug': 44, 'feature_request': 78, 'stale_unclear': 11, 'not_actionable': 9, 'duplicate': 6, 'already_fixed': 2} (52% feature requests). Median upvotes 95.
- Two sampled issues were fixed in 2.1.319, the release that shipped Nov 6: #105108 (slash commands after a leading space) and #104886 (VS Code dictation toggle). #71539 (25 upvotes) fixed in 2.1.239 (Aug 21), still open.
- Critical bugs in the sample right now: #93469 and #93791 (Windows ~/.claude wiped) carry the stale label; #93099 (rm -rf "$HOME" in auto mode, labeled high-priority + model) is idle and would be labeled by a fixed sweep.

## Backlog estimates (weighted; pipeline/stats.py)
- valid_bug: 41.6% (95% CI 38.1%-45.1%), about 6,704 issues (6,141-7,266)
- feature_request: 19.0% (95% CI 16.2%-21.8%), about 3,066 issues (2,616-3,517)
- not_actionable: 13.8% (95% CI 11.4%-16.2%), about 2,222 issues (1,831-2,613)
- duplicate: 11.9% (95% CI 9.7%-14.2%), about 1,925 issues (1,559-2,291)
- needs_info: 7.8% (95% CI 5.9%-9.7%), about 1,256 issues (942-1,569)
- already_fixed: 3.3% (95% CI 2.0%-4.6%), about 537 issues (328-746)
- stale_unclear: 2.5% (95% CI 1.4%-3.6%), about 402 issues (224-580)
- closable_now: 13.3% (95% CI 10.9%-15.7%), about 2,140 issues (1,753-2,526)
- close_or_redirect: 27.1% (95% CI 23.9%-30.2%), about 4,362 issues (3,856-4,868)
- s0_or_s1_bug: 3.7% (95% CI 2.5%-4.9%), about 596 issues (396-795)
- security_verified: 2.0% (95% CI 1.2%-2.7%), about 317 issues (192-442)

## Cost
- 50 triage sessions + 60 verify sessions (+1 pilot each), Opus 5.5, 6 at a time. Triage ~65-100 s per batch of 20; verify ~45 s per batch of 10.

## Waffle groups, weighted (what the backlog widget shows)
- waffle group bug 43.6% (40.1-47.1) ~7,026 (6,461-7,592)
- waffle group feature 19.0% (16.2-21.8) ~3,066 (2,616-3,517)
- waffle group close 13.3% (10.9-15.7) ~2,140 (1,753-2,526)
- waffle group ask 10.3% (8.1-12.5) ~1,658 (1,305-2,011)
- waffle group noact 13.8% (11.4-16.2) ~2,222 (1,831-2,613)

## Serious bugs in the sample vs the sweep (report/serious-bugs.md)
- 52 open bugs rated S0/S1 (valid_bug, needs_info or stale_unclear; security check not rejected): 10 labeled stale now, 16 next for a working sweep, 10 active, 16 protected (10+ upvotes or assignee).
- Pipeline timing: triage outputs 19:44-19:57 EST (pilot 19:43), verify 20:10-20:21 EST. About 25 minutes of reading and checking. 110 sessions (50 triage + 60 verify), plus 5 automatic retries.
- Notional API-equivalent cost reported by the CLI: triage $39.16, verify $22.79 (runs on a Claude Max subscription).
- Reddit post: r/ClaudeAI, u/nseavia71501, "Open question to Anthropic: If you're making 30,000 merges a day, why are more than 98% of open GitHub issues unassigned, including serious security bugs?" (642 upvotes, 79 comments when seen). It cites Anthropic's engineering blog for 30,000+ code changes per day and says 15,766 of 16,060 open issues had no assignee.
- John Crickett's LinkedIn post: asks why Anthropic isn't triaging with a software factory that reviews issues, filters risky ones (prompt injection) and assigns the rest to an agent or a human; says showing that factory would be a better case study than claiming 30,000 PRs per day.
- Verified-only already-fixed estimate (closable and already_fixed): 3.3% (2.0-4.6%), about 524 issues -> "roughly 500".
- Verified-only duplicate estimate: 10.0% (7.9-12.1%), about 1,615.
- "[GitHub integration]" issues: 511 open; body text median ~296 chars (only 20 nearly empty); in the sample 26 of them: 14 needs_info, 9 not_actionable, 1 duplicate, 1 valid_bug, 1 feature_request.
- Agent-addressed comments: #3301 "Put an agent to fix this"; #14202 "Hey Claude Code agent, could we please prioritize this issue?"
- All 9 issues rated critical had 0 upvotes (8 verified, #106326 unverified).
- Live search 2026-11-06 20:31 EST: the fixed query (cutoff Oct 24 10:06 UTC) returned total_count 8,000.
