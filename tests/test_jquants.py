"""J-Quants Free 版の取得ウィンドウ計算テスト。"""

from datetime import date

from src import jquants
from src.jquants import window


def test_window_is_fixed_offset():
    today = date(2026, 10, 24)
    frm, to = window(today)
    assert to == date(2026, 8, 1)    # 12 週間前
    assert frm == date(2026, 6, 27)  # 17 週間前
    assert (to - frm).days == 7 * 5  # 約 5 週間（約 25 営業日分）


def test_window_roughly_25_business_days():
    frm, to = window(date(2026, 1, 1))
    assert frm < to
    assert 20 <= (to - frm).days <= 40


def test_fetch_prices_uses_last_two_business_days(monkeypatch):
    """fetch_prices はウィンドウの最後の2営業日の close から終値・前日比を算出する。"""
    bars = {
        "13050": {"t": ["2026-07-28", "2026-07-29", "2026-07-30"],
                  "v": [3600.0, 3650.0, 3630.0], "vol": [800, 1000, 1200]},
        "99990": {"t": ["2026-07-30"], "v": [100.0], "vol": [50]},
    }
    monkeypatch.setattr("src.jquants.fetch_bars", lambda **kwargs: bars)
    prices = jquants.fetch_prices()
    etf = prices["1305"]  # J-Quants の5桁コードは先頭4桁で突合
    assert etf["close"] == 3630.0
    assert etf["volume"] == 1200  # 最終営業日の出来高
    assert etf["as_of"] == "2026-07-30"
    assert abs(etf["change_pct"] - round((3630.0 / 3650.0 - 1) * 100, 3)) < 1e-9
    # 1点しかない銘柄は change_pct=None
    assert prices["9999"]["close"] == 100.0
    assert prices["9999"]["volume"] == 50
    assert prices["9999"]["change_pct"] is None


def test_fetch_prices_volume_none(monkeypatch):
    """Volume が欠けている場合は volume=None で返す。"""
    bars = {"13050": {"t": ["2026-07-30"], "v": [3630.0], "vol": [None]}}
    monkeypatch.setattr("src.jquants.fetch_bars", lambda **kwargs: bars)
    prices = jquants.fetch_prices()
    assert prices["1305"]["volume"] is None


def test_fetch_prices_filters_codes_and_no_key(monkeypatch):
    bars = {"13050": {"t": ["2026-07-29", "2026-07-30"], "v": [3650.0, 3630.0], "vol": [900, 800]}}
    monkeypatch.setattr("src.jquants.fetch_bars", lambda **kwargs: bars)
    prices = jquants.fetch_prices(codes=["1305"])
    assert list(prices) == ["1305"]
    # API キー未設定（fetch_bars が空を返す）場合は空 dict
    monkeypatch.setattr("src.jquants.fetch_bars", lambda **kwargs: {})
    assert jquants.fetch_prices() == {}


def test_fetch_bars_days_limits_requests(monkeypatch):
    """days=2 の場合はウィンドウ末尾の営業日2日分だけリクエストする。"""
    monkeypatch.setattr("src.jquants.api_key", lambda: "dummy")
    requested: list[str] = []

    def fake_get(url, headers, params, retries=6):
        requested.append(params.get("date", ""))
        return {"data": []}

    monkeypatch.setattr("src.jquants._get_with_retry", fake_get)
    monkeypatch.setattr("src.jquants.time.sleep", lambda s: None)
    jquants.fetch_bars(today=date(2026, 10, 24), days=2)
    assert len(requested) == 2
    assert requested[0] < requested[1]  # ウィンドウ末尾の2営業日
