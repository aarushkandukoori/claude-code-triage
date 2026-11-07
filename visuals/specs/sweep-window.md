# Widget: sweep-window  (format: step machine - an animated scan you run, then fix)

Story: Anthropic's repo runs a "sweep" script twice a day. It is supposed to put a "stale" label on issues with no activity
for 14 days (they get auto-closed 14 days later). Each run it asks GitHub for the 1,000 least-recently-updated open issues
(10 pages of 100) and walks through them. But it is told to skip issues with 10+ upvotes, assigned issues, and issues that
already have a stale label. Those skipped issues never change, so they pile up at the front of the list. Today 941 of the
1,000 slots are issues it always skips. It labels the other 59 (the real logs say 64, 69, 71 per run), while thousands of
quiet issues wait behind the window. A small fix asks GitHub's search for only the issues it may label, so every slot counts.

Data shape (DATA):
{
  "window": ["up","up","as","st","ok", ... exactly 1000 codes in scan order],   // up = 10+ upvotes, as = assigned,
                                                                                // st = already stale, lk = locked, ok = can label
  "counts": {"up": 599, "as": 186, "st": 155, "lk": 1, "ok": 59},
  "logged_runs": [{"when": "Nov 6, 22:06 UTC", "labeled": 64}, {"when": "Nov 6, 10:06 UTC", "labeled": 71}, {"when": "Nov 5, 22:05 UTC", "labeled": 69}],
  "waiting": 7913,           // quiet issues the fixed query finds right now
  "opened_per_day": 260      // new issues per day, last 30 days
}

Layout and interaction
- Title: "What the sweep sees". Lede: one plain sentence.
- A grid of 1,000 small cells (e.g. 40 x 25 on desktop, 20 x 50 on phones), in scan order (left to right, top to bottom),
  each cell colored by code: skipped kinds in the three neutral grays (up, as, st; lk can share the darkest gray), "ok" in
  slot1 blue. Legend with counts.
- Button "Run today's sweep": a scan head moves cell by cell (fast, ~2.5 s for all 1,000). Skipped cells blink and stay
  gray; "ok" cells get labeled: fill turns to a solid ink-colored "stale" mark (or a blue fill with a white tick-like
  inner square). Live counters: "Looked at N of 1,000", "Labeled M". At the end, a sentence: "59 labels from 1,000 looks.
  The real runs on Nov 5-6 labeled 69, 71 and 64."
- Button "Run the fixed sweep" (enabled after the first run, or anytime): the grid refills from the right with 1,000 fresh
  blue "ok" cells (the issues GitHub search returns for the fixed query), then the scan labels all of them. Counter ends at
  "Labeled 1,000". Sentence: "7,913 quiet issues are waiting. At 1,000 a run, the pile is gone in 8 runs, about 4 days."
- A third small control: "Reset".
- Keep a tiny note in muted text under the grid: "Each cell is one real open issue, in the order the sweep reads them
  (least recently updated first), from a snapshot taken Nov 6, 2026."
- Optional but nice: hovering/tapping a cell shows what kind it is ("Skipped - 10+ upvotes").
