'use client';

import React from 'react';

interface Props {
  channelId: number | null;
}

// AgentCollaborationPanel: 複数Agentの提案を比較し人間が採否を決定するモジュール
// TODO: Orchestrator API から Agent提案リストを取得する
// TODO: 採用・修正・却下ボタンを Orchestrator / Ledger に接続する
export function AgentCollaborationPanel({ channelId }: Props) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        color: '#72767d',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
      }}>
        🤝 Agent Collaboration
      </div>

      <div style={{
        background: '#40444b',
        borderRadius: 6,
        padding: '10px 12px',
        fontSize: 12,
        lineHeight: 1.65,
      }}>
        <div style={{ marginBottom: 6, color: '#dcddde', fontWeight: 600 }}>Agent 提案リスト</div>
        <div style={{ color: '#4f545c', fontSize: 11 }}>
          TODO: 複数 Agent の提案が比較表示されます。
          人間が採用・修正・却下を選択できます。
          <br /><br />
          接続先: Orchestrator API（未実装）
        </div>
      </div>

      {/* プレースホルダー Agent 提案カード */}
      {PLACEHOLDER_AGENTS.map((agent) => (
        <div
          key={agent}
          style={{
            background: '#40444b',
            borderRadius: 6,
            padding: '8px 10px',
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: '#dcddde', marginBottom: 4 }}>{agent}</div>
          <div style={{ fontSize: 10, color: '#4f545c', marginBottom: 6 }}>
            TODO: {agent} の提案内容がここに表示されます
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {COLLAB_ACTIONS.map(({ label, color }) => (
              <button
                key={label}
                disabled
                style={{
                  padding: '2px 8px',
                  borderRadius: 10,
                  border: `1px solid ${color}44`,
                  background: `${color}11`,
                  color,
                  cursor: 'not-allowed',
                  fontSize: 10,
                  opacity: 0.55,
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      ))}

      <div style={{ fontSize: 10, color: '#4f545c' }}>
        TODO: Orchestrator / Ledger 本接続後に有効化
      </div>
    </div>
  );
}

const PLACEHOLDER_AGENTS = ['Agent A', 'Agent B', 'Agent C'];

const COLLAB_ACTIONS = [
  { label: '採用', color: '#3ba55d' },
  { label: '修正', color: '#faa61a' },
  { label: '却下', color: '#ed4245' },
];
