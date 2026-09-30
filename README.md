# outreach

Скрипт персонализации для B2B-аутрича: берёт CSV с компаниями, читает их сайты, через Claude Code (`claude -p`) находит конкретный факт о компании и проверяет, не перепутаны ли данные.

## Запуск

Нужны Python 3.12, [uv](https://docs.astral.sh/uv/) и установленный и залогиненный `claude` CLI.

```bash
uv sync
uv run python -m outreach personalize data/base.csv -o data/base_personalized.csv
uv run python -m outreach personalize data/polza_input.csv -o data/polza_personalized.csv
uv run python -m outreach export -o deliverables.xlsx
```

На входе CSV с колонками `company`, `website`, `email` (остальные колонки сохраняются как есть). На выходе добавляются колонки `personalization`, `personalization_source`, `site_company`, `status` (`ok`, `проверить`, `не отправлять`) и `issues`. `export` собирает xlsx с листами «База», «Цепочка писем», «Задача 4» для импорта в Google Таблицы.

Настройки через переменные окружения (см. `.env.example`): `CLAUDE_MODEL`, `CLAUDE_TIMEOUT`, `WORKERS`.

## Тесты

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Как это устроено

- Для каждой строки скачиваются главная и до трёх страниц «о компании», «новости», «кейсы». Текст уходит в `claude -p` без инструментов, ответ приходит по JSON-схеме.
- Модели запрещено додумывать: если на сайте нет конкретики, поле остаётся пустым, а у каждого факта есть ссылка на страницу-источник.
- Проверки данных: синтаксис email и MX-запись домена, бесплатная почта, домен email не совпадает с сайтом (и что на самом деле открывается на домене email), дубли, редиректы на чужой домен, сайт принадлежит другой компании или относится к соседней строке, компания не из России.
- `data/base.csv` собран вручную с помощью веб-поиска: только адреса, опубликованные на сайтах компаний, ссылка на источник есть у каждого email и ЛПР.
- Цепочка писем лежит в `data/sequence.csv`, лимит 120 слов и переменная `{{персонализация}}` проверяются тестом.
