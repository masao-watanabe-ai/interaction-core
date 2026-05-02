'use client';

import React from 'react';
import type { ChatActionType, ChatAction } from '@/types/chat-core';

const ACTION_CONFIG: Record<ChatActionType, { label: string; icon: string; color: string }> = {
  convert_to_decision: { label: 'Decision化', icon: '📋', color: '#5865f2' },
  approve:             { label: '承認',        icon: '✅', color: '#3ba55d' },
  reject:              { label: '却下',        icon: '❌', color: '#ed4245' },
  request_revision:    { label: '修正依頼',    icon: '📝', color: '#faa61a' },
  execute:             { label: '実行',        icon: '⚡', color: '#faa61a' },
  send_to_studio:      { label: 'Studioへ',   icon: '🎨', color: '#3ba55d' },
  escalate:            { label: 'エスカレ',    icon: '🔺', color: '#ed4245' },
};

interface Props {
  messageId: number;
  actionSlots: ChatActionType[];
  onAction: (action: ChatAction) => void;
}

// MessageActions: メッセージに対して用途別アクションを提供するスロット
// 各アクションのバックエンド接続は TODO コメントで示す
export function MessageActions({ messageId, actionSlots, onAction }: Props) {
  if (actionSlots.length === 0) return null;

  return (
    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
      {actionSlots.map((actionType) => {
        const cfg = ACTION_CONFIG[actionType];
        return (
          <button
            key={actionType}
            onClick={() => {
              // TODO: 各アクションのバックエンド接続
              // convert_to_decision → POST /decisions
              // approve/reject/request_revision/escalate → POST /human_actions
              // execute → POST /executions
              // send_to_studio → WS event: studio.sync.requested
              onAction({ type: actionType, label: cfg.label, icon: cfg.icon, messageId });
            }}
            style={{
              padding: '2px 8px',
              borderRadius: 10,
              border: `1px solid ${cfg.color}44`,
              background: `${cfg.color}11`,
              color: cfg.color,
              cursor: 'pointer',
              fontSize: 10,
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 3,
              transition: 'all 0.15s',
            }}
            title={cfg.label}
          >
            <span>{cfg.icon}</span>
            <span>{cfg.label}</span>
          </button>
        );
      })}
    </div>
  );
}
