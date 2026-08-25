"""Publisher for hand-entered group files.

Copies a validated group JSON into the data-branch worktree, adds/updates the
institute's schedule.json manifest, and updates meta/index.json. Runs
validation first — refuses to publish an invalid file.

The publisher stages the changes with `git add` but does NOT commit or push;
that step is intentionally manual so the human can review with `git diff --staged`.

Usage:
    python -m scraper.hand_entry.publish path/to/group.json \\
            --institute geography \\
            --data-branch .data-wt

The institute must already exist in `meta/index.json` OR be listed in
`scraper/config/institutes.json` — in that case the publisher creates the
institute directory + manifest + index entry on the fly.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scraper.hand_entry.validate import check_group

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "institutes.json"


def _load_institute_config(institute_id: str) -> dict:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for i in data["institutes"]:
        if i["id"] == institute_id:
            return i
    raise SystemExit(
        f"institute '{institute_id}' not found in {CONFIG_PATH}. "
        f"Add it there first."
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise SystemExit(f"{p}: existing file is not valid JSON; refuse to overwrite")


def _write_json(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(source: Path, institute_id: str, data_branch: Path) -> None:
    group_data = json.loads(source.read_text(encoding="utf-8"))
    errors = check_group(group_data)
    if errors:
        print(f"✗ refusing to publish — {source} has {len(errors)} validation error(s):")
        for e in errors:
            print(f"    {e}")
        raise SystemExit(1)

    inst_cfg = _load_institute_config(institute_id)
    inst_dir = data_branch / "institutes" / institute_id
    groups_dir = inst_dir / "groups"

    # 1. Write the group file itself.
    group_file = groups_dir / f"{group_data['name']}.json"
    _write_json(group_file, group_data)
    print(f"wrote {group_file}")

    # 2. Update the institute manifest (institutes/<id>/schedule.json).
    manifest_path = inst_dir / "schedule.json"
    manifest = _read_json(manifest_path)
    manifest.setdefault("institute_id", institute_id)
    manifest.setdefault("institute_name", inst_cfg.get("name", institute_id))
    manifest.setdefault("short_name", inst_cfg.get("short_name"))
    manifest.setdefault("academic_year", None)
    manifest["updated_at"] = _now_iso()
    manifest.setdefault("parser_used", "hand_entry")
    manifest.setdefault("version", 1)
    manifest.setdefault("groups", [])

    # replace or add this group's entry
    entry = {
        "name": group_data["name"],
        "file": group_data["name"],
        "year": group_data.get("year"),
        "form": group_data.get("form"),
        "degree": group_data.get("degree"),
    }
    groups_list = manifest["groups"]
    for i, g in enumerate(groups_list):
        if g.get("name") == group_data["name"]:
            groups_list[i] = entry
            break
    else:
        groups_list.append(entry)
    _write_json(manifest_path, manifest)
    print(f"updated {manifest_path}  ({len(groups_list)} groups)")

    # 3. Update meta/index.json's roll-up.
    index_path = data_branch / "meta" / "index.json"
    index = _read_json(index_path)
    index.setdefault("institutes", [])
    idx_entry = {
        "id": institute_id,
        "name": inst_cfg.get("name", institute_id),
        "short_name": inst_cfg.get("short_name"),
        "groups_count": len(groups_list),
        "updated_at": manifest["updated_at"],
    }
    inst_list = index["institutes"]
    for i, e in enumerate(inst_list):
        if e.get("id") == institute_id:
            e.update(idx_entry)  # keep any extra fields (campus etc.)
            break
    else:
        inst_list.append(idx_entry)
    _write_json(index_path, index)
    print(f"updated {index_path}  ({len(inst_list)} institutes)")

    # 4. Stage in git so `git diff --staged` shows the impending change.
    try:
        subprocess.run(
            ["git", "add", str(group_file.relative_to(data_branch)),
                          str(manifest_path.relative_to(data_branch)),
                          str(index_path.relative_to(data_branch))],
            cwd=data_branch,
            check=True,
        )
        print(f"staged in git (cwd={data_branch}). Review with `git diff --staged`, then commit + push.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"⚠ could not `git add` ({e}). Files are on disk; add them manually.")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", type=Path, help="path to the group JSON to publish")
    p.add_argument("--institute", required=True, help="institute id (e.g. geography)")
    p.add_argument("--data-branch", type=Path, required=True,
                   help="path to the data-branch worktree (typically .data-wt at repo root)")
    args = p.parse_args(argv)

    if not args.source.exists():
        print(f"source file not found: {args.source}", file=sys.stderr)
        return 2
    if not args.data_branch.exists():
        print(f"data-branch worktree not found: {args.data_branch}", file=sys.stderr)
        return 2

    publish(args.source, args.institute, args.data_branch)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
