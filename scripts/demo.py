#!/usr/bin/env python3
"""
Demo brief generator for NewsBrief.

Generates fixture-based outputs (HTML, TXT, JSON, Cards HTML) into an output dir.
Used by CI and nightly workflows.

Examples:
  python scripts/demo.py --topic tech --limit 3 --format all --outdir scripts/out/tech
  python scripts/demo.py --topic ""   --limit 3 --format both --outdir scripts/out/ci
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _build_fixture_brief(topic: str, limit: int) -> dict:
    """Build a small, deterministic fixture brief for demos."""
    date_str = _dt.date.today().isoformat()
    topic_label = (topic or "Demo").strip() or "Demo"

    stories = []
    for i in range(1, max(1, int(limit)) + 1):
        sources = [
            {"id": 1, "title": "Fixture Source A", "url": "https://example.com/a"},
            {"id": 2, "title": "Fixture Source B", "url": "https://example.com/b"},
        ]
        summary_lines = [
            {"sentence": f"{topic_label} story {i}: key fact from Source A.", "source": 1},
            {"sentence": f"{topic_label} story {i}: corroborating detail from Source B.", "source": 2},
        ]
        stories.append(
            {
                "headline": f"{topic_label.title()} story {i} headline",
                "summary": summary_lines,
                "why_it_matters": "Demo output to verify pipelines (templates, feeds, schema).",
                "disputed": "",
                "sources": sources,
            }
        )

    return {
        "date": date_str,
        "headline": f"{topic_label.title()} Daily Brief",
        "stories": stories,
    }


def _render_txt(brief: dict) -> str:
    lines = [f"Daily Brief — {brief['date']}", ""]
    for s in brief["stories"]:
        lines.append(s["headline"])
        for ln in s["summary"]:
            lines.append(f"  • {ln['sentence']} [{ln['source']}]")
        if s.get("why_it_matters"):
            lines.append(f"  Why it matters: {s['why_it_matters']}")
        if s.get("disputed"):
            lines.append(f"  Disputed: {s['disputed']}")
        srcs = ", ".join(src["title"] for src in s["sources"])
        lines.append(f"  Sources: {srcs}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", type=str, default="", help="keyword to theme the demo stories")
    ap.add_argument("--limit", type=int, default=3, help="number of stories")
    ap.add_argument(
        "--format",
        type=str,
        choices=["html", "txt", "json", "cards", "both", "all"],
        default="both",
        help="output format(s): 'both' = html+txt, 'all' = html+txt+json+cards",
    )
    ap.add_argument("--outdir", type=str, default="scripts/out/demo", help="output directory")
    args = ap.parse_args()

    # Build brief data
    brief = _build_fixture_brief(args.topic, args.limit)
    date_str = brief["date"]

    OUT = Path(args.outdir).resolve()
    OUT.mkdir(parents=True, exist_ok=True)

    # Jinja environment for HTML templates
    env = Environment(
        loader=FileSystemLoader(str(Path("emailer") / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html_tpl = env.get_template("daily.html")
    cards_tpl = env.get_template("cards.html")

    paths: list[Path] = []

    # HTML
    if args.format in ("html", "both", "all"):
        html_out = html_tpl.render(date=brief["date"], stories=brief["stories"])
        html_path = OUT / f"daily-{date_str}.html"
        html_path.write_text(html_out, encoding="utf-8")
        paths.append(html_path)

    # TXT
    if args.format in ("txt", "both", "all"):
        txt_out = _render_txt(brief)
        txt_path = OUT / f"daily-{date_str}.txt"
        txt_path.write_text(txt_out, encoding="utf-8")
        paths.append(txt_path)

    # JSON manifest
    if args.format in ("json", "all"):
        json_path = OUT / f"daily-{date_str}.json"
        json_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(json_path)

    # Cards HTML
    if args.format in ("cards", "all"):
        cards_out = cards_tpl.render(date=brief["date"], stories=brief["stories"])
        cards_path = OUT / f"daily-{date_str}.cards.html"
        cards_path.write_text(cards_out, encoding="utf-8")
        paths.append(cards_path)

    # Print absolute paths for the workflow logs
    for p in paths:
        print(p)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
