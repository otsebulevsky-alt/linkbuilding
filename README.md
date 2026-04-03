# Linkbuilding

Репозиторий команды Linkbuilding (SEO). Каноническое хранилище знаний: соглашения, правила, инструкции, результаты тестов.

## Оценка доноров (задача из треда seo_meta)

**Цель:** полный контекст процесса оценки доноров. Ты скидываешь доноров в Cursor — он сам их оценивает и записывает результат в **seo/linkbuilding**.

**Что сделано:**

1. **Скрипт по формуле** — автоматически считает вывод (балл 0–10 и «покупать / подумать / не покупать») по метрикам донора. Формула: SEOLB-A-56, SEOLB-A-57.
   - `scripts/donor_score.py` — расчёт по одной строке.
   - `scripts/run_donor_evaluation.py` — пакетная обработка CSV.

2. **Скилл в Cursor** — заполняет таблицу значениями автоматически. Кидаешь в чат пачку доноров (таблицу или список с DR, Traffic, RD, LD, стагнация, цена) → ассистент парсит, считает балл и вывод, дописывает строки в **`data/donors-evaluation.csv`** (результат всегда в seo/linkbuilding). Опционально запускается скрипт отправки в Google-таблицу «[ВНУТРЕННИЙ] Калькулятор доноров».

**Где что лежит:**

| Что | Путь |
|-----|------|
| Результат оценки (CSV) | `data/donors-evaluation.csv` |
| Ссылка на калькулятор | `data/donor-table-url.txt` |
| Скрипты расчёта и отправки | `scripts/` (donor_score.py, run_donor_evaluation.py, sheet_append_donors.py) |
| Скилл Cursor (автозаполнение таблицы) | **в этом репо:** `.cursor/skills/donor-evaluation-table/` |
| Инструкция и формулы | shared-docs: `wiki/about-company/about-departments/about-seo/donor-evaluation-*.md` |

---

## Приложения (Streamlit)

| Сервис | Путь | Назначение |
|--------|------|------------|
| Панель вебмастеров (реестры, «Жду публикации», IMAP/SMTP) | [webmaster-pipeline-dashboard/README.md](webmaster-pipeline-dashboard/README.md) | HACK-382, вариант E |
| Подготовка списка доменов из Ahrefs | [placement-prep-app/README.md](placement-prep-app/README.md) | Вычитание уже размещённых |

## Структура

```
├── docs/                   # Документация команды
│   ├── agreements/         # Договорённости, распределение зон
│   ├── rules/              # Правила, конвенции
│   ├── how-to/             # Инструкции, процессы, чеклисты
│   └── inbox/              # Неклассифицированное (fallback)
├── Application/            # Приложения и сервисы команды (каждый сервис — отдельная подпапка)
│   └── article-generation-service/  # Генерация статей для публикации (выгрузка разработчика)
├── learnings/              # Результаты тестов, гипотезы, кейсы
├── gmail-backlog/          # Backlog из Gmail
├── scripts/                # Скрипты
├── .cursor/
│   ├── rules/              # Правила для AI-агента
│   └── skills/             # Скиллы (linkbuilding-docs-route)
├── AGENTS.md               # Контекст для AI
└── PLAN.md                 # План создания структуры
```

## Как добавлять документы

Сотрудник описывает задачу в Cursor — агент сам определяет папку и формат по скиллу `linkbuilding-docs-route`.

**Примеры запросов:**
- «Задокументируй: мы договорились, что Elena ведёт контент по тематике X»
- «Зафиксируй правило: спортивные новости → спортивные доноры»
- «Добавь инструкцию по переговорам с донорами»
- «Результат теста: evergreen лучше конвертит на всех донорах»

Подробнее: [docs/README.md](docs/README.md)

## Связанные ресурсы

- [Отчёты и шаблоны](../../../shared-docs/wiki/about-company/about-departments/about-seo/docs/linkbuilding/) — daily reports, Bitrix, onboarding (shared-docs)
- [Функция outreach](../../../shared-docs/wiki/about-company/about-departments/about-seo/functions/linkbuilding-outreach.md) — владелец, метрики, процессы
- [LinkBuilder CRM](../hide-linkbuilding-application-crm/) — backend, CMS, API
