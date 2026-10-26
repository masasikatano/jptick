"""JPX 上場銘柄マスタ + Yahoo Finance 価格（J-Quants フォールバック）をまとめて docs/data/latest.json に書き出す。"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src import jquants, master, yahoo

log = logging.getLogger("update")
ROOT = Path(__file__).resolve().parents[1]
JST = ZoneInfo("Asia/Tokyo")


def load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


def build_payload(records: list[dict], prices: dict[str, dict]) -> dict:
    """prices: { "4桁コード": {"close", "change_pct", "volume", "as_of"} }。取得失敗銘柄はキーなし。"""

    items: list[dict] = []
    as_of_dates: list[str] = []
    for rec in records:
        price = prices.get(rec["code"])
        item = {
            "code": rec["code"],
            "code5": rec["code"].zfill(5),
            "name": rec["name"],
            "market": rec["market"],
            "industry": rec["industry"],
            "fields": rec["fields"],
            "price": price,
        }
        if price is not None:
            as_of_dates.append(price["as_of"])
        items.append(item)

    # 業種タブは銘柄数順
    counts: dict[str, int] = {}
    for it in items:
        counts[it["industry"]] = counts.get(it["industry"], 0) + 1
    categories = [
        {"id": ind, "title": ind, "count": n}
        for ind, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    ref_date = max(as_of_dates) if as_of_dates else None
    with_price = sum(1 for it in items if it["price"] is not None)
    return {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "timezone": "Asia/Tokyo",
        "source": "jpx_listed_companies+yahoo_finance(+jquants fallback)",
        "reference": True,
        "reference_date": ref_date,
        "reference_note": f"参考値（{ref_date}時点）" if ref_date else "参考値（データなし）",
        "categories": categories,
        "count": len(items),
        "with_price_count": with_price,
        "items": items,
    }


def run() -> dict:
    load_dotenv()
    records = master.load_master()
    codes = [rec["code"] for rec in records]
    prices = yahoo.fetch_prices(codes)
    # Yahoo で取得できなかった銘柄は J-Quants のウィンドウ内終値で埋める（データなしは行を残す）
    missing = [c for c in codes if c not in prices]
    if missing:
        log.info("Yahoo 未取得 %s 銘柄を J-Quants でフォールバック", len(missing))
        for code, price in jquants.fetch_prices(codes=missing).items():
            if code in missing:
                prices.setdefault(code, price)
    return build_payload(records, prices)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    payload = run()
    out = ROOT / "docs" / "data" / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=None, separators=(",", ":")), encoding="utf-8")
    log.info("wrote %s items=%s with_price=%s ref=%s",
             out, payload["count"], payload["with_price_count"], payload["reference_date"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
