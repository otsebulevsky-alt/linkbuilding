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

**Что делает job (CI перед пушем на GitHub):** в образе **Python 3.12** ставятся зависимости из корневого [`requirements.txt`](../requirements.txt), затем в каталоге `webmaster-pipeline-dashboard/` выполняется **`python -m unittest discover -s tests -p "test_*.py"`**. Если тесты падают — зеркалирование **не** выполняется. После успешных тестов — `git push` в GitHub-репозиторий (ветка совпадает с текущей веткой в GitLab).

1. Убедитесь, что последний коммит с `.gitlab-ci.yml` есть в вашей ветке (у вас уже пушили в `feature/seolb-164-webmaster-prospecting-oleg`).
2. Сделайте любой **новый коммит** в эту ветку **или** в GitLab: **CI/CD → Pipelines → Run pipeline** → выберите ветку **`feature/seolb-164-webmaster-prospecting-oleg`** → **Run pipeline**.
3. Откройте запущенный pipeline → дождитесь стадии **deploy** → job **`mirror_github_streamlit`**.
4. Если job **зелёная** — ветка отправлена на GitHub. Если **красная** — откройте лог job: частые причины — неверный токен, нет прав `repo`, репозиторий GitHub не существует или переименован; либо **упали юнит-тесты** дашборда (исправьте код или тесты и перезапустите пайплайн).

**Если пайплайн долго `Pending` с меткой `stuck`:** свободный runner с Docker для проекта не назначен (типично для self-managed GitLab). На feature-ветках после коммита `f9edb65` в CI остаётся одна job `mirror_github_streamlit`; если она всё равно stuck — обходите CI: локальный **`git push github <ветка>`** (см. «Опционально: локальный git push» ниже). Старый stuck-пайплайн (например на коммите `f866137`) можно **Cancel** — он от старой конфигурации; обновите страницу списка пайплайнов и смотрите **верхний** запуск по **актуальному** SHA.

### Этап E. Проверка GitHub

