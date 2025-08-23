
#!/usr/bin/env python3
"""Validate demo JSON manifests in scripts/out/** against schemas/brief_manifest.schema.json."""
import sys, json, pathlib
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "brief_manifest.schema.json").read_text(encoding="utf-8"))

def main() -> int:
    validator = Draft202012Validator(SCHEMA)
    json_paths = list((ROOT / "scripts" / "out").rglob("*.json"))
    if not json_paths:
        print("No JSON manifests found under scripts/out/", file=sys.stderr)
        return 0
    failures = 0
    for p in json_paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        errs = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errs:
            failures += 1
            print(f"❌ {p}: {len(errs)} error(s)")
            for e in errs:
                path = "$" + "".join([f"[{repr(x)}]" if isinstance(x, int) else f".{x}" for x in e.path])
                print(f"  - {path}: {e.message}")
        else:
            print(f"✅ {p} is valid")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
