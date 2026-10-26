"""J-Quants から日次バーを取得し、ETF コードに突合する。

Free 版のため日次バーは「実行日から 12 週間前〜17 週間前」のウィンドウしか
取れない。この期間の値は終値・前日比・チャートの「参考値」として使う。
有料プランに戻した場合は fetch_window のオフセットを差し替えるだけでよい。
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date, timedelta

import requests

log = logging.getLogger("jquants")

API_URL = "https://api.jquants.com/v2/equities/bars/daily"
WEEK = timedelta(weeks=1)


def window(today: date) -> tuple[date, date]:
    """Free 版の取得可能ウィンドウ: 17 週間前 〜 12 週間前。"""
    return today - 17 * WEEK, today - 12 * WEEK


def api_key() -> str | None:
    key = os.environ.get("JQUANTS_API_KEY")
    return key.strip() if key and key.strip() else None


def _get_with_retry(url: str, headers: dict, params: dict, retries: int = 6) -> dict:
    delay = 5.0
    last: Exception | None = None
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=headers, params=params, timeout=30)
            if res.status_code == 429:
                wait = float(res.headers.get("Retry-After") or 60.0)
                log.warning("レート制限(429)。%.0f 秒待機", wait)
                last = RuntimeError("rate limited (429)")
                if attempt < retries - 1:
                    time.sleep(wait)
                    delay *= 2
                continue
            res.raise_for_status()
            return res.json()
        except Exception as e:
            last = e
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
    raise last  # type: ignore[misc]


def fetch_bars(today: date | None = None, days: int | None = None) -> dict[str, dict]:
    """ウィンドウ内の全銘柄の日次バーを取得する。

    days を指定した場合はウィンドウ末尾からその営業日数のみ取得する
    （フォールバックの終値・前日比には最後の2営業日だけあれば十分）。
    戻り値: { "5桁コード": {"t": [date...], "v": [close...], "vol": [volume...]}, ... }
    API キー未設定・取得失敗時は空 dict（呼び出し側で「データなし」扱い）。
    """
    key = api_key()
    if not key:
        log.warning("JQUANTS_API_KEY が未設定のため価格を取得しません")
        return {}
    today = today or date.today()
    frm, to = window(today)
    headers = {"x-api-key": key}
    out: dict[str, dict] = {}
    try:
        # v2 daily は date または code の指定が必須のため、ウィンドウ内を営業日単位で取得
        targets: list[date] = []
        day = frm
        while day <= to:
            day += timedelta(days=1)
            if day.weekday() >= 5:
                continue
            targets.append(day)
        if days is not None:
            targets = targets[-days:]
        for day in targets:
            params: dict = {"date": day.isoformat()}
            while True:
                data = _get_with_retry(API_URL, headers, params)
                for row in data.get("data") or []:
                    # レスポンスキーは PascalCase（Code/Date/C）だが念のため小文字も受ける
                    code = str(row.get("Code") or row.get("code") or "")
                    close = row.get("C") if row.get("C") is not None else row.get("close")
                    vol = row.get("Volume") if row.get("Volume") is not None else row.get("volume")
                    d = str(row.get("Date") or row.get("date") or day.isoformat())
                    if not code or close is None:
                        continue
                    bars = out.setdefault(code, {"t": [], "v": [], "vol": []})
                    bars["t"].append(d)
                    bars["v"].append(float(close))
                    bars["vol"].append(int(vol) if vol is not None else None)
                nxt = data.get("pagination_key")
                if not nxt:
                    break
                params = {"pagination_key": nxt}
            time.sleep(3.0)  # レート制限対策：リクエスト間の間隔
    except Exception as e:
        log.warning("J-Quants 取得失敗: %s", e)
        return {}
    for bars in out.values():
        order = sorted(range(len(bars["t"])), key=lambda i: bars["t"][i])
        bars["t"] = [bars["t"][i] for i in order]
        bars["v"] = [bars["v"][i] for i in order]
        bars["vol"] = [bars["vol"][i] for i in order]
    log.info("J-Quants: %s 銘柄分のバーを取得", len(out))
    return out


def fetch_prices(codes: list[str] | None = None) -> dict[str, dict]:
    """ウィンドウ内の日次バーから終値・前日比を算出して返す（Yahoo 失敗時のフォールバック用）。

    ウィンドウの最後の2営業日の close で (P_n/P_{n-1}-1)*100 を算出する。
    出来高は最終営業日の Volume を返す。
    戻り値: { "4桁コード": {"close": float, "change_pct": float|None, "volume": int|None, "as_of": "YYYY-MM-DD"}, ... }
    API キー未設定・取得失敗時は空 dict（呼び出し側で「データなし」扱い）。
    """
    bars_by_code = fetch_bars(days=2)
    wanted = set(codes) if codes is not None else None
    out: dict[str, dict] = {}
    for jq_code, bars in bars_by_code.items():
        code4 = jq_code[:4]
        if wanted is not None and code4 not in wanted:
            continue
        if len(bars["v"]) < 1:
            continue
        change_pct = None
        if len(bars["v"]) >= 2 and bars["v"][-2]:
            change_pct = round((bars["v"][-1] / bars["v"][-2] - 1) * 100, 3)
        out.setdefault(code4, {
            "close": bars["v"][-1],
            "change_pct": change_pct,
            "volume": bars.get("vol", [None])[-1],
            "as_of": bars["t"][-1],
        })
    log.info("J-Quants: %s 銘柄分の価格を算出", len(out))
    return out
