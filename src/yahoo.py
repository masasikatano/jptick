"""Yahoo Finance から終値・前日比を取得する（主データソース）。

エンドポイント: https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d
銘柄コードは「4桁コード＋.T」（例: 1306 → 1306.T）。

終値・前日比は close 配列の最後の2点から自前で算出する
（(P_n/P_{n-1}-1)*100。spec.md の定義と一致させるため
meta.regularMarketChangePercent は使わない）。
出来高は indicators.quote の volume 配列から、close と同じ最終ポイントの値を採用する
（最終点が None の場合は直近の有効値にフォールバック）。

取得失敗した銘柄は戻り値に含めず、呼び出し側で「データなし」扱いとする。
"""

from __future__ import annotations

import logging
import time
from datetime import date

import requests

log = logging.getLogger("yahoo")

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
REQUEST_INTERVAL = 0.5  # リクエスト間の間隔（秒）
RETRIES = 3

# Yahoo で取得を除外する銘柄コード（必要になったらここに追加）
YAHOO_EXCLUDE: set[str] = set()

HEADERS = {"User-Agent": "Mozilla/5.0"}


def symbol(code: str) -> str:
    return f"{code}.T"


def parse_chart(data: dict) -> dict | None:
    """chart API レスポンスから終値・前日比・出来高・基準日を算出する。

    close 配列の最後の2点から (P_n/P_{n-1}-1)*100 を計算する。
    出来高は close と同じ最終ポイントの volume を採用し、
    最終点が None の場合は直近の有効値にフォールバックする。
    取得できない場合は None を返す。
    """
    try:
        result = data["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        closes = quote["close"]
        volumes = quote.get("volume")
        timestamps = result["timestamp"]
    except (KeyError, IndexError, TypeError):
        return None
    points = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
    if not points:
        return None
    last_ts, last_close = points[-1]
    change_pct = None
    if len(points) >= 2:
        prev = points[-2][1]
        if prev:
            change_pct = round((last_close / prev - 1) * 100, 3)
    volume = None
    if volumes:
        for v in reversed(volumes[:len(points)]):
            if v is not None:
                volume = int(v)
                break
    return {
        "close": float(last_close),
        "change_pct": change_pct,
        "volume": volume,
        "as_of": date.fromtimestamp(last_ts).isoformat(),
    }


def _fetch_one(code: str, session: requests.Session, retries: int = RETRIES) -> dict | None:
    url = CHART_URL.format(symbol=symbol(code))
    delay = 2.0
    last: Exception | None = None
    for attempt in range(retries):
        try:
            res = session.get(url, params={"interval": "1d", "range": "5d"}, timeout=30)
            res.raise_for_status()
            parsed = parse_chart(res.json())
            if parsed is None:
                raise ValueError("no data")
            return parsed
        except Exception as e:
            last = e
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
    log.warning("Yahoo 取得失敗: %s (%s)", code, last)
    return None


def fetch_prices(codes: list[str], session: requests.Session | None = None) -> dict[str, dict]:
    """銘柄コード（4桁）ごとの終値・前日比を取得する。

    戻り値: { "4桁コード": {"close": float, "change_pct": float|None, "as_of": "YYYY-MM-DD"}, ... }
    取得失敗・除外銘柄は戻り値に含めない（呼び出し側で「データなし」扱い）。
    """
    session = session or requests.Session()
    session.headers.update(HEADERS)
    out: dict[str, dict] = {}
    for code in codes:
        if code in YAHOO_EXCLUDE:
            continue
        price = _fetch_one(code, session)
        if price is not None:
            out[code] = price
        time.sleep(REQUEST_INTERVAL)
    log.info("Yahoo Finance: %s/%s 銘柄の価格を取得", len(out), len(codes))
    return out
