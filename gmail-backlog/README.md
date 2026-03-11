# Gmail backlog (выгрузки писем)

Выгрузки писем из Gmail для линкбилдинга: каждая выгрузка — в отдельной папке **`gmail-backlog-<username>`** (например, `gmail-backlog-elenatyschuk`).

## Как добавить свою выгрузку

1. **Скрипт выгрузки** лежит в shared-docs:  
   `shared-docs/wiki/about-company/about-departments/about-seo/docs/linkbuilding/gmail-backlog/`  
   Там же инструкция по настройке Gmail API и файл `export_gmail.py`.

2. **Запустите выгрузку**, указав эту папку репозитория как каталог для экспорта (подставьте свой логин):
   ```bash
   cd <workspace>/shared-docs/wiki/about-company/about-departments/about-seo/docs/linkbuilding/gmail-backlog
   pip install -r requirements.txt
   python export_gmail.py "<workspace>/internal/seo/linkbuilding/gmail-backlog/gmail-backlog-ВАШ_ЛОГИН"
   ```

3. **Закоммитьте** в репозитории `internal/seo/linkbuilding`:
   ```bash
   cd internal/seo/linkbuilding
   git add gmail-backlog/gmail-backlog-ВАШ_ЛОГИН
   git commit -m "Added Gmail backlog export for ВАШ_ЛОГИН: ..."
   git push
   ```

Доступ к почте настраивается только у вас локально (OAuth в браузере); пароли и токены никому не передавайте.
