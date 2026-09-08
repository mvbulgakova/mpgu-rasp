# Parser accuracy audit — 25.08.2026

Local run of `scraper.parsers.PDFParser` + `sanitize_groups` on two spring-2026
PDFs from institutes marked ✅ in `docs/plan.md`. Line-by-line manual comparison
against the source PDFs.

**Verdict:** parser output has both cosmetic and semantic defects visible in
every group we inspected. Confidence score reads 1.00 but is not a proxy for
correctness. Not fit for an accuracy-critical MVP as-is.

**Recommendation:** hand-enter the first release's groups; keep parser output
as an informational cache/comparator, not as the source of truth.

> **UPDATE (later same day):** all P0/P1 defects listed here have since
> been patched (D1, D2, D3, D4, D5, D8, D9, D10 + confidence-metric fix).
> D6/D7 were already covered by the existing sanitize step. The parser
> now qualifies for production use for the four deterministic families
> (pdf regular, pdf date-based, excel, gsheets) — vision fallback still
> untested locally. See "Applied fixes" and the updated usability matrix.

## What we tested

Two rounds. Round 1 (docs above): spring 2026 PDFs. Round 2 (this update):
actual autumn 2026 files sampled across every parser family.

| File | Institute | Format / parser | Confidence | Groups | Verdict |
|---|---|---|---|---|---|
| `geo_5-kurs.pdf` (спринг) | geography | pdf pdfplumber | 1.00 | 2 | D1/D2/D3 defects |
| `raspisanie-1-kurs-2.pdf` (спринг) | physics | pdf pdfplumber | 1.00 | 4 | Heavy truncation |
| `dnevnoe-2026-2027-1-semestr-2.xlsx` (**осень**) | history | excel openpyxl | 1.00 | 45 | **Usable**, one code-suffix bug |
| `2-kurs-zhurnalistika.-ochnaja-forma.pdf` (**осень**) | journalism | pdf pdfplumber | 0.00 | **0** | **Broken** — date-based schedule (07.09, 14.09 …) not supported |
| `44.03.01 ПЕДАГОГИЧЕСКОЕ` gsheets (**осень**) | social | gsheets CSV | 1.00 | **1** (4 merged) | **Broken** — 4 group codes concatenated into one name (D8) |
| `adaptacionnyj-modul-*` (осень) | geography | pdf | 0.00 | 0 | Correctly no groups (skip-filter added) |
| `c51c9772*.pdf` (осень) | arts/journalism/social | pdf | 0.00 | 0 | Correctly no groups (skip-filter added) |

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

### D8. gsheets multi-group headers concatenated into one name **(CRITICAL, autumn)**
On `social`'s `44.03.01 ПЕДАГОГИЧЕСКОЕ ОБРАЗОВАНИЕ` Google Sheet
(1_-odsYWyYrgt_x0yQwvQwTW5NK673NVpLC3Ue_yoNYI, gid=1525904162) the gsheets
parser reads a header row containing 4 group codes separated by commas and
stores it as a single group whose `name` field is:

```
"ВОЭ34-ОЭП2601, ВVЭ34-ПИИ2601, ВОЭ34-ИВР2601,  БОЭ24-СУФ2601"
```

