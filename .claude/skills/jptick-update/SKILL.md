---
name: jptick-update
description: jptick のデータ更新パイプラインを実行し、結果を検証する（docs/data/latest.json の再生成、pytest、簡易サーバでの確認）。
---

jptick（東証上場個別株一覧サイト）のデータ更新と検証を行う手順です。

## 手順

1. 依存の確認: `.venv` が無ければ `./run_local.sh` が作成する（pip install 済みの前提）。
2. データ更新だけ実行する場合: `./run_local.sh --no-serve`
   - `python -m src.update` が JPX の data_j.xlsx をダウンロード（失敗時はリポジトリ内の `data_j.xlsx` にフォールバック）し、Yahoo Finance から約3800銘柄の価格を取得（6〜7分）→ J-Quants でフォールバック → `docs/data/latest.json` を上書き。
   - `.env` の `JQUANTS_API_KEY` が未設定でも成功する（フォールバック分は「データなし」）。
3. テスト: `pytest -q`（更新前後どちらでも実行可）。
4. 閲覧確認: `./run_local.sh --serve-only` で `http://127.0.0.1:8080/` を配信し、ブラウザで一覧が描画されることを確認。

## 注意

- `docs/data/latest.json` は git 管理対象。更新結果を git に含めるかはユーザーに確認する。
- `.env`（API キー）を読み書き・表示しない。
- Yahoo 取得はリクエスト間隔 0.1 秒あり、完了まで time out させないこと（バックグラウンド推奨）。
