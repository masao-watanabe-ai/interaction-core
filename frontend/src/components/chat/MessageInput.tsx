import { useRef, useState } from 'react';
import { uploadEvidence } from '@/lib/api';

interface Props {
  channelId: number;
  channelName: string;
  onSubmit: (content: string) => Promise<void>;
}

export function MessageInput({ channelId, channelName, onSubmit }: Props) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadEvidence(channelId, file);
      console.log('Evidence upload OK', result);
    } catch (err) {
      console.error('Evidence upload failed', err);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  async function submit() {
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    setSending(true);
    try {
      await onSubmit(trimmed);
      setInput('');
    } catch (e) {
      console.error('Failed to send message', e);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const canSend = input.trim().length > 0 && !sending;

  return (
    <div style={{ padding: '0 16px 24px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: '#40444b',
        borderRadius: 8,
        padding: '0 12px',
        gap: 8,
      }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          title="ファイルを添付"
          style={{
            background: 'none',
            border: 'none',
            color: uploading ? '#72767d' : '#b9bbbe',
            fontSize: 22,
            lineHeight: 1,
            cursor: uploading ? 'not-allowed' : 'pointer',
            padding: '0 2px',
            flexShrink: 0,
          }}
        >
          {uploading ? '…' : '+'}
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`#${channelName} へメッセージを送信`}
          disabled={sending}
          maxLength={2000}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#dcddde',
            fontSize: 15,
            padding: '12px 0',
            caretColor: '#dcddde',
          }}
        />
        <button
          onClick={submit}
          disabled={!canSend}
          style={{
            background: canSend ? '#5865f2' : '#4e5058',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            padding: '6px 18px',
            cursor: canSend ? 'pointer' : 'not-allowed',
            fontSize: 14,
            fontWeight: 500,
            flexShrink: 0,
            opacity: canSend ? 1 : 0.6,
            transition: 'background 0.15s, opacity 0.15s',
          }}
        >
          {sending ? '送信中…' : '送信'}
        </button>
      </div>
      <div style={{ marginTop: 4, fontSize: 11, color: '#72767d', textAlign: 'right' }}>
        {input.length}/2000 　Enter で送信
      </div>
    </div>
  );
}
