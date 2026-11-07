# Widget: backlog-waffle  (format: animated unit chart you can filter and tap)

Story: I had Claude agents triage 1,000 open issues from Anthropic's claude-code GitHub repo. Each dot is one real issue.
On load, 1,000 gray dots sit in a loose unsorted cloud, then fly into five colored groups, one group per "what should a
maintainer do with it". The reader can tap any dot to see that issue, and filter by how it was sampled.

Groups (fixed order = color slots 1..5):
  bug      "Real bugs"            slot1 blue
  feature  "Feature requests"     slot2 orange
  close    "Close now"            slot3 aqua    (already fixed or a duplicate, and two separate checks agreed)
  ask      "Ask the reporter"     slot4 yellow  (needs info, or old and needs a retest)
  noact    "Not actionable"       slot5 magenta (not about Claude Code, support request, vague, works as intended)

Data shape (DATA):
{
  "issues": [ {"n": 41234, "t": "issue title", "g": "bug", "d": "valid_bug", "sev": "S1_high"|"S2_medium"|"S3_low"|"S0_critical"|"none",
               "s": "top"|"security"|"rest", "sum": "our one-line summary", "act": "what a maintainer should do",
               "chk": "confirmed"|"likely"|"rejected"|"unverified"|null, "up": 12 } ... 1000 items ],
  "strata": {"top": {"label": "150 most-upvoted", "picked": 150, "of": 150},
             "security": {"label": "security-flavored", "picked": 250, "of": 1574},
             "rest": {"label": "random", "picked": 600, "of": 14388}},
  "estimate": {"bug": {"share": 0.31, "low": 0.27, "high": 0.35, "issues": 5000}, ... one per group },
  "population": 16112
}
"d" is the finer call (valid_bug, feature_request, already_fixed, duplicate, needs_info, stale_unclear, not_actionable).
"sev" matters only for bugs. Show S0/S1 bugs with a visible extra mark (e.g. a 1.5px ring in ink color) and say so
in the legend ("ring = high or critical severity").

Layout
- Title (h2, 18px): "1,000 issues, sorted". One-line lede under it in muted ink.
- Filter row of chips: All 1,000 | 150 most-upvoted | 250 security-flavored | 600 random. Filtering fades the other dots
  to ~12% opacity (don't remove them; positions stay put so the shape stays stable).
- The plot: five groups as compact blocks of square dots (like a waffle per group), each block with a direct label
  under/over it: group name + count for the current filter. Blocks wrap on narrow screens. Dots ~7-9px with 2px gaps on
  desktop, smaller on phones; canvas recommended for 1,000 marks, with your own hit-testing.
- Tap/hover a dot: a details card (not a floating tooltip on phones; a fixed card under the plot is fine on all sizes)
  showing "#41234", the title (textContent), the call in plain words (e.g. "Real bug, high severity"), the summary,
  the next action, whether the call was checked ("Checked twice, both agreed" for confirmed, "Checked twice, one agreed,
  one unsure" for likely, "A checker disagreed, so it stays open as a real bug" for rejected) and an "Open on GitHub"
  link. Selected dot gets a ring. Arrow keys / Tab can move selection (simple: a "Random issue" button also works).
- Under the plot, a small "Scaled up to all 16,112 open issues" row: for each group a horizontal bar of the estimated
  share with its 95% interval as a thin whisker, label like "Real bugs 31% (27-35%)". Note in muted text: "The sample
  over-weights popular and security issues on purpose. These bars re-weight it." Bars animate in on load.
- Legend with swatches + labels always visible.

Make the sorted-into-groups animation feel physical: staggered, eased, ~1.2 s total.
