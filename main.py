#!/usr/bin/env python3
"""
meeting-minutes: 会議文字起こしから議事録を自動生成するツール
Zoom / Microsoft Teams の .vtt ファイルに対応

使い方:
    python main.py <VTTファイルパス> [オプション]

例:
    python main.py meeting.vtt
    python main.py meeting.vtt --glossary config/glossary.csv
    python main.py meeting.vtt --context "四半期レビュー会議" --output minutes.md
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from src.glossary_loader import load_from_csv, load_from_sheets, format_for_prompt
from src.transcript_corrector import correct_transcript
from src.minutes_generator import run_minutes_generation
from src.glossary_suggester import suggest_and_update_glossary


def main():
    parser = argparse.ArgumentParser(
        description="会議文字起こし(.vtt)から議事録を自動生成します（Zoom / Teams 対応）"
    )
    parser.add_argument("vtt_file", help="VTTファイルパス（Zoom / Teams）")
    parser.add_argument(
        "--glossary",
        default="config/glossary.csv",
        help="用語集CSVファイルパス (デフォルト: config/glossary.csv)",
    )
    parser.add_argument(
        "--context",
        default="",
        help="会議の背景・目的（例: '四半期売上レビュー会議'）",
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

    # .envから環境変数を読み込む
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[エラー] ANTHROPIC_API_KEY が設定されていません。")
        print("  .env ファイルを作成するか、環境変数を設定してください。")
        print("  参考: .env.example")
        sys.exit(1)

    vtt_path = args.vtt_file
    if not Path(vtt_path).exists():
        print(f"[エラー] VTTファイルが見つかりません: {vtt_path}")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # 用語集を読み込む（GoogleスプレッドシートIDがあればSheets優先）
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if sheet_id:
        glossary_entries = load_from_sheets(sheet_id)
        if not glossary_entries:
            print("[用語集] Sheetsの読み込みに失敗したためCSVにフォールバックします")
            glossary_entries = load_from_csv(args.glossary)
    else:
        glossary_entries = load_from_csv(args.glossary)
    glossary_text = format_for_prompt(glossary_entries)

    # ステップ1: 文字起こし補正
    if args.skip_correction:
        print("[スキップ] 用語集補正をスキップします")
        with open(vtt_path, encoding="utf-8") as f:
            corrected = f.read()
    else:
        corrected = correct_transcript(client, vtt_path, glossary_text)

    # ステップ2: 議事録生成
    minutes = run_minutes_generation(client, corrected, args.context)

    # 出力
    output_path = args.output or f"minutes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(minutes)

    print(f"\n✓ 議事録を保存しました: {output_path}")

    # ステップ3: 用語集への追加提案
    if not args.skip_suggestion:
        suggest_and_update_glossary(
            client,
            corrected,
            glossary_entries,
            args.glossary,
        )


if __name__ == "__main__":
    main()
