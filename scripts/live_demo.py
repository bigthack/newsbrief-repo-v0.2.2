#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import feedparser, trafilatura, yaml

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Local fetcher with UA/retries/robots/budget
from scripts.http_fetch import build_session, fetch_html, FetchConfig, RobotsCache, Budget

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "emailer" / "templates"
CFG_SOURCES = ROOT / "config" / "sources.yaml"
CFG_IPTC = ROOT / "config" / "iptc_map.yaml"
METRICS_DIR = ROOT / "data" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_FILE = METRICS_DIR / "brief_metrics.jsonl"

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def title_key(title: str) -> str:
    """Stable dedupe key: normalize title, strip punctuation/stopwords."""
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    stop = {"the","a","an","of","to","and","in","on","for","with","at","from","by"}
    toks = [w for w in t.split() if w not in stop]
    t = " ".join(toks) or title.lower()
    return hashlib.sha1(t.encode("utf-8","ignore")).hexdigest()[:12]

def fetch_items(urls: list[str], max_items: int) -> list[dict]:
    out: list[dict] = []
    for u in urls:
        try:
            feed = feedparser.parse(u)
        except Exception:
            continue
        for e in feed.entries[: max_items * 3]:
            title = norm(getattr(e, "title", ""))
            link = getattr(e, "link", "")
            summary = norm(getattr(e, "summary", "") or getattr(e, "description", ""))
            if not (title and link):
                continue
            out.append({"title": title, "link": link, "summary": summary, "domain": domain(link)})
    return out

def dedupe_title_domain(items: list[dict]) -> list[dict]:
    seen = set()
    uniq = []
    for it in items:
        k = (title_key(it["title"]), it["domain"])
        if k in seen: 
            continue
        seen.add(k)
        uniq.append(it)
    return uniq

def cluster_by_title(items: list[dict]) -> list[list[dict]]:
    """Small, deterministic clusters: same normalized title_key across domains."""
    groups = defaultdict(list)
    for it in items:
        groups[title_key(it["title"])].append(it)
    # Keep only clusters with at least 1 item (always true); sort by size desc
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]["title"]))

def extract_texts(session, cfg, robots, allowlist, budget, items: list[dict]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for it in items:
        html = fetch_html(session, it["link"], cfg, robots, allowlist, budget)
        if not html:
            texts[it["link"]] = ""
            continue
        try:
            art = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                favor_recall=True,
            )
            texts[it["link"]] = norm(art or "")
        except Exception:
            texts[it["link"]] = ""
    return texts

def split_sentences(text: str, max_len: int = 240) -> list[str]:
    # Very simple sentence split; good enough for prototypes
    raw = re.split(r"(?<=[\.\!\?])\s+", text)
    sents = []
    for s in raw:
        s = norm(s)
        if not s:
            continue
        if len(s) > max_len:
            s = s[: max_len - 1] + "…"
        sents.append(s)
    return sents[:4]

def select_citation_spans(cluster_items: list[dict], texts: dict[str,str], max_spans_per_src: int = 1) -> list[tuple[str, str]]:
    """Pick short spans from each source to use as 'quotes' for summary."""
    spans: list[tuple[str, str]] = []
    for it in cluster_items:
        txt = texts.get(it["link"], "")
        sents = split_sentences(txt) if txt else (split_sentences(it["summary"]) if it["summary"] else [])
        if not sents:
            continue
        spans.append((it["link"], sents[0]))
        if len(spans) >= 3:  # keep summary tight
            break
    # Ensure at least one span by falling back to titles
    if not spans and cluster_items:
        spans.append((cluster_items[0]["link"], cluster_items[0]["title"]))
    return spans

def build_story_from_cluster(topic: str, cluster_items: list[dict], texts: dict[str,str]) -> dict:
    # Build sources list (order matters → citation numbers)
    sources = []
    link_to_id = {}
    for idx, it in enumerate(cluster_items, start=1):
        sources.append({"id": idx, "title": it["domain"] or "Source", "url": it["link"]})
        link_to_id[it["link"]] = idx

    spans = select_citation_spans(cluster_items, texts)
    summary_lines = [{"sentence": span, "source": link_to_id[link]} for (link, span) in spans]

    headline = cluster_items[0]["title"]
    return {
        "headline": headline,
        "summary": summary_lines,
        "why_it_matters": "Auto-generated from live sources; each line cites a source [n].",
        "disputed": "",
        "sources": sources[: max(2, len(summary_lines))],  # keep sources list small
    }

