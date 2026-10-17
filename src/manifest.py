import json
import os
from datetime import datetime, timezone
from . import config


def build(topic, fmt_name, cuts, presenter, records, dry_run):
    return {
        "created": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "format": fmt_name,
        "dry_run": dry_run,
        "cuts": len(cuts),
        "presenter_cuts": sorted(presenter),
        "assets": records,
        "all_allowed": all(r["allowed"] for r in records),
    }


def write(manifest, path=None):
    path = path or os.path.join(config.WORKDIR, "manifest.json")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path


def summary(manifest):
    stock = sum(1 for r in manifest["assets"] if r["provider"] == "pixabay")
    own = sum(1 for r in manifest["assets"] if r["provider"] == "own")
    rights_ok = "yes" if manifest["all_allowed"] else "NO"
    return (f"Dry run report\n"
            f"Format: {manifest['format']}\n"
            f"Cuts: {manifest['cuts']}, presenter cuts: {len(manifest['presenter_cuts'])}\n"
            f"Stock clips: {stock}, presenter clips: {own}\n"
            f"All footage licensed: {rights_ok}")