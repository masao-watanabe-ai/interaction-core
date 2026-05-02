'use client';

import React from 'react';

interface Props {
  channelId: number | null;
}

// ExecutePanel: 外部API実行前確認・実行指示・実行結果通知モジュール
// TODO: GET /executions?channel_id={channelId}&status=pending から実行待ちタスクを取得
// TODO: 実行ボタンを POST /executions に接続する
// TODO: WS event "execution.completed" で結果を受信して表示する
export function ExecutePanel({ channelId }: Props) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        color: '#72767d',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
      }}>
        ⚡ Execute Chat
      </div>

      {/* TODO: GET /executions?status=pending */}
      <div style={{
        background: '#40444b',
        borderRadius: 6,
        padding: '10px 12px',
        fontSize: 12,
        lineHeight: 1.65,
      }}>
        <div style={{ marginBottom: 6, color: '#dcddde', fontWeight: 600 }}>実行待ちタスク</div>
        <div style={{ color: '#4f545c', fontSize: 11 }}>
          TODO: 外部API実行前確認・実行指示・結果通知がここに表示されます。
          <br /><br />
          接続先:{' '}
          <code style={{ color: '#faa61a' }}>GET /executions?status=pending</code>
        </div>
      </div>

      {/* 実行履歴プレースホルダー */}
      <div style={{
        background: '#40444b',
        borderRadius: 6,
        padding: '10px 12px',
      }}>
        <div style={{ fontSize: 11, color: '#72767d', marginBottom: 6 }}>実行履歴</div>
        <div style={{ color: '#4f545c', fontSize: 11 }}>
          TODO: ExecutionEvent ログがここに表示されます。
          <br />
          WS Event: <code style={{ color: '#faa61a' }}>execution.completed</code>
          <br />
          接続先: <code style={{ color: '#faa61a' }}>GET /executions</code>
        </div>
      </div>

      <div style={{ fontSize: 10, color: '#4f545c' }}>
        TODO: Execute処理は <code>/executions</code> API および Decision連携実装後に有効化
      </div>
    </div>
  );
}
