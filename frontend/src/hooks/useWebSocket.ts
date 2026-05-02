'use client';

import { useState, useEffect, useRef } from 'react';
import type { WsEvent } from '@/types';

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

type Handler = (event: WsEvent) => void;

const RECONNECT_DELAY_MS = 3000;

/**
 * true  → dev-login モード: ?token={token} を query param で送信
 * false → Google OAuth モード: Cookie を自動送信（token なし）
 */
const DEV_LOGIN = process.env.NEXT_PUBLIC_DEV_LOGIN === 'true';

export function useWebSocket(token: string | null, onEvent: Handler) {
  const [status, setStatus] = useState<WsStatus>('disconnected');
  const handlerRef = useRef<Handler>(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    // dev mode: token が揃うまで待つ
    // cookie mode: token 不要（Cookie が自動送信される）
    const shouldConnect = DEV_LOGIN ? token !== null : true;

    if (!shouldConnect) {
      setStatus('disconnected');
      return;
    }

    let cancelled = false;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (cancelled) return;
      setStatus('connecting');

      const base = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
        .replace(/^http/, 'ws');

      // dev mode: ?token=... で Bearer JWT を送信
      // cookie mode: Cookie は WebSocket 接続時に自動送信される
      const url = (DEV_LOGIN && token) ? `${base}/ws?token=${token}` : `${base}/ws`;
      ws = new WebSocket(url);

      ws.onopen = () => {
        if (cancelled) { ws?.close(); return; }
        setStatus('connected');
      };

      ws.onmessage = (e) => {
        try { handlerRef.current(JSON.parse(e.data) as WsEvent); } catch { /* ignore */ }
      };

      // onerror は onclose の直前に呼ばれるので onclose に任せる
      ws.onerror = () => {};

      ws.onclose = (event) => {
        if (cancelled) return;
        // 認証失敗 (4001) はリトライしない
        if (event.code === 4001) {
          setStatus('disconnected');
          return;
        }
        setStatus('reconnecting');
        timer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      ws?.close();
      setStatus('disconnected');
    };
  }, [token]);

  return { status };
}
