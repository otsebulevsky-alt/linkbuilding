# Панель линкбилдинга — вебмастеры (Streamlit)

Приложение для сценария **HACK-382 / вариант E**: дашборд по Google Sheets (реестры TelecomAsia и второй файл), фильтр **только ваши строки** по колонке **Linkbuilder**, вкладка **«Жду публикации»** с черновиком письма и отправкой через **SMTP (Gmail)**, просмотр **непрочитанных** через **IMAP**, просмотр **калькулятора** (два листа по `gid`).

Код: `app.py`, модули в `lib/`.

### Как задумывалось в документах HACK-382 (без GitLab CI и зеркала)

Первоисточник: [implementation-notes](../../../../shared-docs/events/2026-03-30_ai-hackaton/results/hack-382/implementation-notes.md) (раздел **«Вариант E — Streamlit»**), кратко [README hack-382](../../../../shared-docs/events/2026-03-30_ai-hackaton/results/hack-382/README.md). Там панель = **Python Streamlit** + ключи в **Secrets**, деплой в облако — **опция** ([Streamlit Community Cloud](https://streamlit.io/cloud) или Cloud Run), а не обязательный GitLab → GitHub pipeline.

**Рабочий минимум сейчас:** папка `webmaster-pipeline-dashboard/` + `.streamlit/secrets.toml` + `.streamlit/gcp-service-account.json` → локальный запуск (**[Шаг 4](#шаг-4-локальный-запуск)** ниже) или [SETUP.md](SETUP.md). Этого достаточно, чтобы «продолжить логику и вёрстку».

**Постоянный URL в интернете (24/7)** — отдельный необязательный слой: [DEPLOY.md](DEPLOY.md) (в т.ч. зеркало GitHub, если понадобится Streamlit Cloud).

### Где лежит ключ Google (канон)

**Выбранный вариант:** один файл **`.streamlit/gcp-service-account.json`** + в `secrets.toml` строка  
`GOOGLE_SERVICE_ACCOUNT_FILE = ".streamlit/gcp-service-account.json"` — **без** вставки всего JSON в TOML (меньше дублей, проще ротировать ключ).

| Назначение | Путь |
|------------|------|
| **Ключ для панели** (не в git) | [`.streamlit/gcp-service-account.json`](.streamlit/gcp-service-account.json) |
| **Остальные настройки** (SMTP, фильтры) | [`.streamlit/secrets.toml`](.streamlit/secrets.toml) |
| Бэкап до нормализации | `.streamlit/secrets.toml.bak` (создаётся скриптом один раз) |

**Порядок загрузки ключа в коде:** `GOOGLE_SERVICE_ACCOUNT_JSON` → `GOOGLE_SERVICE_ACCOUNT_FILE` → `GOOGLE_APPLICATION_CREDENTIALS` → по очереди `gcp-service-account.json`, `service_account.json`.

**Если в статистике «0 строк» при том что данные есть:** откройте **Диагностика** на странице — там список колонок и частоты имён в колонке исполнителя. Часто в таблице фамилия латиницей: добавьте в `secrets.toml` строку `LINKBUILDER_ALIASES = "Oleg,фамилия"` (через запятую). Убедитесь, что **gid** листа в секретах совпадает с вкладкой реестра в браузере (`#gid=...` в URL).

Скрипты: `py scripts/import_sa_to_secrets.py` — собрать TOML с встроенным JSON из файла; `py scripts/normalize_secrets_to_file.py` — убрать встроенный JSON из `secrets.toml`, оставить указатель на файл (бэкап `.bak`).

## Что сделано в коде (можно использовать сразу после настройки секретов)

- Чтение реестров по API Google Sheets (сервисный аккаунт).
- Определение имени листа по **gid** из URL (как в ссылке на таблицу).
- Статистика по статусам для строк с выбранным линкбилдером.
- Экспорт отфильтрованных строк в CSV.
- Вкладка «Жду публикации»: выбор строки, вставка ссылки из **Article/post**, тема/тело письма RU/EN, отправка через SMTP.
- Вкладка «Входящие»: список непрочитанных (IMAP) — заготовка под дальнейший сценарий «собрать доноров в служебную таблицу».
- Вкладка «Калькулятор»: превью первых строк листов калькулятора (вкладки 1 и 2 по `gid`).
- Вкладка «Варианты оплаты»: чтение справочной книги «Возможности оплаты» (`SPREADSHEET_PAYMENT_OPTIONS_ID`, по умолчанию `17MoDWn…`; вкладка по `GID_PAYMENT_OPTIONS`, по умолчанию `0`).

## Что ассистент / CI не может сделать за вас

Ниже — пошаговые действия **только у вас** (Google Cloud, доступы, деплой).

---

### Шаг 1. Сервисный аккаунт Google Cloud

1. Откройте [Google Cloud Console](https://console.cloud.google.com/) и выберите или создайте проект.
2. Включите API **Google Sheets API** (и при необходимости позже **Gmail API** — для этого приложения используется IMAP/SMTP с паролем приложения, не OAuth).
3. **IAM** → **Service Accounts** → **Create service account** → создайте учётную запись.
4. **Keys** → **Add key** → **JSON** — скачайте файл ключа.
5. Скопируйте **весь** JSON в переменную `GOOGLE_SERVICE_ACCOUNT_JSON` (локально в `.streamlit/secrets.toml`, в облаке — в Secrets приложения). См. `secrets.toml.example`.

#### Ключ JSON создать нельзя (организационная политика)

Если при создании ключа появляется сообщение вроде **«Service account key creation is disabled»** и политика **`iam.disableServiceAccountKeyCreation`**, это **запрет на уровне организации** Google Cloud: ключи считаются рискованными, админы часто отключают их по умолчанию.

**Что можно сделать:**

| Вариант | Когда уместно |
|--------|----------------|
| **Попросить исключение у админа** | Роль **Organization Policy Administrator** (`roles/orgpolicy.policyAdmin`) может ослабить ограничение для **папки/проекта** или временно — чтобы выдать ключ для Streamlit / песочницы. Укажите политику: `iam.disableServiceAccountKeyCreation`. |
| **Отдельный проект вне «жёсткой» организации** | Если политика компании позволяет тестовый GCP-проект без этого ограничения — создайте сервисный аккаунт там, расшарьте таблицы на его `client_email`, JSON положите в Secrets. |
| **Локальная разработка без JSON** | В `.streamlit/secrets.toml` задайте `GOOGLE_USE_ADC = true`, выполните `gcloud auth application-default login` под **личным/корпоративным** Google-аккаунтом, включите **Google Sheets API** для проекта (или используйте тот же проект), и **расшарьте все таблицы на email этого пользователя** (не на `@...iam.gserviceaccount.com`). Это обход для **только локального** запуска; **Streamlit Community Cloud** по-прежнему ожидает JSON в Secrets (или деплой на GCP с привязанным сервисным аккаунтом без ключа — отдельная доработка). |

Сервисный аккаунт из шага 3 всё равно нужен для **шаринга таблиц** по `client_email`, если вы используете JSON в проде; при режиме ADC доступ идёт через **ваш** аккаунт из `gcloud`.

### Шаг 2. Доступ к таблицам

Для email вида `your-sa@project-id.iam.gserviceaccount.com` из JSON:

1. Откройте каждую таблицу из [implementation-notes](../../../../shared-docs/events/2026-03-30_ai-hackaton/results/hack-382/implementation-notes.md) (служебная, оба реестра, калькулятор).
2. **Настройки доступа** → добавьте сервисный аккаунт с ролью **Читатель** (или **Редактор**, если позже добавите запись в таблицу из приложения).
3. Убедитесь, что первая строка листа содержит заголовки: `Linkbuilder`, `Status`, `Article/post`, `Website Donor`, `Cost $` — как в конфиге или поправьте ключи в `secrets.toml`.

### Шаг 3. Пароль приложения Gmail (SMTP + IMAP)

1. В Google-аккаунте включите **двухэтапную аутентификацию**.
2. Создайте **пароль приложения** для «Почта» / «Другое».
3. Вставьте в `GMAIL_SMTP_USER`, `GMAIL_SMTP_APP_PASSWORD` (и при необходимости те же для IMAP).

Без этого кнопка «Отправить письмо» и IMAP работать не будут; вкладки с таблицами — будут.

### Шаг 4. Локальный запуск

**Важно:** `app.py` лежит **не** в корне `start/`, а в этой папке. Если в терминале было `C:\project\start>` и ошибка `File does not exist: app.py` — сначала перейдите в каталог приложения.

От корня репозитория (`start/`):

```bash
cd internal/seo/linkbuilding/webmaster-pipeline-dashboard
py -m pip install -r requirements.txt
mkdir .streamlit
copy secrets.toml.example .streamlit\secrets.toml
# Edit .streamlit\secrets.toml — keys, SMTP, etc.
py -m streamlit run app.py
```

**Windows (абсолютный путь):**

```text
cd C:\project\start\internal\seo\linkbuilding\webmaster-pipeline-dashboard
py -m streamlit run app.py
```

Либо из любого каталога:

```text
powershell -ExecutionPolicy Bypass -File C:\project\start\internal\seo\linkbuilding\webmaster-pipeline-dashboard\run.ps1
```

Скрипт [run.ps1](run.ps1) сам делает `cd` в папку с `app.py` и, если порт **8503** уже занят (часто второй экземпляр Streamlit), автоматически пробует **8504** — смотрите строку `Streamlit URL:` в консоли.

#### Локально: частые сбои

| Симптом | Что сделать |
|--------|-------------|
| **`Port 8503 is not available`** | Закройте старый Streamlit в другом окне или в диспетчере задач (процесс `python` / Streamlit), либо запустите снова [run.ps1](run.ps1) — он переключится на 8504. |
| **`git push` на GitHub → 403, denied to другой логин** | Windows отдаёт GitHub сохранённый логин не того аккаунта. Удалите учётные данные для `git:https://github.com` в «Параметры → Учётные данные», затем снова `git push` и войдите под **владельцем** репозитория или используйте PAT. Подробно: [DEPLOY.md](DEPLOY.md) (таблица «Учётные записи Rantsports»). |
| **Красный traceback в браузере при загрузке таблицы** | Обновите страницу после исправления сети/VPN; при 403 к таблице — расшарьте книгу на email сервисного аккаунта (см. шаг 2). Код больше не падает на сетевых ошибках API — при сбое лист может отобразиться пустым, смотрите **Диагностика**. |

### Постоянный доступ 24/7 (рекомендуется: облако)

**Сводная инструкция:** [DEPLOY.md](DEPLOY.md) (Streamlit Cloud, Docker, GitLab → GitHub mirror).

Чтобы дашборд открывался **в любой момент с любого устройства** и **не зависел от вашего ПК**, задеплойте приложение в **[Streamlit Community Cloud](https://streamlit.io/cloud)** — постоянный URL вида `https://<имя>.streamlit.app`.

1. Закоммитьте и отправьте в **Git** репозиторий, где есть путь `internal/seo/linkbuilding/webmaster-pipeline-dashboard/` (удобнее **GitHub** — вход в Streamlit Cloud через GitHub).
2. Зайдите на [share.streamlit.io](https://share.streamlit.io) → **Sign in** → **New app**.
3. Выберите репозиторий и ветку (например `main`).
4. **Main file path** (от корня репо):  
   `internal/seo/linkbuilding/webmaster-pipeline-dashboard/app.py`
5. Если в форме есть поле **App root** / **Root directory** / **Working directory**, укажите:  
   `internal/seo/linkbuilding/webmaster-pipeline-dashboard`  
   Тогда `requirements.txt` и `runtime.txt` подхватятся из этой папки.
6. **Deploy**. Дождитесь зелёного статуса и откройте выданный URL.
7. **Settings** (шестерёнка у приложения) → **Secrets** — вставьте TOML по образцу [secrets.toml.example](secrets.toml.example). В облаке **нет** файла `.streamlit/gcp-service-account.json`, поэтому обязательно задайте **`GOOGLE_SERVICE_ACCOUNT_JSON`** (весь JSON сервисного аккаунта в тройных кавычках `'''...'''` или одной строкой). Остальное: SMTP, `LINKBUILDER_FILTER`, при необходимости `LINKBUILDER_ALIASES`.
8. **Reboot app** после сохранения Secrets.

**Монорепо:** в `app.py` добавлен `sys.path` для папки приложения — импорт `lib/` работает и локально, и в облаке.

**GitLab без GitHub:** у Streamlit Cloud исторически проще связка с GitHub; для GitLab смотрите актуальную [документацию Streamlit](https://docs.streamlit.io/streamlit-community-cloud) или задеплойте копию только папки `webmaster-pipeline-dashboard` в отдельный репозиторий с `app.py` в корне.

### Постоянный локальный дашборд (Windows, без облака)

Пока **включён ваш ПК**: можно не держать терминал открытым вручную — автозапуск при входе в Windows и перезапуск при падении процесса.

1. Локальный порт задаёт [run.ps1](run.ps1) / [run-daemon.ps1](run-daemon.ps1) (**8503**, при занятости — **8504**). В [`.streamlit/config.toml`](.streamlit/config.toml) **нет** `port`/`address` — иначе ломается деплой на Streamlit Community Cloud.
2. Один раз из корня репозитория `start/`:

```text
powershell -ExecutionPolicy Bypass -File internal/seo/linkbuilding/webmaster-pipeline-dashboard/scripts/install-autostart.ps1
```

Создаётся ярлык в **автозагрузке**: стартует [run-daemon.ps1](run-daemon.ps1) (упал — через 5 с снова). Окно PowerShell свёрнуто; остановить — закрыть окно или снять задачу в диспетчере задач. Отключить: [scripts/uninstall-autostart.ps1](scripts/uninstall-autostart.ps1).

### Шаг 5. Google Sites «домашняя страница»

1. [Google Sites](https://sites.google.com) → новый сайт (или страница в существующем).
2. Заголовок, краткий текст: «Панель линкбилдинга — вебмастеры».
3. Кнопка или ссылка на URL из облака (Streamlit) или на локальный `http://localhost:8503`.
4. Настройте доступ к сайту (только отдел / домен).

### Шаг 6. Вторая вкладка калькулятора (опционально)

Если нужен второй лист в превью: откройте калькулятор, переключитесь на вкладку 2, скопируйте `gid` из URL (`#gid=...`) и задайте в Secrets `GID_CALCULATOR_TAB_2`. Если `0` — вторая вкладка в UI не показывается.

---

## Безопасность

- Не коммитьте `.streamlit/secrets.toml` и JSON ключи.
- Ограничьте доступ к приложению Streamlit Cloud (приватный репозиторий, список зрителей — по правилам Streamlit).
- Пароль приложения Gmail храните только в Secrets.

## Связанные документы

- [HACK-382 implementation-notes](../../../../shared-docs/events/2026-03-30_ai-hackaton/results/hack-382/implementation-notes.md)
- Скилл черновиков ответов: [webmaster-reply-draft](../../../../.cursor/skills/webmaster-reply-draft/SKILL.md) (в корневом workspace `start/`).

**Последнее обновление:** 2026-03-31 — облако 24/7: раздел Streamlit Community Cloud; `sys.path` в `app.py`; `runtime.txt`; автозапуск Windows: `run-daemon.ps1`.

**Пошаговый чеклист только для вас (с ссылками):** [SETUP.md](SETUP.md).