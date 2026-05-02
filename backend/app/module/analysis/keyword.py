import re
from collections import Counter

STOP_WORDS = {
    "は", "が", "を", "に", "で", "の", "と", "も", "から", "まで",
    "です", "ます", "ました", "ません", "した", "して", "する", "ある",
    "いる", "なる", "なっ", "れる", "られる", "ので", "ため", "こと",
    "これ", "それ", "あれ", "この", "その", "あの", "どの", "また",
    "そして", "しかし", "でも", "けど", "けれど",
    "i", "the", "a", "is", "it", "in", "of", "to", "and", "for",
    "on", "this", "that", "with", "you", "he", "she", "we", "they",
    "be", "at", "by", "or", "an", "are", "was", "has", "have", "had",
    "do", "did", "will", "would", "can", "could", "should", "may", "might",
    "seed", "message",
}

_SPLIT_RE = re.compile(r'[\s\u3000、。！？!?,.\-_/\\|()（）「」【】\[\]]+')


def extract_keywords(texts: list[str], top_n: int = 10) -> list[str]:
    words: list[str] = []
    for text in texts:
        for token in _SPLIT_RE.split(text.lower()):
            token = token.strip()
            if len(token) >= 2 and token not in STOP_WORDS:
                words.append(token)
    return [word for word, _ in Counter(words).most_common(top_n)]
