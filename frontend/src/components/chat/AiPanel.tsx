'use client';

import React, { useState } from 'react';
import type { AnalysisSummary, UserRankingEntry } from '@/types';
import { RankingPanel } from './RankingPanel';
import { SignalAnalysisPanel } from './modules/SignalAnalysisPanel';

interface Props {
  channelId: number | null;
  channelName: string;
  summary: AnalysisSummary | null;
  pending: boolean;
  error: string | null;
  onAnalyze: () => void;
  ranking: UserRankingEntry[];
  rankingLoading: boolean;
}

type Tab = 'analysis' | 'ranking';

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
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
        whiteSpace: 'nowrap' as const,
      }}
    >
      {children}
    </button>
  );
}

export function AiPanel({ channelId, channelName, summary, pending, error, onAnalyze, ranking, rankingLoading }: Props) {
  const [tab, setTab] = useState<Tab>('analysis');

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
      {/* Tab bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid rgba(0,0,0,0.35)',
        flexShrink: 0,
      }}>
        <TabButton active={tab === 'analysis'} onClick={() => setTab('analysis')}>
          🤖 AI 分析
        </TabButton>
        <TabButton active={tab === 'ranking'} onClick={() => setTab('ranking')}>
          🏆 ランキング
        </TabButton>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {tab === 'analysis' ? (
          /* Analysis タブは SignalAnalysisPanel に委譲 */
          <SignalAnalysisPanel
            channelId={channelId}
            channelName={channelName}
            summary={summary}
            pending={pending}
            error={error}
            onAnalyze={onAnalyze}
          />
        ) : (
          <RankingPanel ranking={ranking} loading={rankingLoading} />
        )}
      </div>
    </div>
  );
}
