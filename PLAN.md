# План: структура Linkbuilding и агентная маршрутизация

**Назначение:** Единый план создания структуры docs и настройки агента, который сам определяет, куда класть контент. Сотрудник описывает задачу — агент выбирает папку, формат и файл.

**Опорные документы:**
- [LINKBUILDING_DOCS_AGENT_ROUTING_DEEP_RESEARCH.md](../../../.cursor/standards/research/LINKBUILDING_DOCS_AGENT_ROUTING_DEEP_RESEARCH.md) — полный research
- [RESEARCH_LINKBUILDING_DOCS_ROUTING_SUMMARY.md](RESEARCH_LINKBUILDING_DOCS_ROUTING_SUMMARY.md) — краткий отчёт
- [linkbuilding-outreach.md](../../../shared-docs/wiki/about-company/about-departments/about-seo/functions/linkbuilding-outreach.md) — функция outreach

---

## Часть 1: Структура (основной план)

### 1.1. Текущее состояние

**Разбросанность:**

| Где | Что |
|-----|-----|
| `internal/seo/linkbuilding/` | Только Gmail backlog (сырые письма), README — шаблон GitLab |
| `shared-docs/.../about-seo/docs/linkbuilding/` | 99+ документов: SEOLB_august, SEOLB_december, SEOLB_dokumenty, SEOLB_generatsiya-statey, SEOLB_instruktsii, daily reports, Bitrix-инструкции, шаблоны доноров (MR, TA), onboarding |
| `shared-docs/.../about-seo/functions/linkbuilding-outreach.md` | Описание функции outreach (владелец, метрики, границы, ключевые процессы) |
| `internal/seo/hide-linkbuilding-application-crm/` | LinkBuilder CRM (backend, linkbuilder-cms, docs), свой AGENTS.md |

**Ключевая проблема:** Нет единого канонического хранилища выводов, гипотез, соглашений и правил. Документация разбросана; сотрудники плохо ориентируются в репозитории и Cursor.

### 1.2. Задачи по зонам (из скринов — исходный контекст)

Эти задачи задавались Elena, Feruza, Oleg. docs/ и learnings/ должны их закрывать.

**Elena (контент, типы статей):**

| Задача | Куда пойдёт в новой структуре |
|--------|-------------------------------|
| Тип статьи: news vs evergreen, 30/70 | docs/how-to/article-type-classification.md |
| Placement: спортивные новости → спортивные доноры; общие → общие | docs/how-to/content-placement-guidelines.md |
| Шаблоны от Ильи Герасимова для инфо-статей | docs/how-to/content-creation-playbook.md |
| Evergreen хорошо работал на всех донорах | learnings/ (кейс) |

**Feruza (переговоры, два линка):**

| Задача | Куда пойдёт |
|--------|-------------|
| Гипотеза: если разрешают 2 ссылки — пробовать | learnings/ (гипотеза) |
| Сколько hops от главной до статьи? Вопросы, условия, согласование | docs/how-to/negotiation-guide.md |
| Процесс при типовых отказах | docs/how-to/rejection-handling.md |

**Oleg (EEAT, Tier 2, трекинг):**

| Задача | Куда пойдёт |
|--------|-------------|
| EEAT: ссылки на авторов при двух линках | docs/how-to/eeat-authors-checklist.md |
| Tier 2 links | docs/how-to/link-placement-strategies.md |
| Отслеживание взаимосвязей ссылок | docs/how-to/link-tracking-methodology.md |
| Метрики: ссылки на авторов, упоминания без ссылок | docs/rules/ или docs/how-to/ |

### 1.3. Целевая структура

```
internal/seo/linkbuilding/
├── README.md                    # Назначение репо, навигация
├── AGENTS.md                    # Контекст для AI (что читать, какие скиллы)
├── PLAN.md                     # Этот план
├── .cursor/
│   ├── rules/
│   │   └── linkbuilding-context.mdc
│   └── skills/
│       └── linkbuilding-docs-route/
│           └── SKILL.md
├── docs/
│   ├── README.md               # Навигация: что где лежит
│   ├── agreements/             # Договорённости, распределение зон
│   ├── rules/                  # Правила, конвенции
│   ├── how-to/                 # Инструкции «как делаем»
│   └── inbox/                  # Fallback при неопределённости
├── learnings/                  # Результаты тестов (отдельно от docs)
├── gmail-backlog/              # Существующее — без изменений
└── scripts/                    # Существующее — без изменений
```

### 1.4. Связь с shared-docs

