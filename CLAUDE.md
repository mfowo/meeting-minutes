# meeting-minutes プロジェクト

## 概要
慶應義塾体育会馬術部の会議（Zoom）の文字起こしVTTファイルから議事録MDを自動生成するツール。

## 使い方
```bash
python main.py <VTTファイルパス> [オプション]

# 例
python main.py ~/Downloads/meeting.vtt --context "慶應馬術部 運営ミーティング"
```

出力は `output/` フォルダに保存される。

## プロジェクト構成
- `main.py` — エントリーポイント
- `src/` — 処理モジュール群
- `config/glossary.csv` — 用語集（人名・馬名・専門用語）
- `output/` — 生成された議事録MDの保存先
- `KNOWLEDGE.md` — ノウハウ・フィードバックの蓄積

## 重要なルール
- **用語集を最初に参照すること**。人名・馬名は `config/glossary.csv` に正式表記が登録されている。
- 議事録の修正フィードバックは `KNOWLEDGE.md` に追記して次回に活かす。
- 音声文字起こし特有の誤変換（同音異字、カタカナ揺れ）に注意する。
