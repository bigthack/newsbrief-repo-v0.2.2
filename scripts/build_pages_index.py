
#!/usr/bin/env python3
# Create ./public/ with an index.html that links to demo outputs in scripts/out/**.

import pathlib, datetime, html

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scripts" / "out"
PUB = ROOT / "public"
PUB.mkdir(parents=True, exist_ok=True)

entries = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.suffix in {".html", ".txt", ".json"}:
        rel = p.relative_to(ROOT)
        entries.append((str(rel), p.stat().st_mtime))

# Copy assets into public/ preserving relative subdirs
for rel, _ in entries:
    src = ROOT / rel
    dest = PUB / pathlib.Path(rel).relative_to("scripts/out")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())

# Build simple index
rows = []
for rel, mtime in sorted(entries, key=lambda x: x[1], reverse=True):
    name = html.escape(rel.replace("scripts/out/", ""))
    href = html.escape(name)
    rows.append(f'<li><a href="{href}">{name}</a></li>')

index = """<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>NewsBrief Demo Index</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
body {{ font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif; margin: 2rem; }}
h1 {{ font-size: 1.5rem; }}
code {{ background: #f6f8fa; padding: 0.15rem 0.35rem; border-radius: 4px; }}
</style>
</head>
<body>
<h1>NewsBrief Demo Index</h1>
<p>Generated {ts}Z</p>
<p><strong>Feeds:</strong> <a href="feeds/index.xml">RSS</a> &middot; <a href="feeds/atom.xml">Atom</a></p>
<ul>
{rows}
</ul>
<p>Generated from fixture pipelines. Source on <a href="https://github.com/">GitHub</a>.</p>
</body>
</html>
""".format(ts=datetime.datetime.utcnow().isoformat(), rows=''.join(rows))

(PUB / "index.html").write_text(index, encoding="utf-8")
print(str(PUB / "index.html"))
