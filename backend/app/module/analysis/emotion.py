POSITIVE_WORDS = {
    "良い", "いい", "助かる", "助かった", "賛成", "すごい",
    "ありがとう", "完璧", "最高", "good", "great", "nice",
    "thanks", "perfect", "excellent", "ok", "okay",
}
NEGATIVE_WORDS = {
    "問題", "困る", "困った", "難しい", "エラー", "遅い",
    "バグ", "失敗", "error", "bug", "fail", "issue", "slow", "bad", "broken",
}
QUESTION_TOKENS = {
    "?", "？", "どう", "なぜ", "何", "いつ", "どこ", "だれ",
    "how", "why", "what", "when", "where", "who",
}


def classify_message(text: str) -> str:
    lower = text.lower()
    for w in POSITIVE_WORDS:
        if w in lower:
            return "positive"
    for w in NEGATIVE_WORDS:
        if w in lower:
            return "negative"
    for p in QUESTION_TOKENS:
        if p in lower:
            return "question"
    return "neutral"


def analyze_emotions(texts: list[str]) -> dict[str, int]:
    positive = negative = question = 0
    for text in texts:
        label = classify_message(text)
        if label == "positive":
            positive += 1
        elif label == "negative":
            negative += 1
        elif label == "question":
            question += 1
    return {
        "positive_count": positive,
        "negative_count": negative,
        "question_count": question,
    }
