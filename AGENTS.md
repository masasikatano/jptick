# 東証上場個別株一覧サイト

JPX の「東証上場銘柄一覧」（data_j.xlsx）を銘柄マスタとし、東証プライム・スタンダード・グロースの普通株（約3800銘柄）について [Yahoo Finance](https://finance.yahoo.com/) から価格（終値・前日比・出来高の参考値）を追記して、GitHub Pages で公開する静的サイトです。仕様は [spec.md](spec.md) です。構成は `etp` リポジトリがテンプレート。

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

- **銘柄マスタ**: JPX の東証上場銘柄一覧 xlsx（[統計ページ](https://www.jpx.co.jp/markets/statistics-equities/misc/01.html) から `data_j*.xlsx` の href を動的に抽出してダウンロード。失敗時はリポジトリ内の `data_j.xlsx` をフォールバックとして使う）。1 行目ヘッダ、2 行目〜。列は コード/銘柄名/市場・商品区分/33業種コード/33業種区分/17業種コード/17業種区分/規模コード/規模区分 などをすべて `fields` として保持する。
- **対象銘柄の絞り込み**: 「市場・商品区分」列が「プライム（内国株式）」「スタンダード（内国株式）」「グロース（内国株式）」のものだけ（普通株）。ETF・ETN / REIT・ベンチャーファンド等 / 外国株式 / PRO Market / 出資証券は除外する。コードが4桁数字でない銘柄（例: 130A 等のアルファベットコード）も対象外。
- **価格（主）**: Yahoo Finance の chart API（`query1.finance.yahoo.com/v8/finance/chart/{code}.T?interval=1d&range=5d`）。終値・前日比は close 配列の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算する。出来高は `volume` 配列の最終ポイント（None なら直近の有効値）。リクエスト間隔は 0.1 秒（約3800銘柄で 6〜7分）。取得失敗・除外銘柄（`src/yahoo.py` の `YAHOO_EXCLUDE` で管理）は行を残し「データなし」。
- **価格（フォールバック）**: [J-Quants](https://jquants.com/) の日次バー。Yahoo で取れなかった銘柄だけ埋める。Free 版のため取得ウィンドウは「実行日から 12 週間前〜17 週間前」。ウィンドウの最後の2営業日の close で同様に終値・前日比を算出し、UI 上は Yahoo の値と混在して「参考値（YYYY-MM-DD時点）」と明記する。J-Quants の code は「4桁コード＋市場区分1桁」（例: 7203 → 72030）で返るため、先頭4桁で xlsx のコードと突合する。日次バーは latest.json に保持しない。

API キーは `.env` の `JQUANTS_API_KEY`（git 対象外。JSON・ログに出さないこと）。未設定でもジョブは成功し、Yahoo で取れなかった銘柄の価格は「データなし」になる。Yahoo 側にキーは不要。

## テスト

```bash
pip install -r requirements-dev.txt
pytest -q
```

data_j.xlsx の列マッピング・普通株フィルタ・市場区分の値域、J-Quants ウィンドウ計算、Yahoo の終値・前日比算出、latest.json スキーマを検証する。xlsx の列構成が JPX 側で変わると `tests/test_master.py` が落ちる。

## GitHub Pages

リポジトリ Settings → Pages → **Deploy from a branch** → Branch: `main`、Folder: `/docs`。

GitHub Actions（`.github/workflows/update.yml`）が平日 12:30 UTC（JST 21:30）と `workflow_dispatch` で Yahoo Finance から価格を取り（J-Quants はフォールバック）、JPX ページの xlsx 差分をチェックして `latest.json` を `[skip ci]` 付きで `main` に push します。`JQUANTS_API_KEY` をリポジトリ secret に設定します（未設定でも Yahoo 経由でジョブは成功）。`GITHUB_TOKEN` に `contents: write` が必要です。

## プロジェクト構造

```
src/
  master.py    # JPX data_j.xlsx のダウンロード（href 動的抽出）とパース・普通株フィルタ（銘柄マスタ）
  yahoo.py     # Yahoo Finance 価格取得（主。終値・前日比の自前計算・除外銘柄管理）
  jquants.py   # J-Quants 日次バー取得（Free 版ウィンドウ・ページネーション・リトライ。フォールバック用に終値・前日比を返す）
  update.py    # オーケストレーション（Yahoo → J-Quants フォールバック）→ docs/data/latest.json
docs/
  index.html   # 33業種タブ＋7列シンプルテーブルの一覧。初期表示は前日比%降順、ヘッダクリックで昇順・降順ソート（検索なし）
  common.js    # 共通ユーティリティ
  data/latest.json  # 生成済みスナップショット（git 管理）
data_j.xlsx    # フォールバック用マスタスナップショット（git 管理）
tests/         # pytest 単体テスト
```

## 検証コマンド

```bash
pytest -q
python -m src.update
./run_local.sh --no-serve
```
