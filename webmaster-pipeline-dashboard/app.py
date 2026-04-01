"""
Linkbuilding: webmaster pipeline dashboard (HACK-382, Streamlit + Google Sheets).

Run: streamlit run app.py
Secrets: see secrets.toml.example and README.md
"""

from __future__ import annotations

import sys
from pathlib import Path

# Monorepo / Streamlit Cloud: ensure imports from this directory (lib/).
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import html
import json
from datetime import datetime

import pandas as pd
import streamlit as st
from googleapiclient.errors import HttpError

from lib.config import load_config, load_service_account_info, use_google_adc
from lib.mail_imap import fetch_unread_summaries
from lib.mail_smtp import send_smtp_html
from lib.sheets_service import (
    a1_all_columns,
    build_sheets_service,
    build_sheets_service_adc,
    count_by_status,
    filter_by_linkbuilder,
    get_sheet_title_by_gid,
    get_values_as_dataframe,
    resolve_article_column,
    resolve_cost_column,
    resolve_donor_column,
    resolve_linkbuilder_column,
    resolve_status_column,
)

st.set_page_config(page_title="Linkbuilding — панель вебмастеров", layout="wide")


def _secrets():
    try:
        return st.secrets
    except Exception:
        return None


_secrets_obj = _secrets()
cfg = load_config(_secrets_obj)
sa_info = load_service_account_info(_secrets_obj)
_use_adc = use_google_adc(_secrets_obj)
try:
    _SA_JSON_KEY = json.dumps(sa_info, sort_keys=True) if sa_info else ""
except (TypeError, ValueError):
    _SA_JSON_KEY = ""


@st.cache_resource
def sheets_service_cached(sa_json_key: str, use_adc: bool):
    if use_adc:
        try:
            return build_sheets_service_adc()
        except Exception:
            return None
    if not sa_json_key:
        return None
    try:
        info = json.loads(sa_json_key)
    except json.JSONDecodeError:
        return None
    try:
        return build_sheets_service(info)
    except Exception:
        # Invalid key or google-auth build failure — avoid Streamlit Cloud "Oh no"
        return None


def load_registry_df(service, spreadsheet_id: str, gid: int) -> tuple[pd.DataFrame, str | None]:
    title = get_sheet_title_by_gid(service, spreadsheet_id, gid) if service else None
    if not title:
        return pd.DataFrame(), title
    rng = a1_all_columns(title)
    df = get_values_as_dataframe(service, spreadsheet_id, rng)
    return df, title


def registry_diagnostics(
    df: pd.DataFrame,
    mine: pd.DataFrame,
    lb_col: str | None,
    st_col: str | None,
    label: str,
) -> None:
    with st.expander(f"Диагностика: {label}", expanded=False):
        st.caption(f"Строк данных (без заголовка): **{len(df)}**")
        if df.empty:
            st.write("Лист пустой или первая строка не прочитана как заголовок.")
            return
        cols = [str(x) for x in df.columns[:50]]
        st.text(", ".join(cols))
        if not lb_col:
            st.warning("Колонка исполнителя не найдена. Ожидаютcя имя `Linkbuilder` или заголовок с «link» и «build».")
        else:
            uni = df[lb_col].dropna().astype(str).str.strip()
            uni = uni[uni != ""]
            if uni.empty:
                st.caption("Колонка исполнителя есть, но пустая.")
            else:
                st.caption("Кто в колонке исполнителя (топ-частоты):")
                st.dataframe(uni.value_counts().head(15).to_frame(name="rows"), use_container_width=True)
        if mine.empty and lb_col and len(df) > 0:
            st.info(
                "По фильтру нет строк. Проверьте имя в таблице или добавьте в `secrets.toml` "
                "**LINKBUILDER_ALIASES** (например `Oleg` или фамилия через запятую)."
            )
        if not st_col and len(df) > 0:
            st.warning("Колонка статуса не найдена — ожидается `Status` или заголовок со «status».")


