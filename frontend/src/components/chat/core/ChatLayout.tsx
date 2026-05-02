'use client';

import React from 'react';

interface Props {
  sidebar: React.ReactNode;
  header: React.ReactNode;
  messages: React.ReactNode;
  input: React.ReactNode;
  rightPanel: React.ReactNode;
}

// ChatLayout: Chat Core の基本レイアウト骨格
// 用途依存ロジックを持たず、スロット経由で各領域を受け取る
export function ChatLayout({ sidebar, header, messages, input, rightPanel }: Props) {
  return (
    <div style={{ display: 'flex', height: '100vh', background: '#36393f', overflow: 'hidden' }}>
      {sidebar}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {header}
        {messages}
        {input}
      </div>
      {rightPanel}
    </div>
  );
}
