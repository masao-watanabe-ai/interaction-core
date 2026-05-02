# AI / Scoring Design

> このドキュメントはスコアリングシステムの**技術仕様と設計思想**を記述する。  
> 実装の変更は `backend/app/services/score_service.py` と `backend/app/services/llm_service.py` を正とする。

---

## 目次

1. [なぜ「質」を評価するのか](#1-なぜ質を評価するのか)
2. [なぜ AI を使うのか](#2-なぜ-ai-を使うのか)
3. [スコアリング全体像](#3-スコアリング全体像)
4. [Layer 1 — ルールベーススコア](#4-layer-1--ルールベーススコア)
5. [Layer 2 — LLM ベーススコア](#5-layer-2--llm-ベーススコア)
6. [スコア統合式](#6-スコア統合式)
7. [熱量スコアの正規化](#7-熱量スコアの正規化)
8. [影響力スコア（impact_score）](#8-影響力スコアimpact_score)
9. [レベル判定](#9-レベル判定)
10. [ランキングロジック](#10-ランキングロジック)
11. [スコア保全ルール](#11-スコア保全ルール)
12. [チューニングガイド](#12-チューニングガイド)

---

## 1. なぜ「質」を評価するのか

### 量は測れても、価値は測れない

チャットツールが計測しやすいのは**量**だ。メッセージ数、文字数、反応数——これらはカウントするだけでいい。しかし量は価値の代理指標にすぎず、そこには根本的なズレがある。

> チームを最も動かした一言は、  
> 議論を止めた五十の相槌と、数字の上では区別できない。

量に偏ったスコアが生み出す歪みは二種類ある。

**1. ハイプレイヤーの不可視化**  
深い洞察を一言で提示するタイプの貢献者は、発言量が少なく見過ごされる。スコアが量に比例するなら、このタイプは常に過小評価される。

**2. ノイズの過大評価**  
相槌、「了解です」、絵文字連投——これらはコミュニケーション上の潤滑油であり、否定されるべきものではない。しかしそれがチームの成果物に与える影響は、アーキテクチャ上の決断の一言とは別次元にある。

### 「質」とは何か

このシステムが測定する「質」は三軸で構成される。

| 軸 | 問いかけ | 例 |
|---|---|---|
| **洞察力** | その発言は議論の理解を深めたか | 前提を覆す情報提示、技術的根拠の提示 |
| **議論への影響** | その発言は会話の流れを変えたか | 新しい論点の提起、行き詰まりの突破 |
| **意思決定貢献** | その発言は決断に近づいたか | 選択肢の整理、反対意見の解消、合意形成 |

これらはいずれも**テキストの意味を理解しなければ測れない**。単純なルールでは近似すらできない。だから AI を使う。

---

## 2. なぜ AI を使うのか

### ルールが壊れる場所

ルールベースの感情分類（`emotion.py`）は次の三値を返す: `positive` / `negative` / `question`。これは高速で決定的だが、意味の理解には限界がある。

```
「このアーキテクチャで本当に大丈夫ですか？」→ question ✓

「アーキテクチャの選択Aには隠れた前提がある。
 スケール時に X という問題が発生し、それは Y で解決できる。
 ただし Z のトレードオフを受け入れる必要がある。」→ neutral ✗
```

後者の発言は議論において最も価値が高い類のメッセージだが、ルールには `positive_words` も `question_tokens` も含まれていないため `neutral` に分類される。

### AI が測れること

LLM（GPT-4o-mini）は会話全体を文脈として読み、**各ユーザーの発言が議論の中でどのような役割を果たしたか**を評価できる。個々のメッセージの意味だけでなく、会話の流れの中での相対的な位置づけを判断できる。

```
チャンネルの文脈（要約・キーワード）を与え、
各ユーザーの代表発言（最大5件）を提示する。

→ insight_quality     0.0–1.0  (洞察力・知見の深さ)
→ discussion_impact   0.0–1.0  (議論を活性化した度合い)
→ decision_contribution 0.0–1.0 (意思決定に貢献した度合い)
```

### AI をオラクルにしない

ただし AI はスコアの**入力**であって、**判定者**ではない。

- LLM の出力は常に `[0.0, 1.0]` にクランプされ、重みをかけてポイントに変換される
- LLM が失敗した場合でも既存スコアが保全され、ゼロリセットされない
- 最終ランキングは人間が閲覧するシグナルであり、AI が「この人が優秀」と断言するものではない

> AI はシグナルを出力する。評価は人間が行う。

---

## 3. スコアリング全体像

```
┌─────────────────────────────────────────────────────────────┐
│                    Scoring Pipeline                          │
│                                                             │
│  Messages                                                   │
│      │                                                      │
│      ├──► Rule-based analysis ──────────────────────────┐  │
│      │    (emotion.py + heuristics)                      │  │
│      │    message_count, reply_count, reaction_count     │  │
│      │    positive_count, question_count, important_count│  │
│      │                                                    │  │
│      └──► LLM analysis (score_user_messages) ──────────┐│  │
│           Top 10 users × 5 messages each                ││  │
│           insight_quality   0.0–1.0                     ││  │
│           discussion_impact 0.0–1.0                     ││  │
│           decision_contribution 0.0–1.0                 ││  │
│                                                         ││  │
│                                          ┌──────────────┘│  │
│                                          │               │  │
│                                          ▼               ▼  │
│                                   compute_points()          │
│                                          │                  │
│                                          ▼                  │
│                              points (integer)               │
│                                          │                  │
│                         ┌────────────────┼──────────────┐  │
│                         ▼                ▼              ▼  │
│                    compute_level  normalize_enthusiasm  rank│
│                     Platinum/Gold  enthusiasm_score (0-100) │
│                     Silver/Bronze                           │
└─────────────────────────────────────────────────────────────┘
```

実装ファイル対応:

| 処理 | ファイル |
|---|---|
| 感情分類 | `app/module/analysis/emotion.py` |
| 重み定数 | `app/services/score_service.py` → `WEIGHTS`, `QUALITY_WEIGHTS` |
| ポイント計算 | `score_service.py` → `compute_points()` |
| LLM品質評価 | `app/services/llm_service.py` → `score_user_messages()` |
| ワークスペース再計算 | `score_service.py` → `recalculate_workspace_scores()` |
| ランキング応答 | `app/routes/scores.py` → `GET /scores/ranking` |

---

## 4. Layer 1 — ルールベーススコア

### 設計方針

ルールベース層は**決定的・高速・API不要**で動作する。分析パイプラインがLLMなしで実行された場合でも必ず計算される。

### シグナルと重み

```python
WEIGHTS = {
    "message_count":           2,   # 発言した（存在している）
    "reply_count":             3,   # 他者に返答した（関与している）
    "reaction_received_count": 5,   # 他者から反応を得た（評価された）
    "question_count":          2,   # 問いを立てた（議論を促した）
    "positive_count":          3,   # ポジティブな発言（場を前進させた）
    "important_message_count": 10,  # 重要メッセージ（! 含む）
}
```

**重みの意図**

| 重み | 意味 |
|---|---|
| `reaction_received_count × 5` | 他者の評価は自己申告より信頼できる。チームが「良い」と判断した発言を高く評価する |
| `important_message_count × 10` | `!` を含む発言は強調表現。意図的なマーキングを高く評価する |
| `reply_count × 3` | 返答は受動的な傍観より能動的な関与を示す |
| `message_count × 2` | ベースライン。存在を認めるが、これだけでは高得点にならない設計 |

### シグナル検出

```python
# reply: "@" で始まる発言
def _is_reply(content: str) -> bool:
    return content.startswith("@")

# important: "!" または "！" を含む発言
def _is_important(content: str) -> bool:
    return "!" in content or "！" in content

# emotion: keyword matching (emotion.py)
# → "positive" | "negative" | "question" | "neutral"
```

### ルールポイント計算

```
rule_pts = message_count         × 2
         + reply_count           × 3
         + reaction_received_count × 5
         + question_count        × 2
         + positive_count        × 3
         + important_message_count × 10
```

---

## 5. Layer 2 — LLM ベーススコア

### 処理フロー

LLM品質評価は分析パイプライン Step 5 で実行される（`analysis_worker.py`）。チャットのレスポンスパスには絶対に入らない。

```
analysis_worker.py
  Step 1: rule-based channel analysis
  Step 2: LLM channel summary (analyze_with_llm)
  Step 3: persist channel_analyses
  Step 4: publish WebSocket event
  Step 5: LLM per-user quality scoring  ← ここ
  Step 6: recalculate_workspace_scores
```

### プロンプト設計

```
System: チャット会話を分析し、各参加者の発言の「質」を評価するAI
        → JSON形式のみで返答

User:   チャンネルの文脈（キーワード + 要約）
        + 各ユーザーの代表発言（上位10名 × 最大5件）

        評価指標:
        - insight_quality     洞察力・知見の深さ    (薄い=0, 深い=1)
        - discussion_impact   議論を活性化した度合い (受動的=0, 主導的=1)
        - decision_contribution 意思決定への貢献     (なし=0, 中核的=1)
```

**コンテキストを与える理由**  
個別メッセージの評価ではなく、**チャンネルの文脈の中での相対評価**を行うため。同じ「アーキテクチャを変えよう」という発言も、その前後の議論次第で意味が変わる。

### API パラメータ

```python
model       = settings.openai_model  # gpt-4o-mini
temperature = 0.2   # 低温: 安定した評価を重視
max_tokens  = 512   # 10ユーザー分のJSON出力に十分
response_format = {"type": "json_object"}
```

温度を 0.3（チャンネル分析）より低い 0.2 に設定しているのは、スコアリングでは創造性より一貫性を優先するためだ。

### 出力とクランプ

```python
# LLM出力例
{"users": [
  {"user_id": 3, "insight_quality": 0.8, "discussion_impact": 0.6, "decision_contribution": 0.9},
  {"user_id": 7, "insight_quality": 0.2, "discussion_impact": 0.4, "decision_contribution": 0.1},
]}

# 全値を [0.0, 1.0] にクランプ（LLMが範囲外を返した場合の防御）
def _clamp(v: object) -> float:
    return max(0.0, min(1.0, float(v)))
```

### フォールバック

LLMが失敗した場合（APIキー未設定・タイムアウト・不正JSON等）、`score_user_messages()` は `None` を返す。呼び出し元はゼロ値でフォールバックせず、**既存DBのスコアを保全する**（詳細は §11）。

```python
# llm_service.py
except Exception as exc:
    logger.warning("LLM quality scoring failed: %s", exc)
    return None  # → callers preserve existing DB scores
```

---

## 6. スコア統合式

```
QUALITY_WEIGHTS = {
    "insight_quality_score":      10,
    "discussion_impact_score":     5,
    "decision_contribution_score": 20,
}

points = rule_pts
       + insight_quality_score      × 10
       + discussion_impact_score    × 5
       + decision_contribution_score × 20
```

実装（`score_service.py:compute_points()`）:

```python
def compute_points(
    *,
    message_count, reply_count, reaction_received_count,
    question_count, positive_count, important_message_count,
    insight_quality_score=0.0,
    discussion_impact_score=0.0,
    decision_contribution_score=0.0,
) -> int:
    rule_pts = (
        message_count         * 2
        + reply_count         * 3
        + reaction_received_count * 5
        + question_count      * 2
        + positive_count      * 3
        + important_message_count * 10
    )
    quality_pts = (
        insight_quality_score      * 10
        + discussion_impact_score  * 5
        + decision_contribution_score * 20
    )
    return int(rule_pts + quality_pts)
```

### 重みの意図

| 指標 | 重み | 最大ポイント | 意図 |
|---|---|---|---|
| `decision_contribution` | ×20 | 20 pts | 意思決定への貢献は最も希少で高価値 |
| `insight_quality` | ×10 | 10 pts | 深い洞察は議論の質を根本的に変える |
| `discussion_impact` | ×5 | 5 pts | 議論の活性化は重要だが、上二つより広く見られる |

品質スコアの最大合計値は `35 pts`（全指標が 1.0 の場合）。これはルールポイントで換算すると **重要メッセージ 3.5 件分** に相当する。LLMスコアは「補正」であり、活動量を完全に逆転させるほど支配的にはなっていない。

### 具体例

**ケース A: 多発言だが質は普通**

```
message_count=50, reply_count=10, important_message_count=2
insight_quality=0.3, discussion_impact=0.4, decision_contribution=0.1

rule_pts    = 50×2 + 10×3 + 2×10 = 150
quality_pts = 0.3×10 + 0.4×5 + 0.1×20 = 3+2+2 = 7
points      = 157  → Silver
```

**ケース B: 発言少ないが質が高い**

```
message_count=5, reply_count=2, important_message_count=1
insight_quality=0.9, discussion_impact=0.7, decision_contribution=0.95

rule_pts    = 5×2 + 2×3 + 1×10 = 26
quality_pts = 0.9×10 + 0.7×5 + 0.95×20 = 9+3.5+19 = 31.5
points      = 57   → Bronze (但し高影響力バッジ表示)
```

**ケース C: 量・質ともに高い**

```
message_count=30, reply_count=15, reaction_received_count=8
insight_quality=0.8, discussion_impact=0.9, decision_contribution=0.85

rule_pts    = 30×2 + 15×3 + 8×5 = 145
quality_pts = 0.8×10 + 0.9×5 + 0.85×20 = 8+4.5+17 = 29.5
points      = 174  → Bronze（だが Silver に近い）
```

---

## 7. 熱量スコアの正規化

### 目的

絶対ポイントはワークスペースの活発度によって大きく変動する。熱量スコアはワークスペース内での**相対的な貢献度**を 0–100 に正規化することで、異なる規模のワークスペース間でも比較可能な指標にする。

### 計算式

```python
def normalize_enthusiasm(points: int, max_points: int) -> float:
    if max_points <= 0:
        return 0.0
    return round(min(100.0, (points / max_points) * 100), 1)
```

```
enthusiasm_score = (user_points / max_points_in_workspace) × 100
```

1位のユーザーは常に `100.0`。全員が同じポイントなら全員 `100.0`。

### フロントエンド表示色

| 熱量スコア | 色 | 意味 |
|---|---|---|
| ≥ 80 | オレンジ `#faa61a` | 圧倒的な貢献 |
| ≥ 50 | パープル `#5865f2` | 積極的な参加 |
| < 50 | グリーン `#3ba55d` | 参加中 |

---

## 8. 影響力スコア（impact_score）

### 目的

`impact_score`（0–100）は LLM 由来の品質貢献のみを正規化した値。活動量（ルールポイント）は含まない。「少ない発言で高い質を発揮した」タイプの貢献者を可視化する。

### 計算式

```python
_MAX_QUALITY_PTS = sum(QUALITY_WEIGHTS.values())  # = 35

def compute_impact_score(insight, discussion, decision) -> float:
    raw = insight * 10 + discussion * 5 + decision * 20
    return round(min(100.0, (raw / 35) * 100), 1)
```

```
impact_score = (insight×10 + discussion×5 + decision×20) / 35 × 100
```

### 特性

- **保存されない**——毎回 `GET /scores/ranking` 時に計算される（QUALITY_WEIGHTS 変更に即時追従）
- **活動量非依存**——発言が少なくても `impact_score` は高くなりえる
- `impact_score > 0` の時のみ影響力バッジを表示（LLM分析が実行済みのシグナル）

---

## 9. レベル判定

```python
def compute_level(points: int) -> str:
    if points >= 1000: return "Platinum"
    if points >= 500:  return "Gold"
    if points >= 200:  return "Silver"
    return "Bronze"
```

| レベル | 閾値 | 意味 |
|---|---|---|
| 💎 Platinum | ≥ 1,000 pts | 継続的かつ高質な貢献 |
| 🏆 Gold | ≥ 500 pts | 顕著な貢献 |
| 🥈 Silver | ≥ 200 pts | 積極的な参加 |
| 🥉 Bronze | 0 pts〜 | 参加中 |

閾値設計の考え方: `important_message_count × 10` が最大重み。Bronze → Silver には重要メッセージ換算で約 20 件分が必要。Gold は 50 件分、Platinum は 100 件分。通常の活動では Platinum は希少であり意味を持つ。

---

## 10. ランキングロジック

### 再計算タイミング

ランキングは分析パイプラインの最終ステップで更新される。

```
analysis.completed WebSocket イベント発火
         ↓
フロントエンドが GET /scores/ranking を再取得
         ↓
最新ランキングを表示
```

### 再計算スコープ

`recalculate_workspace_scores()` はワークスペース全体を再計算する。チャンネル単位ではない。

**理由:** 1チャンネルを分析するとそのチャンネルの参加者のルールポイントが変動する。rank（順位）はワークスペース全員の相対値なので、1人のポイント変動は他者の rank にも影響する。ゆえに全員を再計算する。

```
1. workspace の全 channel_id を取得
2. 全チャンネルの全メッセージを集計 → per-user activity stats
3. 既存 UserScore を一括取得（upsert + 品質保全用）
4. quality scores を解決（LLM新値 > 既存DB > ゼロ）
5. compute_points() で全員のポイントを計算
6. points 降順でソート → rank を付番
7. enthusiasm_score を正規化（max_points を基準）
8. DB に upsert（既存行は UPDATE、新規行は INSERT）
```

### rank の付番

```python
sorted_users = sorted(user_points.items(), key=lambda x: -x[1])
for rank_pos, (uid, pts) in enumerate(sorted_users, start=1):
    ...
    score.rank = rank_pos
```

同点の場合は Python の `sorted()` が安定ソートであるため、DBから取得した順序が維持される。

### API レスポンス

`GET /scores/ranking?workspace_id=1`

```json
[
  {
    "user_id": 3,
    "display_name": "Alice",
    "points": 247,
    "level": "Silver",
    "rank": 1,
    "enthusiasm_score": 100.0,
    "insight_quality_score": 0.82,
    "discussion_impact_score": 0.65,
    "decision_contribution_score": 0.91,
    "impact_score": 83.7
  },
  ...
]
```

---

## 11. スコア保全ルール

### 問題

チャンネル A を分析 → ユーザー X のLLMスコアが更新される  
チャンネル B を分析 → ユーザー X はチャンネル B に参加していない

→ ユーザー X の品質スコアをゼロリセットすべきか？

### 答え: しない

```python
def _quality(uid: int) -> tuple[float, float, float]:
    if quality_scores and uid in quality_scores:
        # 優先1: 今回のLLM評価結果
        qs = quality_scores[uid]
        return (qs["insight_quality"], qs["discussion_impact"], qs["decision_contribution"])
    prev = existing.get(uid)
    if prev is not None:
        # 優先2: 既存DB値（過去の分析結果）
        return (prev.insight_quality_score, prev.discussion_impact_score, prev.decision_contribution_score)
    # 優先3: 初回ユーザーはゼロ
    return 0.0, 0.0, 0.0
```

**優先順位:**

```
1. 今回の LLM 評価結果（最新の分析で評価されたユーザー）
2. 既存 DB 値（今回の分析に参加していないユーザーの過去スコア）
3. ゼロ（そのワークスペースで初めてスコアが作成されるユーザー）
```

**理由:** 品質スコアは「このユーザーが示した質の履歴」である。あるチャンネルが分析されたからといって、別チャンネルでの質の高い貢献が否定されるべきではない。

---

## 12. チューニングガイド

### 重みの変更

すべての重み定数は `score_service.py` の先頭に集約されている。ロジックを触らずに重みだけ変更できる。

```python
WEIGHTS = {
    "message_count": 2,          # ← ここを変える
    ...
}
QUALITY_WEIGHTS = {
    "insight_quality_score": 10,  # ← ここを変える
    ...
}
```

変更後は既存の全スコアを再計算する必要がある（次の分析トリガーまで更新されない）。

### LLM モデルの変更

```
OPENAI_MODEL=gpt-4o-mini  # .env で変更可能
```

精度を上げたい場合は `gpt-4o` に変更できる。コストと速度のトレードオフ。

### プロンプト評価軸の追加・変更

`llm_service.py` の `_QUALITY_SYSTEM_PROMPT` と `score_user_messages()` 内のユーザープロンプトを編集し、新しい評価軸を `QUALITY_WEIGHTS` に追加する。DB の `user_scores` テーブルにカラムを追加し、`UserScore` モデルと `compute_points()` も更新する。

### LLM なしで動作させる

`OPENAI_API_KEY` を空にすると LLM 品質スコアは実行されない。ルールベーススコアのみで動作し、`insight_quality_score` / `discussion_impact_score` / `decision_contribution_score` は 0.0 のまま維持される。

---

## 付記: 設計思想の要約

```
量  ──► ルールが測る   (速い・決定的・API不要)
質  ──► AI が測る      (文脈依存・意味理解・非同期)
判断 ──► 人間が行う    (AI はシグナルを出力するだけ)
```

量は参加の証明だ。質は貢献の証明だ。  
どちらも必要で、どちらかだけでは不十分だ。  
そして両方を合わせても、「この人を昇進させるべきか」という判断の代わりにはならない。

スコアはレンズだ。決断ではない。
