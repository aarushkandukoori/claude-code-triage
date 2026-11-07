"""Fill a widget template's __DATA__ element with JSON, escaped so it can't close the <script> tag."""
import json, sys

template, data_path, out = sys.argv[1:4]
data = json.load(open(data_path))
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
blob = blob.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")  # no tag can open or close
html = open(template).read()
assert html.count("__DATA__") == 1, "template must contain exactly one __DATA__"
open(out, "w").write(html.replace("__DATA__", blob))
print("wrote", out, len(blob), "bytes of data")
