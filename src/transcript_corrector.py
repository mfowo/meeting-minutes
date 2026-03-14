"""
文字起こし補正モジュール
Zoom / Microsoft Teams の .vttファイルを読み込み、用語集を使ってClaudeで補正する
"""

import re
import anthropic


def parse_vtt(vtt_path: str) -> list[dict]:
    """
    Zoom VTTファイルを解析してセグメントリストに変換

    戻り値: [{"timestamp": "00:01:23", "speaker": "田中", "text": "..."}, ...]
    """
    segments = []

    with open(vtt_path, encoding="utf-8") as f:
        content = f.read()

    # VTTのブロックを分割（空行区切り）
    blocks = re.split(r"\n\n+", content.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines or lines[0] == "WEBVTT":
            continue

        # タイムスタンプ行を探す（例: 00:01:23.000 --> 00:01:25.000）
        timestamp_line = None
        text_lines = []
        for line in lines:
            if "-->" in line:
                timestamp_line = line.split("-->")[0].strip()
                # ミリ秒を除去: 00:01:23.000 → 00:01:23
                timestamp_line = re.sub(r"\.\d+$", "", timestamp_line)
            elif timestamp_line is not None:
                text_lines.append(line)

        if not timestamp_line or not text_lines:
            continue

        text = " ".join(text_lines)

        # 話者分離: "<v 田中健二>テキスト</v>" 形式に対応
        speaker_match = re.match(r"<v ([^>]+)>(.*)</v>", text)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            text = speaker_match.group(2).strip()
        else:
            # "田中: テキスト" 形式に対応
            colon_match = re.match(r"^([^\s：:]{1,20})[：:]\s*(.+)", text)
            if colon_match:
                speaker = colon_match.group(1).strip()
                text = colon_match.group(2).strip()
            else:
                speaker = ""

        segments.append({
            "timestamp": timestamp_line,
            "speaker": speaker,
            "text": text,
        })

    return segments


def segments_to_text(segments: list[dict]) -> str:
    """セグメントリストを補正用テキストに変換"""
    lines = []
    for seg in segments:
        if seg["speaker"]:
            lines.append(f"[{seg['timestamp']}] {seg['speaker']}: {seg['text']}")
        else:
            lines.append(f"[{seg['timestamp']}] {seg['text']}")
    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int = 12000) -> list[str]:
    """長い文字起こしを行単位でチャンク分割"""
    lines = text.splitlines()
    chunks = []
    current_lines = []
    current_size = 0

    for line in lines:
        if current_size + len(line) > chunk_size and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_size = 0
        current_lines.append(line)
        current_size += len(line)

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


def correct_chunk(
    client: anthropic.Anthropic,
    chunk: str,
    glossary_text: str,
    chunk_num: int,
    total_chunks: int,
) -> str:
    """1チャンクをClaudeで補正する"""
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": f"""以下は会議の文字起こし（パート{chunk_num}/{total_chunks}）です。
用語集を参考に誤変換を修正してください。

## 用語集
{glossary_text}

## 補正ルール
- 用語集の誤変換パターンを正しい表記に修正する
- 文脈から明らかな誤変換も修正する
- タイムスタンプ・話者名はそのまま残す
- 補正した箇所は【】で囲む（例：【Kubernetes】）
- 意味不明で補正できない箇所は[要確認]とマークする
- 補正不要な箇所はそのまま出力する

## 文字起こし（補正前）
{chunk}

補正後の文字起こしをそのまま出力してください（説明不要）。""",
            }
        ],
    )
    return response.content[0].text


def correct_transcript(
    client: anthropic.Anthropic,
    vtt_path: str,
    glossary_text: str,
) -> str:
    """
    VTTファイルを読み込み、用語集で補正した文字起こしを返す
    長時間録音はチャンク分割して処理
    """
    print(f"[文字起こし] VTTファイルを解析中: {vtt_path}")
    segments = parse_vtt(vtt_path)
    print(f"[文字起こし] {len(segments)}セグメント検出")

    raw_text = segments_to_text(segments)
    chunks = chunk_text(raw_text)
    print(f"[文字起こし] {len(chunks)}チャンクに分割して補正開始")

    corrected_chunks = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[文字起こし] チャンク {i}/{len(chunks)} を補正中...")
        corrected = correct_chunk(client, chunk, glossary_text, i, len(chunks))
        corrected_chunks.append(corrected)

    return "\n".join(corrected_chunks)
