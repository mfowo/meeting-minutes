"""
用語集ローダー
CSVファイルから正式名称・別名・読み方のマッピングを読み込む
"""

import csv
from pathlib import Path


def load_from_csv(csv_path: str) -> list[dict]:
    """
    CSVから用語集を読み込む

    CSV形式: 正式名称,別名・読み方,カテゴリ,備考
    「別名・読み方」は「/」区切りで複数指定可能
    """
    entries = []
    path = Path(csv_path)

    if not path.exists():
        print(f"[警告] 用語集ファイルが見つかりません: {csv_path}")
        return entries

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            official = row.get("正式名称", "").strip()
            aliases_raw = row.get("別名・読み方", "").strip()
            category = row.get("カテゴリ", "").strip()
            note = row.get("備考", "").strip()

            if not official:
                continue

            aliases = [a.strip() for a in aliases_raw.split("/") if a.strip()]

            entries.append({
                "official": official,
                "aliases": aliases,
                "category": category,
                "note": note,
            })

    print(f"[用語集] {len(entries)}件読み込み: {csv_path}")
    return entries


def append_to_csv(csv_path: str, new_entries: list[dict]) -> None:
    """新しい用語をCSVに追記する"""
    path = Path(csv_path)
    write_header = not path.exists()

    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["正式名称", "別名・読み方", "カテゴリ", "備考"])
        if write_header:
            writer.writeheader()
        for entry in new_entries:
            writer.writerow({
                "正式名称": entry.get("official", ""),
                "別名・読み方": " / ".join(entry.get("aliases", [])),
                "カテゴリ": entry.get("category", ""),
                "備考": entry.get("note", ""),
            })

    print(f"[用語集] {len(new_entries)}件追記しました: {csv_path}")


def format_for_prompt(entries: list[dict]) -> str:
    """用語集をClaudeへのプロンプト用テキストに変換"""
    if not entries:
        return "（用語集なし）"

    lines = ["正式名称（別名・読み方）"]
    for e in entries:
        aliases = " / ".join(e["aliases"]) if e["aliases"] else "なし"
        note = f"  ※{e['note']}" if e["note"] else ""
        lines.append(f"- {e['official']}（{aliases}）{note}")

    return "\n".join(lines)
