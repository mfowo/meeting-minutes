"""
用語集ローダー
CSVファイルから用語集を読み込む
"""

import csv
from pathlib import Path

def _parse_rows(reader) -> list[dict]:
    """CSV行をパースして用語エントリのリストを返す"""
    entries = []
    for row in reader:
        official = row.get("正式名称", "").strip()
        aliases_raw = row.get("別名・呼び方", "").strip()
        mistrans_raw = row.get("誤変換例", "").strip()
        category = row.get("カテゴリ", "").strip()
        note = row.get("備考", "").strip()

        if not official:
            continue

        aliases = [a.strip() for a in aliases_raw.split("/") if a.strip()]
        mistranscriptions = [m.strip() for m in mistrans_raw.split("/") if m.strip()]

        entries.append({
            "official": official,
            "aliases": aliases,
            "mistranscriptions": mistranscriptions,
            "category": category,
            "note": note,
        })
    return entries


def load_from_csv(csv_path: str) -> list[dict]:
    """CSVファイルから用語集を読み込む"""
    path = Path(csv_path)
    if not path.exists():
        print(f"[警告] 用語集ファイルが見つかりません: {csv_path}")
        return []

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        entries = _parse_rows(reader)

    print(f"[用語集] {len(entries)}件読み込み: {csv_path}")
    return entries


def append_to_csv(csv_path: str, new_entries: list[dict]) -> None:
    """新しい用語をCSVに追記する"""
    path = Path(csv_path)
    write_header = not path.exists()

    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["正式名称", "別名・呼び方", "誤変換例", "カテゴリ", "備考"]
        )
        if write_header:
            writer.writeheader()
        for entry in new_entries:
            writer.writerow({
                "正式名称": entry.get("official", ""),
                "別名・呼び方": " / ".join(entry.get("aliases", [])),
                "誤変換例": " / ".join(entry.get("mistranscriptions", [])),
                "カテゴリ": entry.get("category", ""),
                "備考": entry.get("note", ""),
            })

    print(f"[用語集] {len(new_entries)}件追記しました: {csv_path}")


def format_for_prompt(entries: list[dict]) -> str:
    """用語集をClaudeへのプロンプト用テキストに変換（カテゴリ別に整理）"""
    if not entries:
        return "（用語集なし）"

    # カテゴリ別にグループ化
    by_category: dict[str, list[dict]] = {}
    for e in entries:
        cat = e["category"] or "その他"
        by_category.setdefault(cat, []).append(e)

    lines = []
    for category, items in by_category.items():
        lines.append(f"\n【{category}】")
        for e in items:
            aliases = " / ".join(e["aliases"]) if e["aliases"] else ""
            mistrans = " / ".join(e["mistranscriptions"]) if e["mistranscriptions"] else ""
            note = f"  ※{e['note']}" if e["note"] else ""

            parts = [f"  - {e['official']}"]
            if aliases:
                parts.append(f"    別名: {aliases}")
            if mistrans:
                parts.append(f"    【要修正】誤変換例: {mistrans} → 必ず「{e['official']}」に修正")
            if note:
                parts.append(f"    備考: {e['note']}")
            lines.append("\n".join(parts))

    return "\n".join(lines)
