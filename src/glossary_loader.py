"""
用語集ローダー
Google Sheets（公開URL）またはCSVファイルから用語集を読み込む
"""

import csv
import io
import urllib.request
from pathlib import Path


def _parse_rows(reader) -> list[dict]:
    """CSV行をパースして用語エントリのリストを返す"""
    entries = []
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
    return entries


def load_from_sheets(sheet_id: str) -> list[dict]:
    """
    公開設定のGoogleスプレッドシートから用語集を読み込む

    シートは「リンクを知っている全員が閲覧可能」に設定すること
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8")
    except Exception as e:
        print(f"[警告] Googleスプレッドシートの読み込みに失敗しました: {e}")
        return []

    reader = csv.DictReader(io.StringIO(content))
    entries = _parse_rows(reader)
    print(f"[用語集] {len(entries)}件読み込み（Googleスプレッドシート）")
    return entries


def load_from_csv(csv_path: str) -> list[dict]:
    """CSVファイルから用語集を読み込む（ローカルフォールバック用）"""
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
            f, fieldnames=["正式名称", "別名・読み方", "カテゴリ", "備考"]
        )
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
            aliases = " / ".join(e["aliases"]) if e["aliases"] else "なし"
            note = f"  ※{e['note']}" if e["note"] else ""
            lines.append(f"  - {e['official']}（{aliases}）{note}")

    return "\n".join(lines)
