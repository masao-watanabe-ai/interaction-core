# Interaction Core

> **Where human inputs become structured signals.**  
> A reusable Input / Interaction Layer that surfaces what matters — and keeps decisions where they belong: with humans.

---

## What is this?

Interaction Core is not a chat application. It is an **Input / Interaction Layer** — a structured surface for capturing human conversation, file evidence, and AI-generated signals, then routing them to the systems that act on them.

The unit of interaction is the **channel**. Within a channel, two types of input exist on equal footing: **Messages** (text) and **Evidence** (files). Both are captured, persisted, analyzed, and made actionable. Neither produces a decision by itself.

Above the input layer sit external systems — a Signal Layer that analyzes content, a Decision Layer (DTM) that tracks outcomes, a Human Gate that records approvals, an Execute Layer that calls external APIs. Interaction Core connects to all of these. It owns none of them.

---

## Why this exists

Modern collaborative tools are built for volume, not clarity. The result is a set of structural problems that compound over time:

**Signal drowns in noise.** Thousands of messages accumulate with no differentiation between a critical insight and a passing comment. Important inputs are indistinguishable from background chatter.

**Decisions are invisible.** Agreements, blockers, and action items are buried in message threads. They are never surfaced, rarely tracked, and almost never traceable back to their origin.

**Evidence is scattered.** Relevant documents, specs, and reports live in separate systems with no connection to the conversation where they were discussed. Context is lost at the boundary.

**AI is made the decision-maker.** Most AI integrations present model outputs as instructions. This removes accountability from the humans who should own outcomes and creates a false sense of resolution — "the AI said to do X" is not a decision, it is an excuse.

Interaction Core addresses each of these at the structural level. It does not fix them with features layered onto an existing chat tool. It builds the input surface correctly from the start.

---

## Core Concept

- **Input = Message + Evidence** — text and files are first-class, parallel input types
- **Signal ≠ Decision** — AI analysis produces signals; humans convert signals into decisions
- **Chat Core does not decide** — no code path in this layer creates, approves, or executes a decision autonomously
- **Human is always the decision owner** — every decision is made by a named person with a traceable record
- **DTM is the decision layer** — Decision / HumanAction / ExecutionEvent are owned by the Decision Trace Model, not this layer
- **Everything is traceable** — messages, evidence, human actions, and execution events are all immutable records

---

## What you can do

**Input**
- Post real-time messages to a channel
- Upload files as Evidence (image / PDF / Word / PowerPoint / Excel)
- Attach Evidence to a specific message or to the channel context

**Evidence Actions** _(per Evidence item)_
- **Analyze** — extract text content for Signal Layer consumption
- **Convert to Decision** — promote the Evidence to a Decision candidate in DTM
- **Send to Studio** — forward to Decision Trace Studio for DSL / Behavior Tree design

**Signal Layer** _(optional, requires OpenAI API key)_
- Per-channel AI analysis: emotion classification, keyword extraction, LLM summary, insights, suggested actions
- Per-user contribution scoring: insight quality, discussion impact, decision contribution
- Live ranking panel, updated after each analysis cycle

**Interaction Surface**
- ChatMode switcher: configure the right panel and action slots per use case
- MessageActions: slot-based action buttons per message (convert, approve, reject, execute, escalate)
- Real-time WebSocket delivery via Redis Pub/Sub with automatic fallback

**Auth**
- Google OAuth 2.0 (HttpOnly Cookie, production-ready)
- Dev login (Bearer token, zero configuration required)

---

## Architecture

