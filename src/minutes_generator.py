"""
議事録生成モジュール
補正済み文字起こしからClaudeで議事録を生成する（長時間対応）
"""

import anthropic
from .transcript_corrector import chunk_text


def summarize_chunk(
    client: anthropic.Anthropic,
    chunk: str,
    chunk_num: int,
    total_chunks: int,
    meeting_context: str = "",
) -> str:
    """1チャンクから要点を抽出"""
    context_line = f"\n## 会議の背景\n{meeting_context}" if meeting_context else ""

    response = client.messages.create(
        model="claude-opus-4-6",
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
    return response.content[0].text


def generate_minutes(
    client: anthropic.Anthropic,
    summaries: list[str],
    meeting_context: str = "",
) -> str:
    """各チャンクの要点から最終議事録を生成"""
    combined = "\n\n---\n\n".join(
        [f"【パート{i + 1}】\n{s}" for i, s in enumerate(summaries)]
    )
    context_line = f"\n## 会議の背景\n{meeting_context}\n" if meeting_context else ""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=6000,
        messages=[
            {
                "role": "user",
                "content": f"""以下は会議の各パートの要点まとめです。
これを元に正式な議事録を作成してください。{context_line}

## 各パートの要点
{combined}

## 出力形式（Markdown）

# 議事録

## 基本情報
- 日時：（文字起こしから読み取れる場合のみ記載）
- 参加者：（発言者名から推定）

## 議題一覧
1.
2.

## 議事内容
### [議題1]
（内容）

### [議題2]
（内容）

## 決定事項
-

## アクションアイテム
| 担当者 | 内容 | 期限 |
|--------|------|------|
|        |      |      |

## 次回予定
（記載があれば）

## 備考・要確認事項
（[要確認]とマークされた箇所があれば記載）
""",
            }
        ],
    )
    return response.content[0].text


def run_minutes_generation(
    client: anthropic.Anthropic,
    corrected_transcript: str,
    meeting_context: str = "",
) -> str:
    """
    補正済み文字起こしから議事録を生成
    長時間録音はチャンク分割して処理
    """
    chunks = chunk_text(corrected_transcript, chunk_size=15000)
    print(f"[議事録] {len(chunks)}チャンクを処理中...")

    summaries = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[議事録] チャンク {i}/{len(chunks)} の要点抽出中...")
        summary = summarize_chunk(client, chunk, i, len(chunks), meeting_context)
        summaries.append(summary)

    print("[議事録] 最終議事録を生成中...")
    return generate_minutes(client, summaries, meeting_context)