1. Откройте [github.com/otsebulevsky-alt/linkbuilding](https://github.com/otsebulevsky-alt/linkbuilding).
2. Должна отображаться ветка **`feature/seolb-164-webmaster-prospecting-oleg`**, папка **`webmaster-pipeline-dashboard`** (`app.py`, `lib/` …) и в **корне** репо — **[`requirements.txt`](../requirements.txt)** (единственный манифест зависимостей).

### Этап F. Streamlit Community Cloud — деплой

1. Войдите на [share.streamlit.io](https://share.streamlit.io) **тем же GitHub-аккаунтом**, что владеет репозиторием (через **Sign in with GitHub**).
2. **Мои приложения** → **Создать приложение** / **Deploy a public app from GitHub** → **Deploy now**.
3. Заполните форму [share.streamlit.io/deploy](https://share.streamlit.io/deploy):
   - **Repository:** `otsebulevsky-alt/linkbuilding`
   - **Branch:** `feature/seolb-164-webmaster-prospecting-oleg`
   - **Main file path (рекомендуется):** `webmaster-pipeline-dashboard/app.py`, **App root** пустой — один процесс Streamlit, без шима `importlib`. **Альтернатива:** корневой [`app.py`](../app.py) (шим с `chdir` + загрузка дашборда). Зависимости только из **корневого** [`requirements.txt`](../requirements.txt) (**без** второго `requirements.txt` во вложенной папке и без `-r`, иначе в логах **«More than one requirement file»** и возможны **segfault** после установки пакетов).
   - **App URL (optional):** любое свободное имя (например `linkbuilding-webmaster`).
   - **Python version** (в **Advanced settings** при первом деплое или **Manage app → Settings → General**): выберите **3.12** (семейство 3.12.x). Это соответствует [дефолту Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). **Не используйте Python 3.14** (и другие экспериментальные): с бинарными колёсами (`pandas`, `google-*`) процесс может падать с **`corrupted unsorted chunks`** и общим **«Oh no»** даже после успешной установки зависимостей.
   - **App root:** если **Main file path** = `webmaster-pipeline-dashboard/app.py` — поле **App root** оставьте **пустым**. Если **Main file path** = корневой `app.py` (шим) — **App root** тоже **пустой**. Не комбинируйте «корневой app.py + App root = webmaster-pipeline-dashboard» без необходимости (легко сломать путь к файлу).
4. **Deploy**. Дождитесь окончания сборки (логи на экране). При ошибке импорта проверьте, что путь к `app.py` и App root согласованы (см. ниже «Oh no»).

### Этап F1. Обязательная проверка логов после деплоя

В правой колонке логов сборки найдите строку про установку зависимостей:

- **Нужно:** путь вида **`.../linkbuilding/requirements.txt`** (только корень репозитория).
- **Плохо:** **`webmaster-pipeline-dashboard/requirements.txt`** или предупреждение **«More than one requirements file»** — значит Cloud клонировал **старый коммит** или кеш; сделайте **Reboot app**. Если не помогло — **удалите приложение** в Streamlit и создайте заново с теми же Repository / Branch / Secrets (см. [удаление приложения](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/delete-your-app)), затем снова **Deploy**.

После успешного обновления кода в подписи под заголовком панели должна появиться метка из константы **`PANEL_UI_BUILD`** в `webmaster-pipeline-dashboard/app.py` (например **`panel-2026-03-30-logic-sync`**).

### Этап G. Streamlit — Secrets (Google и опции)

1. В карточке приложения: **⋮** (три точки) → **Settings** → **Secrets**.
2. **Быстро собрать блок на ПК** (не отправляйте вывод в чат): из папки `webmaster-pipeline-dashboard` выполните  
   `py scripts/print_streamlit_cloud_secrets_snippet.py` — скопируйте вывод целиком в поле Secrets.
3. Вставьте TOML. Обязательно для Sheets API в облаке:
   - **`GOOGLE_SERVICE_ACCOUNT_JSON`** = весь JSON сервисного аккаунта из вашего локального файла ключа (как в [secrets.toml.example](secrets.toml.example)), в тройных кавычках `''' ... '''`.
   - **Не** используйте в облаке `GOOGLE_SERVICE_ACCOUNT_FILE` (файла ключа там нет).
4. Добавьте строки из локального `.streamlit/secrets.toml`, которые вам нужны: `LINKBUILDER_FILTER`, `LINKBUILDER_ALIASES`, при необходимости `GMAIL_*`, `SPREADSHEET_*`, `GID_*` — по образцу [secrets.toml.example](secrets.toml.example) (скрипт выше уже добавляет `LINKBUILDER_*` по умолчанию).
5. **Почта для кнопки «Прочитать почту»** — либо в **Secrets** (ниже), либо **только на сессию** в приложении: **«Сменить почту»** → логин + пароль приложения → **Применить** (пароль не уходит в Secrets, живёт до закрытия вкладки / Reboot). Для постоянной работы без повторного ввода добавьте в Secrets:

   В тот же блок Secrets, подставив **свой** пароль приложения Google (16 символов, не пароль входа):

   ```toml
   GMAIL_SMTP_USER = "o.tsebulevsky@rantsports.com"
   GMAIL_SMTP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   GMAIL_SMTP_HOST = "smtp.gmail.com"
   GMAIL_SMTP_PORT = "587"
   GMAIL_IMAP_USER = "o.tsebulevsky@rantsports.com"
   GMAIL_IMAP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   IMAP_MAILBOX = "INBOX"
   ```

   Логин один и тот же; пароль приложения обычно **один** на SMTP и IMAP. Если задать только `GMAIL_SMTP_*`, панель использует их для чтения почты; если только **`GMAIL_IMAP_*`** — те же значения подставляются и для **отправки** автоответов (SMTP).
   **Автоответ вебмастеру** по логике колонки F (уточнение оплаты) при нажатии «Прочитать почту» — **включён по умолчанию**, если заданы `GMAIL_SMTP_*` и заполнена книга «Возможности оплаты». Чтобы **не** слать письма, только писать в таблицу: `IMAP_AUTO_REPLY_PAYMENT_FOLLOWUP = "false"`.
6. **Save** → **Reboot app** (или аналог в интерфейсе).

### Этап H. Проверка приложения

1. Откройте выданный URL вида `https://<имя>.streamlit.app`.
2. Должны открыться вкладки панели; данные из Google Sheets подтянутся, если таблицы расшарены на **`client_email`** из JSON и Secrets сохранены без ошибок.
3. **Проверка, что Cloud подтянул свежий код:** в серой подписи под заголовком «Панель линкбилдинга» в начале должна быть метка **`PANEL_UI_BUILD`** из `app.py` (например **`panel-2026-03-30-logic-sync`**). **«Сменить почту»** — **справа от заголовка**; в форме — **логин** и при необходимости **пароль приложения** (можно только на сессию, без Secrets). Ниже — четыре синие кнопки. Если метки нет — push на GitHub и **Reboot app**.
4. **Кнопка «проверка публикаций»:** в реестрах должны быть колонки **Anchor** / **Outgoing link** (или имена из **`COL_ANCHOR`**, **`COL_OUTGOING_LINK`** в Secrets). Иначе в отчёте будет предупреждение, а сверка I+J не выполнится. Опционально: **`GOOGLE_CSE_*`** для проверки индекса, **`EEAT_AUTHOR_MARKERS`** — см. [README.md](README.md).

### Опционально: локальный `git push` на GitHub с ПК (без CI)

Если хотите пушить с Windows без GitLab job:

1. **Параметры** → **Учётные данные** → **Диспетчер учётных данных** → удалите старые записи **`git:https://github.com`** для чужого аккаунта.
2. В PowerShell: `cd C:\project\start\internal\seo\linkbuilding` → `git push -u github feature/seolb-164-webmaster-prospecting-oleg`.
3. При запросе пароля используйте **PAT** (этап B), логин — **`otsebulevsky-alt`**.

---

## Зеркало GitLab → GitHub (Streamlit): только готовые ссылки

Streamlit читает **GitHub**, вы пушите в **GitLab**. После `git push origin …` нужно, чтобы job **`mirror_github_streamlit`** отправил ту же ветку на GitHub.

| Шаг | Куда перейти |
|-----|----------------|
| Проект **linkbuilding** в GitLab | [https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding](https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding) |
| **CI/CD → Variables** (проверить / добавить `GITHUB_TOKEN`) | [https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/settings/ci_cd](https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/settings/ci_cd) (блок **Variables** внизу страницы) |
| **CI/CD → Pipelines** (найти пайплайн по ветке после push) | [https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/pipelines](https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/pipelines) |
| Запуск пайплайна вручную | [https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/pipelines/new](https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/pipelines/new) → ветка **`feature/seolb-164-webmaster-prospecting-oleg`** → **Run pipeline** |
| Репозиторий на **GitHub** (куда зеркалит CI) | [https://github.com/otsebulevsky-alt/linkbuilding](https://github.com/otsebulevsky-alt/linkbuilding) |
| Ветка на GitHub (проверить свежий коммит) | [https://github.com/otsebulevsky-alt/linkbuilding/tree/feature/seolb-164-webmaster-prospecting-oleg](https://github.com/otsebulevsky-alt/linkbuilding/tree/feature/seolb-164-webmaster-prospecting-oleg) |
| Создать **Personal Access Token** (classic, scope **repo**) для `GITHUB_TOKEN` | [https://github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)** |
| Панель **Streamlit Community Cloud** | [https://share.streamlit.io/](https://share.streamlit.io/) → своё приложение → **⋮** → **Reboot app** |
| Создать **Merge Request** из ветки feature (после push) | [https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/merge_requests/new?merge_request%5Bsource_branch%5D=feature%2Fseolb-164-webmaster-prospecting-oleg](https://rantsports.gitlab.yandexcloud.net/ai-first-workspace/internal/seo/linkbuilding/-/merge_requests/new?merge_request%5Bsource_branch%5D=feature%2Fseolb-164-webmaster-prospecting-oleg) |

**Краткий порядок:** push в GitLab → открыть **Pipelines** → убедиться, что job **`mirror_github_streamlit`** **зелёный** → открыть ветку на **GitHub** и проверить коммит → **Reboot** в Streamlit.

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

4. [share.streamlit.io/deploy](https://share.streamlit.io/deploy) — **Repository:** `OWNER/linkbuilding`, **Branch:** `feature/seolb-164-webmaster-prospecting-oleg`, **Main file path:** корневой `app.py` или `webmaster-pipeline-dashboard/app.py` (см. этап F); **App root** не должен конфликтовать с путём к файлу.

---

## Если Cloud: «Oh no» / «The service has encountered an error» сразу после «Processed dependencies»

1. **Версия Python в приложении:** **Manage app → Settings → General → Python version**. Должно быть **3.12** (или стабильная 3.11), **не 3.14**. При 3.14 в логах нередко встречается **`corrupted unsorted chunks`** — смените на **3.12**, **Save**, затем **Reboot app**. По документации Streamlit смена мажорной версии Python иногда требует пересоздать приложение; если после смены и перезапуска ошибка остаётся — удалите приложение и задеплойте снова с **Advanced settings → Python 3.12** (сохраните Secrets и URL в заметку заранее).

2. **Segmentation fault / health check `EOF` сразу после «Processed dependencies»:** (а) В **корне** зеркала GitHub `linkbuilding` (рядом с `requirements.txt`) должен быть **[`runtime.txt`](../runtime.txt)** со строкой **`python-3.12.8`**. Установщик **uv** на Community Cloud часто **не** подхватывает `runtime.txt` только из `webmaster-pipeline-dashboard/` — тогда может подняться **Python 3.13+**, и **`streamlit`** падает с **segfault**. **Commit → push** на GitHub, **Reboot app**. (б) Один корневой **`requirements.txt`**, без второго файла и без **`-r ...`**. Пины **`pyarrow==14.0.2`**, **`protobuf==4.25.3`**, **`pandas==2.1.4`**, **`streamlit==1.36.0`**. (в) В **Settings → General** вручную **Python 3.12** (не 3.14), **Save**, **Reboot**; при необходимости **Python 3.11** и **Main file path** = **`webmaster-pipeline-dashboard/app.py`**, **App root** пустой.

3. **Порт / bind:** в [`.streamlit/config.toml`](.streamlit/config.toml) не должно быть **`server.port`** (например 8503) и **`server.address = "127.0.0.1"`** — иначе health check Cloud не проходит. Локальный порт **8503** — через [run.ps1](run.ps1).

4. **Точка входа и корень:** если в настройках приложения **Main file path** = `app.py`, а **App root** = `webmaster-pipeline-dashboard`, Cloud ищет файл по пути `webmaster-pipeline-dashboard/app.py` внутри подпапки — получается неверный путь. Либо **App root** пустой и **Main file path** = корневой [`app.py`](../app.py) (шим), либо **Main file path** = `webmaster-pipeline-dashboard/app.py` и **App root** пустой или совпадает с документацией Cloud для монорепо.

5. **Зависимости:** в корне репозитория — **единственный** [`requirements.txt`](../requirements.txt) со всеми пакетами дашборда (без `-r` на второй файл).

6. **Текст ошибки:** в [`webmaster-pipeline-dashboard/.streamlit/config.toml`](.streamlit/config.toml) включено **`[client] showErrorDetails = true`** — на странице приложения может появиться traceback (не только «Oh no»).

7. **Секреты ещё не заданы:** приложение должно открываться и без блока Secrets (почта через «Сменить почту»). Если в логах **`StreamlitSecretNotFoundError`** при чтении Gmail — в коде не должно быть **`st.secrets or {}`** и прямого **`.get()`** на `st.secrets`; чтение ключей — как в `lib.config._secrets_get` (исправлено в коммите `589c898`).

После исправления: **commit → push** на GitHub → в Cloud **Reboot** / **Redeploy**. Если в логах всё ещё фигурирует **`webmaster-pipeline-dashboard/requirements.txt`** — пересоздайте приложение (этап F1).

---

## Только обновили код (без смены Secrets)

Достаточно: **push** в ветку, с которой связано приложение Streamlit (или дождаться зеркала GitLab → GitHub) → в [share.streamlit.io](https://share.streamlit.io) у приложения **Reboot app** (или дождаться автодеплоя). **Secrets трогать не нужно**, если вы не меняли ключи и пароли. Убедитесь, что под заголовком панели появилась актуальная метка **`PANEL_UI_BUILD`** (см. этап H).

---

## Чеклист после деплоя

- [ ] **Python version** в **Settings → General** = **3.12** (не 3.14).
- [ ] В **корне** репо есть **`runtime.txt`** (`python-3.12.8`) рядом с **`requirements.txt`**.
- [ ] В логах зависимости ставятся из **`.../requirements.txt` в корне** репо, без **`webmaster-pipeline-dashboard/requirements.txt`** и без **«More than one requirement file»**; **Main file path** = `webmaster-pipeline-dashboard/app.py`.
- [ ] Таблицы Google расшарены на `client_email` из JSON.
- [ ] В облаке задан `GOOGLE_SERVICE_ACCOUNT_JSON` (или эквивалент через env в Docker).
- [ ] Книга «Возможности оплаты» (`17MoDWn…`) открыта для SA, если нужна вкладка «Варианты оплаты».

**Последнее обновление:** 2026-03-30 (проверка публикаций: I+J + EEAT; метка `PANEL_UI_BUILD` в `app.py`)
