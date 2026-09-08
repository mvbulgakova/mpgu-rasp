# Ветка `data`

Содержимое создаётся автоматически (`.github/workflows/scrape.yml`)
и раздаётся клиентам через jsDelivr. Руками сюда коммитить не нужно:
следующий прогон скрапера всё равно перезапишет.

- `institutes/<id>/schedule.json` — манифест института
- `institutes/<id>/groups/*.json` — расписание одной группы
- `meta/index.json` — список институтов
- `meta/groups.json` — поисковый индекс групп
- `meta/week_parity.json` — какие недели НАД, какие ПОД чертой
