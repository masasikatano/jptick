"""JPX の東証上場銘柄一覧 xlsx（data_j.xlsx）を取得・パースする（銘柄マスタ）。

対象は東証プライム・スタンダード・グロースの普通株（内国株式）のみ。
ETF/REIT/優先株式/外国株/PRO Market 等は「市場・商品区分」列で除外する。

xlsx の href はページ依存のため、JPX の統計ページから動的に抽出する。
取得失敗時はリポジトリ内のフォールバック xlsx を使う。
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from openpyxl import load_workbook

log = logging.getLogger("master")

ROOT = Path(__file__).resolve().parents[1]
JPX_PAGE_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
FALLBACK_XLSX = ROOT / "data_j.xlsx"
DOWNLOADED_XLSX = ROOT / "listed_companies.xlsx"

HEADER_ROW = 1  # 1 行目がヘッダ

# 対象市場（普通株＝内国株式）。ETF・ETN / REIT 等 / 外国株式 / PRO Market は除外。
TARGET_MARKETS = ("プライム（内国株式）", "スタンダード（内国株式）", "グロース（内国株式）")

# 「市場・商品区分」→ 表示用の市場区分
MARKET_LABEL = {
    "プライム（内国株式）": "プライム",
    "スタンダード（内国株式）": "スタンダード",
    "グロース（内国株式）": "グロース",
}


def normalize_header(v: object) -> str:
    return str(v).replace("\n", "").strip()


def _normalize_value(v: object) -> object:
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def fetch_xlsx(timeout: int = 30) -> Path | None:
    """JPX ページから data_j 系 .xlsx の href を抽出してダウンロード。失敗時は None。"""
    try:
        res = requests.get(JPX_PAGE_URL, timeout=timeout)
        res.raise_for_status()
        m = re.search(r'href="([^"]*data_j[^"]*\.xlsx)"', res.text)
        if not m:
            m = re.search(r'href="([^"]+\.xlsx)"', res.text)
        if not m:
            log.warning("xlsx の href が見つかりません")
            return None
        url = urljoin(JPX_PAGE_URL, m.group(1))
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        DOWNLOADED_XLSX.write_bytes(r.content)
        log.info("xlsx をダウンロード: %s", url)
        return DOWNLOADED_XLSX
    except Exception as e:
        log.warning("xlsx ダウンロード失敗（フォールバックを使用）: %s", e)
        return None


def xlsx_path(prefer_download: bool = True) -> Path:
    if prefer_download:
        p = fetch_xlsx()
        if p is not None:
            return p
    if FALLBACK_XLSX.is_file():
        return FALLBACK_XLSX
    if DOWNLOADED_XLSX.is_file():
        return DOWNLOADED_XLSX
    raise FileNotFoundError(f"xlsx が見つかりません: {FALLBACK_XLSX} / {DOWNLOADED_XLSX}")


def _row_to_record(fields: dict[str, object]) -> dict | None:
    market = str(fields.get("市場・商品区分") or "")
    if market not in MARKET_LABEL:
        return None
    raw_code = fields.get("コード")
    if raw_code is None:
        return None
    code = str(raw_code).strip().zfill(4)
    if not re.fullmatch(r"\d{4}", code):
        return None
    return {
        "code": code,
        "name": str(fields.get("銘柄名") or ""),
        "market": MARKET_LABEL[market],
        "industry": str(fields.get("33業種区分") or ""),
        "fields": fields,
    }


def load_master(path: Path | None = None) -> list[dict]:
    """xlsx を読み、普通株レコードのリストを返す。

    各レコードは code / name / market / industry / fields。
    fields は xlsx の全列を保持する（詳細ページ復活に備えて残すが表示はしない）。
    """
    path = path or xlsx_path()
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    headers = [normalize_header(h) for h in next(rows)]

    records: list[dict] = []
    for row in rows:
        fields = {
            headers[i]: _normalize_value(row[i] if i < len(row) else None)
            for i in range(len(headers))
            if headers[i]
        }
        rec = _row_to_record(fields)
        if rec is not None:
            records.append(rec)
    wb.close()
    return records
