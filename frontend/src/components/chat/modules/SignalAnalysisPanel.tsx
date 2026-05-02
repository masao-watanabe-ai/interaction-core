'use client';

import React from 'react';
import type { AnalysisSummary } from '@/types';

interface Props {
  channelId: number | null;
  channelName: string;
  summary: AnalysisSummary | null;
  pending: boolean;
  error: string | null;
  onAnalyze: () => void;
}

// AiPanel.tsx の Analysis タブ部分を抽出したモジュール
// Signal ≠ Decision の原則を維持: AI出力はSignalとして表示するのみ
export function SignalAnalysisPanel({ channelId, channelName, summary, pending, error, onAnalyze }: Props) {
  return (
    <>
      <button
        onClick={onAnalyze}
        disabled={!channelId || pending}
        style={{
          width: '100%',
          padding: '8px 0',
          background: pending ? '#4f545c' : '#5865f2',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          cursor: channelId && !pending ? 'pointer' : 'not-allowed',
          fontSize: 13,
          fontWeight: 600,
          marginBottom: 14,
          opacity: !channelId ? 0.5 : 1,
          transition: 'background 0.15s',
        }}
      >
        {pending ? '分析中…' : `#${channelName} を分析`}
      </button>

      {error && (
        <div style={{
          color: '#ed4245',
          fontSize: 12,
          marginBottom: 12,
          padding: '6px 10px',
          background: 'rgba(237,66,69,0.1)',
          borderRadius: 4,
        }}>
          {error}
        </div>
      )}

      {pending && !summary && (
        <div style={{
          color: '#faa61a',
          fontSize: 12,
          textAlign: 'center',
          paddingTop: 24,
          lineHeight: 1.8,
        }}>
          分析を実行中です…<br />
          <span style={{ fontSize: 10, color: '#72767d' }}>完了後に自動更新されます</span>
        </div>
      )}

      {summary && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{
            background: '#40444b',
            borderRadius: 6,
            padding: '10px 12px',
            fontSize: 12,
            color: '#dcddde',
            lineHeight: 1.65,
          }}>
            {summary.summary_text}
          </div>

          {summary.insights.length > 0 && (
            <div>
              <SectionLabel>重要ポイント（Signal）</SectionLabel>
              <ul style={{ margin: 0, padding: '0 0 0 16px', display: 'flex', flexDirection: 'column', gap: 4 }}>
                {summary.insights.map((insight, i) => (
                  <li key={i} style={{ fontSize: 12, color: '#dcddde', lineHeight: 1.6 }}>
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.suggested_actions.length > 0 && (
            <div>
              <SectionLabel>推奨アクション（Signal）</SectionLabel>
              <ul style={{ margin: 0, padding: '0 0 0 16px', display: 'flex', flexDirection: 'column', gap: 4 }}>
                {summary.suggested_actions.map((action, i) => (
                  <li key={i} style={{ fontSize: 12, color: '#43b581', lineHeight: 1.6 }}>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            <Metric label="メッセージ数" value={summary.total_messages} color="#5865f2" />
            <Metric label="参加ユーザー" value={summary.active_users} color="#3ba55d" />
            <Metric label="ポジティブ"   value={summary.positive_count} color="#3ba55d" />
            <Metric label="ネガティブ"   value={summary.negative_count} color="#ed4245" />
            <Metric label="質問"         value={summary.question_count} color="#faa61a" />
          </div>

          {summary.top_keywords.length > 0 && (
            <div>
              <SectionLabel>Top Keywords</SectionLabel>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {summary.top_keywords.slice(0, 10).map((kw) => (
                  <span
                    key={kw}
                    style={{
                      background: '#40444b',
                      color: '#dcddde',
                      fontSize: 11,
                      padding: '2px 8px',
                      borderRadius: 10,
                    }}
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div style={{ fontSize: 10, color: '#4f545c', textAlign: 'right' }}>
            {new Date(summary.analyzed_at).toLocaleString('ja-JP')}
          </div>
        </div>
      )}

      {!summary && !pending && !error && channelId && (
        <div style={{
          color: '#72767d',
          fontSize: 12,
          textAlign: 'center',
          paddingTop: 24,
          lineHeight: 1.8,
        }}>
          「分析する」ボタンを押して<br />チャンネルを分析します
        </div>
      )}
    </>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 10,
      fontWeight: 600,
      color: '#72767d',
      textTransform: 'uppercase' as const,
      letterSpacing: '0.06em',
      marginBottom: 6,
    }}>
      {children}
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ background: '#40444b', borderRadius: 6, padding: '8px 10px' }}>
      <div style={{ fontSize: 20, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 10, color: '#72767d', marginTop: 3 }}>{label}</div>
    </div>
  );
}
