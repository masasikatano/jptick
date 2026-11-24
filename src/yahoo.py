"""Yahoo Finance から終値・前日比を取得する（主データソース）。

エンドポイント: https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo
銘柄コードは「4桁コード＋.T」（例: 1306 → 1306.T）。

終値・前日比は close 配列の最後の2点から自前で算出する
（(P_n/P_{n-1}-1)*100。spec.md の定義と一致させるため
meta.regularMarketChangePercent は使わない）。
出来高は indicators.quote の volume 配列から、close と同じ最終ポイントの値を採用する
（最終点が None の場合は直近の有効値にフォールバック）。

avg_volume_20d は当日を含まない直前最大20営業日の出来高の平均
（出来高 null の日は除外。直前の有効値が10営業日分未満なら None）。
rvol は volume / avg_volume_20d（算出不可は None）。

取得失敗した銘柄は戻り値に含めず、呼び出し側で「データなし」扱いとする。
"""

from __future__ import annotations

import logging
import time
from datetime import date

import requests

log = logging.getLogger("yahoo")

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
REQUEST_INTERVAL = 0.1  # リクエスト間の間隔（秒）。約3800銘柄で 6〜7 分
RETRIES = 3

# Yahoo で取得を除外する銘柄コード（必要になったらここに追加）
YAHOO_EXCLUDE: set[str] = set()

HEADERS = {"User-Agent": "Mozilla/5.0"}


def symbol(code: str) -> str:
    return f"{code}.T"


def parse_chart(data: dict) -> dict | None:
    """chart API レスポンスから終値・前日比・出来高・基準日・平均出来高・RVol を算出する。

    close 配列の最後の2点から (P_n/P_{n-1}-1)*100 を計算する。
    出来高は close と同じ最終ポイントの volume を採用し、
    最終点が None の場合は直近の有効値にフォールバックする。
    avg_volume_20d は当日を含まない直前最大20営業日の出来高の平均
    （出来高 null の日は除外。直前の有効値が10営業日分未満なら None）。
    rvol は volume / avg_volume_20d（算出不可は None）。
    取得できない場合は None を返す。
    """
    try:
        result = data["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        closes = quote["close"]
        volumes = quote.get("volume") or []
        timestamps = result["timestamp"]
    except (KeyError, IndexError, TypeError):
        return None
    aligned = [(ts, c, volumes[i] if i < len(volumes) else None)
               for i, (ts, c) in enumerate(zip(timestamps, closes))]
    points = [(ts, c, v) for ts, c, v in aligned if c is not None]
    if not points:
        return None
    last_ts, last_close, _ = points[-1]
    change_pct = None
    if len(points) >= 2:
        prev = points[-2][1]
        if prev:
            change_pct = round((last_close / prev - 1) * 100, 3)
    volume = None
    for _, _, v in reversed(points):
        if v is not None:
            volume = int(v)
            break
    avg_volume_20d = None
    prior = [v for _, _, v in points[:-1] if v is not None][-20:]
    if len(prior) >= 10:
        avg_volume_20d = int(round(sum(prior) / len(prior)))
    rvol = None
    if volume is not None and avg_volume_20d:
        rvol = round(volume / avg_volume_20d, 2)
    return {
        "close": float(last_close),
        "change_pct": change_pct,
        "volume": volume,
        "as_of": date.fromtimestamp(last_ts).isoformat(),
        "avg_volume_20d": avg_volume_20d,
        "rvol": rvol,
    }


def _fetch_one(code: str, session: requests.Session, retries: int = RETRIES) -> dict | None:
    url = CHART_URL.format(symbol=symbol(code))
    delay = 2.0
    last: Exception | None = None
    for attempt in range(retries):
        try:
            res = session.get(url, params={"interval": "1d", "range": "1mo"}, timeout=30)
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

    戻り値: { "4桁コード": {"close": float, "change_pct": float|None, "as_of": "YYYY-MM-DD",
             "avg_volume_20d": int|None, "rvol": float|None}, ... }
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
