#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, re, sys
from pathlib import Path
import feedparser, trafilatura, yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "emailer" / "templates"

def norm(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s

def hsh(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:10]

def fetch_items(urls: list[str], max_items: int) -> list[dict]:
    out = []
    for u in urls:
        try:
            feed = feedparser.parse(u)
        except Exception:
            continue
        for e in feed.entries[: max_items * 2]:
            title = norm(getattr(e, "title", ""))
            link = getattr(e, "link", "")
            summary = norm(getattr(e, "summary", "") or getattr(e, "description", ""))
            if not (title and link):
                continue
            out.append({"title": title, "link": link, "summary": summary})
    return out

def extract_text(url: str) -> str:
    try:
        txt = trafilatura.fetch_url(url)
        if not txt:
            return ""
        art = trafilatura.extract(txt, include_comments=False, include_tables=False, favor_recall=True)
        return norm(art or "")
    except Exception:
        return ""

def dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    uniq = []
    for it in items:
        key = hsh(it["title"].lower())
        if key in seen: 
            continue
        seen.add(key); uniq.append(it)
    return uniq

def build_manifest(topic: str, items: list[dict], limit: int) -> dict:
    date_str = dt.date.today().isoformat()
    stories = []
    for i, it in enumerate(items[:limit], 1):
        text = extract_text(it["link"])
        # Minimal, safe “summary” lines from sources (no model yet)
        lines = []
        if it["summary"]:
            lines.append({"sentence": it["summary"][:220], "source": 1})
        if text:
            lines.append({"sentence": text[:220], "source": 2})
        if not lines:
            lines.append({"sentence": it["title"], "source": 1})
        stories.append({
            "headline": it["title"],
            "summary": lines,
            "why_it_matters": "Auto-generated from live sources (prototype).",
            "disputed": "",
            "sources": [
                {"id": 1, "title": "Feed", "url": it["link"]},
                {"id": 2, "title": "Extracted", "url": it["link"]},
            ],
        })
    return {"date": date_str, "headline": f"{topic.title()} Daily Brief", "stories": stories}

def render_outputs(brief: dict, outdir: Path) -> list[Path]:
    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=select_autoescape(["html","xml"]))
    daily_tpl = env.get_template("daily.html")
    cards_tpl = env.get_template("cards.html")
    outdir.mkdir(parents=True, exist_ok=True)
    date_str = brief["date"]
    paths = []
    (outdir / f"daily-{date_str}.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"); paths.append(outdir / f"daily-{date_str}.json")
    # TXT (simple)
    txt_lines = [f"Daily Brief — {date_str}", ""]
    for s in brief["stories"]:
        txt_lines.append(s["headline"])
        for ln in s["summary"]:
            txt_lines.append(f"  • {ln['sentence']} [{ln['source']}]")
        txt_lines.append("")
    (outdir / f"daily-{date_str}.txt").write_text("\n".join(txt_lines).strip()+"\n", encoding="utf-8"); paths.append(outdir / f"daily-{date_str}.txt")
    # HTMLs
    (outdir / f"daily-{date_str}.html").write_text(daily_tpl.render(date=brief["date"], stories=brief["stories"]), encoding="utf-8"); paths.append(outdir / f"daily-{date_str}.html")
    (outdir / f"daily-{date_str}.cards.html").write_text(cards_tpl.render(date=brief["date"], stories=brief["stories"]), encoding="utf-8"); paths.append(outdir / f"daily-{date_str}.cards.html")
    return paths

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--sources", type=str, default=str(ROOT / "config" / "sources.yaml"))
    ap.add_argument("--outdir", type=str, default="scripts/out/live")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8"))
    urls = cfg.get(args.topic, [])
    if not urls:
        print(f"No feeds configured for topic={args.topic}", file=sys.stderr)
        return 2

    items = fetch_items(urls, max_items=args.limit)
    items = dedupe(items)
    brief = build_manifest(args.topic, items, args.limit)
    out = Path(args.outdir) / args.topic
    paths = render_outputs(brief, out)
    for p in paths: print(p)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
