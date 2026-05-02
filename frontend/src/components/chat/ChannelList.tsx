'use client';

import { useState } from 'react';
import type { Channel, User } from '@/types';

interface Props {
  channels: Channel[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onCreateChannel: (name: string) => Promise<void>;
  user: User | null;
  onLogout?: () => void;
}

export function ChannelList({ channels, selectedId, onSelect, onCreateChannel, user, onLogout }: Props) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name || submitting) return;
    setSubmitting(true);
    try {
      await onCreateChannel(name);
      setNewName('');
      setCreating(false);
    } catch (err) {
      console.error('Failed to create channel', err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{
      width: 240,
      flexShrink: 0,
      background: '#2f3136',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* ワークスペース名 */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid rgba(0,0,0,0.35)',
        fontWeight: 700,
        fontSize: 15,
        color: '#fff',
        letterSpacing: '-0.01em',
      }}>
        Chat AI Platform
      </div>

      {/* チャンネルラベル + 「+」ボタン */}
      <div style={{
        padding: '16px 16px 4px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#72767d',
        }}>
          Channels
        </span>
        <button
          onClick={() => { setCreating((v) => !v); setNewName(''); }}
          title="チャンネルを作成"
          style={{
            background: 'none',
            border: 'none',
            color: '#72767d',
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: '0 2px',
            borderRadius: 3,
          }}
        >
          +
        </button>
      </div>

      {/* チャンネル作成フォーム（インライン） */}
      {creating && (
        <form onSubmit={handleCreate} style={{ padding: '4px 8px 8px' }}>
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && setCreating(false)}
            placeholder="チャンネル名"
            maxLength={80}
            disabled={submitting}
            style={{
              width: '100%',
              background: '#40444b',
              border: '1px solid #5865f2',
              borderRadius: 4,
              padding: '6px 10px',
              color: '#dcddde',
              fontSize: 13,
              outline: 'none',
            }}
          />
          <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
            <button
              type="submit"
              disabled={!newName.trim() || submitting}
              style={{
                flex: 1,
                background: '#5865f2',
                color: '#fff',
                border: 'none',
                borderRadius: 3,
                padding: '4px 0',
                cursor: 'pointer',
                fontSize: 12,
                opacity: newName.trim() ? 1 : 0.5,
              }}
            >
              {submitting ? '作成中…' : '作成'}
            </button>
            <button
              type="button"
              onClick={() => setCreating(false)}
              style={{
                flex: 1,
                background: '#4f545c',
                color: '#dcddde',
                border: 'none',
                borderRadius: 3,
                padding: '4px 0',
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              キャンセル
            </button>
          </div>
        </form>
      )}

      {/* チャンネル一覧 */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {channels.map((ch) => {
          const active = ch.id === selectedId;
          return (
            <div
              key={ch.id}
              onClick={() => onSelect(ch.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 8px 6px 12px',
                margin: '1px 8px',
                borderRadius: 4,
                cursor: 'pointer',
                background: active ? '#393c43' : 'transparent',
                color: active ? '#fff' : '#8e9297',
                fontSize: 15,
                fontWeight: active ? 500 : 400,
                userSelect: 'none',
              }}
            >
              <span style={{ fontSize: 18, opacity: 0.6, lineHeight: 1 }}>#</span>
              {ch.name}
            </div>
          );
        })}
      </div>

      {/* ログインユーザー */}
      {user && (
        <div style={{
          padding: '8px 12px',
          background: '#292b2f',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          borderTop: '1px solid rgba(0,0,0,0.2)',
        }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: '#5865f2',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: 14,
            color: '#fff',
            flexShrink: 0,
          }}>
            {user.display_name.charAt(0).toUpperCase()}
          </div>
          <div style={{ overflow: 'hidden', flex: 1 }}>
            <div style={{
              fontSize: 13,
              fontWeight: 600,
              color: '#dcddde',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {user.display_name}
            </div>
            <div style={{ fontSize: 11, color: '#72767d' }}>Online</div>
          </div>
          {onLogout && (
            <button
              onClick={onLogout}
              title="ログアウト"
              style={{
                background: 'none',
                border: 'none',
                color: '#72767d',
                cursor: 'pointer',
                fontSize: 15,
                padding: '2px 4px',
                borderRadius: 3,
                flexShrink: 0,
              }}
            >
              ⏏
            </button>
          )}
        </div>
      )}
    </div>
  );
}
