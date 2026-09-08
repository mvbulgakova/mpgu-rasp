"""Обратная связь от пользователей: сообщение → issue в репозитории.

Инбоксом служат GitHub Issues, а не своя база и не чужой сервис: они уже
есть у публичного репозитория, они бесплатны, они уведомляют владельца,
хранят переписку и закрываются вместе с исправлением. Никакого хостинга.

Одна ячейка расписания — один issue. Двадцать студентов одной группы,
заметивших одну и ту же ошибку, добавляют комментарии к нему же: инбокс
должен оставаться читаемым, иначе им перестанут пользоваться.

Репозиторий публичный, поэтому в issue не уезжает ничто, что позволяет
опознать автора: ни telegram-id, ни @username. Для ответа автору хватает
самого Telegram — issue нужен для ПОЧИНКИ, а не для переписки.
"""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

API = "https://api.github.com/repos"
LABEL = "schedule-report"
MARKER_PREFIX = "mpgu-feedback"

DAY_RU = {
    "monday": "понедельник", "tuesday": "вторник", "wednesday": "среда",
    "thursday": "четверг", "friday": "пятница", "saturday": "суббота",
    "sunday": "воскресенье",
}
WEEK_RU = {"odd": "над чертой (нечётная)", "even": "под чертой (чётная)"}

# Хвост, которым обрывается слишком длинный пользовательский текст.
MAX_TEXT = 1500


@dataclass(frozen=True)
class Report:
    """Одно сообщение о проблеме с расписанием."""

    institute: str
    group: str
    day: str | None = None
    week: str | None = None
    text: str = ""
    #: чем пользователь представился Telegram'у — НЕ уезжает в issue,
    #: нужен только боту для rate-limit и ответа в чат.
    reporter_id: int | None = None
    reporter_name: str = ""
    #: `updated_at` манифеста института — чтобы понимать, на каких данных
    #: пользователь это увидел.
    data_updated_at: str = ""
    #: что именно бот показал на экране — заготовка для воспроизведения.
    shown: str = ""


@dataclass(frozen=True)
class Result:
    number: int
    url: str
    created: bool


def marker(report: Report) -> str:
    """Скрытый ключ дедупликации: институт / группа / день."""
    return (f"<!-- {MARKER_PREFIX}:{report.institute}/{report.group}/"
            f"{report.day or '-'} -->")


def _sanitize(text: str) -> str:
    """Текст пользователя — данные, а не разметка issue.

    Гасим HTML-комментарии (иначе можно подделать маркер дедупликации) и
    режем длину; остальное оставляем как есть — это цитата человека.
    """
    clean = (text or "").strip().replace("<!--", "‹!--").replace("-->", "--›")
    if len(clean) > MAX_TEXT:
        clean = clean[:MAX_TEXT] + "…"
    return clean


def title(report: Report) -> str:
    where = DAY_RU.get(report.day or "", "")
    tail = f", {where}" if where else ""
    return f"Расписание: {report.group} ({report.institute}{tail})"


def body(report: Report) -> str:
    said = _sanitize(report.text) or "_(кнопка нажата без описания)_"
    lines = [
        "Сообщение из Telegram-бота.",
        "",
        f"- **Институт:** {report.institute}",
        f"- **Группа:** {report.group}",
    ]
    if report.day:
        lines.append(f"- **День:** {DAY_RU.get(report.day, report.day)}")
    if report.week:
        lines.append(f"- **Неделя:** {WEEK_RU.get(report.week, report.week)}")
    if report.data_updated_at:
        lines.append(f"- **Данные от:** {report.data_updated_at}")
    lines += ["", "### Что не так", "", said]
    if report.shown:
        lines += ["", "<details><summary>Что показал бот</summary>", "",
                  "```", _sanitize(report.shown), "```", "", "</details>"]
    lines += ["", marker(report)]
    return "\n".join(lines)


def github_request(repo: str, token: str):
    """Возвращает `request(method, path, payload)` для одного репозитория."""

    def request(method: str, path: str, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"{API}/{repo}{path}", data=data, method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "mpgu-rasp-feedback",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    return request


def _find_open_issue(report: Report, request) -> dict | None:
    """Ищем открытый issue про ту же ячейку.

    Перебираем открытые issue с нашей меткой и сверяем маркер локально, а
    не через search-API: индекс поиска отстаёт на минуты, и на этом
    отставании дубликаты и плодятся.
    """
    key = marker(report)
    try:
        issues = request("GET", f"/issues?state=open&labels={LABEL}&per_page=100")
    except urllib.error.HTTPError:
        return None
    for issue in issues or []:
        if key in (issue.get("body") or ""):
            return issue
    return None


def add_comment(number: int, text: str, request) -> None:
    request("POST", f"/issues/{number}/comments", {"body": _sanitize(text)})


def submit(report: Report, repo: str, request) -> Result:
    """Заводит issue или комментирует существующий про ту же ячейку."""
    existing = _find_open_issue(report, request)
    if existing:
        said = _sanitize(report.text) or "_(ещё одно подтверждение, без описания)_"
        add_comment(existing["number"], said, request)
        return Result(existing["number"], existing.get("html_url", ""), created=False)

    created = request("POST", "/issues", {
        "title": title(report),
        "body": body(report),
        "labels": [LABEL],
    })
    return Result(created["number"], created.get("html_url", ""), created=True)
