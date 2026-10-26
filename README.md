# 東証上場ETF一覧サイト

[JPX（日本取引所グループ）のETFデータベース](https://www.jpx.co.jp/equities/products/etfs/investors/index.html) を銘柄マスタとし、[Yahoo Finance](https://finance.yahoo.com/) から価格（参考値）を追記して、GitHub Pages で公開する東証上場ETFの一覧サイトです。

カテゴリ別の一覧（12カテゴリ・約450銘柄）を見られます。GitHub Actions が平日自動更新します。

## 使い方（閲覧）

GitHub Pages の URL（リポジトリの Settings → Pages で有効化後）をブラウザで開くだけです。トップページでカテゴリタブを選んで一覧を閲覧します。

ローカルで見る場合:

```bash
./run_local.sh          # http://127.0.0.1:8080/ で閲覧
./run_local.sh --no-serve    # データ更新だけ
./run_local.sh --serve-only  # 既存データを配信するだけ
```

## データについて

- **銘柄マスタ**: JPX の ETF データベース xlsx。更新時は投資家向けページからダウンロードリンクを動的に抽出。新規上場・上場廃止にも追従します。
- **価格（主）**: Yahoo Finance の chart API（`{コード}.T`）。終値・前日比は close の最後の2点から自前計算します。
- **価格（フォールバック）**: [J-Quants](https://jquants.com/) の日次バー。Yahoo で取得できない銘柄に限り、Free 版の取得可能ウィンドウ「12週間前〜17週間前」の最後の2営業日で同様に算出して埋めます。フォールバック値は過去時点のものです。いずれの値もサイトの免責表現として **参考値（YYYY-MM-DD時点）** と表示されます。有料プランに変更すればフォールバックも最新値になります（`src/jquants.py` の `window()` を差し替え）。
- 価格が取得できない銘柄は「データなし」と表示し、行は残ります。

## 自分の環境で更新パイプラインを動かす

1. `.env` に `JQUANTS_API_KEY=...` を記載（git 管理外。Yahoo のフォールバック用で必須ではない）。
2. `./run_local.sh --no-serve` で `docs/data/latest.json` を再生成。

```bash
pip install -r requirements-dev.txt
pytest -q               # テスト
python -m src.update    # データ更新
```

## GitHub Pages ＋ 自動更新の設定

1. GitHub にリポジトリを push。
2. Settings → Pages → **Deploy from a branch** → Branch: `main`、Folder: `/docs`。
3. Settings → Secrets and variables → Actions に `JQUANTS_API_KEY` を登録。
4. `.github/workflows/update.yml` が平日 21:30 JST と手動実行（`workflow_dispatch`）でデータを更新し、`[skip ci]` 付きで `main` に push します。API キー未設定でも Yahoo 経由でジョブ自体は成功します（J-Quants フォールバック分のみ「データなし」）。

## プロジェクト構造

```
src/
  master.py    # JPX xlsx のダウンロード・パース（銘柄マスタ）
  yahoo.py     # Yahoo Finance 価格取得（主データソース）
  jquants.py   # J-Quants 日次バー取得（Yahoo 失敗時のフォールバック）
  update.py    # 統合 → docs/data/latest.json
docs/
  index.html   # カテゴリタブ＋一覧テーブル
  common.js
  data/latest.json
tests/         # pytest 単体テスト
spec.md        # 仕様（設計の決定事項）
AGENTS.md      # 開発者向けガイドライン
```

詳しい仕様は [spec.md](spec.md)、開発・運用の詳細は [AGENTS.md](AGENTS.md) を参照してください。
