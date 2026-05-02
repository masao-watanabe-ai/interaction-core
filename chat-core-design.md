# Chat Core — Design Document

> Chat Core は「再利用可能な Input / Interaction Layer」である。  
> AI が Signal を生成し、人間が Decision を作る。Chat はその橋渡しに徹する。

---

## Overview

Chat Core は Chat AI Platform の **Input / Interaction Layer** である。  
チャンネルごとのリアルタイムメッセージング・Evidence 管理・AI Signal 提示・Human Gate 操作を担い、上位の **Decision Trace Manager (DTM)** に対してデータと操作の接点を提供する。

Chat Core は意思決定しない。AI が生成した Signal を人間が認識しやすい形で提示し、DTM への変換トリガーを人間に委ねる。

---

## Core Concept

### Signal ≠ Decision

AI が生成するのは **Signal** である。Signal は観察・分析・提案であり、それ自体がアクションや決定を生成しない。Decision は人間が明示的に Signal から昇格させることで初めて生まれる。

```
AI Output ──► Signal  (分析結果 / キーワード / 提案)
                   │
                   │  人間が選択・操作
                   ▼
              Decision  (DTM が所有・追跡)
```

### Chat は意思決定しない

Chat Core のメッセージストリームは以下のいずれでもない:

- タスク管理システム
- 承認フロー  
- 実行指示システム

Chat Core は **文脈の記録と Signal の提示** に専念する。意思決定の帰属・追跡・実行は DTM の責務とする。

### Chat Core と DTM の境界

| レイヤー | 責務 |
|---|---|
| Chat Core | Message / Evidence の保存、WebSocket 配信、Signal の可視化 |
| DTM | Decision の生成・状態管理、Human Gate、Execution の追跡 |

DTM の操作は Chat Core の UI から発火されるが、状態の所有権は DTM 側にある。Chat Core は DTM への **ゲートウェイ** であり、DTM の **代替ではない**。

---

## Data Model

```
channels ──1:N──► messages
         └──1:N──► evidence_items
                        │
                   (将来) message_id で message に紐付く

channels ──1:N──► decisions          ← DTM が所有
decisions ──1:N──► human_actions
decisions ──1:N──► execution_events
```

| Entity | 所有者 | 不変条件 |
|---|---|---|
| `messages` | Chat Core | 追記のみ。編集・削除なし |
| `evidence_items` | Chat Core | channel または message に紐付く。extracted_text は非同期に付与 |
| `decisions` | DTM | Signal から人間操作によって昇格。proposed → reviewing → approved / rejected → executed |
| `human_actions` | DTM | approve / reject / escalate などの操作ログ。変更不可 |
| `execution_events` | DTM | 外部 API 実行の記録。pending → running → completed / failed |

---

## Architecture

```
Browser
  │
  ├── REST   (api.ts / credentials: include)
  └── WebSocket (useWebSocket.ts / auto-reconnect 3s)
        │
        ▼
┌──────────────────────────────────────────────────┐
│  Chat Core  (FastAPI :8000)                       │
│                                                  │
│  Input Layer                                     │
│    routes/messages.py      POST / GET messages   │
│    routes/evidence.py      POST upload / GET list│
│    routes/ws.py            WebSocket handshake   │
│                                                  │
│  DTM Integration Layer                           │
│    routes/decisions.py     Signal → Decision     │
│    routes/human_actions.py approve / reject ...  │
│    routes/executions.py    execute / track       │
│                                                  │
│  services/websocket_service.py  ConnectionManager│
│  services/redis_client.py       Pub/Sub publish  │
│  services/redis_subscriber.py   Pub/Sub subscribe│
└──────────┬──────────────────────┬───────────────┘
           │                      │
      PostgreSQL              Redis :6379
      (永続化)               Pub/Sub: chat_events
                             RQ queue: analysis
                                  │
                             ┌────┴──────┐
                             │ RQ Worker │  Analysis Pipeline
                             │           │  (Signal 生成)
                             └───────────┘
```

### 単一チャンネルイベントの流れ

```
POST /messages
  → INSERT messages
  → manager.broadcast("message.created")
    → Redis publish  ──► subscriber → broadcast_local → WS clients
    → fallback: broadcast_local (Redis 停止時)

POST /evidence/upload
  → store file to /uploads
  → INSERT evidence_items
  → manager.broadcast("evidence.created")  [失敗しても upload は成功]

POST /analysis/channels/{id}
  → RQ enqueue
  → Worker: rule-based + LLM → INSERT channel_analyses
  → aioredis.publish("analysis.completed")
    → subscriber → broadcast_local → WS clients
```

---

## UI Structure

```
page.tsx  (全状態を保持: channels / messages / evidenceItems / analysisResults / ranking)
  │
  ├── ChannelList          サイドバー (チャンネル選択 / 作成 / ログアウト)
  │
  └── Main Area
        ├── ChatHeader     チャンネル名 / WS接続状態 / ChatMode セレクター
        │
        ├── MessageList    メッセージ一覧 + Evidence カード
        │     ├── Channel Evidence Section  (message_id なし)
        │     └── Message Row
        │           ├── MessageActions       (ChatMode 依存のアクションスロット)
        │           └── EvidenceCard × N     (message_id 一致)
        │                 └── EvidenceActions  (Analyze / Convert / Send to Studio)
        │
        ├── MessageInput   テキスト入力 (Enter 送信) + ファイルアップロード (+ ボタン)
        │
        └── ChatRightPanel  ChatMode に応じて切り替わる右パネル
```

