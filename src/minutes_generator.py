"""
議事録生成モジュール
補正済み文字起こしからClaudeで議事録を生成する（長時間対応）
"""

import anthropic
from .transcript_corrector import chunk_text
from .cost_tracker import CostTracker


def summarize_chunk(
    client: anthropic.Anthropic,
    chunk: str,
    chunk_num: int,
    total_chunks: int,
    meeting_context: str,
    tracker: CostTracker,
) -> str:
    context_line = f"\n## 会議の背景\n{meeting_context}" if meeting_context else ""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": f"""以下は会議の文字起こし（パート{chunk_num}/{total_chunks}）です。
このパートから以下を箇条書きで抽出してください。{context_line}

## 抽出項目
1. **議題・トピック**：何について話していたか
2. **決定事項**：「〜することになった」「〜で決定」など
3. **アクションアイテム**：誰が何をするか（期限があれば含める）
4. **重要な発言・数字**：重要な意見、数値データ

## 文字起こし
{chunk}

上記4項目を箇条書きで出力してください。""",
            }
        ],
    )
    tracker.add(response)
    return response.content[0].text


def generate_minutes(
    client: anthropic.Anthropic,
    summaries: list[str],
    meeting_context: str,
    tracker: CostTracker,
) -> str:
    combined = "\n\n---\n\n".join(
        [f"【パート{i + 1}】\n{s}" for i, s in enumerate(summaries)]
    )
    context_line = f"\n## 会議の背景\n{meeting_context}\n" if meeting_context else ""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[
            {
                "role": "user",
                "content": f"""あなたは優秀な秘書であり、プロの編集者です。
以下の会議の要点まとめをもとに、議事録を作成してください。
{context_line}

【出力フォーマットに関する厳格なルール】
- Googleドキュメントにコピー＆ペーストしてそのまま使えるよう、Markdown形式で出力してください。
- 見出しの階層は「見出し2（##）」から開始してください。
- 「えー」「あの」などのフィラーや、意味を持たない相槌、重複する発言は削除し、論理的で簡潔な文章にまとめてください。
- 文体は「だ・である調」で統一し、公式な記録としてふさわしい丁寧なトーンに整えてください。
- 誰の発言かが重要な場合は、発言者を明記してください。
- 該当する情報がない項目は省略してください。

【議事録の指定構成】

## 1. 基本情報
- 日時：（文字起こしから読み取れる場合のみ記載）
- 参加者：（発言者名から推定して記載）
- 会議の目的：（--contextの内容または文字起こしから推定）

## 2. 議題と議論の内容
話題が変わるごとに見出し3（###）で区切り、内容を整理する。

### [議題名1]
- 報告・議論内容：

### [議題名2]
- 報告・議論内容：

## 3. 決定事項
この会議で決まったことを箇条書きで簡潔に記述する。

## 4. ネクストアクション（To-Do）
「誰が」「いつまでに」「何を」するかを明確にする。
細かいタスクや準備事項も漏れなく詳細にリストアップすること。

## 5. 次回予定・持ち越し課題
次回のミーティング日程や、今回結論が出ず次回に持ち越した課題などを記載する。

## 6. 備考・要確認事項
（[要確認]とマークされた箇所があれば記載）

---

## 各パートの要点
{combined}
""",
            }
        ],
    )
    tracker.add(response)
    return response.content[0].text


def run_minutes_generation(
    client: anthropic.Anthropic,
    corrected_transcript: str,
    meeting_context: str,
    tracker: CostTracker,
) -> str:
    chunks = chunk_text(corrected_transcript, chunk_size=15000)
    print(f"[議事録] {len(chunks)}チャンクを処理中...")

    summaries = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[議事録] チャンク {i}/{len(chunks)} の要点抽出中...")
        summary = summarize_chunk(client, chunk, i, len(chunks), meeting_context, tracker)
        summaries.append(summary)

    print("[議事録] 最終議事録を生成中...")
    return generate_minutes(client, summaries, meeting_context, tracker)
