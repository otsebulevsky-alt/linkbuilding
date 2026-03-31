# Постоянный онлайн (24/7)

Репозиторий кода: **GitLab** (`internal/seo/linkbuilding`). [Streamlit Community Cloud](https://streamlit.io/cloud) подключается **только к GitHub** — для него нужен зеркальный репозиторий на GitHub.

## Учётные записи Rantsports (канон)

| Что | Правило |
|-----|--------|
| **Код и git** | Только из рабочего workspace. В репозитории `linkbuilding` задано: `user.email` = **`o.tsebulevsky@rantsports.com`**, `user.name` = **Oleg Tsebulevsky**. |
| **GitHub** | Один аккаунт, с которым вы пушите и деплоите: в [GitHub → Emails](https://github.com/settings/emails) должна быть **подтверждена** почта **`o.tsebulevsky@rantsports.com`**. Не пушить в рабочий репозиторий с личного аккаунта с другим email — иначе **403** (как с `olegtseb9806`). |
| **Streamlit Cloud** | Вход через **тот же** GitHub-аккаунт, что и для push (кнопка «Sign in with GitHub»). |
| **Windows: сохранённые пароли** | «Параметры» → «Учётные данные» → удалить записи **`git:https://github.com`**, относящиеся к **чужим** логинам. Затем снова `git push` — авторизоваться аккаунтом с **rantsports**-почтой или [PAT](https://github.com/settings/tokens) для него. |
| **Секреты приложения** | `GOOGLE_SERVICE_ACCOUNT_JSON`, Gmail и т.д. — только из ваших локальных файлов / GCP, не пересылать в общий чат. |

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

## Чеклист после деплоя

- [ ] Таблицы Google расшарены на `client_email` из JSON.
- [ ] В облаке задан `GOOGLE_SERVICE_ACCOUNT_JSON` (или эквивалент через env в Docker).
- [ ] Книга «Возможности оплаты» (`17MoDWn…`) открыта для SA, если нужна вкладка «Варианты оплаты».

**Последнее обновление:** 2026-03-31 (политика учётных записей Rantsports)
