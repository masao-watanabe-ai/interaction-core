'use client';

import React, { useState } from 'react';
import type { UserRankingEntry } from '@/types';

interface Props {
  ranking: UserRankingEntry[];
  loading: boolean;
}

const LEVEL_CONFIG: Record<string, { emoji: string; color: string; bg: string; border: string }> = {
  Platinum: { emoji: '💎', color: '#e5e4e2', bg: 'rgba(229,228,226,0.10)', border: 'rgba(229,228,226,0.25)' },
  Gold:     { emoji: '🏆', color: '#ffd700', bg: 'rgba(255,215,0,0.10)',   border: 'rgba(255,215,0,0.30)'   },
  Silver:   { emoji: '🥈', color: '#c0c0c0', bg: 'rgba(192,192,192,0.10)', border: 'rgba(192,192,192,0.25)' },
  Bronze:   { emoji: '🥉', color: '#cd7f32', bg: 'rgba(205,127,50,0.10)',  border: 'rgba(205,127,50,0.25)'  },
};

const TOP_RANK_EMOJI: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' };

function ScoreBar({
  label,
  value,
  color,
  percent = false,
}: {
  label: string;
  value: number;
  color: string;
  percent?: boolean;
}) {
  const display = percent ? `${value}%` : `${Math.round(value * 100)}%`;
  const width = percent ? value : value * 100;
  return (
    <div style={{ marginBottom: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <span style={{ fontSize: 9, color: '#72767d' }}>{label}</span>
        <span style={{ fontSize: 9, color, fontWeight: 600 }}>{display}</span>
      </div>
      <div style={{ height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.min(100, width)}%`,
            height: '100%',
            background: color,
            borderRadius: 2,
            transition: 'width 0.5s ease',
          }}
        />
      </div>
    </div>
  );
}

function EnthusiasmBar({ value }: { value: number }) {
  const color = value >= 80 ? '#faa61a' : value >= 50 ? '#5865f2' : '#3ba55d';
  return (
    <div style={{ height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden', marginTop: 4 }}>
      <div style={{ width: `${value}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.4s ease' }} />
    </div>
  );
}

function ImpactBadge({ score }: { score: number }) {
  const color = score >= 70 ? '#faa61a' : score >= 40 ? '#5865f2' : '#72767d';
  return (
    <div style={{
      background: `${color}22`,
      border: `1px solid ${color}55`,
      borderRadius: 10,
      padding: '1px 6px',
      fontSize: 9,
      color,
      fontWeight: 700,
      whiteSpace: 'nowrap' as const,
    }}>
      影響力 {score}%
    </div>
  );
}

export function RankingPanel({ ranking, loading }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (userId: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(userId) ? next.delete(userId) : next.add(userId);
      return next;
    });
  };

  if (loading) {
    return (
      <div style={{ color: '#72767d', fontSize: 12, textAlign: 'center', paddingTop: 24, lineHeight: 1.8 }}>
        ランキングを更新中…
      </div>
    );
  }

  if (ranking.length === 0) {
    return (
      <div style={{ color: '#72767d', fontSize: 12, textAlign: 'center', paddingTop: 24, lineHeight: 1.8 }}>
        「分析する」を実行すると<br />
        ユーザーランキングが表示されます
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {ranking.map((entry) => {
        const cfg = LEVEL_CONFIG[entry.level] ?? LEVEL_CONFIG.Bronze;
        const rankLabel = TOP_RANK_EMOJI[entry.rank] ?? `#${entry.rank}`;
        const isExpanded = expanded.has(entry.user_id);
        const hasQuality = entry.impact_score > 0;

        return (
          <div
            key={entry.user_id}
            style={{
              background: cfg.bg,
              border: `1px solid ${cfg.border}`,
              borderRadius: 6,
              overflow: 'hidden',
            }}
          >
            {/* ── Main row ── */}
            <div style={{ padding: '8px 10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* Rank */}
                <div style={{
                  fontSize: entry.rank <= 3 ? 16 : 11,
                  minWidth: 22,
                  textAlign: 'center',
                  color: entry.rank <= 3 ? undefined : '#72767d',
                  fontWeight: 700,
                }}>
                  {rankLabel}
                </div>

                {/* Name + badges */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: '#dcddde',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap' as const,
                    marginBottom: 2,
                  }}>
                    {entry.display_name}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' as const }}>
                    <span style={{ fontSize: 9, color: cfg.color, fontWeight: 700 }}>
                      {cfg.emoji} {entry.level}
                    </span>
                    {hasQuality && <ImpactBadge score={entry.impact_score} />}
                  </div>
                </div>

                {/* Points + expand toggle */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2, flexShrink: 0 }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: cfg.color, lineHeight: 1 }}>
                    {entry.points.toLocaleString()}
                  </div>
                  <div style={{ fontSize: 9, color: '#72767d' }}>pts</div>
                  <button
                    onClick={() => toggle(entry.user_id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#72767d',
                      fontSize: 10,
                      padding: 0,
                      marginTop: 2,
                    }}
                    title="詳細を見る"
                  >
                    {isExpanded ? '▲' : '▼'}
                  </button>
                </div>
              </div>

              {/* Enthusiasm bar */}
              <EnthusiasmBar value={entry.enthusiasm_score} />
              <div style={{ fontSize: 9, color: '#72767d', marginTop: 2, textAlign: 'right' }}>
                熱量 {entry.enthusiasm_score}%
              </div>
            </div>

            {/* ── Expanded quality detail ── */}
            {isExpanded && (
              <div style={{
                borderTop: `1px solid ${cfg.border}`,
                padding: '8px 10px',
                background: 'rgba(0,0,0,0.15)',
              }}>
                <div style={{
                  fontSize: 9,
                  fontWeight: 600,
                  color: '#72767d',
                  textTransform: 'uppercase' as const,
                  letterSpacing: '0.06em',
                  marginBottom: 6,
                }}>
                  スコア内訳
                </div>

                {hasQuality ? (
                  <>
                    <ScoreBar
                      label="洞察力 (Insight)"
                      value={entry.insight_quality_score}
                      color="#5865f2"
                    />
                    <ScoreBar
                      label="議論への影響 (Discussion Impact)"
                      value={entry.discussion_impact_score}
                      color="#3ba55d"
                    />
                    <ScoreBar
                      label="意思決定貢献 (Decision)"
                      value={entry.decision_contribution_score}
                      color="#faa61a"
                    />
                    <div style={{
                      marginTop: 6,
                      padding: '4px 8px',
                      background: 'rgba(255,255,255,0.04)',
                      borderRadius: 4,
                    }}>
                      <ScoreBar
                        label="総合影響力スコア"
                        value={entry.impact_score}
                        color={entry.impact_score >= 70 ? '#faa61a' : entry.impact_score >= 40 ? '#5865f2' : '#72767d'}
                        percent
                      />
                    </div>
                  </>
                ) : (
                  <div style={{ fontSize: 10, color: '#4f545c', textAlign: 'center', padding: '4px 0' }}>
                    分析を実行するとスコアが表示されます
                  </div>
                )}

                {/* Activity breakdown */}
                <div style={{
                  marginTop: 8,
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 4,
                }}>
                  {[
                    { label: '投稿', value: entry.points },
                    { label: '熱量', value: `${entry.enthusiasm_score}%` },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 4, padding: '4px 6px' }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: '#dcddde' }}>{value}</div>
                      <div style={{ fontSize: 9, color: '#72767d' }}>{label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