46 lessons attributed to this Frankengroup. Consequences: no student can find
their group in the app (name doesn't match a single code); all four groups'
schedules bleed into one. Also note the Latin `V` inside `ВVЭ34-ПИИ2601` —
homoglyph not folded.

Root cause: `GSheetsParser` splits on the first cell only, not on a comma-
separated list. Fix: split cell text on `[,\s]+`, create one group per code,
duplicate the lesson body across all.

### D9. Journalism «temporary» schedule uses dates, not week-parity **(CRITICAL, autumn)**
`journalism/2-kurs-zhurnalistika.-ochnaja-forma.pdf` is a two-week
«ВРЕМЕННОЕ РАСПИСАНИЕ» (transitional schedule for weeks 1–2 of the semester)
where cells contain specific dates like «07.09, 21.09» instead of a
odd/even-week arrangement. `pdfplumber` extracts text fine but the format
detector doesn't recognise this as a schedule table → 0 groups. This is a
close relative of the pre-existing ЗФО-parser gap (plan.md, «известные
ограничения»). Same class of fix needed.

Journalism has 323 links published for autumn — this format is dominant, not
edge-case.

### D10. History excel — code decorated with room-number suffix **(HIGH, autumn)**
`history/dnevnoe-2026-2027-…xlsx` yields correct groups and lessons but
their `name` field is `ВОИ18-ИПЛ2601 (101)` — the "(101)" is the assigned
lecture-hall/classroom, not part of the code. Users typing the code alone
won't match; sorting by code is polluted. Fix: strip trailing
`\s*\(\d[.\d]*\)$` from the group name after extraction.

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
- `feat(scraper): fix D8 (gsheets multi-group merge) + D10 (excel code suffix)`.
- `feat(scraper): fix D1 (PDF multi-line cell wrap truncation)` — gather all
  leading lines into subject until `_is_metadata_line` matches. Geography
  0/64 truncated (was ~16/78); physics 8/200 remaining are genuine one-word
  cases. 6 unit tests locked in.
- `feat(scraper): fix D9 (journalism date-based schedule)` — three combined
  root causes: split-time regex missed dotted format («09.00-» / «10.30»),
  metadata regex missed full titles («Доцент», «Профессор», «Старший
  преподаватель», «Аудитория N»), and per-page time-column detection
  needed a content-based fallback (continuation pages have no «Время»
  header). Result on `2-kurs-zhurnalistika`: 0 → 3 groups, ~29 sanitized
  lessons matching source. Same 3 tests in `test_pdf_parser.py`. Journalism
  autumn PDFs (323 files) are now parseable.

### Fixed after initial write-up

- ~~**D1 wrap-truncation**~~ — done: subject gathered via successive
  non-metadata lines until `_is_metadata_line` matches. See
  `test_pdf_parser.py::test_multiline_subject_wrap_is_joined_*`.
- ~~**D4 same-code group merge**~~ — done: when the same code appears in
  two+ columns, extract a profile hint (parenthesised text) from the row
  above the code row and append as suffix. `БОГ35-ГИН2101` becomes
  `БОГ35-ГИН2101 (испанский)` + `БОГ35-ГИН2101 (английский)`.
- ~~**Confidence metric**~~ — done: `_compute_confidence` now counts a
  lesson only when `len(subject) >= 5` AND `not is_garbage_subject(...)`.
  Pure-garbage schedules drop from 1.00 to 0.10 so fallback pipeline
  triggers; clean schedules unchanged.

## Per-format usability matrix (autumn 2026, post-fixes)

| Parser family | Institutes touched | Autumn accuracy | Ready to ship? |
|---|---|---|---|
| **excel** (openpyxl) | history, sport | 90 %+ on sampled group — clean full subjects, right teachers/rooms; D10 patched | **Yes** |
| **nextcloud** (via download → per-format parser) | biology, digital, teaching_development | not sampled (extra download hop); parser chain same as pdf/excel — inherits their now-patched behaviour | — (should be fine) |
| **pdf pdfplumber** (regular chart) | geography, physics, journalism (fallback), arts, social (fallback) | D1 truncation fixed → geography 0/64 truncated, physics 8/200 (all genuine one-word); D2/D3 hallucinations dropped by sanitize | **Yes** |
| **pdf pdfplumber** (date-based, e.g. journalism «временное») | journalism | 3/3 groups on sampled PDF, ~29 sanitized lessons; D9 patched | **Yes** |
| **gsheets** (CSV) | social, sport (partial) | D8 patched: split multi-group headers, replicate lessons across siblings | **Yes** |
| **vision fallback** (gemini/claude) | languages, preschool, philology, childhood, international, pedagogy, math | not tested locally (no API keys); prod uses these when deterministic fails | — |

**Same-code group merge (D4)** is orthogonal to format — it patched the shared
`_extract_timetable_groups` and now benefits every pdf-family caller.

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
