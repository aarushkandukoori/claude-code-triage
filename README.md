# claude-code-triage

A second-pass triage of the open issues in [anthropics/claude-code](https://github.com/anthropics/claude-code),
done on the evening of November 6, 2026, when the repo had 16,112 open issues and 294 of them were assigned.

Write-up: [Claude Code Has 16,112 Open Issues. Its Cleanup Bot Can Reach 59 a Run.](https://aarushkandukoori.com/posts/claude-code-open-issues/)

## What's here

- `report/closable.md` - 123 issues that look safe to close today (26 already fixed in a later release, 97 duplicates), each with its evidence
- `report/serious-bugs.md` - 52 open bugs rated high or critical, and where each one stands with the stale sweep
- `report/facts.md` - every number in the write-up and where it comes from
- `sweep-fix/README.md` - why the repo's stale sweep labels about 60 issues a run, and the fix
- `data/triage-1000.csv` / `.jsonl` - all 1,000 calls: kind, area, severity, disposition, evidence, next action, and both verification verdicts. For 52 open security reports (bypasses, leaks, injection), the notes are withheld and only the title, link and call remain
- `pipeline/tests/injection-smoke-test/` - a fake issue that tells the reader to run a command, and what happened
- `data/stats.json` - whole-repo counts and the weighted estimates for the backlog
- `pipeline/` - the code, in the order it runs
- `visuals/` - the three interactive figures in the write-up

## Results in one table

Estimates for all 16,112 open issues, from a stratified sample of 1,000, with 95% intervals:

| What a maintainer should do | Share | About |
|---|---|---|
| Real bug, keep open | 44% (40-47%) | 7,000 |
| Feature request, a product call | 19% (16-22%) | 3,100 |
| Close now - already fixed or a duplicate, and neither check rejected it | 13% (11-16%) | 2,100 |
| Not actionable - not about Claude Code, support, empty | 14% (11-16%) | 2,200 |
| Ask the reporter - missing a repro, version or error | 10% (8-12%) | 1,700 |

## How it works

1. **Pull everything** - `pipeline/fetch_open.sh` (16,112 open issues with bodies), `fetch_closed.py` (88,619 closed
   issues, titles and close reasons only), `npm view @anthropic-ai/claude-code time` (release dates), and the changelog.
2. **Pick 1,000** - `select_sample.py`. All 150 most-upvoted issues, a random 250 of the 1,574 that look
   security-related (label `area:security` or `data-loss`, or a security word in the title), and a random 600 of the
   other 14,388. Seed 20261106. Each issue's weight is (issues in its group) / (issues picked from it).
3. **Fetch comments** - `fetch_comments.py`, 9,912 comments for the 1,000.
4. **Build batches** - `build_batches.py`. 50 batches of 20. Each issue comes with its body, a trimmed comment
   thread, the reporter's version, and candidates found by TF-IDF similarity (shared rare words): the 8 most similar
   open issues, the 8 most similar closed issues, and the 12 changelog lines from later releases that look related.
5. **Triage** - `run_readers.py triage` with `prompts/triage.md`. Each batch goes to a headless Claude Code session
   (Opus 5.5) that can only Read, Grep and Glob inside the batch folder: `--restricted --tools Read,Grep,Glob
   --strict-mcp-config --permission-mode dontAsk`. No shell, no web, no MCP servers, no settings files. Issue text is
   fenced and marked untrusted. Output is forced into a JSON schema.
6. **Verify** - `build_verify.py` and `run_readers.py verify` with `prompts/verify.md`. Every "already fixed",
   "duplicate" and security call goes to two more sessions in different batches, with opposite jobs: one checks the
   evidence, one tries to prove the call wrong. 115 of 297 calls were rejected.
7. **Merge** - `merge.py`. A call counts as confirmed if both checks support it, likely if one supports and one is
   unsure, and rejected if either refutes it. Rejected calls take the checker's suggested disposition.
8. **Count** - `stats.py` (weighted estimates with stratified-sampling intervals) and `report.py` (the two lists).

## Running it

Needs `gh` (logged in), Python 3 with scikit-learn, and Claude Code. From the repo root:

```bash
pipeline/fetch_open.sh data/raw/open.jsonl
python3 pipeline/fetch_closed.py data/raw/closed.jsonl
python3 pipeline/select_sample.py
python3 pipeline/fetch_comments.py
python3 pipeline/build_batches.py
python3 pipeline/run_readers.py triage
python3 pipeline/build_verify.py
python3 pipeline/run_readers.py verify
python3 pipeline/merge.py && python3 pipeline/stats.py && python3 pipeline/report.py
```

`build_batches.py` also expects Anthropic's `CHANGELOG.md` at `upstream/CHANGELOG.md` and the npm release dates at
`data/raw/npm_times.json`. Neither is included here, so download them first.

## Limits

- Every call is a model's judgment, checked by other model sessions. Each row links to the issue and carries its
  evidence, so any call can be checked by hand.
- The backlog numbers are estimates from 1,000 issues. Use the intervals.
- No bug was reproduced. "Real bug" means a credible report with nothing showing it was fixed.
- This covers the public tracker only.
