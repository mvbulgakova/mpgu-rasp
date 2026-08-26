"""Gsheets (ИСГО) parser tests.

Focus: D8 multi-group header split. A cell like
«ВОЭ34-ОЭП2601, ВОЭ34-ПИИ2601, ВОЭ34-ИВР2601, БОЭ24-СУФ2601» is FOUR
distinct groups sharing this column's lesson body. Old code kept it as
one Frankengroup; new code creates a group per code and replicates.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper.parsers.gsheets_parser import _parse_isgo, _GROUP_RE


def test_group_regex_finds_all_codes_in_multi_group_header():
    """D8 rootcause: `_GROUP_RE.findall` must return every code in a header."""
    header = "ВОЭ34-ОЭП2601, ВOЭ34-ПИИ2601, ВОЭ34-ИВР2601,  БОЭ24-СУФ2601"
    codes = _GROUP_RE.findall(header)
    # 3 valid codes + one with Latin O (homoglyph) that regex may or may not
    # accept. We ONLY assert that at least the pure-Cyrillic codes match —
    # homoglyph folding is a separate concern handled by sanitize.
    assert "ВОЭ34-ОЭП2601" in codes
    assert "ВОЭ34-ИВР2601" in codes
    assert "БОЭ24-СУФ2601" in codes


def test_parse_isgo_splits_multi_group_column_into_separate_groups():
    """D8 end-to-end: header cell with N comma-separated codes → N groups."""
    rows = [
        # header row: col0=День, col1=Время, col2=ONE cell with 3 codes
        ["День", "Время", "ВОЭ34-ОЭП2601, ВОЭ34-ПИИ2601, ВОЭ34-ИВР2601"],
        # data row
        [
            "Понедельник",
            "9:00 - 10:30",
            "Экономика фирмы (ЛК 16) доц. Иванов И.И. (ауд. 826)",
        ],
    ]
    groups = _parse_isgo(rows, header_idx=0)
    names = sorted(g["name"] for g in groups)
    assert names == [
        "ВОЭ34-ИВР2601",
        "ВОЭ34-ОЭП2601",
        "ВОЭ34-ПИИ2601",
    ], f"expected all 3 sibling groups, got {names}"

    # Each group has ONE lesson on monday with the same subject text.
    for g in groups:
        mon = g["schedule"]["odd_week"]["monday"]
        assert len(mon) == 1, f"{g['name']}: expected 1 monday lesson, got {len(mon)}"
        assert "Экономика фирмы" in mon[0]["subject"]


def test_parse_isgo_single_group_header_unchanged():
    """Regression: a header with a SINGLE code still produces one group."""
    rows = [
        ["День", "Время", "ВОЭ34-ОЭП2601"],
        ["Понедельник", "9:00 - 10:30", "Экономика (ЛК 16) доц. Иванов (ауд. 826)"],
    ]
    groups = _parse_isgo(rows, header_idx=0)
    assert len(groups) == 1
    assert groups[0]["name"] == "ВОЭ34-ОЭП2601"


# ── D26: sport CSV uses the MPGU grid shifted one column right ────────────────


def _sport_csv_rows():
    """Mirrors sport/1-курс.csv: col0 always empty, day in col1, time in col2,
    group codes (with a «(30)» capacity suffix) in col3+, and each lesson
    spread over four consecutive rows: subject / teacher / dates / room.
    """
    return [
        ["", "группы", "", "ВОЗ34-ФКС2601 (30)", "ВОЗ34-ФКБ2601 (25)"],
        ["", "ПОНЕДЕЛЬНИК", "9:00-10:30", "", "Физическая культура и спорт (ЛК)"],
        ["", "", "", "", "ст. преп. Чернышева О.В."],
        ["", "", "", "", "26.10., 09.11., 23.11."],
        ["", "", "", "", "с/з №3"],
        ["", "", "10:40-12:10", "Анатомия человека (ЛК)", ""],
        ["", "", "", "доц. Кешишев А.Г.", ""],
        ["", "", "", "21.09., 05.10.", ""],
        ["", "", "", "ауд. 216", ""],
    ]


def test_sport_csv_grid_is_parsed():
    """D26: раньше _parse_csv_rows возвращал 0 групп на всех 16 файлах sport."""
    from scraper.parsers.gsheets_parser import _parse_csv_rows

    groups = _parse_csv_rows(_sport_csv_rows())
    names = sorted(g["name"] for g in groups)
    assert names == ["ВОЗ34-ФКБ2601", "ВОЗ34-ФКС2601"], names

    by_name = {g["name"]: g for g in groups}
    fkb = by_name["ВОЗ34-ФКБ2601"]["schedule"]["odd_week"]["monday"]
    assert len(fkb) == 1, fkb
    assert fkb[0]["subject"] == "Физическая культура и спорт"
    assert "Чернышева" in (fkb[0]["teacher"] or "")
    assert fkb[0]["room"] is not None, "«с/з №3» должен стать аудиторией"

    fks = by_name["ВОЗ34-ФКС2601"]["schedule"]["odd_week"]["monday"]
    assert len(fks) == 1, fks
    assert fks[0]["subject"] == "Анатомия человека"
