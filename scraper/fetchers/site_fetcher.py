"""Загружает страницу расписания института и возвращает ссылки на файлы."""
import re
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

SCHEDULE_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc"}
GSHEETS_PATTERN = re.compile(r"docs\.google\.com/spreadsheets")
NEXTCLOUD_PATTERN = re.compile(r"oc\.mpgu\.su")
GDRIVE_FILE_PATTERN = re.compile(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MPGURaspBot/1.0; "
        "+https://github.com/mvbulgakova/mpgu-rasp)"
    )
}


# Link-text patterns that are known non-schedule documents. Files matching any
# of these are skipped before download — they never contain group codes and
# would only waste PDF/vision API calls and trigger false-positive anomaly alerts.
# See docs/audits/2026-08-25-parser-audit.md, defect D5.
_SKIP_LINK_TEXT = (
    "адаптац",           # адаптационный модуль (Sep 1-week orientation)
    "задолженност",      # ликвидация задолженностей
    "ликвидац",          # ликвидация ..
    "консультац",        # график консультаций перед сессией
    "переэкзаменов",
)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=16))
async def fetch_schedule_links(session: aiohttp.ClientSession, url: str) -> list[dict]:
    """Возвращает список {url, type, text} для всех файлов расписания на странице.

    Ссылки с явно не-расписательным текстом (адаптационный модуль, ликвидация
    задолженностей, консультации) отфильтровываются — они не содержат кодов
    групп и только зря тратят API-квоты vision-fallback.
    """
    async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        resp.raise_for_status()
        html = await resp.text(encoding="utf-8", errors="replace")

    soup = BeautifulSoup(html, "lxml")
    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue

        abs_url = urljoin(url, href)

        if abs_url in seen:
            continue
        seen.add(abs_url)

        link_type = _classify_link(abs_url)
        if link_type is None:
            continue

        text = a.get_text(strip=True) or ""
        text_low = text.lower()
        if any(marker in text_low for marker in _SKIP_LINK_TEXT):
            continue

        links.append({"url": abs_url, "type": link_type, "text": text})

    return links


def _classify_link(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path.lower()

    if GSHEETS_PATTERN.search(url):
        return "gsheets"
    if NEXTCLOUD_PATTERN.search(url):
        return "nextcloud"
    if GDRIVE_FILE_PATTERN.search(url):
        return "pdf"

    for ext in SCHEDULE_EXTENSIONS:
        if path.endswith(ext):
            ext_clean = ext.lstrip(".")
            return "excel" if ext_clean in {"xlsx", "xls"} else ext_clean

    return None
