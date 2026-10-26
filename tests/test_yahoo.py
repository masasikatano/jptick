"""Yahoo Finance 価格取得のテスト（モック使用）。"""

from datetime import datetime, timezone
from unittest.mock import patch

from src import yahoo

# timestamp: 2026-10-22 / 2026-10-23 (UTC)
TS = [int(datetime(2026, 10, d, tzinfo=timezone.utc).timestamp()) for d in (22, 23)]


def _chart_body(closes, volumes=None):
    return {
        "chart": {
            "result": [{
                "timestamp": TS[:len(closes)],
                "indicators": {"quote": [{"close": closes, "volume": volumes}]},
            }],
        },
    }


def test_parse_chart_calculates_change_pct():
    # close 配列の最後の2点から (P_n/P_{n-1}-1)*100 で自前計算する
    parsed = yahoo.parse_chart(_chart_body([3630.0, 3650.0], [1000, 1200]))
    assert parsed["close"] == 3650.0
    assert abs(parsed["change_pct"] - round((3650.0 / 3630.0 - 1) * 100, 3)) < 1e-9
    assert parsed["volume"] == 1200  # close と同じ最終ポイントの出来高
    assert parsed["as_of"] == "2026-10-23"


def test_parse_chart_volume_fallback_and_missing():
    # 最終点の volume が None の場合は直近の有効値にフォールバック
    parsed = yahoo.parse_chart(_chart_body([3630.0, 3650.0], [1000, None]))
    assert parsed["volume"] == 1000
    # volume 配列自体がない場合は None
    parsed = yahoo.parse_chart(_chart_body([3630.0, 3650.0]))
    assert parsed["volume"] is None


def test_parse_chart_single_point_no_change():
    parsed = yahoo.parse_chart(_chart_body([3650.0]))
    assert parsed["close"] == 3650.0
    assert parsed["change_pct"] is None


def test_parse_chart_no_data():
    assert yahoo.parse_chart({"chart": {"result": []}}) is None
    assert yahoo.parse_chart(_chart_body([None, None])) is None


def test_symbol():
    assert yahoo.symbol("1306") == "1306.T"


@patch("src.yahoo._fetch_one")
def test_fetch_prices_skips_failures(mock_fetch):
    # 取得失敗した銘柄は戻り値に含めず「データなし」扱いにする
    mock_fetch.side_effect = [
        {"close": 3650.0, "change_pct": 0.5, "volume": 1200, "as_of": "2026-10-23"},
        None,
    ]
    out = yahoo.fetch_prices(["1305", "9999"])
    assert out == {"1305": {"close": 3650.0, "change_pct": 0.5, "volume": 1200, "as_of": "2026-10-23"}}


@patch("src.yahoo._fetch_one")
def test_fetch_prices_respects_exclude(mock_fetch):
    yahoo.YAHOO_EXCLUDE.add("9999")
    try:
        out = yahoo.fetch_prices(["9999"])
        assert out == {}
        mock_fetch.assert_not_called()
    finally:
        yahoo.YAHOO_EXCLUDE.discard("9999")
