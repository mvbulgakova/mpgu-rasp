# Parser accuracy audit — 25.08.2026

Local run of `scraper.parsers.PDFParser` + `sanitize_groups` on two spring-2026
PDFs from institutes marked ✅ in `docs/plan.md`. Line-by-line manual comparison
against the source PDFs.

**Verdict:** parser output has both cosmetic and semantic defects visible in
every group we inspected. Confidence score reads 1.00 but is not a proxy for
correctness. Not fit for an accuracy-critical MVP as-is.

**Recommendation:** hand-enter the first release's groups; keep parser output
as an informational cache/comparator, not as the source of truth.

## What we tested

| PDF | Institute | Confidence | Groups extracted |
|---|---|---|---|
| `geo_5-kurs.pdf` (спринг, 5 курс geo) | geography | 1.00 | 2 (БОГ35-ГЭК2101, БОГ35-ГИН2101) |
| `raspisanie-1-kurs-2.pdf` (спринг, 1 курс физ) | physics | 1.00 | 4 (БОФ34-ФиИ, ИИТ, ФИХ; БОФ54-ФПТ) |
| `adaptacionnyj-modul-*` (осень, оррnтац. модуль) | geography | 0.00 | 0 (correctly no groups) |
| `c51c9772*.pdf` (осень, общий адаптационный модуль) | arts/journalism/social | 0.00 | 0 (correctly no groups) |

## Defects observed (line-by-line diff against source)

Both spring PDFs surfaced the same classes of defect. Class → count found →
severity for a schedule-accuracy-critical UI.

### D1. Subject truncated at multi-line cell wrap **(CRITICAL)**
Cells that wrap onto multiple lines in the PDF are extracted only up to the
first newline. Actual behaviour:

```
Source PDF:  Практика устной и письменной речи английского языка (ПЗ)
Parser out:  «Практика устной и»
```
```
Source PDF:  Иностранный язык (ПЗ)
Parser out:  «Иностранный»
```
```
Source PDF:  Общая и неорганическая химия (ПЗ)
Parser out:  «Общая»
```

Every wrapped cell across both PDFs was truncated. Users would see subjects
that are useless as identifiers.

### D2. Empty subject falls back to teacher / room text **(CRITICAL, hallucination)**
When the parser can't identify a subject in a cell but there IS teacher/room
text there, it uses that as the subject:

```
wed 14:20  «ауд. 502» | — | ауд.502   (subject = "ауд. 502")
wed 10:40  «доц. С.Г.Толкунова» | доц. С.Г.Толкунова | ауд.407
tue 14:20  «доц. В.В. Гамага»  | доц. В.В. Гамага  | ауд.502
```

User sees rooms/teachers as if they were subjects of a lesson.

### D3. Footer / legend text becomes a lesson **(CRITICAL, hallucination)**
The `Исполнитель: И.А. Курдюков` signature line at the bottom of the PDF got
parsed as a Saturday 14:20 lesson with `subject = "ель: И.А. Курдюков"`. Same
class of bug produces phantom lessons from «Формы проведения занятий»,
«Занятия по нечётным неделям», etc.

### D4. Two groups sharing a code silently merged **(HIGH, ambiguity)**
`geo_5-kurs.pdf` has TWO group columns both labelled `БОГ35-ГИН2101` — one
профиль «Испанский язык», one «Английский язык». Parser produces ONE
`БОГ35-ГИН2101` with the union of lessons. If they are indeed the same
academic group (subgroups 503-05, 504-06, 504-07), the merge is correct.
If they are separate groups whose code was reused, we lose data. Not
resolvable without the deanery's confirmation.

### D5. Adaptation-module PDF triggers full vision-fallback chain
PDF that describes the first-week orientation programme for freshmen has NO
group codes and should not be parsed as a schedule. Current behaviour:
pdfplumber returns 0 groups (correct) → confidence 0 → parser calls camelot,
tesseract, Gemini, Claude in sequence. In prod that's 3 paid API calls per
adaptation PDF per scrape run.

**Autumn 2026 status snapshot (as of 25.08 evening):** every institute that
already published something for autumn published ONLY the adaptation module.
`arts`, `journalism`, `social` even share a single PDF
(`c51c9772*.pdf`). Waste multiplied.

### D6. Homoglyph in group code (FIXED by sanitize)
Raw parser output: `БOГ35-ГЭК2101` (Latin O). `sanitize_groups` correctly folds
to Cyrillic `БОГ35-ГЭК2101`. No action needed.

### D7. Double `ауд. ауд.` prefix (FIXED by sanitize)
Raw parser output puts `ауд.ауд. 502` because the PWA prepends `ауд. `.
`clean_room` handles the double marker correctly. No action needed.

## Why the parser can look green (100 % confidence) and still be wrong

`confidence` is measured as `fraction of rows for which both a time and a
subject were extracted`. When a wrap-truncated subject like «Иностранный»
is returned, the row DOES have a subject text — so confidence counts it as
a hit, not as a miss.

Every institute marked ✅ in `docs/plan.md` was validated on the same shallow
metric. **A groups-count-plus-confidence check is not a substitute for reading
the actual JSON against the source PDF.** This audit is the counter-example.

## Applied fixes in this session

- `feat(scraper): skip adaptation-module PDFs in fetcher` — link text contains
  "адаптационн" → drop before download. Eliminates D5's wasted vision calls
  and prevents the phantom 0-groups anomaly alert.
- `feat(scraper): reject garbage subjects post-sanitize` — a lesson whose
  `subject` is only teacher text (starts with «доц.», «проф.» …) or only
  room text («ауд. XXX») or matches known legend markers («Исполнитель», «Формы
  проведения», «Занятия по нечётным/чётным») is dropped. Fixes D2 and D3.

Neither touches the underlying wrap-truncation (D1), which requires a
deeper pdfplumber cell-extraction rewrite (documented in follow-ups).

## Follow-ups (not fixed in this session)

- **D1 wrap-truncation** — rewrite `_extract_lessons_from_table` to join
  multi-line cell text via `cell.split("\n")` and reassemble
  subject/teacher/room correctly. Non-trivial: cell boundary detection also
  needs to respect subgroup columns.
- **D4 group-code collision** — either treat two same-name groups on one
  page as two distinct groups (append profile suffix) or explicitly log
  a warning + issue.
- **Confidence metric** — count a row as valid ONLY if `len(subject) >= 5`
  AND subject does not match the D2/D3 garbage patterns. Would immediately
  drop today's ✅ from 100 % to something meaningful.

## Decision matrix for the near term

**For MVP release** (accuracy-critical, autumn 2026 launch window):
- **hand-enter groups** using `scraper/hand_entry/` pipeline (added this
  session). Deanery/старосты publish schedules → someone types them into
  JSON template → validator → commit to `data` branch. Half-a-day of
  effort per institute per semester.
- **run parser in shadow mode** — keep the pipeline live for change
  detection and confidence tracking, but do NOT publish its output to
  users. It just tells us "the source file changed, please re-verify by
  hand".

**Post-MVP** (parser rehab):
- Fix D1 → gets truncation down.
- Fix confidence metric → we stop trusting ✅ that isn't.
- Implement parity-check pipeline (Этап 1 of the migration design doc):
  screenshot the mpgu.su page and diff parsed JSON against it.
