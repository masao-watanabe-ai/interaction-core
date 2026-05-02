# Architecture — Chat Core

> A reusable Input / Interaction Layer for human conversation, file evidence, and AI signal routing.  
> Chat Core does not decide. It surfaces signals so that humans and upper layers can.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core Concept](#2-core-concept)
3. [System Architecture](#3-system-architecture)
4. [Data Model](#4-data-model)
5. [Interaction Model](#5-interaction-model)
6. [Evidence Model](#6-evidence-model)
7. [WebSocket Architecture](#7-websocket-architecture)
8. [Extension Points](#8-extension-points)
9. [Design Principles](#9-design-principles)
10. [Future Integration](#10-future-integration)

---

## 1. Overview

Chat Core is a **structured input and interaction surface** built for systems that need to combine real-time human conversation, file evidence, AI analysis, and decision routing — without conflating any of these concerns.

It is not a chat application. It is an **Input Core** that can be embedded into any product layer that requires a human-driven, signal-aware interaction surface. The channel is the unit of context. The message and evidence are the units of input. Everything beyond that — signals, decisions, approvals, executions — belongs to upper layers that Chat Core connects to, not contains.

Chat Core integrates with the **Decision Trace Model (DTM)**, a separate layer that owns the lifecycle of decisions, human approvals, and execution events. Chat Core provides the gateway; DTM owns the state.

---

## 2. Core Concept

### What Chat Core is

- A **real-time message surface**: text input, persistence, and multi-client delivery
- An **Evidence intake system**: structured file input with per-channel and per-message attachment
- A **Signal router**: AI analysis output surfaced to humans through a configurable UI
- An **interaction gateway to DTM**: action slots that forward human intent upstream

### What Chat Core is not

- A decision engine — it does not produce decisions
- A task management system — it does not track to-dos or statuses
- An approval workflow — it does not own approval state
- An execution system — it does not call external APIs on its own

### Input Core / Interaction Layer

```
Human Input
  │
  ├── Text (Message)        → stored, analyzed, broadcast
  └── File (Evidence)       → stored, indexed, action-ready
                                     │
                            AI Signal Layer
                                     │
                            ┌────────┴────────┐
                            │  Human reviews  │
                            │  signal, takes  │
                            │  action via     │
                            │  Chat Core UI   │
                            └────────┬────────┘
                                     │
                              DTM / Upper Layers
```

The boundary is explicit: Chat Core ends where Decision begins.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Chat Core                                                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   Message    │  │   Evidence   │  │      WebSocket         │ │
│  │  (text input)│  │ (file input) │  │  (real-time delivery)  │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ChatMode  ×  Action Slots  ×  Right Panel               │   │
│  │  (signal | human_gate | execute | studio | agent_collab) │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────────────────┐
          │                │                            │
          ▼                ▼                            ▼
  ┌──────────────┐ ┌───────────────────┐  ┌────────────────────┐
  │ Signal Layer │ │  Decision Layer   │  │   Execute Layer    │
  │              │ │  (DTM)            │  │                    │
  │ Rule-based + │ │                   │  │ External API calls │
  │ LLM analysis │ │ Decision          │  │ Execution tracking │
  │              │ │ HumanAction       │  │                    │
  │ → insights   │ │ ExecutionEvent    │  └────────────────────┘
  │ → scoring    │ │                   │
  └──────────────┘ │ proposed →        │  ┌────────────────────┐
                   │ reviewing →       │  │   Ledger           │
                   │ approved /        │  │                    │
                   │ rejected →        │  │ Immutable event    │
                   │ executed          │  │ log for audit,     │
                   └───────────────────┘  │ replay, trace      │
                                          └────────────────────┘
```

### Infrastructure

```
Browser
  │  HTTP REST  /  WebSocket
  ▼
┌───────────────────────────────────────────────────────────────┐
│  Backend  (FastAPI · Python 3.11)  :8000                       │
│                                                               │
│  Input routes:     /channels/{id}/messages                    │
│                    /evidence/upload  /evidence                │
│  DTM routes:       /decisions  /human_actions  /executions    │
│  Signal routes:    /analysis/channels/{id}                    │
│  WebSocket:        /ws                                        │
│                                                               │
│  services: websocket_service · redis_client · redis_subscriber│
└──────────┬───────────────────────────────┬────────────────────┘
           │                               │
      PostgreSQL 16                    Redis 7
      (persistence)                (Pub/Sub: chat_events
                                    RQ queue: analysis)
                                         │
                                    ┌────┴──────┐
                                    │ RQ Worker │
                                    │ Analysis  │
                                    │ Pipeline  │
                                    └───────────┘
```

**Tech stack**

| Layer | Technology |
|---|---|
| API | FastAPI 0.111, Python 3.11 |
| ORM | SQLAlchemy 2.0 async (asyncpg) |
| Frontend | Next.js 14, React 18, TypeScript |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7, RQ |
| LLM | OpenAI GPT-4o-mini (configurable) |
| Auth | JWT HS256 + Google OAuth 2.0 + HttpOnly Cookie |
| Container | Docker Compose |

---

## 4. Data Model

```
workspaces
  └── channels ──────────────────────────────────────────┐
        │                                                │
        ├── messages          ← CORE INPUT               │
        │     └── (future) evidence_items[message_id]   │
        │                                                │
        ├── evidence_items    ← CORE INPUT               │
        │                                                │
        ├── channel_analyses  ← Signal Layer output      │
        │                                                │
        ├── decisions         ← DTM (external)           │
        │     ├── human_actions                          │
        │     └── execution_events                       │
        │                                                │
        └── user_scores       ← Signal Layer output ─────┘
```

### Core entities (Chat Core owns)

| Entity | Type | Invariants |
|---|---|---|
| `messages` | Core input | Append-only. No edit, no delete. |
| `evidence_items` | Core input | Stored to `/uploads`. `extracted_text` is async-populated. |

### External entities (DTM owns)

| Entity | Status transitions | Source |
|---|---|---|
| `decisions` | proposed → reviewing → approved / rejected → executed | Human promotes from Signal |
| `human_actions` | Immutable log entries | Human action on a Decision |
| `execution_events` | pending → running → completed / failed | Execution request on a Decision |

The distinction is structural: Chat Core writes to `messages` and `evidence_items`. It reads from DTM tables for display purposes. It never transitions DTM state autonomously.

### Evidence schema

```
evidence_items
  id             SERIAL PK
  channel_id     FK → channels.id   NOT NULL
  uploaded_by    FK → users.id      NOT NULL
  file_name      TEXT NOT NULL
  file_path      TEXT NOT NULL       -- /uploads/{uuid}{ext}
  mime_type      TEXT NOT NULL
  extracted_text TEXT               -- NULL until Analyze action runs
  created_at     TIMESTAMPTZ
  -- reserved
  message_id     (future FK → messages.id)
  file_size      (future INTEGER)
```

---

## 5. Interaction Model

### Message post

```
User types → Enter / Send button
  → POST /channels/{id}/messages
  → INSERT messages
  → manager.broadcast("message.created")
  → All WebSocket clients receive event
  → Frontend deduplicates by id and appends to list
```

### Evidence upload

```
User clicks + → file picker (image / pdf / doc / ppt / xls)
  → POST /evidence/upload  (multipart: channel_id + file)
  → Store to /uploads/{uuid}{ext}
  → INSERT evidence_items  (extracted_text = NULL)
  → manager.broadcast("evidence.created")  -- fire-and-forget; upload already succeeded
  → Frontend appends EvidenceCard to channel or message
```

### Evidence Actions (per card)

| Action | Trigger | Backend (current) |
|---|---|---|
| Analyze | Button click | TODO: `POST /evidence/{id}/analyze` |
| Convert to Decision | Button click | TODO: `POST /decisions` with evidence source |
| Send to Studio | Button click | TODO: WS event `studio.sync.requested` |

### Message Actions (slot-based, mode-dependent)

| Action | DTM endpoint | Available in modes |
|---|---|---|
| convert_to_decision | `POST /decisions` | signal, studio, agent_collab |
| approve | `POST /human_actions` | human_gate, agent_collab |
| reject | `POST /human_actions` | human_gate, execute, agent_collab |
| request_revision | `POST /human_actions` | human_gate, agent_collab |
| escalate | `POST /human_actions` | human_gate |
| execute | `POST /executions` | execute |
| send_to_studio | WS event | signal, studio |

### ChatMode switch

Mode changes the active action slots and the right panel. It does not modify any data and does not change the channel context. It is a UI-level context switch, not a state transition.

---

## 6. Evidence Model

Evidence is **not an attachment**. It is a first-class input entity, equivalent in standing to a Message.

A Message captures human intent through language. An Evidence item captures it through a document, image, or structured file. Both are raw inputs that feed the Signal Layer and serve as source material for Decisions.

### Why Evidence is first-class

```
Message  →  "We should migrate to PostgreSQL"
Evidence →  migration-plan.pdf  (the document behind the proposal)

Both are inputs to the same channel context.
Both can become the source of a Decision.
Both are broadcast via WebSocket on creation.
Both persist in the database as immutable records.
```

### Evidence in the upper layers

```
evidence_items
  │
  ├── [Analyze]              → extracted_text populated
  │                            → becomes queryable content for Signal Layer
  │
  ├── [Convert to Decision]  → Decision created in DTM
  │                            with evidence_id as source reference
  │
  └── [Send to Studio]       → studio.sync.requested WS event
                               → Decision Trace Studio receives file context
```

### Display rules

- `message_id` is null → displayed in **Channel Evidence** section (top of MessageList)
- `message_id` is set  → displayed as a card **below the linked message**

---

## 7. WebSocket Architecture

### Connection lifecycle

```
Client → new WebSocket("ws://backend:8000/ws?token=...")
  → ws.py: decode token (Bearer query param or Cookie)
  → invalid: close(4001)  ← client does NOT reconnect on 4001
  → valid:   manager.connect(websocket)
             loop: receive_text()  (keep-alive, client sends nothing)
             disconnect: manager.disconnect(websocket)
```

### Broadcast reliability

```
manager.broadcast(event)
  │
  ├── publish_event(event)  →  Redis PUBLISH chat_events
  │     └── success: redis_subscriber_loop on every process
  │                  → manager.broadcast_local(event)
  │                  → all WebSocket clients on that process
  │
  └── publish fails (Redis down):
        → broadcast_local(event) on the calling process only
        → no cross-process delivery until Redis recovers

Evidence upload: broadcast wrapped in try/except
  → failure is logged as warning; upload response is unaffected
```

### Event reference

| Event | Direction | Payload | Status |
|---|---|---|---|
| `message.created` | S → C | `{id, channel_id, user_id, content, created_at}` | ✅ live |
| `analysis.completed` | S → C | `{channel_id, result: AnalysisSummary}` | ✅ live |
| `evidence.created` | S → C | `EvidenceItem` | ✅ live |
| `decision.created` | S → C | `Decision` | future |
| `decision.updated` | S → C | `Decision` | future |
| `human_action.created` | S → C | `HumanAction` | future |
| `execution.requested` | S → C | `ExecutionEvent` | future |
| `execution.completed` | S → C | `ExecutionEvent` | future |
| `studio.sync.requested` | S → C | `{evidence_id?, message_id?}` | future |

All state changes go through REST. WebSocket is delivery-only.

---

## 8. Extension Points

Chat Core's reusability rests on four composable slots. None of these require changes to core message or evidence logic.

### RightPanel Slot

The right panel is driven entirely by `ChatMode`. Each mode maps to a panel component:

```typescript
CHAT_MODE_CONFIGS: Record<ChatMode, ChatPanelConfig> = {
  signal:             { panel: AiAnalysis,  actionSlots: [...] },
  human_gate:         { panel: HumanGate,   actionSlots: [...] },
  execute:            { panel: Execute,     actionSlots: [...] },
  studio:             { panel: Studio,      actionSlots: [...] },
  agent_collaboration:{ panel: AgentCollab, actionSlots: [...] },
}
```

To add a new integration, add a `ChatMode` entry and provide a panel component. The message layer is unchanged.

### MessageActions

`MessageActions` renders a set of action buttons that appear on hover. The active set is determined by `actionSlots` from the current `ChatMode`. Adding a new action requires:

1. Add the `ChatActionType` to the type union
2. Add its config to `ACTION_CONFIG`
3. Wire its `onAction` handler in `page.tsx`

### EvidenceActions

`EvidenceActions` renders per-card action buttons. Currently: `analyze`, `convert_to_decision`, `send_to_studio`. Each maps to a future API call or WebSocket event. The component is stateless; the caller owns the side effect.

### ChatMode

ChatMode is the outermost context switch. It controls:

- Which action slots appear on messages
- Which panel renders on the right
- What the user interface communicates as the current intent

It does **not** filter messages, change the channel, or modify any persisted state. It is safe to switch at any time.

---

## 9. Design Principles

### Signal ≠ Decision

AI outputs are signals: insights, summaries, scores, keywords. A signal has no authority. It cannot approve, reject, create a task, or execute an action. A Decision is a separate entity, created by a named human, with an owner, a status, and a traceable history. The two must not be conflated.

### Chat Core does not decide

No code path in Chat Core transitions a Decision's status autonomously. No analysis result is written into a Decision record. No AI output triggers an approval, execution, or escalation. The system deliberately enforces this boundary. Removing it would transfer accountability from humans to the system — an outcome this architecture explicitly rejects.

### Evidence is first-class input

Evidence is not a message attachment. It is a parallel input type with its own persistence, schema, WebSocket event, and action surface. A file uploaded to a channel is as significant as a message posted to it. Both feed the Signal Layer. Both can originate a Decision.

### Everything is traceable

Every input — message, evidence upload, human action, execution event — is written to a permanent record with a timestamp and actor. The system does not overwrite or soft-delete. Analysis results are appended, not replaced. User scores are upserted with a `calculated_at` timestamp. The history is always recoverable.

### UI is slot-based

The interface exposes slots — action slots, panel slots — rather than hardcoded controls. Adding a new integration mode does not require modifying the message or evidence rendering path. New behavior is added by filling new slots, not by editing existing components.

### Separation of concerns

| Concern | Owner |
|---|---|
| Real-time message delivery | Chat Core + Redis Pub/Sub |
| File input and storage | Chat Core + filesystem |
| AI signal generation | Signal Layer (RQ Worker) |
| Decision lifecycle | DTM |
| Human approval tracking | DTM |
| Execution tracking | Execute Layer |
| Audit trail | Ledger (future) |

Each concern is owned by exactly one layer. Chat Core does not reach into DTM state. DTM does not write messages. The pipeline flows one way: input → signal → human decision → execution → ledger.

---

## 10. Future Integration

### Decision Trace Studio

A design environment for building Decision DSLs and Behavior Trees from conversation-derived signals. Chat Core connects via the `studio` ChatMode and the `send_to_studio` action, which emits a `studio.sync.requested` WebSocket event carrying message or evidence context.

### Multi-Agent Collaboration

Multiple AI agents propose, debate, and refine candidates within the `agent_collaboration` ChatMode. Chat Core provides the shared message surface and action slots for human arbitration (approve / reject / request_revision). Agent outputs are messages; human decisions remain with humans.

### Orchestrator

An external orchestrator (e.g., workflow engine or BT executor) subscribes to `execution.requested` and `execution.completed` events. Chat Core's Execute layer forwards human-approved execution intents upstream. Results flow back as WebSocket events and are displayed in the Execute panel.

### Ledger

An append-only, cryptographically verifiable log of all significant events: decision state transitions, human actions, execution outcomes. Chat Core emits the events; the Ledger stores and indexes them for audit, replay, and traceability. The Ledger is a consumer of Chat Core's event stream — it does not modify Chat Core's behavior.

---

*Last updated: 2026-05*
