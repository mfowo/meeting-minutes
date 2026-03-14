"""
用語集ローダー
CSVファイルから誤変換→正しい表記のマッピングを読み込む
"""

import csv
from pathlib import Path


def load_from_csv(csv_path: str) -> dict[str, str]:
    """
    CSVから用語集を読み込む

    CSV形式: 誤変換,正しい表記,カテゴリ,備考
    1行目はヘッダーとしてスキップ
    """
    glossary = {}
    path = Path(csv_path)

    if not path.exists():
        print(f"[警告] 用語集ファイルが見つかりません: {csv_path}")
        return glossary

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wrong = row.get("誤変換", "").strip()
            correct = row.get("正しい表記", "").strip()
            if wrong and correct:
                glossary[wrong] = correct

    print(f"[用語集] {len(glossary)}件読み込み: {csv_path}")
    return glossary


def format_for_prompt(glossary: dict[str, str]) -> str:
    """用語集をClaudeへのプロンプト用テキストに変換"""
    if not glossary:
        return "（用語集なし）"

    lines = ["誤変換 → 正しい表記"]
    for wrong, correct in glossary.items():
        lines.append(f"- {wrong} → {correct}")

    return "\n".join(lines)
