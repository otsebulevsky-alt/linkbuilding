# Проспектинг вебмастеров (поиск и отбор площадок)

Здесь лежат **отдельные способы** поиска вебмастеров / владельцев площадок / контактов для размещений. Один способ = **один** Markdown-файл.

## Почему такое название папки

**webmaster-prospecting** — в outreach «prospecting» это процесс **поиска и первичной квалификации** контактов до стадии переговоров. По смыслу совпадает с «как мы находим вебмастеров».

## Правила файлов

- **Имя файла:** латиница, `kebab-case`, по сути способа  
  Примеры: `search-via-competitor-backlinks.md`, `niche-forums-and-chats.md`
- **Содержание:** максимально практично — пошагово, с критериями отбора и типичными ошибками.
- **Скриншоты:** класть рядом с гайдом в подпапку `assets/<имя-гайда-без-md>/` (PNG/WebP), в тексте ссылаться относительными путями, например `assets/competitor-backlinks/step-2-serp.png`.
- **Не дублировать:** если способ уже есть — дополнять существующий файл, а не создавать второй с другим именем.

## Шаблон нового способа

Копировать и переименовать: [TEMPLATE-webmaster-method.md](TEMPLATE-webmaster-method.md).

## Запрос в Cursor (для билдера)

Указать явно папку:

`internal/seo/linkbuilding/docs/how-to/webmaster-prospecting/`

и вставить сырой список шагов / критериев — агент оформляет по шаблону и предлагает имя файла.

## Индекс способов (SEOLB-164, Oleg)

Один файл = один канал проспектинга. Перед добавлением нового проверьте, нет ли пересечения — дополняйте существующий гайд.

| Файл | Кратко |
|------|--------|
| [serp-guest-post-operators.md](serp-guest-post-operators.md) | Поисковая выдача, операторы guest post / contribute / guidelines. |
| [competitor-backlinks-outreach.md](competitor-backlinks-outreach.md) | Ссылки и referring domains конкурентов (Ahrefs / Semrush / Majestic). |
| [ahrefs-keyword-explorer-prospecting.md](ahrefs-keyword-explorer-prospecting.md) | Ahrefs Keyword Explorer: семантика → SERP → домены. |
| [ahrefs-content-explorer-prospecting.md](ahrefs-content-explorer-prospecting.md) | Ahrefs Content Explorer: сильные страницы по теме → домены. |
| [directories-and-marketplaces-bases.md](directories-and-marketplaces-bases.md) | Каталоги, маркетплейсы, готовые базы и прайсы. |
| [niche-media-manual-lists.md](niche-media-manual-lists.md) | Ручной обход нишевых медиа и кураторских списков. |
| [social-professional-networks.md](social-professional-networks.md) | LinkedIn, X, Telegram и др. для поиска редакций и ЛПР. |
| [cold-outreach-via-site-contacts.md](cold-outreach-via-site-contacts.md) | Холодные письма по контактам с сайта без публичной программы гостевых постов. |
| [brand-partnerships-content-exchange.md](brand-partnerships-content-exchange.md) | Партнёрства и обмен контентом со смежными брендами (PR/маркетинг). |

Общий справочник по каналам в **корневом workspace** (отдельный git `shared-docs`): `shared-docs/seo/linkbuilding/context/donor-discovery-methods.md` — дублирует каналы одним файлом для всего отдела; детальные пошаговые гайды — только в этой папке.

**Задача YouTrack:** [SEOLB-164](https://youtrack.rantsports.com/issue/SEOLB-164).
