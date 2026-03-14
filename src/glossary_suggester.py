"""
用語集追加提案モジュール
議事録生成後に用語集への追加候補をClaudeで抽出し、ユーザーに確認する
"""

import json
import anthropic
from .glossary_loader import append_to_csv, format_for_prompt
from .cost_tracker import CostTracker


def extract_new_terms(
    client: anthropic.Anthropic,
    transcript: str,
    existing_entries: list[dict],
    tracker: CostTracker,
) -> list[dict]:
    existing_text = format_for_prompt(existing_entries)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": f"""以下の会議の文字起こしを分析して、用語集に追加すべき新規用語を抽出してください。

## 既存の用語集
{existing_text}

## 抽出対象
- 人名（複数の呼称・読み方で登場しているもの）
- 組織名・会社名
- 技術用語・専門用語・馬術用語
- 社内用語・プロジェクト名
- 馬の名前

## 除外基準
- 既存の用語集に登録済みのもの
- 一般的な日本語の名詞
- 1回しか登場せず重要性が低いと判断されるもの

## 出力形式（JSON配列）
[
  {{
    "official": "正式名称",
    "aliases": ["別名1", "読み方1"],
    "category": "人名_慶應 or 人名_連盟 or 馬名 or 馬術用語 or 組織名 or その他",
    "note": "役職・関係性など補足（なければ空文字）",
    "reason": "追加を提案する理由（1行）"
  }}
]

JSON配列のみ出力してください（説明不要）。

## 文字起こし
{transcript[:8000]}
""",
            }
        ],
    )
    tracker.add(response)

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def prompt_user_selection(candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    print("\n" + "─" * 50)
    print("📋 用語集への追加候補")
    print("─" * 50)

    for i, entry in enumerate(candidates, 1):
        aliases = " / ".join(entry.get("aliases", []))
        note = f"  ※{entry['note']}" if entry.get("note") else ""
        reason = entry.get("reason", "")
        print(f"  {i}. {entry['official']}（{aliases}）[{entry['category']}]{note}")
        if reason:
            print(f"     → {reason}")

    print("─" * 50)
    print("追加する番号を入力してください")
    print("  y = すべて追加 / n = スキップ / 1,3,5 = 個別選択")

    while True:
        answer = input("> ").strip().lower()
        if answer == "y":
            return candidates
        elif answer == "n":
            return []
        else:
            try:
                indices = [int(x.strip()) - 1 for x in answer.split(",")]
                selected = [candidates[i] for i in indices if 0 <= i < len(candidates)]
                return selected
            except (ValueError, IndexError):
                print("入力が正しくありません。y / n / 番号(カンマ区切り) で入力してください。")


def suggest_and_update_glossary(
    client: anthropic.Anthropic,
    transcript: str,
    existing_entries: list[dict],
    glossary_path: str,
    tracker: CostTracker,
) -> None:
    print("\n[用語集] 追加候補を抽出中...")
    candidates = extract_new_terms(client, transcript, existing_entries, tracker)

    if not candidates:
        print("[用語集] 追加候補は見つかりませんでした。")
        return

    selected = prompt_user_selection(candidates)

    if selected:
        append_to_csv(glossary_path, selected)
    else:
        print("[用語集] 追加をスキップしました。")
