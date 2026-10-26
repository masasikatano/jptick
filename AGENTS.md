# 東証上場個別株一覧サイト（改造中）

JPX の上場銘柄一覧（プライム/スタンダード/グロースの普通株）を銘柄マスタとし、Yahoo Finance から価格（終値・前日比・出来高の参考値）を追記して
GitHub Pages で公開する静的サイトです。仕様は [spec.md](spec.md) です。構成は `etp` リポジトリがテンプレート。

**注意**: 以下の内容は etp からのコピーのままで、個別株版への改造（master.py の個別株用パース、33業種タブへの変更など）は未着手です。

## 動かし方

```bash
./run_local.sh
```

venv 作成、依存インストール、`python -m src.update`、`docs/` の簡易サーバ（既定 8080）まで一気にやります。`docs/data/latest.json` が上書きされます。ブラウザで `http://127.0.0.1:8080/` を開きます。

```bash
./run_local.sh --no-serve    # JSON 更新だけ
./run_local.sh --serve-only  # 既存 latest.json を配信するだけ
PORT=9000 ./run_local.sh
```

## データソース

- **銘柄マスタ**: JPX の ETF データベース xlsx（[投資家向けページ](https://www.jpx.co.jp/equities/products/etfs/investors/index.html) から href を動的に抽出してダウンロード。失敗時はリポジトリ内の `nlsgeu000000vx9t.xlsx` をフォールバックとして使う）。1 行目タイトル、4 行目ヘッダ（B 列「コード」始まり、A 列は空白列）、5 行目〜が 454 銘柄。約 40 列をすべて保持する。
- **価格（主）**: Yahoo Finance の chart API（`query1.finance.yahoo.com/v8/finance/chart/{code}.T?interval=1d&range=5d`）。終値・前日比は close 配列の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算する。出来高は `volume` 配列の最終ポイント（None なら直近の有効値）。取得失敗・除外銘柄（`src/yahoo.py` の `YAHOO_EXCLUDE` で管理）は行を残し「データなし」。
- **価格（フォールバック）**: [J-Quants](https://jquants.com/) の日次バー。Yahoo で取れなかった銘柄だけ埋める。Free 版のため取得ウィンドウは「実行日から 12 週間前〜17 週間前」。ウィンドウの最後の2営業日の close で同様に終値・前日比を算出し、UI 上は Yahoo の値と混在して「参考値（YYYY-MM-DD時点）」と明記する。J-Quants の code は「4桁コード＋市場区分1桁」（例: 1301 → 13010）で返るため、先頭4桁で xlsx のコードと突合する。日次バーは latest.json に保持しない。

API キーは `.env` の `JQUANTS_API_KEY`（git 対象外。JSON・ログに出さないこと）。未設定でもジョブは成功し、Yahoo で取れなかった銘柄の価格は「データなし」になる。Yahoo 側にキーは不要。

## テスト

```bash
pip install -r requirements-dev.txt
pytest -q
```

xlsx 列マッピング（1305「iFreeETF TOPIX」行など）、J-Quants ウィンドウ計算、Yahoo の終値・前日比算出、latest.json スキーマを検証する。xlsx の列構成が JPX 側で変わると `tests/test_master.py` が落ちる。

## GitHub Pages

リポジトリ Settings → Pages → **Deploy from a branch** → Branch: `main`、Folder: `/docs`。

GitHub Actions（`.github/workflows/update.yml`）が平日 12:30 UTC（JST 21:30）と `workflow_dispatch` で Yahoo Finance から価格を取り（J-Quants はフォールバック）、JPX ページの xlsx 差分をチェックして `latest.json` を `[skip ci]` 付きで `main` に push します。`JQUANTS_API_KEY` をリポジトリ secret に設定します（未設定でも Yahoo 経由でジョブは成功）。`GITHUB_TOKEN` に `contents: write` が必要です。

## プロジェクト構造

```
src/
  master.py    # JPX xlsx のダウンロード（href 動的抽出）とパース（銘柄マスタ）
  yahoo.py     # Yahoo Finance 価格取得（主。終値・前日比の自前計算・除外銘柄管理）
  jquants.py   # J-Quants 日次バー取得（Free 版ウィンドウ・ページネーション・リトライ。フォールバック用に終値・前日比を返す）
  update.py    # オーケストレーション（Yahoo → J-Quants フォールバック）→ docs/data/latest.json
docs/
  index.html   # カテゴリタブ（12）＋シンプルテーブルの一覧。検索・ソートなし
  common.js    # 共通ユーティリティ
  data/latest.json  # 生成済みスナップショット（git 管理）
tests/         # pytest 単体テスト
```

## 検証コマンド

```bash
pytest -q
python -m src.update
./run_local.sh --no-serve
```
