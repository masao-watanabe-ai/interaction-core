'use client';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908C16.658 14.215 17.64 11.907 17.64 9.2z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  );
}

export function LoginPage() {
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#36393f',
      gap: 20,
    }}>
      {/* ロゴ / タイトル */}
      <div style={{
        width: 64,
        height: 64,
        borderRadius: 16,
        background: '#5865f2',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 32,
        marginBottom: 4,
      }}>
        &#128172;
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>
        Chat AI Platform
      </div>
      <div style={{ fontSize: 13, color: '#72767d' }}>
        アカウントにログインして続けてください
      </div>

      {/* Google ログインボタン */}
      <a
        href={`${BASE}/auth/google`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 10,
          padding: '11px 24px',
          background: '#fff',
          color: '#3c4043',
          textDecoration: 'none',
          borderRadius: 6,
          fontWeight: 600,
          fontSize: 14,
          marginTop: 8,
          boxShadow: '0 2px 10px rgba(0,0,0,0.4)',
          transition: 'box-shadow 0.15s',
        }}
      >
        <GoogleLogo />
        Google でログイン
      </a>

      <div style={{ fontSize: 11, color: '#4f545c', marginTop: 4 }}>
        ログインすることで利用規約に同意したとみなされます
      </div>
    </div>
  );
}
