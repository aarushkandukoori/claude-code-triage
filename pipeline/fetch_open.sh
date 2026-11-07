#!/bin/bash
# Pull every open issue (not PRs) from anthropics/claude-code, one JSON object per line.
# Oldest first, so issues opened during the crawl land at the end instead of shifting pages.
set -euo pipefail
OUT="${1:-data/raw/open.jsonl}"
gh api --paginate 'repos/anthropics/claude-code/issues?state=open&sort=created&direction=asc&per_page=100' \
  --jq '.[] | select(.pull_request == null) | {number, title, body, labels: [.labels[].name], assignees: [.assignees[].login], created_at, updated_at, comments, thumbs: .reactions["+1"], reactions: .reactions.total_count, user: .user.login, assoc: .author_association, locked}' \
  > "$OUT"
wc -l "$OUT"
