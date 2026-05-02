'use client';

import { useEffect, useRef, useState } from 'react';
import type { Message, User } from '@/types';
import type { ChatActionType, ChatAction } from '@/types/chat-core';
import type { EvidenceItem } from '@/types/evidence';
import { MessageActions } from '@/components/chat/core/MessageActions';
import { EvidenceActions } from '@/components/chat/core/EvidenceActions';

interface Props {
  messages: Message[];
  currentUser: User | null;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  // アクションスロット: 省略時はアクション非表示（後方互換）
  actionSlots?: ChatActionType[];
  onAction?: (action: ChatAction) => void;
  evidenceItems?: EvidenceItem[];
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function fileIcon(mimeType: string): string {
  if (mimeType.startsWith('image/')) return '🖼️';
  if (mimeType === 'application/pdf') return '📄';
  if (mimeType.includes('word')) return '📝';
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📊';
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return '📑';
  return '📎';
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  return (
    <div style={{
      display: 'inline-flex',
      flexDirection: 'column',
      background: '#2f3136',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 6,
      padding: '6px 10px',
      marginTop: 4,
      maxWidth: 360,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 18, flexShrink: 0 }}>{fileIcon(item.mime_type)}</span>
        <div style={{ minWidth: 0 }}>
          <div style={{
            color: '#00b0f4',
            fontSize: 13,
            fontWeight: 500,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {item.file_name}
          </div>
          <div style={{ color: '#72767d', fontSize: 11 }}>
            {item.file_size != null ? `${formatBytes(item.file_size)} · ` : ''}
            {formatDate(item.created_at)} {formatTime(item.created_at)}
          </div>
        </div>
      </div>
      <EvidenceActions evidenceId={item.id} />
    </div>
  );
}

export function MessageList({ messages, currentUser, hasMore, loadingMore, onLoadMore, actionSlots = [], onAction, evidenceItems = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const savedOffset = useRef(0);
  // ホバー中のメッセージID（アクションスロット表示用）
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  // message_id なし → Channel Evidence、あり → message_id でグループ化
  const channelEvidence = evidenceItems.filter((e) => !e.message_id);
  const evidenceByMessage = evidenceItems.reduce<Record<number, EvidenceItem[]>>((acc, e) => {
    if (e.message_id == null) return acc;
    (acc[e.message_id] ??= []).push(e);
    return acc;
  }, {});

  // メッセージ変化時: 上部読み込み後はスクロール位置を復元、それ以外は最下部へ
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (savedOffset.current > 0) {
      el.scrollTop = el.scrollHeight - savedOffset.current;
      savedOffset.current = 0;
    } else {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  function handleScroll() {
    const el = containerRef.current;
    if (!el || !hasMore || loadingMore) return;
    if (el.scrollTop < 80) {
      // 上部読み込み前にオフセットを記録
      savedOffset.current = el.scrollHeight - el.scrollTop;
      onLoadMore();
    }
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      style={{ flex: 1, overflowY: 'auto', padding: '8px 16px' }}
    >
      {/* 上部ローディング */}
      {loadingMore && (
        <div style={{ textAlign: 'center', padding: '8px 0', color: '#72767d', fontSize: 13 }}>
          読み込み中…
        </div>
      )}

      {/* Channel Evidence: message_id なしのファイル一覧 */}
      {channelEvidence.length > 0 && (
        <div style={{
          background: '#2f3136',
          borderRadius: 8,
          padding: '10px 14px',
          marginBottom: 12,
          borderLeft: '3px solid #5865f2',
        }}>
          <div style={{ color: '#b9bbbe', fontSize: 12, fontWeight: 600, marginBottom: 6, letterSpacing: '0.04em' }}>
            CHANNEL EVIDENCE
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {channelEvidence.map((item) => (
              <EvidenceCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* チャンネルの始まり */}
      {!hasMore && messages.length > 0 && (
        <div style={{
          textAlign: 'center',
          padding: '16px 0 8px',
          color: '#72767d',
          fontSize: 12,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          marginBottom: 8,
        }}>
          ── このチャンネルの始まりです ──
        </div>
      )}

      {/* 空状態 */}
      {messages.length === 0 && !loadingMore && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          color: '#72767d',
          fontSize: 14,
        }}>
          まだメッセージはありません。最初のメッセージを送ってみましょう！
        </div>
      )}

      {/* メッセージ一覧 */}
      {messages.map((msg, i) => {
        const prev = messages[i - 1];
        const isContinuation =
          prev?.user_id === msg.user_id &&
          new Date(msg.created_at).getTime() - new Date(prev.created_at).getTime() < 5 * 60 * 1000;
        const displayName =
          msg.user_id === currentUser?.id ? currentUser.display_name : `User ${msg.user_id}`;

        return (
          <div
            key={msg.id}
            onMouseEnter={() => actionSlots.length > 0 && setHoveredId(msg.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{ padding: isContinuation ? '1px 8px' : '16px 8px 1px', borderRadius: 4, position: 'relative' }}
          >
            {!isContinuation && (
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
                <span style={{ fontWeight: 600, fontSize: 15, color: '#fff' }}>
                  {displayName}
                </span>
                <span style={{ fontSize: 11, color: '#72767d' }}>
                  {formatDate(msg.created_at)} {formatTime(msg.created_at)}
                </span>
              </div>
            )}
            <div style={{
              color: '#dcddde',
              fontSize: 15,
              lineHeight: 1.4,
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
            {/* MessageAction スロット: ホバー時のみ表示 */}
            {actionSlots.length > 0 && onAction && hoveredId === msg.id && (
              <MessageActions
                messageId={msg.id}
                actionSlots={actionSlots}
                onAction={onAction}
              />
            )}
            {/* このメッセージに紐付いた Evidence カード */}
            {(evidenceByMessage[msg.id] ?? []).map((item) => (
              <EvidenceCard key={item.id} item={item} />
            ))}
          </div>
        );
      })}

      <div ref={bottomRef} />
    </div>
  );
}
