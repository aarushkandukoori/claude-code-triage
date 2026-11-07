# Common rules for all three widgets (read fully)

These are sandboxed iframes embedded in a Jekyll (Chirpy theme) blog post at aarushkandukoori.com.
The iframe tag is `<iframe class="interactive-embed" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox" ...>`.

Hard technical rules
- One self-contained HTML file. No external scripts, fonts, images or network calls of any kind.
- First line inside <head>: exactly
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:">
- Data comes from this exact element, which a script later fills with real JSON:
  <script id="data" type="application/json">__DATA__</script>
  Read it with JSON.parse(document.getElementById('data').textContent). While developing, put realistic SAMPLE
  data in visuals/sample-data/<name>.json and test with: python3 /Users/aarushkandukoori/random/claude-code-triage/visuals/inject.py build/<name>.html sample-data/<name>.json /tmp/claude-501/<name>-test.html
- Every string from the data (issue titles, summaries) was written by strangers. Render it ONLY with textContent /
  createTextNode / setAttribute on safe attributes. Never innerHTML, insertAdjacentHTML, outerHTML or document.write
  with data. Links: build <a> elements, set href only to https://github.com/anthropics/claude-code/issues/<number>
  built from the numeric issue number (never a URL from the data), target="_blank", rel="noopener noreferrer".
- Report height to the parent so the iframe fits its content:
  function reportHeight(){ const h = Math.ceil(document.documentElement.getBoundingClientRect().height);
    window.parent.postMessage({ type: "chirpy-interactive-height", height: h }, "*"); }
  Call it on load, after every layout change, and on resize (ResizeObserver on body is fine).
- html, body { margin:0; overflow:hidden } and no horizontal scroll anywhere. Must work from 320px to 760px wide.
  Phone first: tap must do everything hover does. Use pointer events. Hit targets >= 24px where possible.
- Light and dark mode via CSS custom properties and @media (prefers-color-scheme: dark). Give body an explicit background.
- Animated: something moves on load (respect prefers-reduced-motion: reduce by jumping to the end state).
  Use requestAnimationFrame or CSS transitions. Keep it smooth with 1,000 marks (canvas is fine for dense marks;
  SVG/DOM is fine if it stays smooth).
- Accessibility: real <button>s, visible focus rings, keyboard operable, aria-live region for results,
  every color has a text label nearby (legend or direct label). Identity is never color alone.
- Fonts: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif. No icon fonts, no emoji.

Colors (validated categorical palette; use these exact slots, in this order, for categories):
  light surface #fcfcfb, page bg #f9f9f7, ink #0b0b0b, secondary ink #52514e, muted #898781, gridline #e1e0d9
  dark surface #1a1a19, page bg #0d0d0d, ink #f0efec, secondary ink #c3c2b7, muted #898781, gridline #2c2c2a
  slot1 blue    light #2a78d6 dark #3987e5
  slot2 orange  light #eb6834 dark #d95926
  slot3 aqua    light #1baf7a dark #199e70
  slot4 yellow  light #eda100 dark #c98500
  slot5 magenta light #e87ba4 dark #d55181
  Neutral grays for "skipped/inactive" marks: light #c3c2b7 / #a9a79e / #898781, dark #4a4a46 / #5e5d58 / #75746e
  Text never wears a series color; a colored swatch next to the text carries identity.

Look and voice (important; the author hates anything that looks AI-generated)
- Plain and quiet, like a grad student's figure: no gradient cards, no glowing shadows, no "kicker" labels in caps,
  no numbered accent circles, no decorative icons. Thin borders, generous whitespace, small type (13-15px).
- Visible text: short, plain English, first person is fine. NO em dashes (use commas, periods or " - "). No
  "not X, but Y" constructions. When a bold label is followed by an explanation, write "Label - explanation", never
  "Label: explanation".
- Style reference: /Users/aarushkandukoori/random/claude-code-triage/site/assets/files/weekly/the-number-next-to-the-mechanism/explorer.html
  (read it for structure, reportHeight, and tone; do not copy its colors).

Deliverables
- Write the widget to /Users/aarushkandukoori/random/claude-code-triage/visuals/build/<name>.html
- Write sample data to /Users/aarushkandukoori/random/claude-code-triage/visuals/sample-data/<name>.json
- Validate: node or python check that the template has the CSP line, the __DATA__ element, no innerHTML /
  insertAdjacentHTML / outerHTML / document.write, no "http" except the github issue URL prefix, no em dash (U+2014).
- Return a short report: what it does, how you tested, any known gaps.
