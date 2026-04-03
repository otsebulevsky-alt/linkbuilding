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

from lib.config import _secrets_get, _secrets_get_int, load_config, load_service_account_info, use_google_adc
from lib.mail_imap import fetch_unread_summaries
from lib.mail_smtp import send_smtp_html
from lib.article_publish_batch import run_article_publish_batch
from lib.publication_check_batch import run_publication_check_batch
from lib.trade_bargain import run_trade_bargain_round
from lib.inbox_sheet_dedupe import dedupe_and_highlight_inbox_sheet
from lib.webmaster_inbox_sync import sync_unseen_webmasters_to_inbox_sheet
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

# Меняйте при каждом релизе UI — в подписи под заголовком видно, что Cloud подтянул новый код.
PANEL_UI_BUILD = "panel-2026-04-03-no-inbox-noise-ui"

st.set_page_config(
    page_title="Linkbuilding — панель вебмастеров",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _secrets():
    try:
        return st.secrets
    except Exception:
        return None


def _gmail_imap_credentials(secrets_obj):
    """Gmail IMAP: dedicated keys or same as SMTP (app password).

    Не использовать `secrets_obj or {}` и прямой `.get()` на st.secrets: при отсутствии Secrets
    Streamlit бросает StreamlitSecretNotFoundError. Чтение — через lib.config._secrets_get.
    """
    user = (_secrets_get(secrets_obj, "GMAIL_IMAP_USER") or _secrets_get(secrets_obj, "GMAIL_SMTP_USER")).strip()
    password = (
        _secrets_get(secrets_obj, "GMAIL_IMAP_APP_PASSWORD") or _secrets_get(secrets_obj, "GMAIL_SMTP_APP_PASSWORD")
    ).strip()
    return user, password


def _gmail_smtp_settings(secrets_obj):
    """SMTP для автоответа про оплату и вкладки «Жду публикации».

    Симметрично IMAP: если заданы только **GMAIL_IMAP_***, используем их для SMTP
    (один пароль приложения на чтение и отправку).
    """
    user = _secrets_get(secrets_obj, "GMAIL_SMTP_USER").strip()
    password = _secrets_get(secrets_obj, "GMAIL_SMTP_APP_PASSWORD").strip()
    if not user:
        user = _secrets_get(secrets_obj, "GMAIL_IMAP_USER").strip()
    if not password:
        password = _secrets_get(secrets_obj, "GMAIL_IMAP_APP_PASSWORD").strip()
    host = (_secrets_get(secrets_obj, "GMAIL_SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com").strip()
    port = _secrets_get_int(secrets_obj, "GMAIL_SMTP_PORT", 587)
    return host, port, user, password


def _normalize_session_email_override() -> str:
    """Подмена логина почты на время сессии (пароль остаётся из Secrets)."""
    try:
        v = st.session_state.get("mail_email_override", "")
    except Exception:
        return ""
    if v is None:
        return ""
    s = str(v).strip()
    return s


def _session_stored_mail_password() -> str:
    """Пароль приложения, введённый в этой вкладке (не пишется в Secrets)."""
    try:
        v = st.session_state.get("mail_session_app_password", "")
    except Exception:
        return ""
    if v is None:
        return ""
    return str(v).strip()


def _effective_gmail_imap_credentials(secrets_obj):
    u, p = _gmail_imap_credentials(secrets_obj)
    ov = _normalize_session_email_override()
    if ov:
        u = ov
    pw_sess = _session_stored_mail_password()
    if pw_sess:
        p = pw_sess
    return u, p


def _effective_gmail_smtp_settings(secrets_obj):
    host, port, user, password = _gmail_smtp_settings(secrets_obj)
    ov = _normalize_session_email_override()
    eff_user = ov if ov else user
    pw_sess = _session_stored_mail_password()
    eff_pw = pw_sess if pw_sess else password
    return host, port, eff_user, eff_pw


def _mail_ready_effective(secrets_obj) -> tuple[str, bool]:
    """(эффективный email, достаточно ли логина + пароля: Secrets и/или сессия)."""
    u, p = _effective_gmail_imap_credentials(secrets_obj)
    return (u, bool(u and p))


def _looks_like_email(s: str) -> bool:
    s = (s or "").strip()
    if "@" not in s or s.startswith("@") or s.endswith("@"):
        return False
    local, _, domain = s.partition("@")
    if not local or not domain or "." not in domain:
        return False
    return True


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


def _render_mail_change_panel(secrets_mail_user: str, secrets_have_mail_password: bool) -> None:
    """Адрес + опционально пароль приложения в сессии; IMAP/SMTP без обязательного Secrets для пароля."""
    st.markdown("---")
    st.subheader("Почта для этой сессии")
    ov = _normalize_session_email_override()
    sess_pw = _session_stored_mail_password()
    if ov:
        src = "Secrets + сессия" if secrets_have_mail_password and sess_pw else ("сессия" if sess_pw else "Secrets")
        st.success(f"Логин: **{html.escape(ov)}** · пароль: **{src}**.")
    elif secrets_mail_user:
        st.caption(f"Логин из Secrets: `{html.escape(secrets_mail_user)}`")
    if not secrets_have_mail_password:
        st.info(
            "В **Secrets** нет пароля приложения — введите **пароль приложения Google** ниже. "
            "Он хранится **только в этой вкладке браузера** (до закрытия / Reboot). Для постоянного варианта добавьте "
            "**GMAIL_SMTP_APP_PASSWORD** в [Settings → Secrets](https://share.streamlit.io)."
        )
    else:
        st.caption(
            "Пароль уже есть в **Secrets**. Ниже можно временно подставить другой (на сессию) или оставить пустым."
        )

    cur = ov or (secrets_mail_user or "")
    with st.form("mail_session_override_form"):
        new_mail = st.text_input(
            "Адрес почты (логин Gmail)",
            value=cur,
            placeholder="name@company.com",
        )
        app_pw = st.text_input(
            "Пароль приложения Google (16 символов)",
            type="password",
            placeholder="" if secrets_have_mail_password else "обязательно, если нет в Secrets",
            help="Не пароль от аккаунта Google. Создать: Google → Безопасность → пароли приложений.",
        )
        c1, c2, c3 = st.columns(3)
        apply_b = c1.form_submit_button("Применить", type="primary")
        reset_b = c2.form_submit_button("Сбросить сессию")
        close_b = c3.form_submit_button("Закрыть")

    if apply_b:
        candidate = (new_mail or "").strip()
        pw_field = (app_pw or "").strip()
        if not _looks_like_email(candidate):
            st.error("Введите корректный email (например name@company.com).")
        elif not secrets_have_mail_password and not pw_field and not sess_pw:
            st.error("Нужен пароль приложения: введите в поле выше или задайте **GMAIL_SMTP_APP_PASSWORD** в Secrets.")
        else:
            st.session_state.mail_email_override = candidate
            if pw_field:
                st.session_state.mail_session_app_password = pw_field
            st.session_state.mail_settings_panel = False
            st.rerun()
    elif reset_b:
        st.session_state.mail_email_override = ""
        st.session_state.mail_session_app_password = ""
        st.session_state.mail_settings_panel = False
        st.rerun()
    elif close_b:
        st.session_state.mail_settings_panel = False
        st.rerun()

    with st.expander("Полная инструкция по Secrets и паролю приложения", expanded=False):
        st.markdown(
            "На **Streamlit Cloud** секреты: **Manage app (⋮) → Settings → Secrets**. После правок — **Save** и **Reboot app**. "
            "Локально: `.streamlit/secrets.toml`, образец — `secrets.toml.example`."
        )


def main():
    if "mail_settings_panel" not in st.session_state:
        st.session_state.mail_settings_panel = False
    if "mail_email_override" not in st.session_state:
        st.session_state.mail_email_override = ""

    secrets_mail_u, secrets_mail_p = _gmail_imap_credentials(_secrets_obj)
    secrets_have_mail_password = bool(secrets_mail_p)
    mail_addr, mail_ok = _mail_ready_effective(_secrets_obj)
    session_ov = _normalize_session_email_override()
    sess_pw_active = bool(_session_stored_mail_password())

    # Сайдбар — только статус; «Сменить почту» — справа от заголовка страницы.
    with st.sidebar:
        st.markdown("##### Почта (IMAP / SMTP)")
        if mail_ok:
            st.success(html.escape(mail_addr))
            if session_ov:
                st.caption("Логин задан в сессии.")
            if sess_pw_active and not secrets_have_mail_password:
                st.caption("Пароль приложения только в этой вкладке; для постоянного — Secrets.")
        elif session_ov:
            st.warning(
                f"Логин `{html.escape(session_ov)}` — укажите пароль приложения в форме «Сменить почту» или в Secrets."
            )
        else:
            st.warning("Нет логина/пароля — откройте «Сменить почту» справа от заголовка.")
        st.caption("Смена логина/пароля на сессию — кнопка справа от «Панель линкбилдинга».")

    # Заголовок + «Сменить почту» в одной строке (markdown # — чтобы темы Streamlit не съедали колонку).
    row_title, row_mail = st.columns([22, 3.4], gap="small")
    with row_title:
        st.markdown("# Панель линкбилдинга — вебмастеры")
    with row_mail:
        if st.button("Сменить почту", key="hdr_change_mail", type="primary", use_container_width=True):
            st.session_state.mail_settings_panel = not st.session_state.mail_settings_panel

    if mail_ok and sess_pw_active and not secrets_have_mail_password:
        mail_line = f"**Почта:** `{html.escape(mail_addr)}` · пароль **в сессии** (вкладка браузера)"
    elif session_ov and mail_ok:
        mail_line = f"**Почта (сессия):** `{html.escape(mail_addr)}` · пароль из Secrets или сессии"
    elif session_ov:
        mail_line = (
            f"**Логин (сессия):** `{html.escape(session_ov)}` — нужен пароль приложения (форма «Сменить почту» или Secrets)"
        )
    elif mail_ok:
        mail_line = f"**Почта (Secrets):** `{html.escape(mail_addr)}`"
    else:
        mail_line = "**Почта:** нажмите «Сменить почту» — логин + пароль приложения (можно без Secrets, только на сессию)"
    st.caption(
        f"`{PANEL_UI_BUILD}` · {mail_line} · Фильтр Linkbuilder: **{cfg.linkbuilder_filter}** · "
        f"Статусы: «{cfg.status_prep_text}», «{cfg.status_wait_publish}»"
    )

    if st.session_state.mail_settings_panel:
        _render_mail_change_panel(secrets_mail_u, secrets_have_mail_password)

    # До проверки Sheets — чтобы стили шапки применялись даже при st.stop() из-за SA.
    st.markdown(
        """
        <style>
        /* Четыре основные кнопки в ряду */
        div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)):not(:has(> div:nth-child(5)))
          > div button[kind="primary"] {
            width: 100% !important;
            font-weight: 600 !important;
            padding-top: 0.55rem !important;
            padding-bottom: 0.55rem !important;
            background: linear-gradient(180deg, #3b8eed 0%, #1c7ed6 100%) !important;
            border: 1px solid #1864ab !important;
            color: #ffffff !important;
        }
        /* «Сменить почту» справа от h1 — компактная синяя */
        section[data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has(h1) .stButton > button[kind="primary"] {
            width: 100% !important;
            font-weight: 600 !important;
            padding: 0.28rem 0.55rem !important;
            font-size: 0.72rem !important;
            min-height: 2rem !important;
            line-height: 1.2 !important;
            border-radius: 0.35rem !important;
            background: linear-gradient(180deg, #3b8eed 0%, #1c7ed6 100%) !important;
            border: 1px solid #1864ab !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
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

    if "imap_sync_report" not in st.session_state:
        st.session_state.imap_sync_report = None
    if "inbox_dedupe_report" not in st.session_state:
        st.session_state.inbox_dedupe_report = None
    if "trade_bargain_report" not in st.session_state:
        st.session_state.trade_bargain_report = None
    if "article_publish_report" not in st.session_state:
        st.session_state.article_publish_report = None
    if "publication_check_report" not in st.session_state:
        st.session_state.publication_check_report = None

    qa1, qa2, qa3, qa4 = st.columns(4, gap="small")
    with qa1:
        if st.button("Прочитать почту", key="qa_mail", use_container_width=True, type="primary"):
            gu, gp = _effective_gmail_imap_credentials(_secrets_obj)
            if not gu or not gp:
                st.session_state.imap_sync_report = {
                    "emails_seen": 0,
                    "rows_appended": 0,
                    "emails_marked_read": 0,
                    "skipped": [],
                    "unseen_total": 0,
                    "capped": False,
                    "payment_followup_rows": 0,
                    "payment_options_enabled": False,
                    "payment_reference_empty": False,
                    "payment_reply_sent": 0,
                    "payment_reply_errors": [],
                    "sync_run_date_iso": "",
                    "sync_date_timezone": "",
                    "budget_inquiry_highlighted": 0,
                    "errors": [
                        "Нет доступа к почте: в Streamlit **Settings → Secrets** задайте "
                        "**GMAIL_IMAP_USER** = `o.tsebulevsky@rantsports.com` и **GMAIL_IMAP_APP_PASSWORD** "
                        "(пароль **приложения** Google, не обычный пароль входа). "
                        "Достаточно вместо IMAP указать только **GMAIL_SMTP_USER** / **GMAIL_SMTP_APP_PASSWORD** "
                        "с тем же логином и паролем приложения — кнопка подхватит их для IMAP. "
                        "После сохранения Secrets — **Reboot app**."
                    ],
                }
            else:
                sm_host, sm_port, sm_user, sm_pass = _effective_gmail_smtp_settings(_secrets_obj)
                st.session_state.imap_sync_report = sync_unseen_webmasters_to_inbox_sheet(
                    imap_host="imap.gmail.com",
                    imap_user=gu,
                    imap_password=gp,
                    imap_mailbox=cfg.imap_mailbox,
                    sheets_service=svc,
                    spreadsheet_id=cfg.spreadsheet_inbox_log_id,
                    sheet_gid=cfg.gid_inbox_log,
                    max_messages=cfg.imap_sync_max_messages,
                    imap_timeout_sec=cfg.imap_sync_timeout_sec,
                    payment_options_spreadsheet_id=cfg.spreadsheet_payment_options_id,
                    payment_options_gid=cfg.gid_payment_options,
                    imap_newest_first=cfg.imap_sync_newest_first,
                    auto_reply_payment_followup=cfg.imap_auto_reply_payment_followup,
                    smtp_host=sm_host,
                    smtp_port=sm_port,
                    smtp_user=sm_user,
                    smtp_password=sm_pass,
                    sync_date_timezone=cfg.trade_timezone,
                )
            rep = st.session_state.imap_sync_report
            if rep.get("errors") and rep.get("rows_appended", 0) == 0:
                try:
                    st.toast("Синхронизация почты: ошибка (см. блок ниже)", icon="⚠️")
                except Exception:
                    pass
            else:
                extra = ""
                if rep.get("payment_reply_sent"):
                    extra = f" · автоответов SMTP: {rep.get('payment_reply_sent', 0)}"
                _quick_notify(
                    f"Строк в таблицу: {rep.get('rows_appended', 0)} · "
                    f"писем помечено прочитанными: {rep.get('emails_marked_read', 0)}{extra}"
                )
    with qa2:
        if st.button("торг", key="qa_trade", use_container_width=True, type="primary"):
            sm_host, sm_port, sm_user, sm_pass = _effective_gmail_smtp_settings(_secrets_obj)
            im_u, im_p = _effective_gmail_imap_credentials(_secrets_obj)
            if not im_u or not im_p:
                st.session_state.trade_bargain_report = {
                    "errors": [
                        "Нет доступа к **IMAP**: без него нельзя найти тред для ответа. Задайте в Secrets "
                        "**GMAIL_IMAP_USER** / **GMAIL_IMAP_APP_PASSWORD** или **GMAIL_SMTP_*** (как для "
                        "**«Прочитать почту»**). После сохранения — **Reboot app**."
                    ],
                    "today": "",
                    "needles": [],
                    "rows_matched": 0,
                    "domains_considered": 0,
                    "sent": 0,
                    "skipped": [],
                    "smtp_errors": [],
                }
            else:
                st.session_state.trade_bargain_report = run_trade_bargain_round(
                    sheets_service=svc,
                    cfg=cfg,
                    smtp_host=sm_host,
                    smtp_port=sm_port,
                    smtp_user=sm_user,
                    smtp_password=sm_pass,
                    imap_host="imap.gmail.com",
                    imap_user=im_u,
                    imap_password=im_p,
                    imap_mailbox=cfg.imap_mailbox,
                    imap_timeout_sec=cfg.imap_sync_timeout_sec,
                )
            tr = st.session_state.trade_bargain_report
            if tr.get("errors") and tr.get("sent", 0) == 0:
                try:
                    st.toast("Торг: ошибка или нет строк (см. отчёт)", icon="⚠️")
                except Exception:
                    pass
            elif tr.get("sent", 0) == 0 and int(tr.get("rows_matched", 0) or 0) > 0:
                try:
                    st.toast("Торг: ни одного письма не отправлено (см. пропуски в отчёте)", icon="⚠️")
                except Exception:
                    pass
            else:
                _quick_notify(f"Торг: отправлено писем {tr.get('sent', 0)} · строк за сегодня: {tr.get('rows_matched', 0)}")
    with qa3:
        if st.button("отправить статьи", key="qa_send", use_container_width=True, type="primary"):
            sm_host, sm_port, sm_user, sm_pass = _effective_gmail_smtp_settings(_secrets_obj)
            im_u, im_p = _effective_gmail_imap_credentials(_secrets_obj)
            if not im_u or not im_p:
                st.session_state.article_publish_report = {
                    "errors": [
                        "Нет доступа к **IMAP**: без него нельзя найти тред для ответа. Задайте в Secrets "
                        "**GMAIL_IMAP_USER** и **GMAIL_IMAP_APP_PASSWORD** (или **GMAIL_SMTP_*** с тем же "
                        "логином и паролем приложения — как для кнопки **«Прочитать почту»**). После сохранения — **Reboot app**."
                    ],
                    "wait_rows_total": 0,
                    "queued": 0,
                    "sent": 0,
                    "skipped": [],
                    "smtp_errors": [],
                    "capped": False,
                }
            else:
                st.session_state.article_publish_report = run_article_publish_batch(
                    sheets_service=svc,
                    cfg=cfg,
                    smtp_host=sm_host,
                    smtp_port=sm_port,
                    smtp_user=sm_user,
                    smtp_password=sm_pass,
                    imap_host="imap.gmail.com",
                    imap_user=im_u,
                    imap_password=im_p,
                    imap_mailbox=cfg.imap_mailbox,
                    imap_timeout_sec=cfg.imap_sync_timeout_sec,
                )
            ar = st.session_state.article_publish_report
            if ar.get("errors") and ar.get("sent", 0) == 0:
                try:
                    st.toast("Статьи: ошибка или нечего слать (см. отчёт)", icon="⚠️")
                except Exception:
                    pass
            elif ar.get("sent", 0) == 0 and int(ar.get("queued", 0) or 0) > 0:
                try:
                    st.toast("Статьи: ни одного письма не отправлено (см. пропуски в отчёте)", icon="⚠️")
                except Exception:
                    pass
            else:
                cap = " (лимит)" if ar.get("capped") else ""
                _quick_notify(f"Статьи: отправлено {ar.get('sent', 0)}{cap} · пропусков: {len(ar.get('skipped') or [])}")
    with qa4:
        if st.button("проверка публикаций", key="qa_check", use_container_width=True, type="primary"):
            st.session_state.publication_check_report = run_publication_check_batch(
                sheets_service=svc,
                cfg=cfg,
            )
            pc = st.session_state.publication_check_report
            if pc.get("errors") and int(pc.get("checked", 0) or 0) == 0:
                try:
                    st.toast("Проверка публикаций: ошибка или нечего проверять (см. отчёт)", icon="⚠️")
                except Exception:
                    pass
            else:
                ov = sum(1 for r in (pc.get("results") or []) if r.get("overall_ok"))
                _quick_notify(
                    f"Проверка: строк OK {ov}/{pc.get('checked', 0)} · HTTP OK {pc.get('http_ok_count', 0)} · "
                    f"I+J OK {pc.get('placement_pair_yes', 0)} · индекс «да» {pc.get('index_yes', 0)} · "
                    f"пропусков {len(pc.get('skipped') or [])}"
                )
    st.divider()

    if st.session_state.imap_sync_report is not None:
        rep = st.session_state.imap_sync_report
        with st.expander("📬 Синхронизация ответов вебмастеров → таблица «Сбор с ответов»", expanded=True):
            st.caption(
                "Непрочитанные (UNSEEN) из **IMAP** разбираются на сервере: домен из темы (`… for site.com`), "
                "дополнительные сайты из ссылок в теле, в колонку **дата** пишется **дата нажатия «Прочитать почту»** "
                f"(часовой пояс **{cfg.trade_timezone}**), черновик **цены** из текста письма, **Почта** отправителя. "
                "По одной строке на домен. Колонка **«Цена после торг»** не заполняется (ручной ввод). "
                "Колонка **F** — черновик ответа про **оплату**: сверка с книгой «Возможности оплаты»; "
                "если в письме **нет** вариантов оплаты или они **не входят** в ваш справочник — подставляется фраза про USDT/PayPal "
                "(на **английском**, если в теме/теле нет кириллицы). "
                "**Автоответ вебмастеру по SMTP** — **включён по умолчанию**: если заданы **GMAIL_SMTP_*** и в колонке F есть текст "
                "(логика «Возможности оплаты»), письмо уходит **один раз на входящее** с этим текстом. "
                "Чтобы **только таблица** без отправки — в Secrets: **`IMAP_AUTO_REPLY_PAYMENT_FOLLOWUP = false`**. "
                "Темы вида **«… for site.com»** и **«… your website site.com»** распознаются; UNSEEN обрабатываются **сначала более новые** "
                "(можно отключить: `IMAP_SYNC_NEWEST_FIRST = false`). "
                "Письмо помечается прочитанным, если добавлена хотя бы одна строка **или** оно отфильтровано как не ответ вебмастера: "
                "**только наш шаблон** про USDT/PayPal в теле (как исходящее уточнение), **отказ доставки** (mailer-daemon, «Address not found», «message wasn't delivered»), "
                "**только платформенные хосты** в теме/ссылках (github.com, slack.com, hunter.io, YouTrack, биржи ссылок — см. **lib/mail_parse.py**, `_NON_WEBMASTER_HOST_ROOTS`) "
                "или **From** совпадает с ящиком IMAP — в таблицу не пишется, **SMTP не шлётся**; такие UNSEEN помечаются прочитанными. "
                "Вопрос про **бюджет** («What is your budget», «какой бюджет» и т.п.) — **без** автоответа и **без** текста в F; "
                "добавленные строки **жёлтые** (ответ вручную)."
            )
            sid = cfg.spreadsheet_inbox_log_id
            st.markdown(
                f"Таблица: [открыть в Google Sheets](https://docs.google.com/spreadsheets/d/{sid}/edit#gid={cfg.gid_inbox_log})"
            )
            ut = rep.get("unseen_total", 0)
            if rep.get("capped"):
                st.warning(
                    f"В ящике было **{ut}** непрочитанных; обработана только последняя порция "
                    f"(лимит **IMAP_SYNC_MAX_MESSAGES** в Secrets). Увеличьте лимит или поставьте **0** для всех."
                )
            ar_on = cfg.imap_auto_reply_payment_followup
            st.caption(
                "Автоответ SMTP: **включён** — текст колонки F уходит вебмастеру при необходимости."
                if ar_on
                else "Автоответ SMTP: **выключен** в Secrets (`IMAP_AUTO_REPLY_PAYMENT_FOLLOWUP = false`) — только строки в таблице."
            )
            m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
            m1.metric("UNSEEN в ящике", ut)
            m2.metric("Писем обработано", rep.get("emails_seen", 0))
            m3.metric("Строк в таблицу", rep.get("rows_appended", 0))
            m4.metric("Помечено прочитанными", rep.get("emails_marked_read", 0))
            m5.metric("Черновик оплаты (стр.)", rep.get("payment_followup_rows", 0))
            m6.metric("Отправлено SMTP (оплата)", rep.get("payment_reply_sent", 0))
            m7.metric("Жёлтых (бюджет)", rep.get("budget_inquiry_highlighted", 0))
            if rep.get("sync_run_date_iso"):
                st.caption(
                    f"В колонку **дата** для строк этого запуска: **{rep.get('sync_run_date_iso')}** "
                    f"({rep.get('sync_date_timezone', '—')})."
                )
            for pre in rep.get("payment_reply_errors") or []:
                st.warning(pre)
            if rep.get("payment_options_enabled") and rep.get("payment_reference_empty"):
                st.info(
                    "В справочнике «Возможности оплаты» не найдено ни одного знакомого метода (USDT, PayPal, карта и т.д.) — "
                    "колонка F не заполняется. Добавьте явные названия на лист или расширьте шаблоны в **lib/payment_match.py**."
                )
            for err in rep.get("errors") or []:
                st.error(err)
            skipped = rep.get("skipped") or []
            if skipped:
                st.warning("Пропуски (строка в таблицу не добавлялась; см. колонку **reason**):")
                st.dataframe(pd.DataFrame(skipped), use_container_width=True, height=min(220, 60 + 28 * len(skipped)))
            if not rep.get("errors") and rep.get("emails_seen", 0) == 0:
                st.info("Нет непрочитанных писем в ящике.")
            if st.button("Скрыть отчёт", key="imap_sync_clear"):
                st.session_state.imap_sync_report = None
                st.rerun()

    with st.expander("Дедуп строк «Сбор с ответов» и подсветка цен по домену", expanded=False):
        st.caption(
            "**1)** Полностью одинаковые строки (все столбцы) — удаляются лишние, остаётся верхняя. "
            "**2)** Для одного и того же **домена** при двух и более строках с **разными числовыми ценами** "
            "в колонке **«цена»** (не «после торг»): меньшая — **зелёный** фон строки, большая — **красный**, "
            "промежуточные — без цвета. Сначала сбрасывается фон всех строк данных (белый), затем красятся нужные. "
            "**Внимание:** жёлтая подсветка строк «вопрос про бюджет» после **«Прочитать почту»** этим шагом **сотрётся**."
        )
        if st.button("Выполнить дедуп и подсветку", key="inbox_dedupe_highlight"):
            st.session_state.inbox_dedupe_report = dedupe_and_highlight_inbox_sheet(
                sheets_service=svc,
                spreadsheet_id=cfg.spreadsheet_inbox_log_id,
                sheet_gid=cfg.gid_inbox_log,
            )
            dr = st.session_state.inbox_dedupe_report
            if dr.get("errors"):
                try:
                    st.toast("Дедуп: ошибка (см. блок ниже)", icon="⚠️")
                except Exception:
                    pass
            else:
                try:
                    st.toast(
                        f"Дублей удалено: {dr.get('duplicates_removed', 0)} · "
                        f"строк с подсветкой: {dr.get('rows_formatted', 0)}",
                        icon="✅",
                    )
                except Exception:
                    pass
            st.rerun()

    if st.session_state.inbox_dedupe_report is not None:
        dr = st.session_state.inbox_dedupe_report
        with st.expander("📊 Дедуп и подсветка «Сбор с ответов»", expanded=bool(dr.get("errors"))):
            st.write(
                f"Лист: **{dr.get('sheet_title') or '—'}** · удалено полных дублей: **{dr.get('duplicates_removed', 0)}** · "
                f"строк с зелёным/красным фоном: **{dr.get('rows_formatted', 0)}**."
            )
            for err in dr.get("errors") or []:
                st.error(err)
            if st.button("Скрыть отчёт дедупа", key="inbox_dedupe_clear"):
                st.session_state.inbox_dedupe_report = None
                st.rerun()

    if st.session_state.trade_bargain_report is not None:
        tr = st.session_state.trade_bargain_report
        with st.expander("💬 Торг (калькулятор → «Сбор с ответов» → IMAP-тред → SMTP)", expanded=True):
            st.caption(
                "Строки **калькулятора** (вкладка `GID_CALCULATOR_TAB_1`), где в колонке **даты** стоит **сегодня** "
                f"({tr.get('today', '…')} по **{cfg.trade_timezone}**), а в колонке **ответственного** есть одна из подстрок: "
                f"{', '.join(repr(x) for x in (tr.get('needles') or [])[:12]) or '—'}. "
                "Email вебмастера — **только** из таблицы **«Сбор с ответов»** (последняя по дате строка с тем же доменом). "
                "По **IMAP** ищется переписка с этим адресом и доменом; письмо уходит **ответом в тот же тред** "
                "(тема **Re:** из найденного письма, In-Reply-To / References). "
                "Без треда в ящике — пропуск **no_imap_thread**. "
                "Текст: скидка **TRADE_DISCOUNT_PERCENT** (по умолчанию 20 %). "
                "**COL_TRADE_DATE**, **TRADE_RESPONSIBLE_NAME** — в Secrets."
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Сегодня (фильтр)", tr.get("today", "—"))
            c2.metric("Доменов к отправке", tr.get("rows_matched", 0))
            c3.metric("Отправлено SMTP", tr.get("sent", 0))
            c4.metric("Доменов обработано", tr.get("domains_considered", 0))
            for err in tr.get("errors") or []:
                st.error(err)
            for se in tr.get("smtp_errors") or []:
                st.warning(se)
            skipped = tr.get("skipped") or []
            if skipped:
                st.warning("Пропуски:")
                st.dataframe(pd.DataFrame(skipped), use_container_width=True, height=min(200, 60 + 28 * len(skipped)))
            if st.button("Скрыть отчёт торг", key="trade_report_clear"):
                st.session_state.trade_bargain_report = None
                st.rerun()

    if st.session_state.article_publish_report is not None:
        ar = st.session_state.article_publish_report
        with st.expander("📎 Отправить статьи (реестры → «Сбор с ответов» → IMAP-тред → SMTP)", expanded=True):
            lim = cfg.article_publish_max_send
            lim_txt = "без лимита" if lim == 0 else str(lim)
            st.caption(
                f"Условия как в реестре **TelecomAsia**: колонка **Status** = **«{cfg.status_wait_publish}»**, "
                "в **Article/post** (у вас обычно колонка **H**) — ссылка на **Google Docs** или **Google Drive**, "
                "домен для почты — **Website Donor** (колонка **A**). "
                "Адрес берётся из **«Сбор с ответов»** по домену (сначала **«Прочитать почту»**). "
                "По **IMAP** ищется последнее письмо в переписке с этим адресом, где в теме/теле фигурирует домен; "
                "отправка идёт **ответом в тот же тред** (тема **Re:** …, заголовки In-Reply-To / References). "
                "Если тред в ящике не найден — строка в пропусках с причиной **no_imap_thread**, письмо не шлётся. "
                f"За клик не более **{lim_txt}** отправок (**ARTICLE_PUBLISH_MAX_SEND**; **0** = без лимита). "
                "Ручная правка — вкладка **«Жду публикации → отправка»**."
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Строк «Жду публикации»", ar.get("wait_rows_total", 0))
            c2.metric("В очереди разбора", ar.get("queued", 0))
            c3.metric("Отправлено SMTP", ar.get("sent", 0))
            c4.metric("Пропусков", len(ar.get("skipped") or []))
            if ar.get("capped"):
                st.warning(f"Достигнут лимит отправок за запуск (**{cfg.article_publish_max_send}**). Остальные строки не обработаны.")
            for err in ar.get("errors") or []:
                st.error(err)
            for se in ar.get("smtp_errors") or []:
                st.warning(se)
            skipped = ar.get("skipped") or []
            if skipped:
                st.warning("Пропуски:")
                st.dataframe(pd.DataFrame(skipped), use_container_width=True, height=min(260, 60 + 24 * len(skipped)))
            if st.button("Скрыть отчёт статьи", key="article_publish_clear"):
                st.session_state.article_publish_report = None
                st.rerun()

    if st.session_state.publication_check_report is not None:
        pc = st.session_state.publication_check_report
        with st.expander("✅ Проверка публикаций (HTTP + EEAT + Anchor/Outgoing + индекс)", expanded=True):
            to = cfg.publication_check_timeout_sec
            mx = cfg.publication_check_max_rows
            lim_txt = "без лимита" if mx == 0 else str(mx)
            stst = ", ".join(repr(s) for s in (cfg.publication_check_statuses or [])[:8])
            ci_note = (
                "регистр букв анкора игнорируется (**PUBLICATION_CHECK_ANCHOR_CASE_INSENSITIVE**)."
                if cfg.publication_check_anchor_case_insensitive
                else "анкор сравнивается **с учётом регистра** (можно включить без учёта регистра в Secrets)."
            )
            st.caption(
                f"Статусы строк: **{stst}** (**PUBLICATION_CHECK_STATUSES**; по умолчанию только **Готово**). "
                "В **Article/post** (обычно колонка **H**) — URL опубликованной статьи; **GET** HTML (**2xx–3xx**, лимит тела **PUBLICATION_CHECK_MAX_BODY_BYTES**). "
                f"На странице ищется одна и та же ссылка **<a>**: href из **{cfg.col_outgoing_link}** (колонка **J**) и видимый текст = **{cfg.col_anchor}** (колонка **I**); {ci_note} "
                "**EEAT** — как **weekly-outreach-sync.gs**: **EEAT_AUTHOR_MARKERS**, колонки **Автор со ссылкой** / **Автор без ссылки**; при URL в «Автор со ссылкой» — href на странице. "
                "**Индекс** — опционально **Google CSE** (**GOOGLE_CSE_API_KEY**, **GOOGLE_CSE_CX**). "
                f"Таймаут **{to}** с, за клик до **{lim_txt}** URL (**0** = без лимита). "
                "Устаревшее имя **COL_PLACED_TARGET_URL** в Secrets подставляется, если **COL_OUTGOING_LINK** пусто."
            )
            if pc.get("options_note"):
                st.info(pc["options_note"])
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
            c1.metric("Строк по статусам", pc.get("wait_rows_total", 0))
            c2.metric("В очереди", pc.get("queued", 0))
            c3.metric("Проверено URL", pc.get("checked", 0))
            c4.metric("HTTP OK", pc.get("http_ok_count", 0))
            c5.metric("I+J на странице", pc.get("placement_pair_yes", 0))
            c6.metric("Индекс «да»", pc.get("index_yes", 0))
            c7.metric("Индекс «нет»", pc.get("index_no", 0))
            overall_n = sum(1 for r in (pc.get("results") or []) if r.get("overall_ok"))
            c8.metric("Все проверки OK", overall_n)
            if pc.get("capped"):
                st.warning(
                    f"Достигнут лимит проверок за запуск (**{cfg.publication_check_max_rows}**). "
                    "Увеличьте **PUBLICATION_CHECK_MAX_ROWS** или поставьте **0**."
                )
            for err in pc.get("errors") or []:
                st.error(err)
            results = pc.get("results") or []
            if results:
                st.subheader("Результаты")
                bad = [r for r in results if not r.get("overall_ok")]
                if bad:
                    st.warning("Строки, где не прошла хотя бы одна из включённых проверок:")
                    st.dataframe(pd.DataFrame(bad), use_container_width=True, height=min(320, 60 + 22 * len(bad)))
                good = [r for r in results if r.get("overall_ok")]
                if good:
                    st.success(f"Все включённые проверки OK ({len(good)}):")
                    st.dataframe(pd.DataFrame(good), use_container_width=True, height=min(240, 60 + 22 * len(good)))
            skipped = pc.get("skipped") or []
            if skipped:
                st.caption("Пропуски")
                st.dataframe(pd.DataFrame(skipped), use_container_width=True, height=min(240, 60 + 22 * len(skipped)))
            if st.button("Скрыть отчёт проверки", key="publication_check_clear"):
                st.session_state.publication_check_report = None
                st.rerun()

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
            "Отправка с этой вкладки — **новое** письмо через SMTP (`GMAIL_SMTP_*`). "
            "Кнопка **«отправить статьи»** вверху шлёт **ответ в тот же тред** (IMAP ищет переписку, затем SMTP с In-Reply-To)."
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
                        f"<p>Пожалуйста, разместите нашу статью. Документ в Google Docs: "
                        f"<a href=\"{html.escape(art)}\">{html.escape(art)}</a></p>"
                        f"<p>Сумма за размещение (гемблинг): <b>{html.escape(cost)}</b> USD (уточните по калькулятору при необходимости).</p>"
                        f"<p>С уважением</p>"
                    )
                else:
                    default_body = (
                        f"<p>Hello,</p>"
                        f"<p>Could you please publish our article? The text is in this Google Doc: "
                        f"<a href=\"{html.escape(art)}\">{html.escape(art)}</a></p>"
                        f"<p>Placement fee (gambling): <b>{html.escape(cost)}</b> USD (see internal calculator if needed).</p>"
                        f"<p>Best regards</p>"
                    )
                body_html = st.text_area("Тело письма (HTML)", value=default_body, height=220)
                subj = st.text_input("Тема", value="Article for publication / Статья для публикации")

                smtp_host, smtp_port, smtp_user, smtp_pass = _effective_gmail_smtp_settings(_secrets_obj)

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
        gu, gp = _effective_gmail_imap_credentials(_secrets())
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