def main():
    st.title("Панель линкбилдинга — вебмастеры")
    st.caption(
        f"Фильтр Linkbuilder: **{cfg.linkbuilder_filter}** · Статусы: «{cfg.status_prep_text}», «{cfg.status_wait_publish}»"
    )

    svc = sheets_service_cached("ADC" if _use_adc else _SA_JSON_KEY, _use_adc)

    if _use_adc and svc is None:
        st.error(
            "Включён **GOOGLE_USE_ADC**, но учётные данные не найдены. Локально выполните "
            "`gcloud auth application-default login` под корпоративным Google-аккаунтом и расшарьте таблицы "
            "на **ваш** email (не на сервисный аккаунт). Подробно: README.md."
        )
        st.stop()
    if not _use_adc and (not sa_info or svc is None):
        if sa_info and svc is None:
            st.error(
                "Не удалось создать клиент Google Sheets. Проверьте **GOOGLE_SERVICE_ACCOUNT_JSON** в Secrets: "
                "валидный JSON сервисного аккаунта (поле `private_key` целиком, без обрезки), scope **Sheets API** в GCP."
            )
        else:
            st.error(
                "Не задан сервисный аккаунт Google для облака. "
                "**Streamlit Cloud:** Manage app (или ⋮) → **Settings** → **Secrets** → вставьте TOML с ключом "
                "**`GOOGLE_SERVICE_ACCOUNT_JSON`** (весь JSON в тройных кавычках `'''...'''`), **Save** → **Reboot app**. "
                "Локально сгенерировать блок: `py scripts/print_streamlit_cloud_secrets_snippet.py` в папке приложения. "
                "Таблицы расшарьте на email из поля **`client_email`** в JSON. "
                "Если организация запрещает JSON-ключи — см. README.md, раздел «Ключ JSON создать нельзя»."
            )
        st.stop()

    def _quick_notify(msg: str) -> None:
        try:
            st.toast(msg, icon="✅")
        except Exception:
            st.info(msg)

    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) button[kind="primary"] {
            width: 100% !important;
            font-weight: 600 !important;
            padding-top: 0.55rem !important;
            padding-bottom: 0.55rem !important;
            background: linear-gradient(180deg, #3b8eed 0%, #1c7ed6 100%) !important;
            border: 1px solid #1864ab !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    qa1, qa2, qa3, qa4 = st.columns(4, gap="small")
    with qa1:
        if st.button("Прочитать почту", key="qa_mail", use_container_width=True, type="primary"):
            _quick_notify(
                "Вкладка «Входящие (IMAP)» → «Загрузить непрочитанные»."
            )
    with qa2:
        if st.button("торг", key="qa_trade", use_container_width=True, type="primary"):
            _quick_notify("Сценарий «торг» — заготовка; логику можно добавить позже.")
    with qa3:
        if st.button("отправить статьи", key="qa_send", use_container_width=True, type="primary"):
            _quick_notify("Вкладка «Жду публикации → отправка» — выбор строки и отправка письма.")
    with qa4:
        if st.button("проверка публикаций", key="qa_check", use_container_width=True, type="primary"):
            _quick_notify("Проверка публикаций — заготовка; позже: сверка статусов с реестром.")
    st.divider()

    tab_stats, tab_reg, tab_wait, tab_inbox, tab_calc, tab_pay = st.tabs(
        (
            "Статистика",
            "Реестры (мои строки)",
            "Жду публикации → отправка",
            "Входящие (IMAP)",
            "Калькулятор (просмотр)",
            "Варианты оплаты",
        )
    )

    with tab_stats:
        st.subheader("Сводка по реестрам")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**TelecomAsia (реестр 1)**")
            df1, t1 = load_registry_df(svc, cfg.spreadsheet_telecom_id, cfg.gid_telecom_registry)
            if t1:
                st.caption(f"Лист: `{t1}` · gid={cfg.gid_telecom_registry}")
            lb1 = resolve_linkbuilder_column(df1, cfg.col_linkbuilder, [])
            st1 = resolve_status_column(df1, cfg.col_status)
            mine1 = filter_by_linkbuilder(df1, lb1, cfg.linkbuilder_filter, cfg.linkbuilder_aliases)
            st.metric("Строк «мой» линкбилдер", len(mine1))
            if not mine1.empty and st1:
                for k, v in sorted(count_by_status(mine1, st1).items(), key=lambda x: -x[1]):
                    st.write(f"- **{k}**: {v}")
            else:
                registry_diagnostics(df1, mine1, lb1, st1, "TelecomAsia")
        with c2:
            st.markdown("**Реестр 2**")
            df2, t2 = load_registry_df(svc, cfg.spreadsheet_registry_2_id, cfg.gid_registry_2)
            if t2:
                st.caption(f"Лист: `{t2}` · gid={cfg.gid_registry_2}")
            lb2 = resolve_linkbuilder_column(df2, cfg.col_linkbuilder, [])
            st2 = resolve_status_column(df2, cfg.col_status)
            mine2 = filter_by_linkbuilder(df2, lb2, cfg.linkbuilder_filter, cfg.linkbuilder_aliases)
            st.metric("Строк «мой» линкбилдер", len(mine2))
            if not mine2.empty and st2:
                for k, v in sorted(count_by_status(mine2, st2).items(), key=lambda x: -x[1]):
                    st.write(f"- **{k}**: {v}")
            else:
                registry_diagnostics(df2, mine2, lb2, st2, "Реестр 2")

    with tab_reg:
        st.subheader("Только ваши строки (оба реестра)")
        which = st.radio("Таблица", ("TelecomAsia", "Реестр 2"), horizontal=True)
        if which == "TelecomAsia":
            df, _ = load_registry_df(svc, cfg.spreadsheet_telecom_id, cfg.gid_telecom_registry)
        else:
            df, _ = load_registry_df(svc, cfg.spreadsheet_registry_2_id, cfg.gid_registry_2)
        lb = resolve_linkbuilder_column(df, cfg.col_linkbuilder, [])
        mine = filter_by_linkbuilder(df, lb, cfg.linkbuilder_filter, cfg.linkbuilder_aliases)
        st.dataframe(mine, use_container_width=True, height=420)
        csv = mine.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Скачать CSV", csv, file_name=f"registry_mine_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

    with tab_wait:
        st.subheader("Строки со статусом «Жду публикации»")
        st.markdown(
            "Выберите реестр, укажите **email вебмастера** и при необходимости отредактируйте текст. "
            "Отправка — через SMTP (пароль приложения Gmail), если заданы секреты `GMAIL_SMTP_*`."
        )
        reg_choice = st.radio("Реестр", ("TelecomAsia", "Реестр 2"), horizontal=True, key="wait_reg")
        if reg_choice == "TelecomAsia":
            df, _ = load_registry_df(svc, cfg.spreadsheet_telecom_id, cfg.gid_telecom_registry)
        else:
            df, _ = load_registry_df(svc, cfg.spreadsheet_registry_2_id, cfg.gid_registry_2)
        lb = resolve_linkbuilder_column(df, cfg.col_linkbuilder, [])
        st_col = resolve_status_column(df, cfg.col_status)
        col_donor = resolve_donor_column(df, cfg.col_website_donor)
        col_art = resolve_article_column(df, cfg.col_article_post)
        col_cost = resolve_cost_column(df, cfg.col_cost)
        mine = filter_by_linkbuilder(df, lb, cfg.linkbuilder_filter, cfg.linkbuilder_aliases)
        if not st_col:
            st.warning("В таблице не найдена колонка статуса (Status).")
        else:
            wait_df = mine[mine[st_col].astype(str).str.strip() == cfg.status_wait_publish]
            st.metric("Строк в «Жду публикации»", len(wait_df))
            if wait_df.empty:
                st.info("Нет строк для обработки.")
            else:
                idx_list = list(wait_df.index)
                labels = []
                for i in idx_list:
                    row = wait_df.loc[i]
                    dom = ""
                    if col_donor and col_donor in wait_df.columns:
                        dom = str(row.get(col_donor, "") or "").strip()
                    labels.append(f"{dom} — row index {i}")
                choice = st.selectbox("Строка", range(len(idx_list)), format_func=lambda j: labels[j])
                row = wait_df.loc[idx_list[choice]]
                art = ""
                if col_art and col_art in row.index:
                    art = str(row.get(col_art, "") or "").strip()
                cost = ""
                if col_cost and col_cost in row.index:
                    cost = str(row.get(col_cost, "") or "").strip()
                to_email = st.text_input("Email вебмастера (кому отправить)", placeholder="webmaster@example.com")
                lang = st.radio("Язык письма", ("RU", "EN"), horizontal=True)
                if lang == "RU":
                    default_body = (
                        f"<p>Здравствуйте!</p>"
                        f"<p>Просьба разместить нашу статью: <a href=\"{html.escape(art)}\">{html.escape(art)}</a></p>"
                        f"<p>Сумма за размещение (гемблинг): <b>{html.escape(cost)}</b> USD (уточните по калькулятору при необходимости).</p>"
                        f"<p>С уважением</p>"
                    )
                else:
                    default_body = (
                        f"<p>Hello,</p>"
                        f"<p>Please publish our article: <a href=\"{html.escape(art)}\">{html.escape(art)}</a></p>"
                        f"<p>Placement fee (gambling): <b>{html.escape(cost)}</b> USD (see internal calculator if needed).</p>"
                        f"<p>Best regards</p>"
                    )
                body_html = st.text_area("Тело письма (HTML)", value=default_body, height=220)
                subj = st.text_input("Тема", value="Article for publication / Статья для публикации")

                secrets = _secrets() or {}
                smtp_user = str(secrets.get("GMAIL_SMTP_USER", "") or "").strip()
                smtp_pass = str(secrets.get("GMAIL_SMTP_APP_PASSWORD", "") or "").strip()
                smtp_host = str(secrets.get("GMAIL_SMTP_HOST", "smtp.gmail.com") or "").strip()
                smtp_port = int(secrets.get("GMAIL_SMTP_PORT", 587))

                if st.button("Отправить письмо", type="primary"):
                    if not to_email.strip():
                        st.error("Укажите email.")
                    elif not smtp_user or not smtp_pass:
                        st.error("Задайте GMAIL_SMTP_USER и GMAIL_SMTP_APP_PASSWORD в Secrets (см. README).")
                    else:
                        try:
                            send_smtp_html(
                                host=smtp_host,
                                port=smtp_port,
                                user=smtp_user,
                                password=smtp_pass,
                                to_addr=to_email.strip(),
                                subject=subj,
                                html_body=body_html,
                                use_tls=True,
                            )
                            st.success("Отправлено.")
                        except Exception as e:
                            st.error(f"Ошибка SMTP: {e}")

    with tab_inbox:
        st.subheader("Непрочитанные (IMAP)")
        st.markdown(
            "Для сбора «доноров по ответам» позже можно дописать запись в служебную таблицу. "
            "Сейчас — просмотр последних непрочитанных писем в ящике."
        )
        secrets = _secrets() or {}
        gu = str(secrets.get("GMAIL_IMAP_USER", "") or secrets.get("GMAIL_SMTP_USER", "") or "").strip()
        gp = str(secrets.get("GMAIL_IMAP_APP_PASSWORD", "") or secrets.get("GMAIL_SMTP_APP_PASSWORD", "") or "").strip()
        if st.button("Загрузить непрочитанные"):
            if not gu or not gp:
                st.error("Задайте GMAIL_IMAP_USER / GMAIL_IMAP_APP_PASSWORD (или общие GMAIL_SMTP_*).")
            else:
                try:
                    rows = fetch_unread_summaries(
                        host="imap.gmail.com",
                        user=gu,
                        password=gp,
                        mailbox=cfg.imap_mailbox,
                        limit=30,
                    )
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=400)
                except Exception as e:
                    st.error(f"IMAP: {e}")

    with tab_calc:
        st.subheader("Калькулятор — снимок листов")
        t_calc1 = get_sheet_title_by_gid(svc, cfg.spreadsheet_calculator_id, cfg.gid_calculator_tab_primary)
        if t_calc1:
            df_c1 = get_values_as_dataframe(svc, cfg.spreadsheet_calculator_id, a1_all_columns(t_calc1))
            st.markdown(f"**Вкладка 1:** `{t_calc1}`")
            st.dataframe(df_c1.head(40), use_container_width=True, height=360)
        if cfg.gid_calculator_tab_secondary > 0:
            t_calc2 = get_sheet_title_by_gid(svc, cfg.spreadsheet_calculator_id, cfg.gid_calculator_tab_secondary)
            if t_calc2:
                df_c2 = get_values_as_dataframe(svc, cfg.spreadsheet_calculator_id, a1_all_columns(t_calc2))
                st.markdown(f"**Вкладка 2:** `{t_calc2}`")
                st.dataframe(df_c2.head(40), use_container_width=True, height=360)

    with tab_pay:
        st.subheader("Справочник «Возможности оплаты»")
        pid = cfg.spreadsheet_payment_options_id
        gid_po = cfg.gid_payment_options
        link = f"https://docs.google.com/spreadsheets/d/{pid}/edit"
        if gid_po:
            link = f"{link}?gid={gid_po}#gid={gid_po}"
        st.markdown(f"Источник: [открыть в Google Sheets]({link}) · `gid={gid_po}` (первая вкладка = 0)")
        st.caption(
            "Сводка методов (USDT, карты, Capitalist и др.). При пустом экране проверьте доступ сервисного аккаунта к книге — см. SETUP.md."
        )
        try:
            svc.spreadsheets().get(spreadsheetId=pid, fields="properties.title").execute()
        except HttpError as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status == 403:
                st.error(
                    "Нет доступа к этой книге у сервисного аккаунта (403). "
                    "В таблице: **Доступ** → добавьте email из поля `client_email` в JSON-ключе."
                )
            else:
                st.error(f"Google Sheets: {e}")
        else:
            df_pay, t_pay = load_registry_df(svc, pid, gid_po)
            if t_pay:
                st.caption(f"Лист: `{t_pay}`")
            if df_pay.empty:
                st.warning("Лист пуст или не удалось сопоставить вкладку по gid — проверьте `GID_PAYMENT_OPTIONS` в secrets.")
            else:
                st.dataframe(df_pay, use_container_width=True, height=560)


main()
