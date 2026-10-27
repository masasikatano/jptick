# 東証上場個別株一覧サイト 仕様

東証上場個別株（プライム/スタンダード/グロースの普通株）の業種別一覧を GitHub Pages で公開し、GitHub Actions で定期自動更新する静的サイト。構成は `/home/masasikatano/project/etp/` をテンプレートにする。

## 決定事項（grilling による合意）

1. **データソース**
   - JPX の「上場銘柄一覧」系 xls/xlsx を正（master）とする。GitHub Actions で定期ダウンロードし差し替える。
   - マスタファイルの href はページ依存のため、更新時は JPX の該当ページを取得して `.xls`/`.xlsx` の href を動的に抽出する。ハードコードしない。ダウンロード失敗時はリポジトリ内のフォールバックファイルを使う。
   - **対象は東証プライム・スタンダード・グロースの普通株のみ**（約3800銘柄）。ETF/REIT/優先株式/投資証券/外国株等は除外する。除外判定はマスタの市場区分・証券種別列で行う。
   - **価格は Yahoo Finance（主）と J-Quants（フォールバック）**。
     - Yahoo: `query1.finance.yahoo.com/v8/finance/chart/{4桁コード}.T?interval=1d&range=5d`。終値・前日比は close 配列の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算する（`meta.regularMarketChangePercent` は使わない）。リクエスト間隔は 0.1 秒（約3800銘柄で 6〜7分）。
     - J-Quants: Yahoo で取得失敗した銘柄のみ、日次バーのウィンドウ（Free 版は「12週間前〜17週間前」）の最後の2営業日の close で同様に算出して埋める。日次バー全体は latest.json に保持しない。
   - 恒常的に Yahoo から取得失敗する銘柄は `src/yahoo.py` の `YAHOO_EXCLUDE` で管理し、Yahoo リクエストを省いて J-Quants フォールバックで埋める。

2. **更新スケジュール**
   - 日次1回。平日 10:12 UTC（JST 19:12）と `workflow_dispatch` で Actions を回し、(a) Yahoo Finance から価格取得（J-Quants フォールバック）、(b) マスタ xls の差分チェック＆差し替え。
   - `[skip ci]` 付きで main に push（etp 同様）。

3. **詳細ページ**
   - **詳細ページは作らない**（etp と同じく一覧テーブルのみ）。マスタの全列は `fields` として latest.json に保持するが表示はしない（将来の復活に備えデータは残す）。

4. **データファイル構成**
   - 単一 `docs/data/latest.json`。銘柄マスタ（全列）＋ 各銘柄の価格 `{ close, change_pct, as_of }` の最小形。日次バーは含めない。サイズは 1〜2MB 想定。

5. **一覧ページ機能**
   - 業種タブ（JPX 33業種区分そのまま）のみのシンプル一覧。検索・ソートはつけない（etp 同型）。
   - 表示列は コード / 銘柄名 / 市場区分（プライム/スタンダード/グロース） / 業種 / 終値 / 前日比 / 出来高 の7列。
   - 価格はサイトの免責表現として「参考値（YYYY-MM-DD時点）」と必ず明記する（Yahoo の最新終値も含めて）。
   - 業種タブは銘柄数順（または五十音順）で並べる。1タブ最大でも約300銘柄程度になりうる。

6. **構成・技術**
   - etp 同型の独立リポジトリ（tick/ を git init 済み）。etp から src/・tests/・docs/・run_local.sh・requirements*.txt・.github/workflows/update.yml・AGENTS.md・.gitignore をコピーして改造する。
   - Pages: branch `main` の `/docs`。バニラ JS（index.html / common.js）、Python パイプライン（`python -m src.update`）、pytest、run_local.sh。
   - 改造の要点:
     - `src/master.py`: JPX の上場銘柄一覧ファイルの取得・パース。ETF xlsx 用の列マッピングを個別株用に差し替え、普通株のみにフィルタ。
     - `docs/index.html`: カテゴリタブを33業種に変更。7列テーブル。
     - `src/yahoo.py` / `src/jquants.py`: 価格ロジックはほぼ流用（終値・前日比の自前計算・フォールバック・除外管理）。
     - `tests/`: マスタファイルの列マッピング・フィルタ条件・価格算出・latest.json スキーマを検証。

7. **価格データソースの扱い（重要）**
   - Yahoo Finance を主とし、取得失敗した銘柄は J-Quants でフォールバックする。それも失敗・未対象銘柄は行を残し「データなし」表示（etp 同方針）。
   - Yahoo は銘柄コードに `.T` を付与（例: 7203 → 7203.T）。銘柄ごとの除外が必要な場合は `src/yahoo.py` の `YAHOO_EXCLUDE` で管理する。
   - 終値・前日比はいずれのソースでも close の最後の2点から自前計算する（前日比% = (P_n/P_{n-1}-1)*100）。Yahoo の `meta.regularMarketChangePercent` は使わない。
   - 出来高は終値と同じ基準日のものを使う（Yahoo は `indicators.quote.volume` の最終ポイント、J-Quants は最終営業日の `Volume`）。取得できなければ `volume: null` で表示は「—」。
   - J-Quants の code は5桁（例: 72030）、マスタは4桁（7203）→ 先頭4桁で突合。
   - J-Quants APIキーはリポジトリ secret（`JQUANTS_API_KEY`）か `.env`。ログ・JSON に出さない。未設定でもジョブは成功（その場合フォールバックは「データなし」）。
   - J-Quants Free版の取得ウィンドウは「12週間前〜17週間前」の固定オフセット。フォールバックで埋めた銘柄はこの期間の過去値になる。
   - 有料プランに戻した場合は `src/jquants.py` のウィンドウ計算を差し替えるだけで最新値表示に切替可能な構造にする。

## 残リスク・注意

- Yahoo Finance のレート制限・レスポンス変更（約3800銘柄・数千リクエスト規模で顕在化しやすい。リトライ＋リクエスト間隔 0.1 秒で対処。恒常失敗銘柄は `YAHOO_EXCLUDE`）。
- J-Quants Free版のレート制限（フォールバックは Yahoo の失敗銘柄のみに絞る。リトライ＋バックオフ）。
- JPX の上場銘柄一覧ファイルの列構成・除外対象の区分変更（列名マッピングのテストで防ぐ）。
- 約3800銘柄のブラウザ描画・latest.json サイズ（1〜2MB 想定。問題になったら業種ごと分割を検討）。
