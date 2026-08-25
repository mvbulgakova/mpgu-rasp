# Hand-entering a group's schedule

For institutes / groups where the auto-parser is unreliable (see
`docs/audits/2026-08-25-parser-audit.md`) we type schedules by hand.
The result is a JSON file that Android/PWA read verbatim from the
`data` branch — same schema, same layout — so hand-entered and
auto-parsed groups are indistinguishable to the client.

## What you need

- The source PDF/xlsx or a photo from the deanery.
- A text editor.
- Python 3.10+ to run the validator (`validate.py`).
- Access to the `data` branch worktree (`.data-wt/` at repo root) OR
  a checkout of the `data` branch elsewhere.

## The workflow

1. Copy `template.json` next to your work, rename it after the group code
   (e.g. `БОП40-ПФК2501.json`). Keep the exact code (Cyrillic).
2. Fill in every field. See the field guide below.
3. `python -m scraper.hand_entry.validate ./БОП40-ПФК2501.json`
   → prints ✓ if OK, otherwise lists errors line-by-line.
4. Publish:
   `python -m scraper.hand_entry.publish ./БОП40-ПФК2501.json \
       --institute geography --data-branch .data-wt`
   → copies the file into `institutes/geography/groups/`, updates
   `institutes/geography/schedule.json` (manifest) and
   `meta/index.json` (roll-up), stages the changes in git. Commit +
   push are yours to run.

If you'd rather skip Python: after `validate.py` prints ✓, drop the
file into `.data-wt/institutes/<id>/groups/` yourself and add its
name to `.data-wt/institutes/<id>/schedule.json`'s `groups` array.
The publisher just automates that step.

## Field guide (see also `template.json`)

```jsonc
{
  "name":   "БОП40-ПФК2501",   // group code, Cyrillic, matches poster
  "year":   1,                  // 1..6 or null
  "form":   "full_time",        // full_time | part_time | evening
  "degree": "bachelor",         // bachelor | master | specialist | postgrad
  "schedule": {
    "odd_week":  { "monday": [ ...lessons ], "tuesday": [ ... ], ... },
    "even_week": { "monday": [ ... ], ... }
  }
}
```

Weekday keys are lowercase English: `monday`, `tuesday`, `wednesday`,
`thursday`, `friday`, `saturday`, `sunday`. Omit weekdays with no lessons.

Each lesson:

```jsonc
{
  "slot":        2,             // 1..7, MUST match MPGU bell schedule
  "time_start":  "10:40",       // HH:MM, MUST match one of the 7 slot starts
  "time_end":    "12:10",       // HH:MM, MUST match its slot end
  "subject":     "Общая физика",
  "type":        "lecture",     // lecture | practice | lab | seminar | other
  "teacher":     "Доц. Иванов А.В.",  // or null
  "room":        "301",         // "301" or "302 / 303" for multi-rooms, or null
  "subgroup":    1,             // 1 or 2 or null (null = the whole group)
  "notes":       ""             // extra info, or ""
}
```

### Slot / time correspondence (must match exactly)

The scraper stamps `slot: N` on every auto-parsed lesson using this table.
Kotlin/JS reader expect the same. Use the exact `time_start`/`time_end`
below or the validator will reject the file.

| Slot | Start | End   |
|------|-------|-------|
| 1    | 09:00 | 10:30 |
| 2    | 10:40 | 12:10 |
| 3    | 12:40 | 14:10 |
| 4    | 14:20 | 15:50 |
| 5    | 16:00 | 17:30 |
| 6    | 17:40 | 19:10 |
| 7    | 19:20 | 20:50 |

Source: `scraper/normalizer/schedule_normalizer.py:22–30`.

### Odd / even week (числитель/знаменатель)

- If the same lesson happens EVERY week, put it in BOTH `odd_week` and
  `even_week` (identical entries).
- If the schedule PDF has a single column and no odd/even markings, treat
  every lesson as "both weeks" — same rule.
- If PDF says "числитель" or "нечётная" or "н/", put in `odd_week`.
- If PDF says "знаменатель" or "чётная" or "з/", put in `even_week`.

### Group code (Cyrillic, no homoglyphs)

Codes look like `БОП40-ПФК2501`. Use the CYRILLIC letters exactly:
`А, В, Е, К, М, Н, О, Р, С, Т, У, Х` — even though the PDF font may
render them looking like Latin. The validator will flag any Latin
lookalike in the code.

### Subgroup

- If the lesson runs for the whole group → `"subgroup": null`.
- If it runs only for the first половина группы → `"subgroup": 1`.
- If only для second half → `"subgroup": 2`.
- If the PDF says "п/г 3" or higher, ask the deanery to explain — MPGU
  splits into 2 subgroups conventionally.

## After publishing

The Android app reads `https://cdn.jsdelivr.net/gh/mvbulgakova/mpgu-rasp@data/institutes/<id>/groups/<name>.json` directly. jsDelivr's
edge cache has a ~12 h TTL — for a hard refresh append `?v=<timestamp>`
via the app's manual-refresh action (once wired) or wait it out.

## What NOT to hand-enter

Do not hand-enter data that the auto-parser handled correctly for the
current release — you would create a divergence risk. The audit doc lists
which institutes the parser today handles versus needs help.
