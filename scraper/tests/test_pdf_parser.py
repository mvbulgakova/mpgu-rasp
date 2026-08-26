"""PDF parser regression tests.

Focus: cell-level extraction. `_parse_timetable_cell` is the single point where
a raw multi-line cell string from pdfplumber turns into a lesson dict. Every
audit defect around subject text (D1 wrap-truncation) lives here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper.parsers.pdf_parser import (
    _parse_timetable_cell, _compute_confidence, _extract_timetable_groups,
)


def test_multiline_subject_wrap_is_joined_geography_style():
    """Cell whose subject wraps across 3 lines before metadata (D1 defect).

    Source PDF (geography 5-курс): «Практика устной и\\nписьменной речи\\n
    английского языка (ПЗ),\\nдоц. Ю.С. Кузин,\\nауд. 206». Old code took only
    the first line («Практика устной и»); reader had no idea what the lesson
    actually was.
    """
    cell = (
        "Практика устной и\n"
        "письменной речи\n"
        "английского языка (ПЗ),\n"
        "доц. Ю.С. Кузин,\n"
        "ауд. 206"
    )
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert lesson["subject"] == (
        "Практика устной и письменной речи английского языка"
    )
    assert lesson["type"] == "practice"
    assert lesson["teacher"] == "доц. Ю.С. Кузин"
    assert lesson["room"] == "ауд. 206"


def test_multiline_subject_wrap_is_joined_physics_style():
    """Physics 1-курс defect: «Общая» instead of «Общая и неорганическая химия»."""
    cell = (
        "Общая\n"
        "и неорганическая химия\n"
        "(ПЗ)\n"
        "Асс. А.И. Ломакин\n"
        "(ауд. 55)"
    )
    lesson = _parse_timetable_cell(cell, "11:00", "12:35", None)
    assert lesson is not None
    assert lesson["subject"] == "Общая и неорганическая химия"
    assert lesson["type"] == "practice"
    assert "Ломакин" in (lesson["teacher"] or "")


def test_singleline_subject_with_inline_type_marker():
    """Single-line cell with type marker in body — unchanged behaviour."""
    cell = "Экологический мониторинг (ПЗ),\nдоц. Э.Г. Рябова,\nауд. 502"
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert lesson["subject"] == "Экологический мониторинг"
    assert lesson["type"] == "practice"


def test_lecture_marker_after_wrapped_subject():
    cell = (
        "Основы российской\n"
        "государственности\n"
        "(ЛК)\n"
        "проф. Асонов Н. В\n"
        "ауд. 314"
    )
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert lesson["subject"] == "Основы российской государственности"
    assert lesson["type"] == "lecture"


def test_single_word_subject_survives():
    """A genuine one-word subject like «Психология» must NOT be flagged/dropped."""
    cell = "Психология\n(ЛК)\nдоц. Иванов И.И.\nауд. 100"
    lesson = _parse_timetable_cell(cell, "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "Психология"
    assert lesson["type"] == "lecture"


def test_empty_cell_returns_none():
    assert _parse_timetable_cell("", "09:00", "10:30", None) is None
    assert _parse_timetable_cell("   \n\n  ", "09:00", "10:30", None) is None


# ── D9: journalism "temporary" schedule with dates instead of week parity ─────


def test_journalism_full_title_teacher_and_date_line():
    """journalism cell: полные звания и дата вместо чёт/нечёт (D9).

    Раньше «Доцент П.В. Макарова» не распознавался как teacher (regex ловил
    только abbrev'ы), а «14.09» съедалось subject'ом. Проверяем правильную
    сборку.
    """
    cell = (
        "ОСНОВЫ ДЕЯТЕЛЬНОСТИ ЖУРНАЛИСТА (ЛК)\n"
        "14.09\n"
        "Доцент П.В. Макарова\n"
        "Аудитория 204"
    )
    lesson = _parse_timetable_cell(cell, "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "ОСНОВЫ ДЕЯТЕЛЬНОСТИ ЖУРНАЛИСТА"
    assert lesson["type"] == "lecture"
    assert lesson["teacher"] == "Доцент П.В. Макарова"
    assert lesson["room"] == "Аудитория 204"


def test_journalism_professor_and_multi_date():
    cell = (
        "ХУДОЖЕСТВЕННО-ПУБЛИЦИСТИЧЕСКАЯ ЖУРНАЛИСТИКА (ЛК)\n"
        "07.09, 21.09\n"
        "Профессор Т.Н. Владимирова\n"
        "Аудитория 204"
    )
    lesson = _parse_timetable_cell(cell, "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "ХУДОЖЕСТВЕННО-ПУБЛИЦИСТИЧЕСКАЯ ЖУРНАЛИСТИКА"
    assert lesson["teacher"] == "Профессор Т.Н. Владимирова"
    assert lesson["room"] == "Аудитория 204"


def test_journalism_senior_lecturer_and_sports_hall():
    cell = (
        "ЭЛЕКТИВНЫЕ КУРСЫ ПО ФИЗИЧЕСКОЙ КУЛЬТУРЕ И СПОРТУ (ПЗ)\n"
        "10.09, 24.09\n"
        "Старший преподаватель С.С. Волхов\n"
        "Спортивный зал"
    )
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert (
        lesson["subject"]
        == "ЭЛЕКТИВНЫЕ КУРСЫ ПО ФИЗИЧЕСКОЙ КУЛЬТУРЕ И СПОРТУ"
    )
    assert lesson["type"] == "practice"
    assert "Волхов" in (lesson["teacher"] or "")
    assert lesson["room"] == "Спортивный зал"


# ── follow-up #3: stricter confidence metric ──────────────────────────────────


def _mkgroup(name: str, subjects: list[str]) -> dict:
    """Test helper: make a group whose Monday-odd has one lesson per subject."""
    from scraper.normalizer.schedule_normalizer import make_schedule_skeleton, lesson_obj
    s = make_schedule_skeleton()
    for i, subj in enumerate(subjects):
        s["odd_week"]["monday"].append(
            lesson_obj(i, "09:00", "10:30", subj, "lecture", None, None)
        )
    return {"name": name, "year": 1, "form": "full_time",
            "degree": "bachelor", "schedule": s}


def test_confidence_ignores_short_and_garbage_subjects():
    """New metric drops truncated subjects («Общая», «Иностранный») and
    garbage (teacher-only, room-only, footer text) from the numerator.
    """
    # 30 real subjects → confidence 1.00
    good = _mkgroup("Х", ["Экологический мониторинг"] * 30)
    assert _compute_confidence([good]) == 1.00

    # 30 truncated subjects (all <5 chars) → confidence 0.10
    trunc = _mkgroup("Х", ["Общая", "Иностр", "Мате"] * 10)  # some <5
    # "Общая"=5 chars OK; "Иностр"=6 OK; "Мате"=4 NOT OK
    # 20/30 valid → 0.67
    assert 0.65 < _compute_confidence([trunc]) < 0.70

    # 30 garbage subjects → confidence 0.10
    garbage = _mkgroup("Х", ["доц. Иванов И.И.", "ауд. 502",
                             "Исполнитель: И.А. Курдюков"] * 10)
    assert _compute_confidence([garbage]) == 0.10

    # No groups → 0.0; empty schedule → 0.1
    assert _compute_confidence([]) == 0.0
    empty = _mkgroup("Х", [])
    assert _compute_confidence([empty]) == 0.10


# ── D4: same-code group discriminator ─────────────────────────────────────────


def test_duplicate_code_gets_profile_suffix():
    """geo_5-kurs.pdf: two cols carry БОГ35-ГИН2101 — one испанский, one английский.

    Without disambiguation they merge into one group and lose data. Fix: append
    the profile hint from the row above the code row as a suffix.
    """
    # Minimal 3-column header table mirroring geo_5-kurs.pdf shape:
    table = [
        ["", "", "", ""],
        ["", "", "", ""],
        ["", "", "", ""],
        ["профиль", "", "География и иностранный язык (испанский)",
         "География и иностранный язык (английский)"],
        ["", "", "", ""],
        ["группа", "", "БОГ35-ГИН2101", "БОГ35-ГИН2101"],
        ["", "", "", ""],
    ]
    gc, _, _, _ = _extract_timetable_groups(table)
    names = [n for n, _ in gc]
    assert "БОГ35-ГИН2101 (испанский)" in names
    assert "БОГ35-ГИН2101 (английский)" in names
    assert len(names) == 2, f"expected 2 distinct groups, got {names}"


def test_single_code_no_suffix_added():
    """Обычный случай — код встречается один раз — не переименовываем."""
    table = [
        ["профиль", "", "География и экология"],
        ["группа", "", "БОГ35-ГЭК2101"],
    ]
    gc, _, _, _ = _extract_timetable_groups(table)
    assert [n for n, _ in gc] == ["БОГ35-ГЭК2101"]


# ── D19: two stacked lesson blocks in one time slot ───────────────────────────


def _mpgu_table_two_blocks_in_one_slot():
    """Mirrors arts/ДПИ layout: the time column has TALLER rows than the
    subject column, so one 12:40 slot physically contains two lesson cells
    stacked vertically. pdfplumber emits them as two consecutive rows, the
    second with an empty time cell.
    """
    return [
        ["День недели", "Группа/время", "БОР06-ДПИ2301"],
        ["ПОНЕДЕЛЬНИК", "10:40-12:10", ""],
        ["", "", "АКАДЕМИЧЕСКАЯ СКУЛЬПТУРА\n(ПЗ)\nдоц. А.А. Ворохоб\n(ауд. 114)"],
        ["", "12:40-14:10", "ХУДОЖЕСТВЕННАЯ КЕРАМИКА (ПЗ)\nдоц. А.А. Ворохоб\n(ауд. 114)"],
        ["", "", "АКАДЕМИЧЕСКАЯ СКУЛЬПТУРА\n(ПЗ)\nдоц. А.А. Ворохоб\n(ауд. 114)"],
    ]


def test_two_stacked_blocks_in_one_slot_both_survive():
    """D19: both lessons of a shared slot must be emitted, not just the first."""
    from scraper.parsers.pdf_parser import _parse_tables

    groups = _parse_tables([_mpgu_table_two_blocks_in_one_slot()])
    assert len(groups) == 1, f"expected 1 group, got {[g['name'] for g in groups]}"
    monday = groups[0]["schedule"]["odd_week"]["monday"]
    at_1240 = [l["subject"] for l in monday if l["time_start"] == "12:40"]
    assert len(at_1240) == 2, f"12:40 slot must hold 2 lessons, got {at_1240}"
    assert any("КЕРАМИКА" in s for s in at_1240), at_1240
    assert any("СКУЛЬПТУРА" in s for s in at_1240), at_1240


# ── D20/D21/D22: preschool cell shapes ────────────────────────────────────────


def test_comma_separated_type_marker_is_stripped():
    """D20: «История России, ПЗ» — тип через запятую, без скобок."""
    lesson = _parse_timetable_cell(
        "История России, ПЗ\nДоц. В.А. Литвиненко\n(ауд. 303)",
        "09:00", "10:30", None,
    )
    assert lesson is not None
    assert lesson["subject"] == "История России"
    assert lesson["type"] == "practice"
    assert lesson["teacher"] == "Доц. В.А. Литвиненко"
    assert lesson["room"] == "ауд. 303"


def test_comma_separated_lecture_marker():
    lesson = _parse_timetable_cell(
        "История России, ЛК\nДоц. В.А. Литвиненко\n(ауд.206)",
        "09:00", "10:30", None,
    )
    assert lesson is not None
    assert lesson["subject"] == "История России"
    assert lesson["type"] == "lecture"


def test_short_senior_lecturer_abbrev_and_kerned_room():
    """D21 «Ст. пр.» (не «ст. преп.») + D22 over-kerned «(а уд. - С/з)»."""
    lesson = _parse_timetable_cell(
        "Физическая культура и спорт, ПЗ\nСт. пр. Н.А. Андросова\n(а уд. - С/з)",
        "12:40", "14:10", None,
    )
    assert lesson is not None
    assert lesson["subject"] == "Физическая культура и спорт"
    assert lesson["type"] == "practice"
    assert "Андросова" in (lesson["teacher"] or ""), lesson["teacher"]
    assert lesson["room"] is not None, "over-kerned «а уд.» must still yield a room"


# ── D23/D24/D25: single-line cell variants found in arts/geography/social ─────


def test_type_marker_with_qualifier_in_parens_is_stripped():
    """D23 (arts): «(ЛК с 14.09.26)» — маркер типа с уточнением внутри скобок."""
    lesson = _parse_timetable_cell(
        "ИСТОРИЯ РОССИИ (ЛК с 14.09.26), доц. Александр Георгиевич Смирнов, ауд. 221",
        "09:00", "10:30", None,
    )
    assert lesson is not None
    assert lesson["subject"] == "ИСТОРИЯ РОССИИ"
    assert lesson["type"] == "lecture"
    assert lesson["teacher"] == "доц. Александр Георгиевич Смирнов"
    assert lesson["room"] == "ауд. 221"


def test_truncated_aud_token_does_not_leak_into_teacher():
    """D24 (geography): «, ауд» без точки и номера — обрезано границей ячейки."""
    lesson = _parse_timetable_cell(
        "История России , доц. М.К. Чиняков, ауд", "09:00", "10:30", None,
    )
    assert lesson is not None
    assert lesson["subject"] == "История России"
    assert lesson["teacher"] == "доц. М.К. Чиняков", lesson["teacher"]


def test_space_separated_teacher_and_empty_room_parens():
    """D25 (social): преподаватель через пробел, «(ауд. )» без номера."""
    lesson = _parse_timetable_cell(
        "Финансово-экономический практикум (ПЗ 10) доц. Н.А. Головань (ауд. )",
        "09:00", "10:30", None,
    )
    assert lesson is not None
    assert lesson["subject"] == "Финансово-экономический практикум"
    assert lesson["type"] == "practice"
    assert lesson["teacher"] == "доц. Н.А. Головань", lesson["teacher"]


def test_type_qualifier_is_preserved_in_notes():
    """D23: «(ЛК с 14.09.26)» — дата-квалификатор уходит в notes, не теряется,
    иначе две пары с разными датами схлопываются дедупом в одну."""
    a = _parse_timetable_cell(
        "ИСТОРИЯ РОССИИ (ЛК с 14.09.26), доц. А.Г. Смирнов, ауд. 221",
        "09:00", "10:30", None)
    b = _parse_timetable_cell(
        "ИСТОРИЯ РОССИИ (ЛК по 30.11.26), доц. А.Г. Смирнов, ауд. 221",
        "09:00", "10:30", None)
    assert a["subject"] == b["subject"] == "ИСТОРИЯ РОССИИ"
    assert "14.09.26" in a["notes"], a["notes"]
    assert "30.11.26" in b["notes"], b["notes"]
    assert a["notes"] != b["notes"], "разные даты должны остаться различимы"


def test_bare_aud_token_without_number_is_metadata():
    """D24: «САМОСТОЯТЕЛЬНАЯ РАБОТА (творческая), ауд.» — обрезанная аудитория
    без номера не должна прилипать к названию предмета."""
    lesson = _parse_timetable_cell(
        "САМОСТОЯТЕЛЬНАЯ РАБОТА (творческая), ауд.", "09:00", "10:30", None)
    assert lesson is not None
    assert "ауд" not in lesson["subject"].lower(), lesson["subject"]


def test_audirovanie_subject_not_mistaken_for_room():
    """Защита от ложного срабатывания: «Аудирование» содержит «ауд»."""
    lesson = _parse_timetable_cell(
        "Аудирование (ПЗ)\nдоц. И.И. Иванов\nауд. 305", "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "Аудирование"
    assert lesson["room"] == "ауд. 305"


def test_room_attached_to_subject_by_space_only():
    """D24b (arts): «ЖИВОПИСЬ ауд. 412» — аудитория без запятой и скобок."""
    lesson = _parse_timetable_cell(
        "ЖИВОПИСЬ ауд. 412\nдоц. С.Г. Брызгалова", "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "ЖИВОПИСЬ"
    assert lesson["room"] == "ауд. 412"


# ── D16/D27: ЗФО — в колонке дня стоит дата, а не название дня ────────────────


def test_zfo_date_with_weekday_in_parens_is_recognised():
    """sport/geography ЗФО: «05.09.2026 (СУББОТА)» вместо «СУББОТА»."""
    from scraper.parsers.pdf_parser import _parse_tables

    table = [
        ["группы", "", "ВZЗ34-ФЗК2601"],
        ["05.09.2026 (СУББОТА)", "9:00-10:30", "Педагогика (ЛК)"],
        ["", "", "доц. Н.Н. Баркова"],
        ["", "", "ауд. 402"],
    ]
    groups = _parse_tables([table])
    assert len(groups) == 1, groups
    sat = groups[0]["schedule"]["odd_week"]["saturday"]
    assert len(sat) == 1, groups[0]["schedule"]["odd_week"]
    assert sat[0]["subject"] == "Педагогика"


def test_zfo_bare_date_infers_weekday():
    """Если день недели не подписан — вычисляем его из самой даты.
    07.09.2026 — понедельник."""
    from scraper.parsers.pdf_parser import _parse_tables

    table = [
        ["группы", "", "ВZЗ34-ФЗК2601"],
        ["07.09.2026", "9:00-10:30", "Педагогика (ЛК)"],
        ["", "", "доц. Н.Н. Баркова"],
        ["", "", "ауд. 402"],
    ]
    groups = _parse_tables([table])
    assert len(groups) == 1, groups
    assert len(groups[0]["schedule"]["odd_week"]["monday"]) == 1, \
        groups[0]["schedule"]["odd_week"]


# ── D32: последняя пара дня уезжала на следующий день ────────────────────────


def test_last_lesson_of_a_day_stays_on_that_day():
    """D32: в цикле по строкам день определялся ДО flush(), поэтому пары,
    накопленные в последнем слоте дня, записывались уже в СЛЕДУЮЩИЙ день.

    Найдено сверкой math/001: «Безопасность жизнедеятельности (ПЗ)» в
    14:20 понедельника оказалась во вторнике.
    """
    from scraper.parsers.pdf_parser import _parse_tables

    table = [
        ["День недели", "Время", "ВОМ34-МКН2501"],
        ["ПОНЕДЕЛЬНИК", "10:40-12:10", "Программирование (ЛК)\nст. пр. Буданов Н.А., ауд. 207"],
        ["", "14:20-15:50", "Безопасность жизнедеятельности (ПЗ)\nдоц. Суворов В.В., ауд. 304"],
        ["ВТОРНИК", "09:00-10:30", "Алгебра (ЛК)\nпроф. Михайлова М.В., ауд. 404"],
    ]
    groups = _parse_tables([table])
    assert len(groups) == 1, groups
    wk = groups[0]["schedule"]["odd_week"]

    mon = {l["time_start"]: l["subject"] for l in wk["monday"]}
    tue = {l["time_start"]: l["subject"] for l in wk["tuesday"]}

    assert "14:20" in mon, f"пара 14:20 должна остаться в понедельнике: {mon} / {tue}"
    assert "Безопасность" in mon["14:20"]
    assert "14:20" not in tue, f"во вторнике её быть не должно: {tue}"
    assert tue.get("09:00", "").startswith("Алгебра"), tue


# ── D33/D34/D35: находки построчной сверки preschool ─────────────────────────


def test_self_study_day_is_not_a_lesson():
    """D33: «ДЕНЬ САМООБРАЗОВАНИЯ» (в т.ч. перевёрнутый в вертикальной
    ячейке) — это пометка, а не пара."""
    for cell in ("ДЕНЬ САМООБРАЗОВАНИЯ",
                 "ЯИНАВОЗАРБООМАС ЬНЕД",
                 "День самообразования"):
        assert _parse_timetable_cell(cell, "09:00", "10:30", None) is None, cell


def test_trailing_type_marker_followed_by_qualifier():
    """D34: «Иностранный язык, ПЗ (с 26.11.2026г.)» — маркер типа через
    запятую, а за ним ещё уточнение в скобках."""
    lesson = _parse_timetable_cell(
        "Иностранный язык, ПЗ (с 26.11.2026г.)\nДоц. И.И. Иванов\n(ауд. 305)",
        "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "Иностранный язык", lesson["subject"]
    assert lesson["type"] == "practice"
    assert "26.11.2026" in lesson["notes"], lesson["notes"]


def test_over_kerned_cell_still_yields_teacher_and_room():
    """D35: preschool рендерит часть ячеек по одному глифу («Д о ц .»).
    Границы слов в названии восстановить нельзя — их нет и в PDF, — но
    преподаватель и аудитория обязаны извлечься."""
    cell = ("В в е д е н и е в п р о ф е с с и о н а л ь н у ю д е я т е л ь н о с т ь , П З\n"
            "Д о ц . Ж . В . М а ц к е в и ч\n"
            "( а у д . - 5 0 3)")
    lesson = _parse_timetable_cell(cell, "09:00", "10:30", None)
    assert lesson is not None
    assert "Мацкевич" in (lesson["teacher"] or "").replace(" ", ""), lesson["teacher"]
    assert lesson["room"] is not None, lesson["room"]
    assert "Доц" not in lesson["subject"].replace(" ", ""), lesson["subject"]
