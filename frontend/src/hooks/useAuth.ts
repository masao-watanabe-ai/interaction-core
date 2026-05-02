'use client';

import { useState, useEffect } from 'react';
import { devLogin, getMe, logoutApi } from '@/lib/api';
import type { User } from '@/types';

/**
 * true  → dev-login モード: sessionStorage + Bearer token (開発用)
 * false → Google OAuth モード: HttpOnly Cookie 認証
 */
const DEV_LOGIN = process.env.NEXT_PUBLIC_DEV_LOGIN === 'true';

export function useAuth() {
  const [token, setToken] = useState<string | null>(null); // Bearer token (dev mode のみ使用)
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function init() {
      if (DEV_LOGIN) {
        // ── dev-login モード ──────────────────────────────────────
        let t = sessionStorage.getItem('token');
        if (!t) {
          const data = await devLogin(1);
          t = data.access_token;
          sessionStorage.setItem('token', t);
        }
        setToken(t);
        try {
          setUser(await getMe(t));
        } catch {
          // トークン期限切れ → 再取得
          sessionStorage.removeItem('token');
          const data = await devLogin(1);
          const newToken = data.access_token;
          sessionStorage.setItem('token', newToken);
          setToken(newToken);
          setUser(await getMe(newToken));
        }
      } else {
        // ── Google OAuth モード ───────────────────────────────────
        // HttpOnly Cookie が存在すれば /auth/me が 200 を返す
        try {
          setUser(await getMe()); // token なし → credentials: include で Cookie 送信
        } catch {
          // 未認証 または Cookie 期限切れ → ログインページを表示
        }
      }
    }

    init().catch(console.error).finally(() => setLoading(false));
  }, []);

  async function logout() {
    if (DEV_LOGIN) {
      sessionStorage.removeItem('token');
      setToken(null);
    } else {
      await logoutApi(); // Cookie を削除
    }
    setUser(null);
  }

  return { token, user, loading, logout };
}