```
Interaction Core
  ├── Message          text input — append-only, broadcast, analyzed
  ├── Evidence         file input — stored, indexed, action-ready
  ├── WebSocket        real-time delivery (Redis Pub/Sub + local fallback)
  ├── ChatMode         UI context switch (signal / human_gate / execute / studio / agent_collab)
  └── Action Slots     MessageActions + EvidenceActions — slot-based, mode-driven

          │
          ▼  connects to — does not contain

  ┌───────────────┐  ┌─────────────────────┐  ┌────────────────────┐
  │ Signal Layer  │  │  Decision Layer      │  │   Execute Layer    │
  │               │  │  (DTM)               │  │                    │
  │ Rule-based +  │  │  Decision            │  │ External API calls │
  │ LLM analysis  │  │  HumanAction         │  │ Execution tracking │
  │ User scoring  │  │  ExecutionEvent      │  └────────────────────┘
  └───────────────┘  └─────────────────────┘
                                                ┌────────────────────┐
                                                │   Ledger           │
                                                │ Immutable audit    │
                                                │ trail (future)     │
                                                └────────────────────┘
```

**Infrastructure**

```
Browser
  │  HTTP REST / WebSocket
  ▼
FastAPI :8000
  ├── /channels/{id}/messages   — message input
  ├── /evidence                 — file input
  ├── /decisions                — DTM gateway
  ├── /human_actions            — DTM gateway
  ├── /executions               — DTM gateway
  ├── /analysis/channels/{id}   — signal trigger
  └── /ws                       — WebSocket endpoint
         │
    ┌────┴────┐     ┌──────────────────────┐
    │ Postgres│     │  Redis               │
    │ (data)  │     │  Pub/Sub: chat_events│
    └─────────┘     │  RQ queue: analysis  │
                    └──────────┬───────────┘
                               │
                          ┌────┴──────┐
                          │ RQ Worker │  6-step analysis pipeline
                          └───────────┘
```

**Tech stack**

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 · Python 3.11 |
| ORM | SQLAlchemy 2.0 async (asyncpg) |
| Frontend | Next.js 14 · React 18 · TypeScript |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 · RQ |
| LLM | OpenAI GPT-4o-mini (configurable, optional) |
| Auth | JWT HS256 · Google OAuth 2.0 · HttpOnly Cookie |
| Container | Docker Compose |

---

## Quick Start

**Prerequisites:** Docker · Docker Compose · (optional) OpenAI API key · (optional) Google OAuth credentials

```bash
git clone https://github.com/your-org/interaction-core.git
cd interaction-core
cp .env.example .env
docker compose up --build
```

| URL | Purpose |
|---|---|
| `http://localhost:3000` | Interaction UI |
| `http://localhost:8000/docs` | API reference (Swagger) |

Dev login mode is on by default. You are signed in as `Demo User` automatically — no Google credentials needed.

**Health checks**

```bash
curl http://localhost:8000/health     # {"status":"ok"}
curl http://localhost:8000/health/db  # {"database":"ok"}
```

**Run tests**

```bash
# Full suite (Docker)
docker compose exec backend pytest tests/ -v

# Unit tests only (no Docker required)
cd backend && python -m pytest tests/test_score_service.py -v
```

**Stop**

```bash
docker compose down       # stop
docker compose down -v    # stop + reset database
```

---

## Signal ≠ Decision

This is the foundational constraint of the system — and the one most commonly violated by AI tooling.

AI analysis produces **Signals**: summaries, insights, keyword patterns, quality scores, suggested actions. A Signal has no authority. It cannot approve a proposal, create a task, or commit to a course of action. It is an observation, made precise.

A **Decision** is structurally different. It has an owner — a named human who can be held accountable. It has a status that transitions through a defined lifecycle: proposed → reviewing → approved / rejected → executed. It has a creation timestamp and a history of who acted on it and when.

Conflating Signal and Decision produces three failures:

1. **Accountability dissolves.** "The AI recommended it" becomes a shield against ownership.
2. **Context is discarded.** Signals are derived from text. Real decisions involve context that no text captures.
3. **Judgment atrophies.** If the model decides, there is no loop through which the team's reasoning can improve.

Interaction Core enforces the boundary structurally. No analysis result writes into a Decision record. No Signal transitions a status. Converting a Signal into a Decision requires a human action, recorded as an immutable `HumanAction` event in DTM.

> The system tells you what is happening.  
> It does not tell you what to do about it.

---

## Signal Quality Scoring

