'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useWebSocket } from '@/hooks/useWebSocket';
import {
  getChannels, createChannel, getMessages, postMessage,
  triggerAnalysis, getAnalysisSummary, getRanking, getEvidence,
} from '@/lib/api';
import { ChannelList } from '@/components/chat/ChannelList';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { LoginPage } from '@/components/chat/LoginPage';
import { ChatHeader } from '@/components/chat/core/ChatHeader';
import { ChatRightPanel } from '@/components/chat/core/ChatRightPanel';
import type { Channel, Message, WsEvent, AnalysisSummary, AnalysisCompletedPayload, UserRankingEntry } from '@/types';
import type { EvidenceItem } from '@/types/evidence';
import type { WsEventType } from '@/types/chat-core';
import type { ChatMode, ChatAction } from '@/types/chat-core';
import { CHAT_MODE_CONFIGS } from '@/types/chat-core';

const PAGE_SIZE = 50;

export default function ChatPage() {
  const { token, user, loading, logout } = useAuth();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const selectedIdRef = useRef<number | null>(null);
  selectedIdRef.current = selectedId;

  // ── ChatMode ─────────────────────────────────────────────────────
  const [chatMode, setChatMode] = useState<ChatMode>('signal');

  // ── AI 分析状態 ──────────────────────────────────────────────────
  const [analysisResults, setAnalysisResults] = useState<Record<number, AnalysisSummary>>({});
  const [analysisPending, setAnalysisPending] = useState<Set<number>>(new Set());
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // ── ランキング状態 ────────────────────────────────────────────────
  const [ranking, setRanking] = useState<UserRankingEntry[]>([]);
  const [rankingLoading, setRankingLoading] = useState(false);

  // ── Evidence 状態 ─────────────────────────────────────────────────
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);

  // ── チャンネル一覧 + 初回ランキング取得 ──
  useEffect(() => {
    if (!user) return;
    getChannels()
      .then((chs) => {
        setChannels(chs);
        if (chs.length > 0) setSelectedId(chs[0].id);
      })
      .catch(console.error);
    getRanking(1).then(setRanking).catch(() => {});
  }, [user?.id]);

  // ── チャンネル切り替え時にメッセージ・分析サマリー・Evidence 取得 ──
  useEffect(() => {
    if (!selectedId) return;
    setMessages([]);
    setHasMore(false);
    setAnalysisError(null);
    setEvidenceItems([]);
    getMessages(selectedId, PAGE_SIZE)
      .then((msgs) => {
        setMessages(msgs);
        setHasMore(msgs.length === PAGE_SIZE);
      })
      .catch(console.error);

    getAnalysisSummary(selectedId)
      .then((s) => {
        if (s) setAnalysisResults((prev) => ({ ...prev, [selectedId]: s }));
      })
      .catch(() => {});

    getEvidence(selectedId)
      .then(setEvidenceItems)
      .catch(() => {});
  }, [selectedId]);

  // ── 過去メッセージ追加読み込み ──
  const handleLoadMore = useCallback(async () => {
    if (!selectedId || loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const oldest = messages[0];
      const older = await getMessages(selectedId, PAGE_SIZE, oldest?.id);
      if (older.length === 0) {
        setHasMore(false);
      } else {
        setMessages((prev) => {
          const existingIds = new Set(prev.map((m) => m.id));
          return [...older.filter((m) => !existingIds.has(m.id)), ...prev];
        });
        if (older.length < PAGE_SIZE) setHasMore(false);
      }
    } catch (e) {
      console.error('Load more failed', e);
    } finally {
      setLoadingMore(false);
    }
  }, [selectedId, messages, loadingMore, hasMore]);

  // ── WebSocket イベント処理 ──
  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === 'message.created') {
      const msg = event.payload as Message;
      if (msg.channel_id !== selectedIdRef.current) return;
      setMessages((prev) => {
        if (prev.some((m) => m.id === msg.id)) return prev;
        return [...prev, msg];
      });
    }

    if (event.type === 'analysis.completed') {
      const { channel_id, result } = event.payload as AnalysisCompletedPayload;
      setAnalysisResults((prev) => ({ ...prev, [channel_id]: result }));
      setAnalysisPending((prev) => {
        const next = new Set(prev);
        next.delete(channel_id);
        return next;
      });
      setRankingLoading(true);
      getRanking(1)
        .then(setRanking)
        .catch(console.error)
        .finally(() => setRankingLoading(false));
    }

    if ((event.type as WsEventType) === 'evidence.created') {
      const item = event.payload as EvidenceItem;
      if (item.channel_id !== selectedIdRef.current) return;
      setEvidenceItems((prev) => {
        if (prev.some((e) => e.id === item.id)) return prev;
        return [item, ...prev];
      });
    }

    // TODO: decision.created / decision.updated / human_action.created /
    //       execution.requested / execution.completed / studio.sync.requested
    //       のハンドラは各 Module API 実装後に追加する
  }, []);

  const { status: wsStatus } = useWebSocket(token, handleWsEvent);

  // ── AI 分析リクエスト ──
  const handleAnalyze = useCallback(async () => {
    if (!selectedId) return;
    setAnalysisError(null);
    setAnalysisPending((prev) => new Set(prev).add(selectedId));
    try {
      await triggerAnalysis(selectedId);
    } catch {
      setAnalysisPending((prev) => {
        const next = new Set(prev);
        next.delete(selectedId);
        return next;
      });
      setAnalysisError('分析リクエストに失敗しました。再度お試しください。');
    }
  }, [selectedId]);

  // ── メッセージ送信 ──
  const handleSend = useCallback(async (content: string) => {
    if (!user || !selectedId) return;
    const msg = await postMessage(token, selectedId, content);
    setMessages((prev) => {
      if (prev.some((m) => m.id === msg.id)) return prev;
      return [...prev, msg];
    });
  }, [token, user, selectedId]);

  // ── チャンネル作成 ──
  const handleCreateChannel = useCallback(async (name: string) => {
    const ch = await createChannel(name);
    setChannels((prev) => [...prev, ch]);
    setSelectedId(ch.id);
  }, []);

  // ── チャンネル選択 ──
  const handleSelectChannel = useCallback((id: number) => {
    setSelectedId(id);
  }, []);

  // ── MessageAction ハンドラ ──
  const handleMessageAction = useCallback((action: ChatAction) => {
    console.info('[MessageAction]', action);
    // TODO: action.type に応じて各APIエンドポイントを呼ぶ
    // convert_to_decision → POST /decisions
    // approve / reject / request_revision / escalate → POST /human_actions
    // execute → POST /executions
    // send_to_studio → WS: studio.sync.requested
  }, []);

  // ── ローディング画面 ──
  if (loading) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#36393f',
        color: '#dcddde',
        fontSize: 16,
      }}>
        接続中…
      </div>
    );
  }

  if (!user) return <LoginPage />;

  const currentChannel = channels.find((c) => c.id === selectedId);
  const actionSlots = CHAT_MODE_CONFIGS[chatMode].actionSlots;

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#36393f', overflow: 'hidden' }}>

      {/* サイドバー */}
      <ChannelList
        channels={channels}
        selectedId={selectedId}
        onSelect={handleSelectChannel}
        onCreateChannel={handleCreateChannel}
        user={user}
        onLogout={logout}
      />

      {/* メインエリア */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* ChatHeader: チャンネル名 + WS状態 + ChatMode セレクター */}
        <ChatHeader
          channelName={currentChannel?.name ?? '...'}
          wsStatus={wsStatus}
          mode={chatMode}
          onModeChange={setChatMode}
        />

        {/* メッセージ一覧（MessageAction スロット付き） */}
        <MessageList
          messages={messages}
          currentUser={user}
          hasMore={hasMore}
          loadingMore={loadingMore}
          onLoadMore={handleLoadMore}
          actionSlots={actionSlots}
          onAction={handleMessageAction}
          evidenceItems={evidenceItems}
        />

        {/* 入力欄 */}
        {currentChannel && (
          <MessageInput
            channelId={currentChannel.id}
            channelName={currentChannel.name}
            onSubmit={handleSend}
          />
        )}
      </div>

      {/* ChatRightPanel: ChatMode に応じて右パネルを切り替え */}
      <ChatRightPanel
        mode={chatMode}
        channelId={selectedId}
        channelName={currentChannel?.name ?? '...'}
        summary={selectedId ? (analysisResults[selectedId] ?? null) : null}
        pending={selectedId ? analysisPending.has(selectedId) : false}
        error={analysisError}
        onAnalyze={handleAnalyze}
        ranking={ranking}
        rankingLoading={rankingLoading}
      />
    </div>
  );
}
