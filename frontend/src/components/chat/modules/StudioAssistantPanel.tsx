'use client';

import React from 'react';

interface Props {
  channelId: number | null;
}

// StudioAssistantPanel: Decision Trace Studio との対話的設計支援モジュール
// TODO: WS event "studio.sync.requested" を送信して Studio に同期する
// TODO: Decision Trace Studio / Orchestrator への本接続を実装する
export function StudioAssistantPanel({ channelId }: Props) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        color: '#72767d',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
      }}>
        🎨 Studio Assistant
      </div>

      <div style={{
        background: '#40444b',
        borderRadius: 6,
        padding: '10px 12px',
        fontSize: 12,
        lineHeight: 1.65,
      }}>
        <div style={{ marginBottom: 6, color: '#dcddde', fontWeight: 600 }}>DSL / Behavior Tree 設計</div>
        <div style={{ color: '#4f545c', fontSize: 11 }}>
          TODO: Decision Trace Studio との接続により、意思決定フロー・DSL・Behavior Tree を
          対話的に設計・修正できるようになります。
          <br /><br />
          WS Event:{' '}
          <code style={{ color: '#3ba55d' }}>studio.sync.requested</code>
        </div>
      </div>

      <div style={{
        background: '#40444b',
        borderRadius: 6,
        padding: '10px 12px',
      }}>
        <div style={{ fontSize: 11, color: '#72767d', marginBottom: 6 }}>現在のフロー</div>
        <div style={{ color: '#4f545c', fontSize: 11 }}>
          TODO: チャンネルに関連付けられた Decision Trace がここに表示されます。
        </div>
      </div>

      <button
        disabled
        title="TODO: WS event studio.sync.requested を実装後に有効化"
        style={{
          padding: '8px 0',
          width: '100%',
          borderRadius: 4,
          border: '1px solid rgba(59,165,93,0.4)',
          background: 'rgba(59,165,93,0.1)',
          color: '#3ba55d',
          cursor: 'not-allowed',
          fontSize: 12,
          opacity: 0.55,
        }}
      >
        🎨 Studioに送信
      </button>

      <div style={{ fontSize: 10, color: '#4f545c' }}>
        TODO: Decision Trace Studio / Orchestrator 本接続後に有効化
      </div>
    </div>
  );
}
