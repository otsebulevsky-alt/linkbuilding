"""Кнопка «проверка публикаций»: HTTP + EEAT + пара колонок I/J (Anchor + Outgoing link) + опционально индекс (CSE).

Согласовано с:
- shared-docs/seo/linkbuilding/context/apps-script-weekly-outreach-sync.md (логика EEAT)
- shared-docs/seo/linkbuilding/context/eeat-registry-columns-for-cursor.md (колонки)
- shared-docs/seo/linkbuilding/context/author-list.md (маркеры в EEAT_AUTHOR_MARKERS)
"""

from __future__ import annotations

from typing import Any

from lib.article_publish_batch import is_google_docs_or_drive_url
from lib.config import AppConfig
from lib.eeat_page_check import (
    expected_author_page_url_on_page,
    run_eeat_html_checks,
    verify_outgoing_link_and_anchor_pair,
)
from lib.google_cse_index_check import check_article_url_in_google_index
from lib.http_url_check import fetch_publication_page
from lib.sheets_service import (
    a1_all_columns,
    filter_by_linkbuilder,
    get_sheet_title_by_gid,
    get_values_as_dataframe,
    resolve_article_column,
    resolve_donor_column,
    resolve_linkbuilder_column,
    resolve_status_column,
)
from lib.trade_bargain import normalize_domain_cell


def _resolve_header_col(df: Any, primary: str, fallbacks: tuple[str, ...] = ()) -> str | None:
    if df is None or df.empty:
        return None
    m = {str(c).strip().lower(): c for c in df.columns}
    for name in (primary,) + fallbacks:
        k = (name or "").strip().lower()
        if k and k in m:
            return str(m[k])
    return None


def _yn(v: bool | None, *, na: str = "—") -> str:
    if v is None:
        return na
    return "да" if v else "нет"


