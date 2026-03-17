# Краткий отчёт: Agent-driven маршрутизация документов Linkbuilding

**Тема исследования:** Как реализовать вариант 1 (docs/ с подпапками agreements, rules, how-to) так, чтобы агент сам понимал, куда класть контент, без зависимости от человека.

**Дата:** 2026-03-17.

---

## Ключевые находки

1. **Router pattern** — стандартный подход: агент анализирует вход, классифицирует, выбирает маршрут по критериям. Используется в LangChain (multi-agent router), SkillMD route skill, DocRouter.AI.

2. **Skill как решений** — Cursor Skills идеальны для маршрутизации: многошаговый workflow, явные критерии, Conditional Workflow Pattern. Пример: `monobrands-extract-by-agent` — агент читает контент, классифицирует (факт/гипотеза/кейс), раскладывает по разделам.

3. **Route skill (SkillMD)** — эталонная структура: Route Definitions (критерии для каждого пути), Selection Logic (эвристики выбора), Default (куда класть при неопределённости).

4. **Классификация не требует ML** — Claude/Cursor отлично справляется с text classification при минимальных примерах, handles unstructured data.

---

## Лучшие практики

- **Явные критерии** для каждого маршрута (agreements vs rules vs how-to) — в виде эвристик в скилле.
- **Inbox как fallback** — при неопределённости класть в `docs/inbox/`, потом разнести вручную или агентом.
- **Шаблоны формата** — лёгкие (не как MARKUP_FORMAT monobrands): 3–5 полей на тип документа.
- **Триггерные фразы** в description скилла: «занеси в документы», «задокументируй», «зафиксируй соглашение», «запиши как мы делаем».

---

## Рекомендации по реализации

### Скилл `linkbuilding-docs-route`

**Расположение:** `internal/seo/linkbuilding/.cursor/skills/linkbuilding-docs-route/SKILL.md`

**Алгоритм:**

1. **Классифицировать** запрос пользователя по типу контента.
2. **Выбрать маршрут** по Route Definitions (см. документ Deep Research).
3. **Определить формат** — шаблон для agreements / rules / how-to.
4. **Определить целевой файл** — существующий или новый (имя по теме).
5. **Создать/обновить** документ и записать в правильную папку.

**Route Definitions (критерии):**

| Маршрут | Критерии | Папка | Примеры |
|---------|----------|-------|---------|
| **agreements** | Распределение зон, договорённости между людьми, формальные соглашения | docs/agreements/ | «TelecomAsia: 60 анкоров внутренним, остальное холдингу» |
| **rules** | Правила, конвенции, что обязательно/запрещено | docs/rules/ | «Проверка: автор в статье, dofollow» |
| **how-to** | Инструкции «как делаем», процессы, шаги | docs/how-to/ | «Как вести переговоры», «Чеклист перед публикацией» |
| **learnings** | Результаты тестов, что сработало/не сработало | learnings/ | «Evergreen лучше на всех донорах» |
| **inbox** | Неясно куда | docs/inbox/ | — |

**Правило:** В скилле указать `allowed-tools: Read, Write` (как в route skill) — агент только читает и пишет, без выполнения внешних команд.

---

## Репозитории и документация

- **SkillMD route skill:** https://skillmd.ai/how-to-build/route/ — эталон структуры route skill.
- **Cursor Skills:** https://cursor.com/docs/context/skills — формат SKILL.md.
- **create-skill (Cursor):** Conditional Workflow Pattern для ветвления по типу задачи.
- **monobrands-extract-by-agent:** `internal/seo/monobrands-project/.cursor/skills/monobrands-extract-by-agent/SKILL.md` — пример classification + routing в workspace.

---

## Связанные артефакты

- **Полный Deep Research:** `d:\shared-workspace\.cursor\standards\research\LINKBUILDING_DOCS_AGENT_ROUTING_DEEP_RESEARCH.md`
- **Скилл create-skill:** Cursor built-in — шаблоны для скиллов.
- **linkbuilding-outreach function:** `shared-docs/.../about-seo/functions/linkbuilding-outreach.md` — контекст функции.

---

## Следующие шаги

1. Создать структуру `internal/seo/linkbuilding/docs/` (agreements, rules, how-to, inbox).
2. Создать скилл `linkbuilding-docs-route` с Route Definitions и форматами.
3. Добавить в skills-registry (или зарегистрировать в репо linkbuilding).
4. Заполнить AGENTS.md / .cursor/rules для контекста linkbuilding.
5. Пилот: 3–5 запросов от сотрудников → проверка маршрутизации.

---

**Confidence: 85%** — практики проверены внешними источниками; критерии для agreements/rules/how-to требуют уточнения с командой Linkbuilding.
