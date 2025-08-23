# newsbrief

A scaffold for an AI-powered daily news brief. Contracts-first, tests-first, and agent-friendly.

## Quick start

```bash
cp .env.example .env
make up      # start stack (db/redis/minio/api)
make test    # run pytest
```


### Demo (fixtures → rendered brief)
```bash
make demo   # writes HTML+TXT under scripts/out/
```
Open the generated HTML to preview the layout.


### CI artifacts
The GitHub Actions workflow runs `scripts/demo.py` on fixtures and uploads the rendered **demo brief** as a build artifact (`demo-brief`).

### Demo flags
```bash
# Change the topic keyword, limit items, or set a custom date/output
make demo TOPIC=tech LIMIT=3 DATE=2025-01-01 FORMAT=html OUTDIR=scripts/out
```


### Nightly demo workflow
A nightly GitHub Actions run renders demo briefs from fixtures and uploads them as artifacts.

> **Badge (update repo path after you push):**
>
> `![Nightly Demo](https://github.com/YOUR_GH_ORG/YOUR_REPO/actions/workflows/nightly.yml/badge.svg)`
>
> Replace `YOUR_GH_ORG/YOUR_REPO` after importing this scaffold.



### Badges
[![CI](https://github.com/YOUR_GH_ORG/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_GH_ORG/YOUR_REPO/actions/workflows/ci.yml)
> Replace `YOUR_GH_ORG/YOUR_REPO` after pushing.

[![Nightly Demo](https://github.com/YOUR_GH_ORG/YOUR_REPO/actions/workflows/nightly.yml/badge.svg)](https://github.com/YOUR_GH_ORG/YOUR_REPO/actions/workflows/nightly.yml)
[![Pages](https://img.shields.io/badge/Pages-live-brightgreen)](https://YOUR_GH_ORG.github.io/YOUR_REPO/)


### JSON manifests
`scripts/demo.py` now supports `--format json` or `--format all`, emitting `daily-YYYY-MM-DD.json` alongside HTML/TXT.
These are copied to `public/` and listed on the GitHub Pages index.

### Ad-hoc publishes (workflow_dispatch inputs)
From the **Actions** tab, choose the `nightly-demo` workflow → **Run workflow**:
- **topic**: keyword filter (e.g., `tech`, `climate`) — leave blank to skip and rely on defaults.
- **limit**: number of stories (default `3`).
- **format**: `html`, `txt`, `json`, `both`, or `all` (default `all`).

Artifacts + the **Pages site** will include the generated files under `manual/`.


### Manifest schema
Schema lives at `schemas/brief_manifest.schema.json` (JSON Schema Draft 2020-12).  
Validate locally:
```bash
pip install jsonschema
python scripts/demo.py --format all --outdir scripts/out
python scripts/validate_manifest.py
```

### Cards layout
Render a compact grid preview for GitHub Pages:
```bash
python scripts/demo.py --format cards --outdir scripts/out/cards
python scripts/build_pages_index.py
open public/index.html
```


### Feeds
Nightly publishes demo feeds to GitHub Pages:
- **RSS**: `/feeds/index.xml`
- **Atom**: `/feeds/atom.xml`

The base URL is auto-derived from the GitHub repo in Actions; override locally via:
```bash
make pages BASE_URL="http://localhost:8000/your/local/path"
```

### Make targets
```bash
make demo     # run fixtures → demo brief
make validate # validate JSON manifests against schema
make pages    # build static site & feeds (BASE_URL configurable)
```
