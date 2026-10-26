"""latest.json スキーマのテスト。"""

from src.update import build_payload

RECORDS = [
    {"code": "7203", "name": "トヨタ自動車", "market": "プライム", "industry": "輸送用機器",
     "fields": {"コード": 7203, "銘柄名": "トヨタ自動車", "市場・商品区分": "プライム（内国株式）"}},
    {"code": "6758", "name": "ソニーグループ", "market": "プライム", "industry": "電気機器",
     "fields": {"コード": 6758, "銘柄名": "ソニーグループ"}},
    {"code": "9999", "name": "取得対象外銘柄", "market": "グロース", "industry": "情報・通信業",
     "fields": {"コード": 9999, "銘柄名": "取得対象外銘柄"}},
]

# 価格は「4桁コード → {close, change_pct, volume, as_of}」の最小形
PRICES = {
    "7203": {"close": 3630.0, "change_pct": round((3630.0 / 3650.0 - 1) * 100, 3),
             "volume": 1200, "as_of": "2026-10-23"},
}


def test_schema():
    p = build_payload(RECORDS, PRICES)
    assert p["reference"] is True
    assert p["count"] == 3
    by_code = {i["code"]: i for i in p["items"]}
    toyota = by_code["7203"]
    assert toyota["market"] == "プライム"
    assert toyota["industry"] == "輸送用機器"
    assert toyota["price"]["close"] == 3630.0
    assert toyota["price"]["volume"] == 1200
    assert toyota["price"]["as_of"] == "2026-10-23"
    assert abs(toyota["price"]["change_pct"] - round((3630.0 / 3650.0 - 1) * 100, 3)) < 1e-9
    # 日次バーは latest.json に含めない
    assert "bars" not in toyota
    # 未対象銘柄は行を残し price=None
    miss = by_code["9999"]
    assert miss["price"] is None
    # 業種タブ集計（銘柄数順）
    cats = [(c["id"], c["count"]) for c in p["categories"]]
    assert dict(cats)["輸送用機器"] == 1
    assert dict(cats)["情報・通信業"] == 1
    counts = [n for _, n in cats]
    assert counts == sorted(counts, reverse=True)
    assert p["reference_date"] == "2026-10-23"
    assert "2026-10-23" in p["reference_note"]
    # 個別株版では sections（詳細ページ用）は持たない
    assert "sections" not in p


def test_no_prices():
    p = build_payload(RECORDS, {})
    assert p["with_price_count"] == 0
    assert all(i["price"] is None for i in p["items"])
    assert p["reference_date"] is None
