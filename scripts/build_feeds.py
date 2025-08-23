
#!/usr/bin/env python3
"""Build RSS 2.0 and Atom 1.0 feeds from JSON manifests under scripts/out/**.

Usage:
  python scripts/build_feeds.py --base-url "https://<org>.github.io/<repo>" --public-dir public

Outputs:
  public/feeds/index.xml  (RSS 2.0)
  public/feeds/atom.xml   (Atom 1.0)
"""
from __future__ import annotations
import argparse, datetime, json, pathlib, html

def iso8601(dt: datetime.datetime) -> str:
    return dt.replace(microsecond=0, tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def rfc2822(dt: datetime.datetime) -> str:
    # Thu, 21 Aug 2025 07:00:00 GMT
    return dt.astimezone(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

def build_entry_title(m: dict) -> str:
    # Use manifest headline or "Daily Brief — YYYY-MM-DD"
    return m.get("headline") or f"Daily Brief — {m.get('date','')}"

def build_entry_desc(m: dict) -> str:
    heads = [s.get("headline","") for s in m.get("stories", []) if s.get("headline")]
    if not heads:
        return "Daily Brief"
    # Limit to first 5
    heads = heads[:5]
    return html.escape(" • ".join(heads))

def xml_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True, help="Base absolute URL for GitHub Pages, e.g., https://org.github.io/repo")
    ap.add_argument("--public-dir", default="public", help="Where to write feeds and copy assets")
    args = ap.parse_args()

    ROOT = pathlib.Path(__file__).resolve().parents[1]
    OUT = ROOT / "scripts" / "out"
    PUB = ROOT / args.public_dir
    FEEDS = PUB / "feeds"
    FEEDS.mkdir(parents=True, exist_ok=True)

    # Collect manifests
    manifests = []
    for p in sorted(OUT.rglob("*.json")):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        date = m.get("date")
        if not date:
            continue
        # Candidate pages to link (prefer cards.html, then html, then txt)
        # Build relative paths under public/
        rel_dir = p.parent.relative_to(OUT)
        prefix = f"{args.base_url}/{rel_dir}".rstrip("/")
        base = f"daily-{date}"
        hrefs = [
            f"{prefix}/{base}.cards.html",
            f"{prefix}/{base}.html",
            f"{prefix}/{base}.txt",
        ]
        manifests.append({
            "date": date,
            "manifest": m,
            "hrefs": hrefs,
            "path": str(p.relative_to(ROOT)),
        })

    if not manifests:
        # write minimal empty feeds
        now = datetime.datetime.utcnow()
        empty_rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>NewsBrief Demo Feed</title>
  <link>{xml_escape(args.base_url)}</link>
  <description>Demo feed (no entries yet)</description>
  <lastBuildDate>{rfc2822(now)}</lastBuildDate>
</channel></rss>"""
        (FEEDS / "index.xml").write_text(empty_rss, encoding="utf-8")
        empty_atom = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>NewsBrief Demo Feed</title>
  <id>{xml_escape(args.base_url)}</id>
  <updated>{iso8601(now)}</updated>
  <link href="{xml_escape(args.base_url)}" />
</feed>"""
        (FEEDS / "atom.xml").write_text(empty_atom, encoding="utf-8")
        print("No manifests found; wrote empty feeds")
        return

    # Sort newest first
    manifests.sort(key=lambda x: x["date"], reverse=True)

    # Build RSS
    now = datetime.datetime.utcnow()
    rss_items = []
    for item in manifests:
        m = item["manifest"]
        date = item["date"]
        title = xml_escape(build_entry_title(m))
        desc = build_entry_desc(m)
        link = xml_escape(item["hrefs"][0])
        pub = rfc2822(datetime.datetime.fromisoformat(date))
        rss_items.append(f"""  <item>
    <title>{title}</title>
    <link>{link}</link>
    <guid isPermaLink="true">{link}</guid>
    <pubDate>{pub}</pubDate>
    <description>{desc}</description>
  </item>""")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>NewsBrief Demo Feed</title>
  <link>{xml_escape(args.base_url)}</link>
  <description>Fixture-based demo briefs</description>
  <lastBuildDate>{rfc2822(now)}</lastBuildDate>
{chr(10).join(rss_items)}
</channel></rss>"""
    (FEEDS / "index.xml").write_text(rss, encoding="utf-8")

    # Build Atom
    atom_entries = []
    for item in manifests:
        m = item["manifest"]
        date = item["date"]
        updated = iso8601(datetime.datetime.fromisoformat(date))
        title = xml_escape(build_entry_title(m))
        link = xml_escape(item["hrefs"][0])
        atom_entries.append(f"""  <entry>
    <title>{title}</title>
    <id>{link}</id>
    <link href="{link}" />
    <updated>{updated}</updated>
    <summary type="html">{build_entry_desc(m)}</summary>
  </entry>""")
    atom = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>NewsBrief Demo Feed</title>
  <id>{xml_escape(args.base_url)}</id>
  <updated>{iso8601(now)}</updated>
  <link href="{xml_escape(args.base_url)}" />
{chr(10).join(atom_entries)}
</feed>"""
    (FEEDS / "atom.xml").write_text(atom, encoding="utf-8")

    print(FEEDS / "index.xml")
    print(FEEDS / "atom.xml")

if __name__ == "__main__":
    main()
