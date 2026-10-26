"""data_j.xlsx 列マッピング・普通株フィルタの回帰テスト（xlsx 列構成が変わった場合に検知する）。"""

import pytest

from src.master import FALLBACK_XLSX, load_master, normalize_header


@pytest.fixture(scope="module")
def records():
    assert FALLBACK_XLSX.is_file(), "テスト用のローカル xlsx（data_j.xlsx）が必要"
    return load_master(path=FALLBACK_XLSX)


def test_record_count(records):
    # 東証プライム・スタンダード・グロースの普通株は約3800銘柄
    assert 3500 <= len(records) <= 4200


def test_only_target_markets(records):
    markets = {r["market"] for r in records}
    assert markets == {"プライム", "スタンダード", "グロース"}
    # ETF/REIT/外国株/PRO Market は除外されていること
    for rec in records:
        assert rec["fields"]["市場・商品区分"] in (
            "プライム（内国株式）", "スタンダード（内国株式）", "グロース（内国株式）")


def test_7203_toyota(records):
    rec = next(r for r in records if r["code"] == "7203")
    assert "トヨタ" in rec["name"]
    assert rec["market"] == "プライム"
    assert rec["industry"] == "輸送用機器"
    f = rec["fields"]
    # 4 桁コード → 5 桁ゼロ埋めで J-Quants 側と突合
    assert rec["code"].zfill(5) == "07203"
    assert f["33業種区分"] == "輸送用機器"
    assert f["17業種区分"] == "自動車・輸送機"
    assert f["規模区分"].startswith("TOPIX")


def test_industries_are_33(records):
    # JPX の33業種区分が全部入っていること（欠けている業種があってもよいが、
    # 業種名は33業種区分の値域に含まれること）
    industries = {r["industry"] for r in records}
    assert len(industries) >= 30
    assert "" not in industries
    for rec in records:
        assert rec["industry"]


def test_all_fields_present(records):
    for rec in records:
        assert "コード" in rec["fields"]
        assert "銘柄名" in rec["fields"]
        assert "市場・商品区分" in rec["fields"]
        assert "33業種区分" in rec["fields"]
        assert len(rec["fields"]) >= 8, f"{rec['code']}: 列が不足"


def test_normalize_header():
    assert normalize_header("市場・商品\n区分") == "市場・商品区分"
    assert normalize_header("33業種区分") == "33業種区分"
