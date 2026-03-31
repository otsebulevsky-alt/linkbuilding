# Постоянный онлайн (24/7)

Репозиторий кода: **GitLab** (`internal/seo/linkbuilding`). [Streamlit Community Cloud](https://streamlit.io/cloud) подключается **только к GitHub** — для него нужен зеркальный репозиторий или форк на GitHub.

---

## Вариант 1 — Streamlit Community Cloud (бесплатный хостинг Streamlit)

1. Создайте **публичный или приватный** репозиторий на GitHub и залейте туда папку **`webmaster-pipeline-dashboard/`** (или весь `linkbuilding`, если удобнее один репо).
2. Войдите на [share.streamlit.io](https://share.streamlit.io) под GitHub.
3. **New app** → выберите репозиторий и ветку.
4. **Main file path** (если в GitHub только папка приложения в корне): `app.py`.  
   Если в репозитории лежит весь `linkbuilding`, укажите:  
   **`webmaster-pipeline-dashboard/app.py`**
5. Если в форме есть **App root / Root directory** / **Working directory**, задайте:  
   **`webmaster-pipeline-dashboard`**
6. **Deploy** → дождитесь URL вида `https://<имя>.streamlit.app`.
7. **Settings → Secrets** — вставьте TOML (как в локальном `secrets.toml.example`), обязательно:
   - **`GOOGLE_SERVICE_ACCOUNT_JSON`** — весь JSON сервисного аккаунта в тройных кавычках `'''...'''` (в облаке нет файла `.streamlit/gcp-service-account.json`).
   - При необходимости: `GMAIL_*`, переопределения `SPREADSHEET_*`, `GID_*`, `LINKBUILDER_*`.
8. **Reboot app** после сохранения Secrets.

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

## Чеклист после деплоя

- [ ] Таблицы Google расшарены на `client_email` из JSON.
- [ ] В облаке задан `GOOGLE_SERVICE_ACCOUNT_JSON` (или эквивалент через env в Docker).
- [ ] Книга «Возможности оплаты» (`17MoDWn…`) открыта для SA, если нужна вкладка «Варианты оплаты».

**Последнее обновление:** 2026-03-31