- **shared-docs/.../linkbuilding/** — daily reports, Bitrix, шаблоны доноров остаются как есть
- **internal/seo/linkbuilding/docs/** — соглашения, правила, процессы; то, что агент использует в контексте
- В `docs/README.md` — ссылка на shared-docs для отчётов и общих инструкций

### 1.5. Этапы по структуре

| № | Этап | Критерий |
|---|------|----------|
| 1 | Создать папки docs/, docs/agreements/, docs/rules/, docs/how-to/, docs/inbox/, learnings/ | Структура существует |
| 2 | Создать docs/README.md с навигацией | Люди понимают, что где лежит |
| 3 | Обновить README.md репо | Назначение, навигация по структуре |
| 4 | Выполнить подплан «Агент» (часть 2) | Агент маршрутизирует контент |
| 5 | Пилот | 3–5 тестовых запросов, проверка маршрутизации |

---

## Часть 2: Подплан — Агент и маршрутизация

Агент сам определяет папку и формат. Человек не должен разбираться в структуре.

### 2.1. Скилл linkbuilding-docs-route

**Путь:** `internal/seo/linkbuilding/.cursor/skills/linkbuilding-docs-route/SKILL.md`

**Триггеры** (в description): «запиши в docs», «задокументируй», «зафиксируй», «добавь соглашение», «добавь правило», «как мы делаем», «результат теста» — в контексте linkbuilding.

**Route Definitions (критерии выбора папки):**

| Маршрут | Критерии | Папка | Примеры |
|---------|----------|-------|---------|
| agreements | Договорённости между людьми/командами, распределение зон | docs/agreements/ | «договорились», «согласовали», «кто за что» |
| rules | Правила, конвенции, обязательно/запрещено | docs/rules/ | «правило», «так надо», «нельзя» |
| how-to | Инструкции «как делаем», процессы, чеклисты | docs/how-to/ | «как делаем», «инструкция», «процесс» |
| learnings | Результаты тестов, что сработало/не сработало | learnings/ | «протестировали», «результат», «гипотеза» |
| inbox | Неясно куда | docs/inbox/ | Fallback |

**Алгоритм (шаги в SKILL.md):**
1. Прочитать запрос и контент пользователя
2. Классифицировать по Route Definitions
3. Определить целевой файл (существующий или новый, kebab-case)
4. Применить формат (шаблоны agreements/rules/how-to/learnings)
5. Создать/обновить файл
6. При неуверенности — docs/inbox/ или уточнить

**Форматы (лаконичные):** см. раздел 5.3 в [LINKBUILDING_DOCS_AGENT_ROUTING_DEEP_RESEARCH.md](../../../.cursor/standards/research/LINKBUILDING_DOCS_AGENT_ROUTING_DEEP_RESEARCH.md)

### 2.2. .cursor/rules

**Файл:** `internal/seo/linkbuilding/.cursor/rules/linkbuilding-context.mdc`

- globs: `internal/seo/linkbuilding/**`
- При запросах на документирование — использовать скилл linkbuilding-docs-route
- Ссылка на AGENTS.md и docs/README.md

### 2.3. AGENTS.md

Кратко: контекст Linkbuilding; при запросе задокументировать — скилл linkbuilding-docs-route; структура: docs/agreements, docs/rules, docs/how-to, learnings, docs/inbox.

### 2.4. Регистрация скилла

- Выполнить `/sync` или скилл **skills-registry** — реестр подтянет скилл из linkbuilding
- Проверить: skills-registry обновлён

### 2.5. Пилот

- 3–5 запросов: «зафиксируй соглашение», «как ведём переговоры», «результат теста: evergreen лучше»
- Проверить: правильная папка, адекватный формат
- При ошибках — скорректировать Route Definitions

---

## Чеклист реализации (общий)

- [x] Создана структура docs/ и learnings/
- [x] docs/README.md с навигацией
- [x] Создан SKILL.md с Route Definitions и алгоритмом
- [x] Добавлены linkbuilding-context.mdc и AGENTS.md
- [ ] Выполнен /sync
- [x] Проведён пилот (3 теста: agreements, rules, learnings — маршрутизация корректна)
- [x] README.md репо обновлён

---

## Риски

| Риск | Митигация |
|------|-----------|
| Неверная классификация | Inbox как fallback; уточнять при противоречиях |
| Критерии требуют доработки | Итерация после пилота; примеры в скилле |
| Сотрудник не знает про скилл | AGENTS.md + README; напоминание в .cursor/rules |
