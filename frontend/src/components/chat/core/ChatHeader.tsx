'use client';

import React from 'react';
import type { ChatMode } from '@/types/chat-core';
import { CHAT_MODE_CONFIGS } from '@/types/chat-core';
import type { WsStatus } from '@/hooks/useWebSocket';

const WS_STATUS_MAP: Record<WsStatus, { color: string; label: string; pulse: boolean }> = {
  connecting:   { color: '#72767d', label: '接続中',   pulse: false },
  connected:    { color: '#3ba55d', label: '接続済み', pulse: false },
  reconnecting: { color: '#faa61a', label: '再接続中', pulse: true  },
  disconnected: { color: '#ed4245', label: '切断',     pulse: false },
};

interface Props {
  channelName: string;
  wsStatus: WsStatus;
  mode: ChatMode;
  onModeChange: (mode: ChatMode) => void;
}

// ChatHeader: チャンネル名・WS状態 + ChatMode セレクターを表示する
// モード切り替えにより右パネルとアクションスロットが変わる
export function ChatHeader({ channelName, wsStatus, mode, onModeChange }: Props) {
  const wsConfig = WS_STATUS_MAP[wsStatus];
  const modes = Object.values(CHAT_MODE_CONFIGS);

  return (
    <div style={{
      padding: '10px 16px 8px',
      borderBottom: '1px solid rgba(0,0,0,0.35)',
      background: '#36393f',
      flexShrink: 0,
    }}>
      {/* チャンネル名 + WS状態 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20, color: '#72767d' }}>#</span>
          <span style={{ fontWeight: 700, fontSize: 15, color: '#fff' }}>{channelName}</span>
        </div>
        <span
          className={wsConfig.pulse ? 'ws-reconnecting' : undefined}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, color: '#96989d' }}
        >
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: wsConfig.color, display: 'inline-block' }} />
          {wsConfig.label}
        </span>
      </div>

      {/* ChatMode セレクター */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {modes.map((cfg) => {
          const active = mode === cfg.mode;
          return (
            <button
              key={cfg.mode}
              onClick={() => onModeChange(cfg.mode)}
              title={cfg.label}
              style={{
                padding: '3px 10px',
                borderRadius: 12,
                border: `1px solid ${active ? '#5865f2' : 'rgba(255,255,255,0.1)'}`,
                background: active ? 'rgba(88,101,242,0.2)' : 'transparent',
                color: active ? '#5865f2' : '#72767d',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: active ? 600 : 400,
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
              }}
            >
              {cfg.icon} {cfg.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
