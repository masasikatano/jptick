"""xlsx 列マッピングの回帰テスト（xlsx 列構成が変わった場合に検知する）。"""

import pytest

from src.master import FALLBACK_XLSX, load_master, normalize_header


@pytest.fixture(scope="module")
def records():
    assert FALLBACK_XLSX.is_file(), "テスト用のローカル xlsx が必要"
    return load_master(path=FALLBACK_XLSX)


def test_record_count(records):
    assert len(records) == 454


def test_categories(records):
    cats = {r["category"] for r in records}
    assert len(cats) == 12


def test_1305_ifreetf_topix(records):
    rec = next(r for r in records if r["code"] == "1305")
    assert "iFreeETF TOPIX" in rec["name"]
    assert rec["category"] == "日本株（市場別）"
    f = rec["fields"]
    assert f["略称"] == "ｉＦＴＰＸ年１"
    assert f["管理会社"] == "大和アセットマネジメント"
    # 4 桁コード → 5 桁ゼロ埋めで J-Quants 側と突合
    assert rec["code"].zfill(5) == "01305"
    # 費用・スケジュール列が読めていること
    assert f["総経費率（年率・税込）"] is not None
    assert f["設定スケジュール【ETF設定に係る債務引受対象である場合】"] in ("T+2", "T+1", "T+3")
    assert f["PCF掲載URL(日本語)"].startswith("http")


def test_all_fields_present(records):
    for rec in records:
        assert "コード" in rec["fields"]
        assert "名称" in rec["fields"]
        assert "カテゴリー" in rec["fields"]
        assert len(rec["fields"]) >= 40, f"{rec['code']}: 列が不足"


def test_normalize_header():
    assert normalize_header("売買単位\n(口)") == "売買単位(口)"
    assert normalize_header("PCF掲載URL\n(日本語)") == "PCF掲載URL(日本語)"
