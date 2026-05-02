CREATE TABLE IF NOT EXISTS users (
    id           SERIAL PRIMARY KEY,
    google_id    VARCHAR(255) UNIQUE,
    email        VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    avatar_url   VARCHAR(512),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspaces (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    slug       VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS channels (
    id           SERIAL PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id) NOT NULL,
    name         VARCHAR(255) NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (workspace_id, name)
);

CREATE TABLE IF NOT EXISTS messages (
    id         SERIAL PRIMARY KEY,
    channel_id INTEGER REFERENCES channels(id) NOT NULL,
    user_id    INTEGER REFERENCES users(id) NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS channel_analyses (
    id                SERIAL PRIMARY KEY,
    channel_id        INTEGER REFERENCES channels(id) NOT NULL,
    total_messages    INTEGER NOT NULL DEFAULT 0,
    positive_count    INTEGER NOT NULL DEFAULT 0,
    negative_count    INTEGER NOT NULL DEFAULT 0,
    question_count    INTEGER NOT NULL DEFAULT 0,
    active_users      INTEGER NOT NULL DEFAULT 0,
    top_keywords      JSONB NOT NULL DEFAULT '[]',
    summary_text      TEXT NOT NULL DEFAULT '',
    insights          JSONB NOT NULL DEFAULT '[]',
    suggested_actions JSONB NOT NULL DEFAULT '[]',
    analyzed_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Migration: add LLM columns to existing DB (idempotent)
ALTER TABLE channel_analyses ADD COLUMN IF NOT EXISTS insights          JSONB NOT NULL DEFAULT '[]';
ALTER TABLE channel_analyses ADD COLUMN IF NOT EXISTS suggested_actions JSONB NOT NULL DEFAULT '[]';

CREATE INDEX IF NOT EXISTS idx_channel_analyses_channel_id ON channel_analyses(channel_id);

-- Seed: demo user (id=1 固定)
INSERT INTO users (id, email, display_name)
VALUES (1, 'demo@example.com', 'Demo User')
ON CONFLICT (id) DO NOTHING;

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- Seed: default workspace (id=1 固定)
INSERT INTO workspaces (id, name, slug)
VALUES (1, 'Default Workspace', 'default')
ON CONFLICT (id) DO NOTHING;

SELECT setval('workspaces_id_seq', (SELECT MAX(id) FROM workspaces));

-- Seed: initial channels
INSERT INTO channels (workspace_id, name)
VALUES (1, 'general'), (1, 'random'), (1, 'ai-analysis')
ON CONFLICT (workspace_id, name) DO NOTHING;

CREATE TABLE IF NOT EXISTS user_scores (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER REFERENCES users(id) NOT NULL,
    workspace_id            INTEGER REFERENCES workspaces(id) NOT NULL,
    message_count           INTEGER NOT NULL DEFAULT 0,
    reply_count             INTEGER NOT NULL DEFAULT 0,
    reaction_received_count INTEGER NOT NULL DEFAULT 0,
    question_count          INTEGER NOT NULL DEFAULT 0,
    positive_count          INTEGER NOT NULL DEFAULT 0,
    important_message_count INTEGER NOT NULL DEFAULT 0,
    enthusiasm_score        FLOAT NOT NULL DEFAULT 0.0,
    points                  INTEGER NOT NULL DEFAULT 0,
    level                   VARCHAR(20) NOT NULL DEFAULT 'Bronze',
    rank                    INTEGER NOT NULL DEFAULT 0,
    calculated_at           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_user_scores_workspace_rank ON user_scores(workspace_id, rank);

-- Migration: add semantic quality columns (idempotent)
ALTER TABLE user_scores ADD COLUMN IF NOT EXISTS insight_quality_score      FLOAT NOT NULL DEFAULT 0.0;
ALTER TABLE user_scores ADD COLUMN IF NOT EXISTS discussion_impact_score    FLOAT NOT NULL DEFAULT 0.0;
ALTER TABLE user_scores ADD COLUMN IF NOT EXISTS decision_contribution_score FLOAT NOT NULL DEFAULT 0.0;

-- ── Chat Core Platform 拡張テーブル (idempotent) ──────────────────────

CREATE TABLE IF NOT EXISTS decisions (
    id                SERIAL PRIMARY KEY,
    channel_id        INTEGER REFERENCES channels(id) NOT NULL,
    source_message_id INTEGER REFERENCES messages(id),
    title             TEXT NOT NULL,
    description       TEXT,
    status            TEXT NOT NULL DEFAULT 'proposed',
    owner_user_id     INTEGER REFERENCES users(id),
    created_by        INTEGER REFERENCES users(id) NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_channel_id ON decisions(channel_id);
CREATE INDEX IF NOT EXISTS idx_decisions_status     ON decisions(status);

CREATE TABLE IF NOT EXISTS human_actions (
    id          SERIAL PRIMARY KEY,
    decision_id INTEGER REFERENCES decisions(id) NOT NULL,
    user_id     INTEGER REFERENCES users(id) NOT NULL,
    action_type TEXT NOT NULL,
    comment     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_human_actions_decision_id ON human_actions(decision_id);

CREATE TABLE IF NOT EXISTS execution_events (
    id               SERIAL PRIMARY KEY,
    decision_id      INTEGER REFERENCES decisions(id) NOT NULL,
    execution_type   TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending',
    request_payload  JSONB,
    response_payload JSONB,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_execution_events_decision_id ON execution_events(decision_id);
CREATE INDEX IF NOT EXISTS idx_execution_events_status      ON execution_events(status);

-- ── Evidence 保存テーブル (idempotent) ──────────────────────────────

CREATE TABLE IF NOT EXISTS evidence_items (
    id             SERIAL PRIMARY KEY,
    channel_id     INTEGER REFERENCES channels(id) NOT NULL,
    uploaded_by    INTEGER REFERENCES users(id)    NOT NULL,
    file_name      TEXT NOT NULL,
    file_path      TEXT NOT NULL,
    mime_type      TEXT NOT NULL,
    extracted_text TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_items_channel_id ON evidence_items(channel_id);
