"""latest.json スキーマのテスト。"""

from src.update import build_payload

RECORDS = [
    {"code": "1305", "name": "iFreeETF TOPIX", "category": "日本株（市場別）",
     "fields": {"コード": 1305, "名称": "iFreeETF TOPIX", "カテゴリー": "日本株（市場別）"}},
    {"code": "2557", "name": "MAXIS 米国株式", "category": "外国株",
     "fields": {"コード": 2557, "名称": "MAXIS 米国株式", "カテゴリー": "外国株"}},
    {"code": "9999", "name": "取得対象外銘柄", "category": "外国株",
     "fields": {"コード": 9999, "名称": "取得対象外銘柄"}},
]

# 価格は「4桁コード → {close, change_pct, volume, as_of}」の最小形
PRICES = {
    "1305": {"close": 3630.0, "change_pct": round((3630.0 / 3650.0 - 1) * 100, 3),
             "volume": 1200, "as_of": "2026-10-23"},
}


def test_schema():
    p = build_payload(RECORDS, PRICES)
    assert p["reference"] is True
    assert p["count"] == 3
    by_code = {i["code"]: i for i in p["items"]}
    etf = by_code["1305"]
    assert etf["price"]["close"] == 3630.0
    assert etf["price"]["volume"] == 1200
    assert etf["price"]["as_of"] == "2026-10-23"
    assert abs(etf["price"]["change_pct"] - round((3630.0 / 3650.0 - 1) * 100, 3)) < 1e-9
    # 日次バーは latest.json に含めない
    assert "bars" not in etf
    assert "ref_close" not in etf and "ref_chg_pct" not in etf and "ref_date" not in etf
    # 未対象銘柄は行を残し price=None
    miss = by_code["9999"]
    assert miss["price"] is None
    # カテゴリ集計
    cats = {c["id"]: c["count"] for c in p["categories"]}
    assert cats["外国株"] == 2
    assert cats["日本株（市場別）"] == 1
    assert p["reference_date"] == "2026-10-23"
    assert "2026-10-23" in p["reference_note"]
    assert len(p["sections"]) >= 5


def test_no_prices():
    p = build_payload(RECORDS, {})
    assert p["with_price_count"] == 0
    assert all(i["price"] is None for i in p["items"])
    assert p["reference_date"] is None
