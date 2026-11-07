"""Build a local preview of the post: rendered markdown plus the widgets with real data.

Only handles the markdown the post uses: front matter, ### headings, paragraphs, - and 1. lists,
**bold**, `code`, [links](url), ```fences```, and raw HTML blocks (the iframes and script).
"""
import html, os, re, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POST = os.path.join(ROOT, "site/_posts/2026-11-06-claude-code-open-issues.md")
OUT = os.path.join(ROOT, "preview")
WIDGETS = ["sweep-window", "backlog-waffle", "sort-the-issues"]


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def render(md):
    front, body = re.match(r"---\n(.*?)\n---\n(.*)", md, re.S).groups()
    title = re.search(r'^title: "(.*)"$', front, re.M).group(1)
    out, para, lst, fence = [], [], None, None
    lines = body.split("\n")
    i = 0

    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            lst = None

    while i < len(lines):
        line = lines[i]
        if fence is not None:
            if line.startswith("```"):
                out.append("<pre><code>" + html.escape("\n".join(fence)) + "</code></pre>")
                fence = None
            else:
                fence.append(line)
        elif line.startswith("```"):
            flush()
            fence = []
        elif line.startswith("<iframe") or line.startswith("<script"):
            flush()
            block = [line]
            while not (block[-1].rstrip().endswith("</iframe>") or block[-1].rstrip().endswith("</script>")):
                i += 1
                block.append(lines[i])
            out.append("\n".join(block))
        elif line.startswith("### "):
            flush()
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif re.match(r"^- ", line):
            if para:
                flush()
            if not lst or lst[0] != "ul":
                flush()
                lst = ("ul", [])
            lst[1].append(line[2:])
        elif re.match(r"^\d+\. ", line):
            if para:
                flush()
            if not lst or lst[0] != "ol":
                flush()
                lst = ("ol", [])
            lst[1].append(re.sub(r"^\d+\. ", "", line))
        elif line.startswith("  ") and lst:
            lst[1][-1] += " " + line.strip()
        elif not line.strip():
            flush()
        else:
            if lst:
                flush()
            para.append(line)
        i += 1
    flush()
    return title, "\n".join(out)


title, body = render(open(POST).read())
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} (preview)</title>
<style>
  :root {{ --bg: #ffffff; --ink: #1f2328; --muted: #59636e; --link: #0969da; --code: #f3f4f6; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #1b1b1e; --ink: #e6e6e6; --muted: #a0a0a8; --link: #8ab4f8; --code: #2a2a2e; }} }}
  body {{ margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.7 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 760px; margin: 0 auto; padding: 32px 16px 80px; }}
  h1 {{ font-size: 32px; line-height: 1.2; margin: 0 0 6px; }} h3 {{ font-size: 21px; margin: 36px 0 8px; }}
  .meta {{ color: var(--muted); font-size: 14px; margin-bottom: 28px; }}
  a {{ color: var(--link); }} code {{ background: var(--code); padding: 1px 5px; border-radius: 4px; font-size: 0.88em; }}
  pre {{ background: var(--code); padding: 12px; border-radius: 6px; overflow-x: auto; }} pre code {{ background: none; padding: 0; }}
  iframe.interactive-embed {{ display: block; width: 100%; border: 0; margin: 18px 0; min-height: 320px; }}
</style></head>
<body><main><h1>{html.escape(title)}</h1><div class="meta">Aarush Kandukoori · local preview</div>
{body}
</main></body></html>
"""
os.makedirs(f"{OUT}/assets/files/claude-code-open-issues", exist_ok=True)
os.makedirs(f"{OUT}/assets/js", exist_ok=True)
open(f"{OUT}/index.html", "w").write(page)
shutil.copy(f"{ROOT}/site/assets/js/interactive-embed-resize.js", f"{OUT}/assets/js/")
for w in WIDGETS:
    template = f"{ROOT}/visuals/build/{w}.html"
    if os.path.exists(template):
        subprocess.run(["python3", f"{ROOT}/visuals/inject.py", template, f"{ROOT}/visuals/data/{w}.json",
                        f"{OUT}/assets/files/claude-code-open-issues/{w}.html"], check=True)
print("preview at", OUT)