def iptc_guess(iptc_cfg: dict, url: str) -> str:
    dom = domain(url)
    topics = iptc_cfg.get("topics", {})
    for label, doms in topics.items():
        if dom in doms:
            return label
    return "general"

def render_outputs(brief: dict, outdir: Path) -> list[Path]:
    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=select_autoescape(["html","xml"]))
    daily_tpl = env.get_template("daily.html")
    cards_tpl = env.get_template("cards.html")
    outdir.mkdir(parents=True, exist_ok=True)
    date_str = brief["date"]
    paths: list[Path] = []
    # JSON
    p = outdir / f"daily-{date_str}.json"
    p.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"); paths.append(p)
    # TXT
    txt_lines = [f"Daily Brief — {date_str}", ""]
    for s in brief["stories"]:
        txt_lines.append(s["headline"])
        for ln in s["summary"]:
            txt_lines.append(f"  • {ln['sentence']} [{ln['source']}]")
        txt_lines.append("")
    p = outdir / f"daily-{date_str}.txt"
    p.write_text("\n".join(txt_lines).strip()+"\n", encoding="utf-8"); paths.append(p)
    # HTMLs
    p = outdir / f"daily-{date_str}.html"
    p.write_text(daily_tpl.render(date=brief["date"], stories=brief["stories"]), encoding="utf-8"); paths.append(p)
    p = outdir / f"daily-{date_str}.cards.html"
    p.write_text(cards_tpl.render(date=brief["date"], stories=brief["stories"]), encoding="utf-8"); paths.append(p)
    return paths

def log_metrics(topic: str, stories: list[dict], items: list[dict]) -> None:
    doms = [domain(src["url"]) for story in stories for src in story["sources"]]
    counts = Counter([d for d in doms if d])
    entry = {
        "date": dt.datetime.utcnow().isoformat() + "Z",
        "topic": topic,
        "stories": len(stories),
        "unique_domains": len(counts),
        "domain_counts": counts,
    }
    # jsonify Counters
    entry["domain_counts"] = {k:int(v) for k,v in entry["domain_counts"].items()}
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Helpful rollup to Action logs
    print(f"Telemetry: {entry}")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--sources", type=str, default=str(CFG_SOURCES))
    ap.add_argument("--iptc", type=str, default=str(CFG_IPTC))
    ap.add_argument("--outdir", type=str, default="scripts/out/live")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8"))
    urls = cfg.get(args.topic, [])
    if not urls:
        print(f"No feeds configured for topic={args.topic}", file=sys.stderr)
        return 2

    iptc_cfg = {}
    if Path(args.iptc).exists():
        iptc_cfg = yaml.safe_load(Path(args.iptc).read_text(encoding="utf-8")) or {}

    # Allowlist domains = domains present in the configured feeds’ article links (approx)
    allow_domains = set()
    for u in urls:
        try:
            d = urlparse(u).netloc.lower()
            if d: allow_domains.add(d)
        except Exception:
            pass

    items = fetch_items(urls, max_items=args.limit)
    items = dedupe_title_domain(items)

    # HTTP session with retries and UA; robots + budget
    fetch_cfg = FetchConfig()
    session = build_session(fetch_cfg)
    robots = RobotsCache()
    budget = Budget(total=int(os.getenv("NB_MAX_REQUESTS", "40")))

    # Extract article texts with guards
    texts = extract_texts(session, fetch_cfg, robots, allow_domains, budget, items)

    # Simple “clusters” by normalized title
    clusters = cluster_by_title(items)

    # Build stories (one per cluster), cap to limit
    stories = []
    for cl in clusters[: args.limit]:
        story = build_story_from_cluster(args.topic, cl, texts)
        # Tiny QA: keep only sentences that are direct spans from sources (they are)
        stories.append(story)

    cfg = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8")) or {}
    topics = sorted(cfg.keys())
    urls = cfg.get(args.topic, [])
    if not urls:
        print(f"No feeds configured for topic={args.topic}. Available: {', '.join(topics) or '(none)'}", file=sys.stderr)
        raise SystemExit(2)



    date_str = dt.date.today().isoformat()
    brief = {"date": date_str, "headline": f"{args.topic.title()} Daily Brief", "stories": stories}

    # Render + telemetry
    out = Path(args.outdir) / args.topic
    paths = render_outputs(brief, out)
    for p in paths: print(p)
    log_metrics(args.topic, stories, items)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
