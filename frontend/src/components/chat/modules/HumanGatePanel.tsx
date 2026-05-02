'use client';

import React from 'react';

interface Props {
  channelId: number | null;
}

// HumanGatePanel: 人間が承認・却下・修正・保留・エスカレーションを行うモジュール
// TODO: /decisions?channel_id={channelId}&status=proposed から承認待ちDecisionを取得
// TODO: 各ボタンを POST /human_actions に接続する
export function HumanGatePanel({ channelId }: Props) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        color: '#72767d',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
      }}>
        🚦 Human Gate
      </div>

      {/* TODO: GET /decisions?channel_id={channelId}&status=proposed */}
      <div style={{
        background: '#40444b',
        borderRadius: 6,
        padding: '10px 12px',
        fontSize: 12,
        lineHeight: 1.65,
      }}>
        <div style={{ marginBottom: 6, color: '#dcddde', fontWeight: 600 }}>承認待ち Decision</div>
        <div style={{ color: '#4f545c', fontSize: 11 }}>
          TODO: 承認待ちのDecision候補がここに表示されます。
          <br /><br />
          接続先:{' '}
          <code style={{ color: '#5865f2' }}>GET /decisions?status=proposed</code>
        </div>
      </div>

      {/* アクションボタン群 — バックエンドAPI実装後に有効化 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {GATE_ACTIONS.map(({ label, color, actionType }) => (
          <button
            key={actionType}
            disabled
            title={`TODO: POST /human_actions { action_type: "${actionType}" }`}
            style={{
              padding: '7px 10px',
              borderRadius: 4,
              border: `1px solid ${color}44`,
              background: `${color}11`,
              color,
              cursor: 'not-allowed',
              fontSize: 12,
              opacity: 0.55,
              textAlign: 'left',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div style={{ fontSize: 10, color: '#4f545c', marginTop: 4 }}>
        TODO: ボタンは <code>POST /human_actions</code> 実装後に有効化
      </div>
    </div>
  );
}

const GATE_ACTIONS = [
  { label: '✅ 承認 (Approve)',       color: '#3ba55d', actionType: 'approve'          },
  { label: '❌ 却下 (Reject)',         color: '#ed4245', actionType: 'reject'           },
  { label: '📝 修正依頼 (Revise)',     color: '#faa61a', actionType: 'revise'           },
  { label: '⏸ 保留 (Hold)',           color: '#72767d', actionType: 'hold'             },
  { label: '🔺 エスカレーション',      color: '#ed4245', actionType: 'escalate'         },
];