状態の流れ: `page.tsx` がすべての状態を保持し、子コンポーネントへ props で渡す。子コンポーネントは状態を持たない（EvidenceActions の console.log を除く）。

---

## ChatMode

ChatMode は Chat Core の **表示・操作コンテキスト** を切り替えるスイッチである。モードはデータモデルに影響せず、右パネルと MessageAction スロットの組み合わせのみを変える。

| Mode | 目的 | Action Slots | 右パネル |
|---|---|---|---|
| `signal` | AI Signal の確認・Decision 化 | convert_to_decision, send_to_studio | AI 分析 |
| `human_gate` | 承認・却下・修正依頼・エスカレ | approve, reject, request_revision, escalate | Human Gate |
| `execute` | 外部 API 実行の確認・指示 | execute, reject | Execute |
| `studio` | Decision Trace Studio 設計 | send_to_studio, convert_to_decision | Studio |
| `agent_collaboration` | 複数 Agent 提案の比較・採否 | approve, reject, request_revision, convert_to_decision | Agent Collab |

モードの設定は `CHAT_MODE_CONFIGS` (types/chat-core.ts) に集約されており、スロット変更はそこだけを編集する。

---

## Evidence Concept

Evidence は「チャンネルに関連するファイル資料」であり、Signal の根拠・補足として機能する。

### ライフサイクル

```
1. アップロード
   POST /evidence/upload  (multipart: channel_id + file)
     → /uploads/{uuid}{ext} に保存
     → evidence_items に INSERT
     → WS event: evidence.created を broadcast

2. 表示
   GET /evidence?channel_id=X
     → message_id あり → 該当 Message 直下にカード
     → message_id なし → MessageList 上部 "CHANNEL EVIDENCE" セクション

3. アクション (現在 UI のみ)
   Analyze          → TODO: POST /evidence/{id}/analyze
   Convert to Decision → TODO: POST /decisions  (evidence_id を source として渡す)
   Send to Studio   → TODO: WS event studio.sync.requested { evidence_id }
```

### 設計上の決定

- `extracted_text` は保存時 NULL。テキスト抽出は非同期で後付けする設計とする
- `message_id` は現在のバックエンドモデルには存在しない（フロントエンド型のみ optional で宣言済み）
- `file_size` も同様に将来フィールド

---

## WebSocket Events

すべてのイベントは Server → Client の単方向配信である。クライアントから WebSocket でデータを送信しない。

| Event | Payload | 発火条件 | 実装状態 |
|---|---|---|---|
| `message.created` | `{id, channel_id, user_id, content, created_at}` | POST /messages | ✅ |
| `analysis.completed` | `{channel_id, result: AnalysisSummary}` | RQ Worker 完了 | ✅ |
| `evidence.created` | `EvidenceItem` | POST /evidence/upload | ✅ |
| `decision.created` | `Decision` | POST /decisions | TODO |
| `decision.updated` | `Decision` | PATCH /decisions/{id} | TODO |
| `human_action.created` | `HumanAction` | POST /human_actions | TODO |
| `execution.requested` | `ExecutionEvent` | POST /executions | TODO |
| `execution.completed` | `ExecutionEvent` | Worker 完了 | TODO |
| `studio.sync.requested` | `{evidence_id?} | ...` | UI アクション | TODO |

### 配信保証モデル

```
Redis 利用可能:
  publish_event() → Pub/Sub → 全インスタンスの subscriber → broadcast_local()

Redis 停止中:
  publish_event() → False → broadcast_local() に直接フォールバック
  (同一プロセスの接続のみ対象)

Evidence upload など broadcast 失敗が許容される場合:
  try/except で握り潰し → logger.warning のみ → 本処理は成功
```

---

## Design Principles

### 1. Signal ≠ Decision

AI が生成するのは Signal である。Signal は根拠として記録されるが、それ自体がタスク・承認・実行を生成しない。Decision の生成は必ず人間の明示的な操作を起点とする。これは機能の欠落ではなく、アーキテクチャ上の境界条件である。

### 2. Chat は記録する、DTM が追跡する

Chat Core はメッセージと Evidence を記録し、Signal を提示する。Decision のステータス遷移・Human Gate ログ・Execution 追跡は DTM が所有する。Chat Core は DTM へのゲートウェイを提供するに留まり、DTM の内部状態を模倣しない。

### 3. Human Gate は自動化しない

Chat Core のすべての DTM 連携アクション（approve / reject / convert_to_decision / execute）は、人間のクリック操作を起点とする。自動昇格・自動承認・自動実行は設計上排除する。

### 4. WebSocket は配信専用

WebSocket は Server → Client の単方向配信に使用する。状態変更はすべて REST API 経由で行い、WS はその結果を他クライアントへ伝搬する手段に徹する。

### 5. Redis 障害耐性

Redis が停止していても、メッセージ送信・Evidence アップロード・分析要求はすべて成功する。broadcast の失敗は警告ログに記録されるが、メインフローを中断しない。アプリケーションの正常性は Redis の可用性に依存しない。

### 6. 状態の単一オーナー

各 Entity の状態は単一のレイヤーが所有する。Chat Core は Message と Evidence のみを変更し、DTM は Decision / HumanAction / ExecutionEvent のみを変更する。クロスレイヤーの直接変更は行わない。

---

*Last updated: 2026-05*
