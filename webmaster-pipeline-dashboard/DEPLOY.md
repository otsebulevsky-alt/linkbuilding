# Постоянный онлайн (24/7)

Репозиторий кода: **GitLab** (`internal/seo/linkbuilding`). [Streamlit Community Cloud](https://streamlit.io/cloud) подключается **только к GitHub** — для него нужен зеркальный репозиторий на GitHub.

## Учётные записи Rantsports (канон)

| Что | Правило |
|-----|--------|
| **Код и git** | Только из рабочего workspace. В репозитории `linkbuilding` задано: `user.email` = **`o.tsebulevsky@rantsports.com`**, `user.name` = **Oleg Tsebulevsky**. |
| **GitHub** | Один аккаунт, с которым вы пушите и деплоите: в [GitHub → Emails](https://github.com/settings/emails) должна быть **подтверждена** почта **`o.tsebulevsky@rantsports.com`**. Не пушить в рабочий репозиторий с личного аккаунта с другим email — иначе **403** (как с `olegtseb9806`). |
| **Streamlit Cloud** | Вход через **тот же** GitHub-аккаунт, что и для push (кнопка «Sign in with GitHub»). |
| **Windows: сохранённые пароли** | «Параметры» → «Учётные данные» → удалить записи **`git:https://github.com`**, относящиеся к **чужим** логинам. Затем снова `git push` — авторизоваться аккаунтом с **rantsports**-почтой или [PAT](https://github.com/settings/tokens) для него. |
| **Обход 403 на ПК** | В GitLab: **Settings → CI/CD → Variables** добавьте **`GITHUB_TOKEN`** (masked): [classic PAT](https://github.com/settings/tokens) GitHub с scope **repo**, созданный под аккаунтом **владельца** `github.com/otsebulevsky-alt/linkbuilding`. После пуша в GitLab job **`mirror_github_streamlit`** (см. `.gitlab-ci.yml`) отправит ветку на GitHub **без** локальных учётных данных Windows. |
| **Секреты приложения** | `GOOGLE_SERVICE_ACCOUNT_JSON`, Gmail и т.д. — только из ваших локальных файлов / GCP, не пересылать в общий чат. |

---

## Пошагово: ваши действия (максимально подробно)

Ниже — порядок, который приводит к **зеркалу кода на GitHub** (через GitLab CI) и к **постоянному URL на Streamlit**. Предполагается: репозиторий GitHub **`otsebulevsky-alt/linkbuilding`** уже [создан пустым](https://github.com/new), ветка с кодом в GitLab — **`feature/seolb-164-webmaster-prospecting-oleg`**.

### Этап A. GitHub — почта и репозиторий

1. Войдите на [github.com](https://github.com) под аккаунтом **`otsebulevsky-alt`** (или тем, кто **владелец** репозитория `linkbuilding`).
2. Откройте [github.com/settings/emails](https://github.com/settings/emails).
3. Убедитесь, что **`o.tsebulevsky@rantsports.com`** есть в списке и статус **Verified**. Если нет — добавьте письмо, перейдите по ссылке из письма, при необходимости сделайте эту почту **Primary** для рабочих репозиториев.
4. Откройте [github.com/otsebulevsky-alt/linkbuilding](https://github.com/otsebulevsky-alt/linkbuilding). Если репозитория нет — [создайте](https://github.com/new): имя **`linkbuilding`**, **без** README / .gitignore / license → **Create repository**.

### Этап B. GitHub — Personal Access Token (для GitLab CI)

1. Откройте [github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token** → выберите **Generate new token (classic)**.
2. **Note:** например `gitlab-mirror-linkbuilding`.
3. **Expiration:** по политике компании (например 90 дней или No expiration, если разрешено).
4. Отметьте scope **`repo`** (полный доступ к репозиториям — нужен для `git push`).
5. **Generate token** — **сразу скопируйте** строку токена (потом её не покажут). Храните как пароль; **не** вставляйте в общий чат.

### Этап C. GitLab — переменная CI/CD

1. Откройте проект в GitLab: **ai-first-workspace / internal / seo / linkbuilding** (URL вида `rantsports.gitlab.yandexcloud.net/.../linkbuilding`).
2. Слева: **Settings** → **CI/CD**.
3. Разверните **Variables** → **Expand**.
4. **Add variable**:
   - **Key:** `GITHUB_TOKEN`
   - **Value:** вставьте токен из этапа B (одной строкой).
   - Включите **Mask variable** (и при необходимости **Protect variable**, если хотите, чтобы токен использовался только на защищённых ветках — тогда ветку нужно пометить как protected или снять флаг).
5. **Add variable**.

### Этап D. Запуск пайплайна с job зеркалирования

Job **`mirror_github_streamlit`** в [`.gitlab-ci.yml`](../.gitlab-ci.yml) выполняется **только если** задана переменная **`GITHUB_TOKEN`**.

1. Убедитесь, что последний коммит с `.gitlab-ci.yml` есть в вашей ветке (у вас уже пушили в `feature/seolb-164-webmaster-prospecting-oleg`).
2. Сделайте любой **новый коммит** в эту ветку **или** в GitLab: **CI/CD → Pipelines → Run pipeline** → выберите ветку **`feature/seolb-164-webmaster-prospecting-oleg`** → **Run pipeline**.
3. Откройте запущенный pipeline → дождитесь стадии **deploy** → job **`mirror_github_streamlit`**.
4. Если job **зелёная** — ветка отправлена на GitHub. Если **красная** — откройте лог job: частые причины — неверный токен, нет прав `repo`, репозиторий GitHub не существует или переименован.

### Этап E. Проверка GitHub

1. Откройте [github.com/otsebulevsky-alt/linkbuilding](https://github.com/otsebulevsky-alt/linkbuilding).
2. Должна отображаться ветка **`feature/seolb-164-webmaster-prospecting-oleg`** и папка **`webmaster-pipeline-dashboard`** с файлами (`app.py`, `requirements.txt` и т.д.).

### Этап F. Streamlit Community Cloud — деплой

1. Войдите на [share.streamlit.io](https://share.streamlit.io) **тем же GitHub-аккаунтом**, что владеет репозиторием (через **Sign in with GitHub**).
2. **Мои приложения** → **Создать приложение** / **Deploy a public app from GitHub** → **Deploy now**.
3. Заполните форму [share.streamlit.io/deploy](https://share.streamlit.io/deploy):
   - **Repository:** `otsebulevsky-alt/linkbuilding`
   - **Branch:** `feature/seolb-164-webmaster-prospecting-oleg`
   - **Main file path:** `webmaster-pipeline-dashboard/app.py`
   - **App URL (optional):** любое свободное имя (например `linkbuilding-webmaster`).
   - **Advanced settings** (если есть): **Main module directory** / **App root** = `webmaster-pipeline-dashboard`
4. **Deploy**. Дождитесь окончания сборки (логи на экране). При ошибке импорта проверьте, что путь к `app.py` и root совпадают с пунктами выше.

### Этап G. Streamlit — Secrets (Google и опции)

1. В карточке приложения: **⋮** (три точки) → **Settings** → **Secrets**.
2. **Быстро собрать блок на ПК** (не отправляйте вывод в чат): из папки `webmaster-pipeline-dashboard` выполните  
   `py scripts/print_streamlit_cloud_secrets_snippet.py` — скопируйте вывод целиком в поле Secrets.
3. Вставьте TOML. Обязательно для Sheets API в облаке:
   - **`GOOGLE_SERVICE_ACCOUNT_JSON`** = весь JSON сервисного аккаунта из вашего локального файла ключа (как в [secrets.toml.example](secrets.toml.example)), в тройных кавычках `''' ... '''`.
   - **Не** используйте в облаке `GOOGLE_SERVICE_ACCOUNT_FILE` (файла ключа там нет).
4. Добавьте строки из локального `.streamlit/secrets.toml`, которые вам нужны: `LINKBUILDER_FILTER`, `LINKBUILDER_ALIASES`, при необходимости `GMAIL_*`, `SPREADSHEET_*`, `GID_*` — по образцу [secrets.toml.example](secrets.toml.example) (скрипт выше уже добавляет `LINKBUILDER_*` по умолчанию).
5. **Почта для кнопки «Прочитать почту»** (иначе будет красная ошибка про IMAP): в тот же блок Secrets добавьте, подставив **свой** пароль приложения Google (16 символов, не пароль входа):

   ```toml
   GMAIL_SMTP_USER = "o.tsebulevsky@rantsports.com"
   GMAIL_SMTP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   GMAIL_SMTP_HOST = "smtp.gmail.com"
   GMAIL_SMTP_PORT = "587"
   GMAIL_IMAP_USER = "o.tsebulevsky@rantsports.com"
   GMAIL_IMAP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   IMAP_MAILBOX = "INBOX"
   ```

   Логин один и тот же; пароль приложения обычно **один** на SMTP и IMAP. Если задать только `GMAIL_SMTP_*`, панель всё равно использует их для чтения почты.
6. **Save** → **Reboot app** (или аналог в интерфейсе).

### Этап H. Проверка приложения

1. Откройте выданный URL вида `https://<имя>.streamlit.app`.
2. Должны открыться вкладки панели; данные из Google Sheets подтянутся, если таблицы расшарены на **`client_email`** из JSON и Secrets сохранены без ошибок.
3. **Проверка, что Cloud подтянул свежий код:** в серой подписи под заголовком «Панель линкбилдинга» в начале должна быть метка вида **`mail-ui-2026-03-30b`**. Первой в ряду синих кнопок идёт **«Сменить почту»**, затем «Прочитать почту». Если метки нет и кнопок по-прежнему четыре — закоммитьте/push в GitHub-репозиторий приложения и сделайте **Reboot app** в Streamlit.

### Опционально: локальный `git push` на GitHub с ПК (без CI)

Если хотите пушить с Windows без GitLab job:

1. **Параметры** → **Учётные данные** → **Диспетчер учётных данных** → удалите старые записи **`git:https://github.com`** для чужого аккаунта.
2. В PowerShell: `cd C:\project\start\internal\seo\linkbuilding` → `git push -u github feature/seolb-164-webmaster-prospecting-oleg`.
3. При запросе пароля используйте **PAT** (этап B), логин — **`otsebulevsky-alt`**.

---

## Вариант 1 — Streamlit Community Cloud (бесплатный хостинг Streamlit)

### Перед кнопкой «Создать приложение»

На GitHub должен быть репозиторий с кодом панели. Варианты:

- **Только папка приложения в корне репозитория** (удобнее для Cloud): содержимое `webmaster-pipeline-dashboard/` лежит в корне GitHub-репо → главный файл: `app.py`, **без** App root.
- **Весь репозиторий `linkbuilding` как на GitLab**: главный файл и корень ниже.

### Мастер на share.streamlit.io (после «Создать приложение»)

1. **Repository** — выберите GitHub-репозиторий, куда залит код.
2. **Branch** — ветка с панелью (например `main` или `feature/seolb-164-webmaster-prospecting-oleg`).
3. **Main file path**
   - репо = только содержимое панели в корне → **`app.py`**
   - репо = весь `linkbuilding` → **`webmaster-pipeline-dashboard/app.py`**
4. **App URL** (если спросят имя) — любое свободное, например `webmaster-pipeline` → URL будет `https://webmaster-pipeline.streamlit.app` (если не занято).
5. **Advanced settings** — если есть поле **Main module directory** / **Root directory** / **App root** и репо = весь `linkbuilding`, укажите: **`webmaster-pipeline-dashboard`**
6. Нажмите **Deploy** / **Развернуть** и дождитесь логов сборки.

### После первого деплоя (обязательно)

1. Откройте приложение → **⋮** / **Settings** (настройки приложения).
2. **Secrets** — вставьте TOML. В облаке **нет** файла `.streamlit/gcp-service-account.json`, поэтому:
   - удалите или не используйте `GOOGLE_SERVICE_ACCOUNT_FILE`;
   - добавьте **`GOOGLE_SERVICE_ACCOUNT_JSON`** — весь JSON сервисного аккаунта в тройных кавычках:

```toml
GOOGLE_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "dashboard@....iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
'''
```

3. Скопируйте остальные нужные строки из локального `.streamlit/secrets.toml` (без паролей в чат): `LINKBUILDER_FILTER`, `LINKBUILDER_ALIASES`, при необходимости `GMAIL_*`, `SPREADSHEET_*`, `GID_*` — по образцу [secrets.toml.example](secrets.toml.example).
4. **Save** → **Reboot app**.

Документация: [Deploy an app](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/deploy).

---

## Вариант 2 — Docker (GitLab CI, Render, Fly.io, свой сервер)

Сборка из **этой** папки (`webmaster-pipeline-dashboard`):

```bash
docker build -t webmaster-dashboard .
docker run -p 8501:8501 \
  -e GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}' \
  webmaster-dashboard
```

Секреты лучше передавать через переменные окружения платформы, не в образ.

Пример **Render.com** (Web Service): подключить GitLab/GitHub, **Dockerfile path**: `webmaster-pipeline-dashboard/Dockerfile`, **Root**: `webmaster-pipeline-dashboard` (если репо — весь linkbuilding).

---

## Вариант 3 — только ваш ПК без облака

Windows: см. [README.md](README.md) — `run-daemon.ps1` / автозапуск. Это **не** 24/7 при выключенном ПК.

---

## GitHub-зеркало для Streamlit (репозиторий на github.com)

Streamlit читает только GitHub. Имя репозитория: **`OWNER/linkbuilding`**, где **`OWNER`** — ваш GitHub-пользователь или организация, **под аккаунтом с рабочей почтой** (см. таблицу выше).

**Remote в локальном клоне** (подставьте свой `OWNER` при необходимости):

```powershell
git remote remove github 2>$null
git remote add github https://github.com/OWNER/linkbuilding.git
```

Пример, если репозиторий создан как `otsebulevsky-alt/linkbuilding`:

```text
git remote add github https://github.com/otsebulevsky-alt/linkbuilding.git
```

**Вручную (ассистент не может зайти в GitHub за вас):**

1. [github.com/new](https://github.com/new) — Owner = аккаунт с **`o.tsebulevsky@rantsports.com`**, имя репо **`linkbuilding`**, без README.
2. Убедиться, что **git push** идёт **не** с личного аккаунта (см. 403 выше).
3. PowerShell:

```powershell
cd C:\project\start\internal\seo\linkbuilding
git push -u github feature/seolb-164-webmaster-prospecting-oleg
```

4. [share.streamlit.io/deploy](https://share.streamlit.io/deploy) — **Repository:** `OWNER/linkbuilding`, **Branch:** `feature/seolb-164-webmaster-prospecting-oleg`, **Main file path:** `webmaster-pipeline-dashboard/app.py`, при необходимости **App root:** `webmaster-pipeline-dashboard`.

---

## Если Cloud: «Oh no» / «The service has encountered an error» сразу после «Processed dependencies»

Частая причина: в [`.streamlit/config.toml`](.streamlit/config.toml) заданы **`server.port`** (например 8503) и/или **`server.address = "127.0.0.1"`**. Тогда процесс слушает «не тот» порт или только localhost — **health check** Streamlit Community Cloud не проходит. В репозитории оставляйте только безопасные опции (`headless`, `gatherUsageStats`); локальный порт **8503** — через [run.ps1](run.ps1).

После исправления: **commit → push** на GitHub → в Cloud **Reboot** / **Redeploy**.

---

## Чеклист после деплоя

- [ ] Таблицы Google расшарены на `client_email` из JSON.
- [ ] В облаке задан `GOOGLE_SERVICE_ACCOUNT_JSON` (или эквивалент через env в Docker).
- [ ] Книга «Возможности оплаты» (`17MoDWn…`) открыта для SA, если нужна вкладка «Варианты оплаты».

**Последнее обновление:** 2026-03-31 (политика учётных записей Rantsports)
