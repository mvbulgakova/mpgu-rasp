"""Cell-by-cell audit dump: parser output for every group + every lesson.

Run: python3 scratchpad/dump_all_lessons.py > scratchpad/audit_all.txt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.parsers.pdf_parser import PDFParser
from scraper.parsers.excel_parser import ExcelParser
from scraper.normalizer.schedule_normalizer import sanitize_groups

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_RU = {"monday": "ПН", "tuesday": "ВТ", "wednesday": "СР",
          "thursday": "ЧТ", "friday": "ПТ", "saturday": "СБ", "sunday": "ВС"}

FILES = [
    ("geography", "/tmp/audit/geo_5.pdf", "pdf"),
    ("physics", "/tmp/audit/phys_1.pdf", "pdf"),
    ("journalism", "/tmp/audit/jour_2.pdf", "pdf"),
    ("history", "/tmp/audit/hist_dnevnoe.xlsx", "excel"),
]


def dump(inst_id: str, path: str, kind: str):
    print("=" * 78)
    print(f"INSTITUTE: {inst_id}   SOURCE: {path}")
    print("=" * 78)
    if kind == "pdf":
        p = PDFParser({"id": inst_id})
        res = p._try_pdfplumber(path)
    else:
        p = ExcelParser({"id": inst_id})
        res = p.parse(path)
    print(f"parser: {res.parser_used}  confidence: {res.confidence:.2f}  "
          f"raw_groups: {len(res.groups)}")
    if res.warnings:
        print("warnings:", res.warnings[:3])

    cleaned = sanitize_groups(res.groups)
    print(f"sanitized_groups: {len(cleaned)}")
    print()

    for g in cleaned:
        odd = sum(len(g["schedule"]["odd_week"].get(d, [])) for d in DAYS)
        even = sum(len(g["schedule"]["even_week"].get(d, [])) for d in DAYS)
        print(f"── {g['name']}  (year={g.get('year')}, form={g.get('form')}, "
              f"degree={g.get('degree')}, odd={odd}, even={even}) ──")
        for wk in ("odd_week", "even_week"):
            for d in DAYS:
                for l in g["schedule"][wk].get(d, []):
                    subj = l.get("subject") or ""
                    t = l.get("teacher") or "—"
                    r = l.get("room") or "—"
                    typ = l.get("type") or ""
                    sg = l.get("subgroup")
                    sg_s = f" п/г{sg}" if sg else ""
                    wk_lab = "нч" if wk == "odd_week" else "чт"
                    # Flag suspicious rows
                    flags = []
                    if len(subj.strip()) < 6:
                        flags.append("SHORT-SUBJ")
                    if not l.get("teacher") and not l.get("room"):
                        flags.append("NO-META")
                    if subj.rstrip().endswith(("-", ",", "по", "на", "в", "и")):
                        flags.append("FRAG?")
                    flag_s = f"   [{' '.join(flags)}]" if flags else ""
                    print(f"  {wk_lab} {DAY_RU[d]} {l.get('time_start','')}-{l.get('time_end','')} "
                          f"{typ[:4]:<4} {subj[:60]!r:64} T={t[:30]:<30} R={r[:25]}{sg_s}{flag_s}")
        print()


for inst_id, path, kind in FILES:
    dump(inst_id, path, kind)
