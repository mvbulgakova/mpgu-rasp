"""Validator for hand-entered group JSON files.

Usage:
    python -m scraper.hand_entry.validate path/to/group.json [more.json ...]

Exit code 0 = every file is valid. Non-zero = at least one has errors.
Errors are printed one per line with a JSON-pointer-like path so the human
can jump to the right spot in the file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Bell schedule — must match scraper/normalizer/schedule_normalizer.py:22-30
TIME_SLOTS: dict[int, tuple[str, str]] = {
    1: ("09:00", "10:30"),
    2: ("10:40", "12:10"),
    3: ("12:40", "14:10"),
    4: ("14:20", "15:50"),
    5: ("16:00", "17:30"),
    6: ("17:40", "19:10"),
    7: ("19:20", "20:50"),
}

VALID_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
VALID_TYPES = ("lecture", "practice", "lab", "seminar", "other")
VALID_FORMS = ("full_time", "part_time", "evening")
VALID_DEGREES = ("bachelor", "master", "specialist", "postgrad")

# Latin letters that look like Cyrillic — must never appear inside a group code.
# Mirrors HOMO in cloudflare-worker-bot/worker.js and scraper/telegram_bot.py.
LATIN_HOMOGLYPHS = set("ABCEHKMOPTXY")

CODE_ALLOWED_RE = re.compile(r"^[А-Яа-я0-9\-]+$")


def check_lesson(l: Any, path: str, errors: list[str]) -> None:
    if not isinstance(l, dict):
        errors.append(f"{path}: lesson must be an object, got {type(l).__name__}")
        return
    required = ("time_start", "time_end", "subject", "type", "teacher", "room", "subgroup", "notes")
    for k in required:
        if k not in l:
            errors.append(f"{path}: missing required field '{k}'")

    slot = l.get("slot")
    ts = l.get("time_start")
    te = l.get("time_end")

    if slot is not None:
        if not isinstance(slot, int) or slot not in TIME_SLOTS:
            errors.append(f"{path}.slot: must be an integer in 1..7 (got {slot!r})")
        else:
            expected_ts, expected_te = TIME_SLOTS[slot]
            if ts != expected_ts:
                errors.append(f"{path}.time_start: slot {slot} demands '{expected_ts}', got '{ts}'")
            if te != expected_te:
                errors.append(f"{path}.time_end: slot {slot} demands '{expected_te}', got '{te}'")
    else:
        # slot omitted → derive from time_start
        match = [n for n, (s, _e) in TIME_SLOTS.items() if s == ts]
        if not match:
            errors.append(
                f"{path}.time_start: '{ts}' is not a recognised slot start"
                f" (allowed: {', '.join(s for s, _ in TIME_SLOTS.values())})"
            )

    subj = l.get("subject", "")
    if not isinstance(subj, str) or len(subj.strip()) < 3:
        errors.append(f"{path}.subject: must be a non-trivial string (got {subj!r})")

    typ = l.get("type")
    if typ not in VALID_TYPES:
        errors.append(f"{path}.type: must be one of {VALID_TYPES} (got {typ!r})")

    for k in ("teacher", "room", "notes"):
        v = l.get(k)
        if v is not None and not isinstance(v, str):
            errors.append(f"{path}.{k}: must be string or null (got {type(v).__name__})")

    sg = l.get("subgroup")
    if sg is not None and sg not in (1, 2):
        errors.append(f"{path}.subgroup: must be 1, 2 or null (got {sg!r})")

    room = l.get("room")
    if isinstance(room, str) and "ауд" in room.lower():
        errors.append(
            f"{path}.room: strip the 'ауд.' prefix — the app prepends it. "
            f"Write just '{room.lower().replace('ауд.', '').replace('ауд', '').strip()}'"
        )


def check_week(week: Any, path: str, errors: list[str]) -> None:
    if not isinstance(week, dict):
        errors.append(f"{path}: must be an object with weekday keys")
        return
    for day, lessons in week.items():
        if day not in VALID_DAYS:
            errors.append(f"{path}.{day}: invalid weekday key (allowed: {', '.join(VALID_DAYS)})")
            continue
        if not isinstance(lessons, list):
            errors.append(f"{path}.{day}: must be a list of lessons")
            continue
        starts_seen: dict[tuple[str, int | None], int] = {}
        for i, l in enumerate(lessons):
            check_lesson(l, f"{path}.{day}[{i}]", errors)
            if isinstance(l, dict):
                key = (l.get("time_start"), l.get("subgroup"))
                if key in starts_seen:
                    errors.append(
                        f"{path}.{day}[{i}]: duplicate slot — a lesson at "
                        f"{key[0]} (subgroup {key[1]}) is already defined at "
                        f"index {starts_seen[key]}. Two lessons at the same time "
                        f"and subgroup would render as one in the app."
                    )
                else:
                    starts_seen[key] = i


def check_code(name: Any, errors: list[str]) -> None:
    if not isinstance(name, str) or not name:
        errors.append("name: group code must be a non-empty string")
        return
    for ch in name:
        if ch in LATIN_HOMOGLYPHS:
            errors.append(
                f"name: contains Latin '{ch}' which looks like a Cyrillic letter — "
                f"replace it with the Cyrillic look-alike so the app's search finds it."
            )
    if not CODE_ALLOWED_RE.match(name):
        errors.append(
            f"name: '{name}' has characters other than Cyrillic letters, digits and '-'. "
            f"Cross-check against the poster."
        )


def check_group(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"top-level: must be a JSON object, got {type(data).__name__}"]

    for k in ("name", "year", "form", "degree", "schedule"):
        if k not in data:
            errors.append(f"missing required top-level field '{k}'")

    check_code(data.get("name"), errors)

    year = data.get("year")
    if year is not None and (not isinstance(year, int) or year < 1 or year > 6):
        errors.append(f"year: must be an integer 1..6 or null (got {year!r})")

    form = data.get("form")
    if form not in VALID_FORMS and form is not None:
        errors.append(f"form: must be one of {VALID_FORMS} or null (got {form!r})")

    degree = data.get("degree")
    if degree not in VALID_DEGREES and degree is not None:
        errors.append(f"degree: must be one of {VALID_DEGREES} or null (got {degree!r})")

    schedule = data.get("schedule", {})
    if not isinstance(schedule, dict):
        errors.append("schedule: must be an object with 'odd_week' and 'even_week'")
    else:
        for wk in ("odd_week", "even_week"):
            if wk not in schedule:
                errors.append(f"schedule.{wk}: missing (put {{}} if truly empty)")
            else:
                check_week(schedule[wk], f"schedule.{wk}", errors)

    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: validate.py FILE [FILE ...]", file=sys.stderr)
        return 2

    any_bad = False
    for arg in argv:
        p = Path(arg)
        if not p.exists():
            print(f"✗ {arg}: file not found", file=sys.stderr)
            any_bad = True
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"✗ {arg}: invalid JSON — {e}", file=sys.stderr)
            any_bad = True
            continue
        errors = check_group(data)
        if errors:
            any_bad = True
            print(f"✗ {arg}: {len(errors)} error(s)")
            for e in errors:
                print(f"    {e}")
        else:
            print(f"✓ {arg}: valid")
    return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
