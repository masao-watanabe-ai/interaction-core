import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Chat AI Platform',
  description: 'Discord-like AI analysis chat system',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
