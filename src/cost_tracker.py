"""
APIコストトラッカー
Anthropic APIの利用料金を集計して表示する
"""

# Claude Sonnet 4.6 の料金（USD/token）
PRICE_INPUT_PER_TOKEN = 3.0 / 1_000_000   # $3 / 1M tokens
PRICE_OUTPUT_PER_TOKEN = 15.0 / 1_000_000  # $15 / 1M tokens

# この金額を超えたらClaude Codeチャットへの切り替えを提案
SUGGESTION_THRESHOLD_USD = 0.50

# 円換算レート（目安）
JPY_RATE = 150


class CostTracker:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def add(self, response) -> None:
        """APIレスポンスからトークン数を加算する"""
        if hasattr(response, "usage"):
            self.input_tokens += response.usage.input_tokens
            self.output_tokens += response.usage.output_tokens

    @property
    def total_usd(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT_PER_TOKEN
            + self.output_tokens * PRICE_OUTPUT_PER_TOKEN
        )

    @property
    def total_jpy(self) -> float:
        return self.total_usd * JPY_RATE

    def print_summary(self) -> None:
        """コスト集計を表示し、高額な場合は代替手段を提案する"""
        print("\n" + "─" * 50)
        print("💰 今回のAPI利用コスト（概算）")
        print("─" * 50)
        print(f"  入力トークン : {self.input_tokens:,}")
        print(f"  出力トークン : {self.output_tokens:,}")
        print(f"  合計        : ${self.total_usd:.4f}（約{self.total_jpy:.0f}円）")
        print("─" * 50)

        if self.total_usd >= SUGGESTION_THRESHOLD_USD:
            print()
            print("💡 コスト削減の提案")
            print("  今回の処理は比較的コストが高くなっています。")
            print("  以下の方法でAPIコストをゼロにできます：")
            print()
            print("  Claude Code チャット（$20/月のサブスクに含まれる）で")
            print("  VTTファイルを直接貼り付けて議事録を作成する方法があります。")
            print()
            print("  詳細は README.md の「コストを抑えたい場合」を参照してください。")
            print("─" * 50)
