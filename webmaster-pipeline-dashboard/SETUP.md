# Что сделать только вам — пошагово (с ссылками)

Этот файл — **расширенный чеклист**: Google Cloud, таблицы, Gmail, локальный запуск, **Streamlit Cloud (24/7)**, Google Sites. Код приложения: [README.md](README.md).

---

## Часть A. Google Cloud: проект, API, сервисный аккаунт, JSON-ключ

1. Откройте **[Google Cloud Console](https://console.cloud.google.com/)** и войдите под корпоративным или личным Google-аккаунтом (как договорено у вас в компании).
2. Создайте **проект** или выберите существующий: меню **Select a project** → **New Project**.
3. Включите **Google Sheets API** для этого проекта:
   - меню **APIs & Services** → **[Library](https://console.cloud.google.com/apis/library)**  
   - найдите **Google Sheets API** → **Enable**.  
   Документация API: [Google Sheets API](https://developers.google.com/sheets/api/guides/concepts).
4. Создайте **сервисный аккаунт**:
   - **IAM & Admin** → **[Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)**  
   - **Create service account** → задайте имя → **Create and Continue** → **Done**.
5. Выпустите **ключ JSON**:
   - откройте созданный сервисный аккаунт → вкладка **Keys** → **Add Key** → **Create new key** → тип **JSON** → скачайте файл.  
   - Сохраните файл **в безопасном месте** (не в публичный репозиторий). Внутри JSON будет поле **`client_email`** (вида `...@...iam.gserviceaccount.com`) — оно понадобится для шаринга таблиц.

### Если ключ создать нельзя (политика организации)

Если появляется сообщение вроде **«Service account key creation is disabled»** и политика **`iam.disableServiceAccountKeyCreation`**:

- Описание политики: [Organization Policy: Restrict service account key creation](https://cloud.google.com/resource-manager/docs/organization-policy/restricting-service-accounts#disable_service_account_key_creation).
- Варианты: попросить **администратора организации** временно разрешить создание ключа для вашего проекта/папки; использовать **отдельный тестовый проект** без этой политики; для **только локального** запуска см. [README.md](README.md) раздел про **GOOGLE_USE_ADC** и `gcloud auth application-default login` (тогда таблицы шарятся на **ваш** личный Google email, не на сервисный аккаунт).

**Для Streamlit Community Cloud** обычно всё равно нужен **JSON в Secrets** (или другой согласованный с IT способ) — без ключа на сервисный аккаунт в облаке приложение не поднимет Sheets API так же, как у вас локально.

---

## Часть B. Доступ сервисного аккаунта к Google Таблицам

Для email **`client_email`** из скачанного JSON (у текущего ключа в проекте это **`dashboard@dashboard-486316.iam.gserviceaccount.com`** — при смене JSON сверяйте поле `client_email` в файле).

1. Откройте **каждую** таблицу из списка ниже → **Настройки доступа** (Share) → добавьте этот email с ролью **Читатель** или **Редактор** (см. примечание после таблицы).

| Назначение | Ссылка (с нужным `gid` вкладки) |
|------------|--------------------------------|
| Справочник **«Возможности оплаты»** (вкладка в панели: «Варианты оплаты»; `SPREADSHEET_PAYMENT_OPTIONS_ID` / `GID_PAYMENT_OPTIONS`) | [Открыть](https://docs.google.com/spreadsheets/d/17MoDWnMesQkpmI9bSZAF5LYQpjyM2itU0PpcaS-X240/edit?gid=0#gid=0) |
| Реестр 2 (MR Anchors) | [Открыть](https://docs.google.com/spreadsheets/d/1DaiRFqU2d_85cXr0fDmyhzIY4V9fm0zxh4KraZMOFnw/edit?gid=1088920242#gid=1088920242) |
| Реестр 1 TelecomAsia Anchors | [Открыть](https://docs.google.com/spreadsheets/d/1S5lk-ya4iWwq5znY_vebAuTqloyTlWTcsNuXydZXT00/edit?gid=728254189#gid=728254189) |
| Калькулятор цены (вкладка по умолчанию в коде: `GID_CALCULATOR_TAB_1` = 225938948) | [Открыть](https://docs.google.com/spreadsheets/d/1xrjeVD0Q94JI08v2gFvtv1NbiTAbq0fSjv-A-g5pPSs/edit?gid=225938948#gid=225938948) |
| Служебная (сбор ответов вебмастеров — дефолт в коде: `SPREADSHEET_INBOX_LOG_ID`) | [Открыть](https://docs.google.com/spreadsheets/d/19dMDf3sxH8RuBI6hZwWwen_cm2A_UOQZdXVtcjMRllc/edit?gid=0#gid=0) |

**Роли для кнопок «Прочитать почту» и «торг»:** книга **«Сбор с ответов»** — обязательно **Редактор** (запись строк из IMAP). **Калькулятор** — достаточно **Читатель** (кнопка «торг» только читает лист). Остальные книги из таблицы — минимум **Читатель**, если не требуется запись из приложения.

По умолчанию в [`lib/config.py`](lib/config.py) как **inbox** указан ID **`19dMDf3sx...`**. Если основная служебная таблица — книга **`17MoDWnMes...`**, задайте в `.streamlit/secrets.toml`:  
`SPREADSHEET_INBOX_LOG_ID = "17MoDWnMesQkpmI9bSZAF5LYQpjyM2itU0PpcaS-X240"`.

2. **Проверить `gid` листа** (должен совпадать с тем, что в приложении / в `secrets.toml`):
   - Откройте нужную **вкладку** в книге.
   - В адресной строке браузера найдите фрагмент **`#gid=ЧИСЛО`** — это идентификатор листа.  
   По умолчанию в коде заданы значения из [implementation-notes](../../../../shared-docs/events/2026-03-30_ai-hackaton/results/hack-382/implementation-notes.md). Если ваши вкладки другие — задайте в Secrets: `GID_TELECOM_REGISTRY`, `GID_REGISTRY_2`, `GID_CALCULATOR_TAB_1`, при необходимости `GID_CALCULATOR_TAB_2`.

3. Убедитесь, что **первая строка** листа — заголовки (например `Linkbuilder`, `Status`, `Article/post`). Если названия другие — поправьте в `secrets.toml` ключи `COL_*` (см. [secrets.toml.example](secrets.toml.example)). Для кнопки **«проверка публикаций»** нужны ещё **`Anchor`** и **`Outgoing link`** (или `COL_ANCHOR` / `COL_OUTGOING_LINK`).

---

## Часть C. Gmail: пароль приложения (SMTP и IMAP)

Нужны для вкладок «Жду публикации → отправка» и «Входящие (IMAP)». Без них таблицы всё равно читаются.

1. Включите **двухфакторную аутентификацию** для аккаунта Google: [Google Account: Security](https://myaccount.google.com/security).
2. Создайте **пароль приложения**: [App passwords](https://myaccount.google.com/apppasswords) (если пункт не виден — сначала включите 2FA).
3. Пропишите в локальном `.streamlit/secrets.toml` или в **Secrets** облака значения:
   - `GMAIL_SMTP_USER`, `GMAIL_SMTP_APP_PASSWORD`  
   - при необходимости `GMAIL_IMAP_USER`, `GMAIL_IMAP_APP_PASSWORD`  
   Шаблон: [secrets.toml.example](secrets.toml.example).

Справка Google: [Sign in with app passwords](https://support.google.com/accounts/answer/185833).

---

## Часть D. Локальный запуск на Windows (проверка перед облаком)

1. Установите Python 3.11+ с [python.org](https://www.python.org/downloads/) если ещё не установлен.
2. В терминале: корень репозитория `linkbuilding` → `pip install` → папка приложения:

```text
cd C:\project\start\internal\seo\linkbuilding
py -m pip install -r requirements.txt
cd webmaster-pipeline-dashboard
```

3. Скопируйте [secrets.toml.example](secrets.toml.example) в **`.streamlit/secrets.toml`** и заполните: ключ (`GOOGLE_SERVICE_ACCOUNT_JSON` **или** файл `gcp-service-account.json` + `GOOGLE_SERVICE_ACCOUNT_FILE`), SMTP, фильтры и т.д.
4. Запуск:

```text
py -m streamlit run app.py
```

или:

```text
powershell -ExecutionPolicy Bypass -File C:\project\start\internal\seo\linkbuilding\webmaster-pipeline-dashboard\run.ps1
```

5. Откройте в браузере: по умолчанию **[http://localhost:8503](http://localhost:8503)** (см. [`.streamlit/config.toml`](.streamlit/config.toml)).

6. **Автозапуск Windows** (по желанию): один раз выполните из корня `start/`:

```text
powershell -ExecutionPolicy Bypass -File internal/seo/linkbuilding/webmaster-pipeline-dashboard/scripts/install-autostart.ps1
```

Отключение: [scripts/uninstall-autostart.ps1](scripts/uninstall-autostart.ps1).

---

## Часть E. Постоянный URL 24/7 — Streamlit Community Cloud (рекомендуется)

1. Убедитесь, что изменения с панелью **закоммичены** и **запушены** в удалённый репозиторий (GitHub удобнее для входа в Streamlit).
2. Откройте **[share.streamlit.io](https://share.streamlit.io)** и войдите (часто через **GitHub**).
3. **New app** → выберите **репозиторий** и **ветку** (например `main`).
4. Укажите **Main file path** от корня репозитория (зеркало GitHub `linkbuilding`): **`webmaster-pipeline-dashboard/app.py`**, **App root** пустой. Зависимости — только корневой [`requirements.txt`](../requirements.txt).

5. Если используете только монорепо `start/` без зеркала — путь к `app.py` будет с префиксом `internal/seo/linkbuilding/...`; для Streamlit Cloud обычно деплой с отдельного репо `linkbuilding`, см. [DEPLOY.md](DEPLOY.md).

6. Нажмите **Deploy** и дождитесь успешного деплоя. Откройте выданный URL вида `https://<имя>.streamlit.app`.

7. **Settings** (шестерёнка у приложения) → **Secrets** — вставьте TOML. В облаке **обязательно** задайте **`GOOGLE_SERVICE_ACCOUNT_JSON`** (весь JSON сервисного аккаунта в тройных кавычках `'''...'''` или одной строкой). Локальный путь к файлу ключа в облаке не работает.

8. Сохраните Secrets и выполните **Reboot app**.

Официальная документация: [Streamlit Community Cloud](https://docs.streamlit.io/streamlit-community-cloud), [Deploy an app](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app).

**Ограничение доступа:** приватный репозиторий + настройки доступа в Streamlit по правилам вашей компании.

---

## Часть F. Google Sites — «домашняя страница» со ссылкой на панель

1. Откройте **[Google Sites](https://sites.google.com)**.
2. Создайте сайт или страницу → добавьте кнопку/ссылку на **URL из Streamlit Cloud** (часть E) или на локальный `http://localhost:8503` (только для вас).
3. Настройте **доступ** к сайту (коллегам / домену).

---

## Часть G. Если в панели «0 строк» по Linkbuilder

1. Откройте **Диагностика** на вкладке «Статистика» — посмотрите, какие значения реально в колонке исполнителя.
2. Добавьте в Secrets строку **`LINKBUILDER_ALIASES`** (например `Oleg` или фамилия), как в [README](README.md).
3. Проверьте **`gid`** вкладки (часть B, пункт 2).

---

## Канонические ссылки на документацию в репозитории

- [HACK-382 implementation-notes](../../../../shared-docs/events/2026-03-30_ai-hackaton/results/hack-382/implementation-notes.md)
- Скилл черновиков ответов: [webmaster-reply-draft](../../../../.cursor/skills/webmaster-reply-draft/SKILL.md)

**Последнее обновление:** 2026-03-31
