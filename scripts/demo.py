
#!/usr/bin/env python3
"""Tiny E2E demo with CLI flags:
- Parse fixture RSS feeds (file://).
- Optionally filter by --topic keyword(s) and --limit number of stories.
- Extract main text, de-dupe near-duplicates.
- Render daily brief email (HTML + TXT) with Jinja2.
Outputs to --outdir (default: ./scripts/out/).
"""

from __future__ import annotations
import pathlib, datetime, os, argparse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ingestion.feeds.adapters.generic import GenericRSSAdapter
from ingestion.feeds import extractor, dedupe

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"

def _file_uri(p: pathlib.Path) -> str:
    return p.resolve().as_uri()

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", type=str, default="", help="keyword filter (e.g., tech, climate)")
    ap.add_argument("--limit", type=int, default=5, help="max stories in the brief")
    ap.add_argument("--date", type=str, default="", help="YYYY-MM-DD override for brief date")
    ap.add_argument("--outdir", type=str, default=str(ROOT / "scripts" / "out"), help="output folder")
    ap.add_argument("--format", type=str, choices=["html","txt","json","cards","both","all"], default="both", help="output format")
    return ap.parse_args()

def main():
    args = parse_args()
    OUT = pathlib.Path(args.outdir)
    OUT.mkdir(parents=True, exist_ok=True)

    feeds = [
        _file_uri(FIX / "rss" / "bbc.xml"),
        _file_uri(FIX / "rss" / "reuters.xml"),
    ]
    adapter = GenericRSSAdapter()
    items = []
    for u in feeds:
        items.extend(adapter.fetch_feed(u))

    # simple topic keyword filter across title/description (case-insensitive)
    topic_kw = (args.topic or "").strip().lower()
    if topic_kw:
        def keep(it):
            blob = ((it.title or "") + " " + (it.description or "")).lower()
            return topic_kw in blob
        items = [it for it in items if keep(it)]

    # map to fixture HTML content when title matches, else use description/title
    html_map = {
        "Markets rally on tech earnings": FIX / "html" / "article1.html",
        "Leaders meet to discuss climate goals": FIX / "html" / "article2.html",
    }

    stories = []
    for it in items[: max(args.limit, 1)]:
        html_path = None
        for k, p in html_map.items():
            if k.lower() in it.title.lower():
                html_path = p; break

        if html_path and html_path.exists():
            html = html_path.read_text(encoding="utf-8")
            text = extractor.extract_main_text(html)
        else:
            text = (it.description or it.title or "").strip()

        stories.append({
            "headline": it.title,
            "text": text,
            "source_url": it.url,
            "published_at": it.published_at,
        })

    # near-dup filter
    filtered = []
    for s in stories:
        if not any(dedupe.is_near_duplicate(s["text"], t["text"]) for t in filtered):
            filtered.append(s)

    # brief JSON
    date_str = args.date or datetime.date.today().isoformat()
    brief = {
        "date": date_str,
        "headline": "Demo Daily Brief",
        "stories": []
    }
    for s in filtered:
        brief["stories"].append({
            "headline": s["headline"],
            "summary": [
                {"sentence": s["text"][:160] + ("..." if len(s["text"])>160 else ""), "source": 1}
            ],
            "why_it_matters": "Demo output from fixtures",
            "disputed": "",
            "sources": [
                {"id": 1, "title": "Source", "url": s["source_url"]}
            ]
        })

    # render
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "emailer" / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html_tpl = env.get_template("daily.html")
    cards_tpl = env.get_template("cards.html")
    txt_tpl = env.get_template("daily.txt")

    paths = []
    json_manifest = None
    if args.format in ("html", "both"):
        html_out = html_tpl.render(date=brief["date"], stories=brief["stories"])
        html_path = OUT / f"daily-{date_str}.html"
        html_path.write_text(html_out, encoding="utf-8")
        paths.append(html_path)

    if args.format in ("txt", "both"):
        txt_out  = txt_tpl.render(date=brief["date"], stories=brief["stories"])
        txt_path = OUT / f"daily-{date_str}.txt"
        txt_path.write_text(txt_out, encoding="utf-8")


if args.format in ("cards", "all"):
    cards_out = cards_tpl.render(date=brief["date"], stories=brief["stories"])
    cards_path = OUT / f"daily-{date_str}.cards.html"
    cards_path.write_text(cards_out, encoding="utf-8")
    paths.append(cards_path)

        paths.append(txt_path)


# JSON manifest (optional)
if args.format in ("json", "all"):
    json_manifest = {
        "date": brief["date"],
        "headline": brief.get("headline", "Demo Daily Brief"),
        "stories": brief["stories"],
    }
    json_path = OUT / f"daily-{date_str}.json"
    json_path.write_text(__import__("json").dumps(json_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.append(json_path)

    for p in paths:
        print(p)

if __name__ == "__main__":
    main()
