#!/usr/bin/env python3
"""
meeting-minutes: 会議文字起こしから議事録を自動生成するツール
Zoom / Microsoft Teams の .vtt ファイルに対応

使い方:
    python main.py <VTTファイルパス> [オプション]

例:
    python main.py meeting.vtt
    python main.py meeting.vtt --context "慶應馬術部 前期総会" --output minutes.md
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import anthropic

from src.glossary_loader import load_from_csv, format_for_prompt
from src.transcript_corrector import correct_transcript
from src.minutes_generator import run_minutes_generation
from src.glossary_suggester import suggest_and_update_glossary
from src.cost_tracker import CostTracker


def main():
    parser = argparse.ArgumentParser(
        description="会議文字起こし(.vtt)から議事録を自動生成します（Zoom / Teams 対応）"
    )
    parser.add_argument("vtt_file", help="VTTファイルパス（Zoom / Teams）")
    parser.add_argument(
        "--glossary",
        default="config/glossary.csv",
        help="用語集CSVファイルパス",
    )
    parser.add_argument(
        "--context",
        default="",
        help="会議の背景・目的（例: '慶應馬術部 2024年度前期総会'）",
    )
    parser.add_argument(
        "--output",
        default="",
        help="出力ファイルパス (デフォルト: minutes_YYYYMMDD_HHMMSS.md)",
    )
    parser.add_argument(
        "--skip-correction",
        action="store_true",
        help="用語集補正をスキップして直接議事録生成（高速化）",
    )
    parser.add_argument(
        "--skip-suggestion",
        action="store_true",
        help="用語集追加提案をスキップする",
    )
    args = parser.parse_args()

    vtt_path = args.vtt_file
    if not Path(vtt_path).exists():
        print(f"[エラー] VTTファイルが見つかりません: {vtt_path}")
        sys.exit(1)

    client = anthropic.Anthropic()
    tracker = CostTracker()

    # 用語集を読み込む
    glossary_entries = load_from_csv(args.glossary)
    glossary_text = format_for_prompt(glossary_entries)

    # ステップ1: 文字起こし補正
    if args.skip_correction:
        print("[スキップ] 用語集補正をスキップします")
        with open(vtt_path, encoding="utf-8") as f:
            corrected = f.read()
    else:
        corrected = correct_transcript(client, vtt_path, glossary_text, tracker)

    # ステップ2: 議事録生成
    minutes = run_minutes_generation(client, corrected, args.context, tracker)

    # 出力
    output_path = args.output or f"output/minutes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(minutes)

    print(f"\n✓ 議事録を保存しました: {output_path}")

    # ステップ3: コスト表示
    tracker.print_summary()

    # ステップ4: 用語集への追加提案
    if not args.skip_suggestion:
        suggest_and_update_glossary(
            client,
            corrected,
            glossary_entries,
            args.glossary,
            tracker,
        )


if __name__ == "__main__":
    main()
