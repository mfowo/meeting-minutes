"""
文字起こし補正モジュール
Zoom / Microsoft Teams の .vttファイルを読み込み、用語集を使ってClaudeで補正する
"""

import re
import anthropic
from .cost_tracker import CostTracker


def parse_vtt(vtt_path: str) -> list[dict]:
    """
    Zoom / Microsoft Teams VTTファイルを解析してセグメントリストに変換

    戻り値: [{"timestamp": "00:01:23", "speaker": "田中", "text": "..."}, ...]
    """
    segments = []

    with open(vtt_path, encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n\n+", content.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines or lines[0] == "WEBVTT":
            continue

        timestamp_line = None
        text_lines = []
        for line in lines:
            if "-->" in line:
                timestamp_line = line.split("-->")[0].strip()
                timestamp_line = re.sub(r"\.\d+$", "", timestamp_line)
            elif timestamp_line is not None:
                text_lines.append(line)

        if not timestamp_line or not text_lines:
            continue

        text = " ".join(text_lines)

        speaker_match = re.match(r"<v ([^>]+)>(.*)</v>", text)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            text = speaker_match.group(2).strip()
        else:
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
    lines = []
    for seg in segments:
        if seg["speaker"]:
            lines.append(f"[{seg['timestamp']}] {seg['speaker']}: {seg['text']}")
        else:
            lines.append(f"[{seg['timestamp']}] {seg['text']}")
    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int = 12000) -> list[str]:
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
    tracker: CostTracker,
) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": f"""以下は会議の文字起こし（パート{chunk_num}/{total_chunks}）です。
用語集を参考に誤変換を修正してください。

## 用語集
{glossary_text}

## 補正ルール（基本）
- 用語集の「別名・読み方」に該当する表現を「正式名称」に統一する
- 文脈から同一人物・組織・用語と判断できる表現も正式名称に統一する
- タイムスタンプ・話者名はそのまま残す
- 補正した箇所は【】で囲む（例：【田中健二】）
- 意味不明で補正できない箇所は[要確認]とマークする
- 補正不要な箇所はそのまま出力する

## 補正ルール（慶應馬術部特有の注意点）

### 人名の旧字体
以下の旧字体は音声認識で常用漢字に誤変換されやすい。用語集を必ず参照すること。
- 「邊」（渡邊など）→「辺」への誤変換に注意
- 「嶋」（中嶋など）→「島」への誤変換に注意
- 「澤」（宮澤など）→「沢」への誤変換に注意

### 人名の略称・呼称
略称・あだ名が正式名称として記載されないよう注意する。
- 「末」→「須江」（略称を正式名称に）
- 「コバ」→「木場」（呼称を正式名称に）
- 「しゅんと」「俊人」→「高橋駿人」

### 外来語（馬名）の誤変換パターン
外来語の馬名は以下のパターンで誤変換されやすい。用語集と照合すること。
- 長音の有無：「ラビー」→「ラヴィ」
- 母音の種類：「ビヨンデッツァ」→「ビオンデッツァ」
- 語頭の音：「ディレクトゥール」→「デレクトゥール」、「ブーナ」→「ブエナ」
- 促音の誤挿入：「リバップ」→「リバプ」
- アルファベット残存：「TAO」→「タオ」

### 馬術用語
- 「途中棄権」→「失権」（競技の公式用語）
- 「先行出走」→「先通し」
- 「6大学」「6台」→「六大学」「六大」（漢字表記が正しい）

### 地名
- 「妻恋」→「つま恋」（施設名は平仮名）

## 文字起こし（補正前）
{chunk}

補正後の文字起こしをそのまま出力してください（説明不要）。""",
            }
        ],
    )
    tracker.add(response)
    return response.content[0].text


def correct_transcript(
    client: anthropic.Anthropic,
    vtt_path: str,
    glossary_text: str,
    tracker: CostTracker,
) -> str:
    print(f"[文字起こし] VTTファイルを解析中: {vtt_path}")
    segments = parse_vtt(vtt_path)
    print(f"[文字起こし] {len(segments)}セグメント検出")

    raw_text = segments_to_text(segments)
    chunks = chunk_text(raw_text)
    print(f"[文字起こし] {len(chunks)}チャンクに分割して補正開始")

    corrected_chunks = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[文字起こし] チャンク {i}/{len(chunks)} を補正中...")
        corrected = correct_chunk(client, chunk, glossary_text, i, len(chunks), tracker)
        corrected_chunks.append(corrected)

    return "\n".join(corrected_chunks)
