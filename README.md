# Linkbuilding

Репозиторий команды Linkbuilding (SEO). Каноническое хранилище знаний: соглашения, правила, инструкции, результаты тестов.

## Структура

```
├── docs/                   # Документация команды
│   ├── agreements/         # Договорённости, распределение зон
│   ├── rules/              # Правила, конвенции
│   ├── how-to/             # Инструкции, процессы, чеклисты
│   └── inbox/              # Неклассифицированное (fallback)
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
