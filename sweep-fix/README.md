# The stale sweep labels about 60 issues a run

`scripts/sweep.ts` in anthropics/claude-code runs twice a day (10:06 and 22:06 UTC). Its first pass, `markStale`, is
supposed to put a `stale` label on every open issue with no activity for 14 days. Those get closed 14 days later if
nobody responds.

## What's wrong

`markStale` asks GitHub for open issues sorted by least recently updated, 10 pages of 100, and walks through them. It
skips issues that are assigned, locked, already labeled `stale`/`autoclose`, or have 10+ upvotes. A skipped issue
doesn't change, so it stays at the front of the list and fills a slot on every run.

The 1,000 issues in the window after the Nov 6 22:06 UTC run (snapshot of all 16,112 open issues, taken right after):

| What the sweep does with them | Issues |
|---|---|
| Skip - 10+ upvotes | 599 |
| Skip - assigned | 186 |
| Skip - already stale | 155 |
| Skip - locked | 1 |
| Can label | 59 |

That matches the run logs: the runs on Nov 5 22:05, Nov 6 10:06 and Nov 6 22:06 UTC labeled 69, 71 and 64 issues
(Actions runs 42118507950, 42200120211 and 42302084908). The counts only work out if pull requests are left out of the
list, which fits a job token that has `issues: write` and nothing else. A token that can see pull requests gets a
window of 555 old PRs plus 445 skipped issues, and a dry run with it labels 0.

As of the next run (Nov 7 10:06 UTC), about 8,000 open issues have had no activity for 14+ days and meet every rule
(8,008 by the script's own checks; 8,003 match the search query below, and GitHub's search returned 8,000 for it that
evening). About 237 more go quiet every day, against roughly 130 a day that the sweep labels.

## The fix

Ask search for only the issues this pass may label, collect them before labeling anything (labeling bumps
`updated_at`, which would shift later pages), and cap and pace the writes:

```ts
// GitHub allows about 500 content-creating requests an hour, and the closing
// pass writes too, so label at most this many issues a run, a little apart.
const MAX_STALE_LABELS_PER_RUN = 300;
const WRITE_GAP_MS = 2000;

const query = [
  `repo:${owner}/${repo}`, "is:issue", "is:open", "is:unlocked", "no:assignee",
  "-label:stale", "-label:autoclose",
  `updated:<${cutoff.toISOString().slice(0, 19)}+00:00`,
  `reactions:<${STALE_UPVOTE_THRESHOLD}`,
].join(" ");

const issues: any[] = [];
for (let page = 1; page <= 10 && issues.length < MAX_STALE_LABELS_PER_RUN; page++) {
  const result = await githubRequest<{ items?: any[] }>(
    `/search/issues?q=${encodeURIComponent(query)}&sort=updated&order=asc&per_page=100&page=${page}`
  );
  if (!result.items?.length) break;
  issues.push(...result.items);
}
// ...then the existing per-issue checks over `issues`, stopping at the cap,
// with a WRITE_GAP_MS pause after each label.
```

- Every issue the query returns is one the pass may label, so a run labels up to 300 instead of about 60.
- At 600 a day against about 237 going quiet, today's pile takes about three weeks. Running the sweep more often with
  the same cap would go faster and spread the writes.
- The closing pass will have more to close two weeks later (two writes per close). Both passes together should stay
  under GitHub's hourly write limit, so the closing pass needs the same kind of cap.
- `reactions:<10` counts every reaction kind, so an issue with 10+ reactions but fewer than 10 upvotes is left alone.
  Five such issues exist today. The exact upvote check still runs on each result.
- Not yet run live: GitHub's search rate limit blocked my read-only dry runs. The numbers above come from the snapshot
  and from one live search count.

## Worth deciding at the same time

- **A sweep that works will close real bugs** - in a 1,000-issue triage of this backlog, about 40% of the issues the sweep
  would label are credible open bugs, and about 3% are bugs the pipeline rated high or critical. Among issues closed after
  being marked stale, 324 carry `data-loss`, 200 `reproduced` and 77 `high-priority`. Adding
  `-label:data-loss -label:high-priority -label:reproduced` to the query (and the same skip in the closing pass) would keep
  those open.
- **The popular issues in the window are mostly old bug reports** - 442 of the 599 carry `bug`, and 527 have had no
  activity since before September 1. Of the 60 that landed in the triage sample, 26 were already fixed, duplicates, or too
  old to trust without a retest. Closing those by hand would also free up the window.
