'use client';

import React, { useState } from 'react';
import type { ChatMode } from '@/types/chat-core';
import type { AnalysisSummary, UserRankingEntry } from '@/types';
import { SignalAnalysisPanel } from '@/components/chat/modules/SignalAnalysisPanel';
import { RankingPanel } from '@/components/chat/RankingPanel';
import { HumanGatePanel } from '@/components/chat/modules/HumanGatePanel';
import { ExecutePanel } from '@/components/chat/modules/ExecutePanel';
import { StudioAssistantPanel } from '@/components/chat/modules/StudioAssistantPanel';
import { AgentCollaborationPanel } from '@/components/chat/modules/AgentCollaborationPanel';

interface Props {
  mode: ChatMode;
  channelId: number | null;
  channelName: string;
  // signal モード用 props
  summary: AnalysisSummary | null;
  pending: boolean;
  error: string | null;
  onAnalyze: () => void;
  ranking: UserRankingEntry[];
  rankingLoading: boolean;
}

// ChatRightPanel: ChatMode に応じて右パネルを切り替えるスロットコンポーネント
// 用途別ロジックは各 Module に委譲し、Core はスロット管理のみを行う
export function ChatRightPanel(props: Props) {
  const { mode } = props;

  return (
    <div style={{
      width: 272,
      flexShrink: 0,
      background: '#2f3136',
      borderLeft: '1px solid rgba(0,0,0,0.35)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {mode === 'signal' && <SignalPanel {...props} />}
      {mode === 'human_gate' && <HumanGatePanel channelId={props.channelId} />}
      {mode === 'execute' && <ExecutePanel channelId={props.channelId} />}
      {mode === 'studio' && <StudioAssistantPanel channelId={props.channelId} />}
      {mode === 'agent_collaboration' && <AgentCollaborationPanel channelId={props.channelId} />}
    </div>
  );
}

// SignalPanel: signal モード専用（Analysis + Ranking タブ）
// AiPanel.tsx と同等の機能を提供する
function SignalPanel(props: Props) {
  const [tab, setTab] = useState<'analysis' | 'ranking'>('analysis');

  return (
    <>
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(0,0,0,0.35)', flexShrink: 0 }}>
        <TabButton active={tab === 'analysis'} onClick={() => setTab('analysis')}>
          🤖 AI 分析
        </TabButton>
        <TabButton active={tab === 'ranking'} onClick={() => setTab('ranking')}>
          🏆 ランキング
        </TabButton>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {tab === 'analysis' ? (
          <SignalAnalysisPanel
            channelId={props.channelId}
            channelName={props.channelName}
            summary={props.summary}
            pending={props.pending}
            error={props.error}
            onAnalyze={props.onAnalyze}
          />
        ) : (
          <RankingPanel ranking={props.ranking} loading={props.rankingLoading} />
        )}
      </div>
    </>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: '10px 8px',
        background: active ? '#36393f' : 'transparent',
        color: active ? '#fff' : '#72767d',
        border: 'none',
        borderBottom: active ? '2px solid #5865f2' : '2px solid transparent',
        cursor: 'pointer',
        fontSize: 11,
        fontWeight: 600,
        transition: 'color 0.15s, background 0.15s',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </button>
  );
}
