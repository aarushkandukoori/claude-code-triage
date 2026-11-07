# Widget: sort-the-issues  (format: sorting game - drag or tap cards into buckets, then check)

Story: the reader gets to be the triage bot. They see 6 real open issues from Anthropic's claude-code repo and decide what
a maintainer should do with each. Then "Check" reveals what my pipeline decided (only calls that two separate checkers
agreed on are in the deck), with the one-line evidence.

Buckets (fixed order, same colors as the other widgets):
  bug "Real bug" slot1 | feature "Feature request" slot2 | close "Close it: fixed or duplicate" slot3 |
  ask "Ask the reporter" slot4 | noact "Not actionable" slot5

Data shape (DATA):
{ "cards": [ {"n": 77578, "t": "issue title", "sum": "one-line plain summary", "bucket": "close",
              "why": "Fixed in 2.1.243: 'Fixed background subagents not waking when ...'", "up": 3, "opened": "2026-05-02"} ... ~30-40 ] }

Interaction
- Title: "You be the triage bot". Lede: "Put each issue where you think it belongs, then check."
- Deal 6 cards at random from the deck, but make sure at least 3 different correct buckets appear in a deal.
- Cards show the title (textContent; clamp to 3 lines with an expand on tap) and the summary in muted text, plus "#number".
- Two ways to place a card: drag it onto a bucket (pointer events, works with touch), OR tap a card to select it and
  then tap a bucket. Placed cards stack inside their bucket and can be moved again.
- Buckets are 5 drop zones in a responsive grid (2 columns on phones).
- "Check" (enabled when all 6 are placed): each wrong card animates (smoothly) to its correct bucket, gets a thin outline
  and shows the one-line "why" under it; right cards get a small "right" text tag (no emoji). Score line in an aria-live
  region: "4 of 6 match the pipeline". Then "Deal again" deals 6 new cards (avoid repeats until the deck runs out) and
  keeps a running total ("Running total 9 of 12").
- A muted footnote: "The answers are my pipeline's calls, each checked by two separate readers. They can still be wrong;
  every card links to the issue."  Each card has a small "Open #number" link.
- Something animated on load: cards deal in from a deck with a short staggered flip/slide.
