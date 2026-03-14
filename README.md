# zoom-minutes

Zoom会議の文字起こし（.vtt）から議事録を自動生成するCLIツールです。

- **長時間対応**：2時間以上の会議もチャンク分割処理で後半欠落なし
- **話者分離対応**：Zoom内蔵文字起こしの話者名をそのまま活用
- **用語集補正**：CSVで管理する用語集を使って専門用語の誤変換を修正
- **Markdown出力**：議題・決定事項・アクションアイテムを構造化して出力

## セットアップ

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# APIキーの設定
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定
```

Anthropic APIキーは https://console.anthropic.com/ で取得できます。

## 使い方

### 基本

```bash
python main.py meeting.vtt
```

### 用語集を指定

```bash
python main.py meeting.vtt --glossary config/glossary.csv
```

### 会議の背景を追加（精度向上）

```bash
python main.py meeting.vtt --context "2024年Q4売上レビュー会議"
```

### 出力ファイル名を指定

```bash
python main.py meeting.vtt --output 2024_q4_review.md
```

### 全オプション

```bash
python main.py meeting.vtt \
  --glossary config/glossary.csv \
  --context "四半期レビュー" \
  --output minutes.md
```

## 用語集の作り方

`config/glossary.csv` を編集（またはコピーして作成）してください。

```csv
誤変換,正しい表記,カテゴリ,備考
くーばねてぃす,Kubernetes,技術用語,
たなかけんじ,田中健二,人名,営業部長
プロジェクトえっくす,Project X,社内用語,
```

- **誤変換**：Zoomが間違えやすい読み方
- **正しい表記**：正しい表記（固有名詞・専門用語など）
- **カテゴリ・備考**：任意（管理用）

## Zoomからのファイル取得方法

1. Zoomのクラウド録画ページを開く
2. 録画を選択 → 「音声文字起こし」をダウンロード（.vtt形式）
3. ダウンロードした `.vtt` ファイルを本ツールに渡す

## 処理の流れ

```
.vttファイル
    ↓ [ステップ1] VTT解析・セグメント化
    ↓ [ステップ2] 用語集CSVを読み込み
    ↓ [ステップ3] Claudeで誤変換補正（チャンク分割処理）
    ↓ [ステップ4] Claudeで議事録生成（チャンク分割処理）
    ↓
議事録.md
```
