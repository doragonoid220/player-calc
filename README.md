# 選手能力 自動計算アプリ Streamlit版

スマホから画像をアップロードし、Geminiで能力・スキルを読み取り、条件を選んで最終能力を計算するアプリです。

## ファイル
- app.py
- requirements.txt
- .streamlit/secrets.toml サンプル

## Streamlit Cloudで使う流れ
1. GitHubで新規リポジトリを作る
2. app.py と requirements.txt をアップロード
3. Streamlit Community Cloudでそのリポジトリを指定
4. Settings > Secrets に以下を登録

```toml
GEMINI_API_KEY = "自分のGemini APIキー"
```

5. Deploy

## 使い方
1. 能力画面・スキル画面・エディション画面の画像をアップロード
2. 「AIで読み取り」を押す
3. 読み取り結果を必要に応じて修正
4. 条件を選ぶ
5. 「現在の選手を比較表に追加」を押す

## 注意
ゲーム画像は文字が小さいため、AI読み取りはミスることがあります。必ず確認・修正してから使ってください。
