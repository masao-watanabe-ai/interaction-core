import type { Channel, Message, User, AnalysisSummary, AnalysisQueued, UserRankingEntry } from '@/types';
import type { EvidenceItem } from '@/types/evidence';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// credentials: "include" で Cookie を常に送信（Google OAuth Cookie 認証に必要）
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...init,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

const authHeader = (token: string) => ({ Authorization: `Bearer ${token}` });

// ── Auth ─────────────────────────────────────────────────────────────

export async function devLogin(userId: number) {
  return request<{ access_token: string; token_type: string }>('/auth/dev-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });
}

/**
 * Bearer token がある場合は Authorization ヘッダーで認証。
 * ない場合は credentials: "include" による Cookie 認証にフォールバック。
 */
export async function getMe(token?: string | null): Promise<User> {
  const headers: HeadersInit = {};
  if (token) Object.assign(headers, authHeader(token));
  return request<User>('/auth/me', { headers });
}

export async function logoutApi(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
}

// ── Channels ─────────────────────────────────────────────────────────

export async function getChannels() {
  return request<Channel[]>('/channels');
}

export async function createChannel(name: string) {
  return request<Channel>('/channels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
}

// ── Messages ─────────────────────────────────────────────────────────

export async function getMessages(channelId: number, limit = 50, beforeId?: number) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (beforeId !== undefined) params.set('before_id', String(beforeId));
  return request<Message[]>(`/channels/${channelId}/messages?${params}`);
}

/**
 * token がある場合は Bearer 認証、ない場合は Cookie 認証（credentials: include）。
 */
export async function postMessage(token: string | null, channelId: number, content: string) {
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (token) Object.assign(headers, authHeader(token));
  return request<Message>(`/channels/${channelId}/messages`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content }),
  });
}

// ── Analysis ─────────────────────────────────────────────────────────

export async function triggerAnalysis(channelId: number): Promise<AnalysisQueued> {
  return request<AnalysisQueued>(`/analysis/channels/${channelId}`, { method: 'POST' });
}

export async function getAnalysisSummary(channelId: number): Promise<AnalysisSummary | null> {
  const res = await fetch(`${BASE}/analysis/channels/${channelId}/summary`, {
    credentials: 'include',
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status}: /analysis/channels/${channelId}/summary`);
  return res.json() as Promise<AnalysisSummary>;
}

// ── Scores / Ranking ─────────────────────────────────────────────────

export async function getRanking(workspaceId = 1): Promise<UserRankingEntry[]> {
  return request<UserRankingEntry[]>(`/scores/ranking?workspace_id=${workspaceId}`);
}

// ── Evidence ─────────────────────────────────────────────────────────

export async function getEvidence(channelId: number): Promise<EvidenceItem[]> {
  return request<EvidenceItem[]>(`/evidence?channel_id=${channelId}`);
}

export async function uploadEvidence(channelId: number, file: File): Promise<unknown> {
  const form = new FormData();
  form.append('channel_id', String(channelId));
  form.append('file', file);
  const res = await fetch(`${BASE}/evidence/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!res.ok) throw new Error(`API ${res.status}: /evidence/upload`);
  return res.json();
}