User contributions are scored across two independent dimensions.

**Activity signals** (rule-based, deterministic)

| Signal | Weight |
|---|---|
| Message sent | ×2 |
| Reply (starts with `@`) | ×3 |
| Reaction received | ×5 |
| Question asked | ×2 |
| Positive message | ×3 |
| High-importance message (contains `!`) | ×10 |

**Quality signals** (LLM-derived, per analysis cycle)

| Signal | Weight | What it measures |
|---|---|---|
| Insight quality | ×10 | Depth and precision of knowledge shared |
| Discussion impact | ×5 | Degree to which the user drives the conversation forward |
| Decision contribution | ×20 | Shaping outcomes and resolving blockers |

```
total_points = activity_points
             + insight_quality_score       × 10
             + discussion_impact_score     × 5
             + decision_contribution_score × 20
```

These scores measure **observable contribution quality**, not seniority or authority. A single insight that reframes the discussion outscores fifty acknowledgements.

| Level | Threshold |
|---|---|
| Platinum | 1,000 pts |
| Gold | 500 pts |
| Silver | 200 pts |
| Bronze | 0 pts |

---

## Future Integration

| System | Connection point |
|---|---|
| **Decision Trace Studio** | `studio` ChatMode · `send_to_studio` action slot · `studio.sync.requested` WS event |
| **Multi-Agent Collaboration** | `agent_collaboration` ChatMode · shared message surface for agent proposals and human arbitration |
| **Orchestrator** | `execution.requested` / `execution.completed` WS events · Execute Layer integration |
| **Ledger** | Consumer of all WS events · Immutable append-only audit log for decisions, actions, and executions |

---

## Project Structure

```
interaction-core/
├── docker-compose.yml
├── .env.example
├── db/
│   └── init.sql                     # Schema + seed data (idempotent)
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan, CORS, router registry
│   │   ├── models/                  # ORM: Message, Evidence, Decision, HumanAction, ExecutionEvent
│   │   ├── routes/                  # messages, evidence, decisions, human_actions, executions,
│   │   │                            #   analysis, scores, auth, ws
│   │   ├── services/
│   │   │   ├── websocket_service.py # ConnectionManager + Redis Pub/Sub broadcast
│   │   │   ├── redis_client.py      # Async Redis singleton, publish_event()
│   │   │   ├── redis_subscriber.py  # Long-running subscriber loop
│   │   │   ├── llm_service.py       # OpenAI: channel analysis + per-user quality scoring
│   │   │   └── score_service.py     # Scoring weights, compute_points, recalculate
│   │   └── worker/
│   │       └── analysis_worker.py   # RQ job: 6-step analysis pipeline
│   └── tests/
│       └── test_score_service.py    # 36 unit tests, no Docker required
└── frontend/
    └── src/
        ├── app/page.tsx             # Root state: channels, messages, evidenceItems, analysis, ranking
        ├── components/chat/
        │   ├── MessageList.tsx      # Infinite scroll · Evidence cards · MessageActions
        │   ├── MessageInput.tsx     # Text composer · Evidence upload (+ button)
        │   ├── ChannelList.tsx      # Sidebar
        │   └── core/
        │       ├── ChatHeader.tsx   # Channel name · WS status · ChatMode selector
        │       ├── ChatRightPanel.tsx  # Mode-driven right panel
        │       ├── MessageActions.tsx  # Slot-based action buttons per message
        │       └── EvidenceActions.tsx # Analyze · Convert · Send to Studio
        ├── hooks/
        │   ├── useAuth.ts           # Dev login / Google OAuth mode switch
        │   └── useWebSocket.ts      # Auto-reconnect, 4001 auth-failure guard
        ├── lib/api.ts               # Typed fetch client, credentials: include
        └── types/
            ├── index.ts             # Message, Channel, User, AnalysisSummary
            ├── evidence.ts          # EvidenceItem
            └── chat-core.ts        # ChatMode, ChatActionType, WsEventType, CHAT_MODE_CONFIGS
```

---

## License

MIT