def run_publication_check_batch(
    *,
    sheets_service: Any,
    cfg: AppConfig,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "errors": [],
        "wait_rows_total": 0,
        "queued": 0,
        "checked": 0,
        "http_ok_count": 0,
        "http_fail_count": 0,
        "eeat_link_yes": 0,
        "eeat_mention_yes": 0,
        "placement_pair_yes": 0,
        "placement_rows": 0,
        "index_yes": 0,
        "index_no": 0,
        "index_skipped": 0,
        "results": [],
        "skipped": [],
        "capped": False,
        "options_note": "",
    }

    markers = [m for m in (cfg.eeat_author_markers or []) if (m or "").strip()]
    statuses = {s.strip() for s in (cfg.publication_check_statuses or []) if s and str(s).strip()}
    if not statuses:
        statuses = {"Готово"}

    has_cse = bool((cfg.google_cse_api_key or "").strip() and (cfg.google_cse_cx or "").strip())
    report["options_note"] = (
        "Индекс Google: **включён** (Custom Search API)."
        if has_cse
        else "Индекс Google: **выключен** — задайте **GOOGLE_CSE_API_KEY** и **GOOGLE_CSE_CX** в Secrets."
    )

    timeout = float(cfg.publication_check_timeout_sec)
    max_rows = int(cfg.publication_check_max_rows)
    max_body = int(cfg.publication_check_max_body_bytes)

    registries: list[tuple[str, str, int]] = [
        ("TelecomAsia", cfg.spreadsheet_telecom_id, cfg.gid_telecom_registry),
        ("Реестр 2", cfg.spreadsheet_registry_2_id, cfg.gid_registry_2),
    ]

    tasks: list[dict[str, Any]] = []
    for reg_label, sid, gid in registries:
        title = get_sheet_title_by_gid(sheets_service, sid, gid)
        if not title:
            report["errors"].append(f"{reg_label}: не найден лист gid={gid}.")
            continue
        df = get_values_as_dataframe(sheets_service, sid, a1_all_columns(title))
        if df.empty:
            continue
        lb = resolve_linkbuilder_column(df, cfg.col_linkbuilder, [])
        st_col = resolve_status_column(df, cfg.col_status)
        col_donor = resolve_donor_column(df, cfg.col_website_donor)
        col_art = resolve_article_column(df, cfg.col_article_post)
        col_aw = _resolve_header_col(
            df,
            cfg.col_author_with_link,
            ("автор со ссылкой", "author with link"),
        )
        col_an = _resolve_header_col(
            df,
            cfg.col_author_without_link,
            ("автор без ссылки", "author without link"),
        )
        col_out = _resolve_header_col(
            df,
            cfg.col_outgoing_link,
            ("исходящ", "outgoing", "outgoing link"),
        )
        col_anchor = _resolve_header_col(
            df,
            cfg.col_anchor,
            ("анкор", "anchor text", "text of link"),
        )
        has_placement_cols = col_out is not None and col_anchor is not None
        if not has_placement_cols:
            report["errors"].append(
                f"{reg_label}: не найдены колонки **{cfg.col_anchor}** и/или **{cfg.col_outgoing_link}** "
                "— проверка точного размещения (I+J) для этого реестра пропущена."
            )
        if not st_col or not col_donor:
            report["errors"].append(f"{reg_label}: не найдены колонки статуса или Website Donor.")
            continue
        mine = filter_by_linkbuilder(df, lb, cfg.linkbuilder_filter, cfg.linkbuilder_aliases)
        st_series = mine[st_col].astype(str).str.strip()
        wait_df = mine[st_series.isin(statuses)]
        report["wait_rows_total"] += len(wait_df)
        for idx, row in wait_df.iterrows():
            dom = str(row.get(col_donor, "") or "").strip()
            art = str(row.get(col_art, "") or "").strip() if col_art else ""
            author_url_cell = str(row.get(col_aw, "") or "").strip() if col_aw else ""
            author_txt_cell = str(row.get(col_an, "") or "").strip() if col_an else ""
            outgoing_url = str(row.get(col_out, "") or "").strip() if col_out else ""
            anchor_text = str(row.get(col_anchor, "") or "").strip() if col_anchor else ""
            tasks.append(
                {
                    "registry": reg_label,
                    "domain": dom or "(пусто)",
                    "art": art,
                    "author_url_cell": author_url_cell,
                    "author_txt_cell": author_txt_cell,
                    "outgoing_url": outgoing_url,
                    "anchor_text": anchor_text,
                    "has_placement_cols": has_placement_cols,
                    "row_index": int(idx) if isinstance(idx, int) else str(idx),
                }
            )

    report["queued"] = len(tasks)
    if not tasks:
        if not report["errors"]:
            report["errors"].append(
                f"Нет строк со статусом из **PUBLICATION_CHECK_STATUSES** "
                f"({', '.join(sorted(statuses))}) среди ваших строк в обоих реестрах."
            )
        return report

    checked = 0
    for t in tasks:
        dom = t["domain"]
        art = (t.get("art") or "").strip()
        reg = t["registry"]

        if not art:
            report["skipped"].append({"registry": reg, "domain": dom, "reason": "empty_article_cell"})
            continue
        if is_google_docs_or_drive_url(art):
            report["skipped"].append({"registry": reg, "domain": dom, "reason": "still_google_doc"})
            continue
        if not art.lower().startswith("http"):
            report["skipped"].append({"registry": reg, "domain": dom, "reason": "not_http_url"})
            continue

        if max_rows > 0 and checked >= max_rows:
            report["capped"] = True
            report["skipped"].append(
                {"registry": reg, "domain": dom, "reason": f"cap_max_checks_{max_rows}"}
            )
            continue

        nd = normalize_domain_cell(dom) if dom and dom != "(пусто)" else ""
        checked += 1
        report["checked"] = checked

        fetch = fetch_publication_page(
            art,
            timeout_sec=max(5.0, min(120.0, timeout)),
            max_bytes=max_body,
        )
        http_ok = bool(fetch.get("ok"))
        html = fetch.get("body") or ""
        if http_ok:
            report["http_ok_count"] += 1
        else:
            report["http_fail_count"] += 1

        eeat_link = eeat_mention = None
        eeat_expected_href_ok: bool | None = None
        # При пустом body после обрезки/ошибки парсинга всё равно считаем EEAT (иначе маркеры «молча» не влияют на overall_ok)
        if http_ok and markers:
            e = run_eeat_html_checks(html or "", markers)
            eeat_link = bool(e.get("eeat_author_link"))
            eeat_mention = bool(e.get("eeat_mention"))
            if eeat_link:
                report["eeat_link_yes"] += 1
            if eeat_mention:
                report["eeat_mention_yes"] += 1
        au = (t.get("author_url_cell") or "").strip()
        if http_ok and au.lower().startswith("http"):
            eeat_expected_href_ok = expected_author_page_url_on_page(html or "", au)
        elif not au:
            eeat_expected_href_ok = None

        placement_pair_ok: bool | None = None
        placement_href_found: bool | None = None
        placement_detail = ""
        if t.get("has_placement_cols"):
            report["placement_rows"] += 1
            ou = (t.get("outgoing_url") or "").strip()
            an = (t.get("anchor_text") or "").strip()
            if http_ok and html:
                vr = verify_outgoing_link_and_anchor_pair(
                    html,
                    outgoing_url=ou,
                    anchor_text=an,
                    anchor_case_insensitive=bool(cfg.publication_check_anchor_case_insensitive),
                )
                placement_pair_ok = bool(vr.get("placement_pair_ok"))
                placement_href_found = bool(vr.get("href_found"))
                placement_detail = str(vr.get("detail") or "")
                if placement_pair_ok:
                    report["placement_pair_yes"] += 1
            elif http_ok:
                placement_pair_ok = False
                placement_href_found = False
                placement_detail = "empty_html_body"
            else:
                placement_pair_ok = None
                placement_href_found = None

        google_indexed: bool | None = None
        index_err = ""
        if not has_cse:
            report["index_skipped"] += 1
        else:
            ir = check_article_url_in_google_index(
                art,
                api_key=cfg.google_cse_api_key,
                cx=cfg.google_cse_cx,
                timeout_sec=max(5.0, min(60.0, timeout)),
            )
            index_err = (ir.get("error") or "")[:200]
            if ir.get("indexed") is True:
                google_indexed = True
                report["index_yes"] += 1
            elif ir.get("indexed") is False:
                google_indexed = False
                report["index_no"] += 1
            else:
                report["index_skipped"] += 1

        overall_ok = http_ok
        if overall_ok and markers and eeat_link is not None:
            overall_ok = overall_ok and (eeat_link or eeat_mention)
        if overall_ok and eeat_expected_href_ok is not None:
            overall_ok = overall_ok and eeat_expected_href_ok
        if overall_ok and placement_pair_ok is not None:
            overall_ok = overall_ok and placement_pair_ok
        if overall_ok and google_indexed is not None:
            overall_ok = overall_ok and google_indexed

        report["results"].append(
            {
                "registry": reg,
                "domain": dom,
                "domain_norm": nd,
                "url": art[:500],
                "http_status": fetch.get("status"),
                "final_url": (fetch.get("final_url") or "")[:500],
                "http_ok": http_ok,
                "error": (fetch.get("error") or "")[:240],
                "eeat_author_link": _yn(eeat_link, na="—") if markers else "—",
                "eeat_mention": _yn(eeat_mention, na="—") if markers else "—",
                "eeat_expected_author_href": _yn(eeat_expected_href_ok, na="—"),
                "placement_pair_I_J": _yn(placement_pair_ok, na="—"),
                "placement_href_found": _yn(placement_href_found, na="—"),
                "placement_detail": placement_detail[:120],
                "google_indexed": (
                    "да"
                    if google_indexed is True
                    else ("нет" if google_indexed is False else ("?" if index_err else "—"))
                ),
                "index_detail": index_err,
                "overall_ok": overall_ok,
            }
        )

    return report
