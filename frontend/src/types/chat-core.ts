// ChatMode: Chat Core Platform の動作モードを定義する
// 各モードは右パネルとメッセージアクションスロットを切り替える
export type ChatMode =
  | 'signal'              // Signal Chat: AI分析・Signal抽出
  | 'human_gate'          // Human Gate Chat: 承認・却下・修正・保留
  | 'execute'             // Execute Chat: 外部API実行確認・実行指示・結果通知
  | 'studio'              // Decision Trace Studio Chat: DSL/BT設計
  | 'agent_collaboration'; // Agent Collaboration Chat: 複数Agent提案の比較・採否

export interface ChatContext {
  channelId: number | null;
  channelName: string;
  mode: ChatMode;
  workspaceId: number;
}

// ChatMessage: 既存の Message 型に用途別メタデータを追加したもの
export interface ChatMessage {
  id: number;
  channel_id: number;
  user_id: number;
  content: string;
  created_at: string;
  // 用途別モジュールが付加するオプションメタデータ
  metadata?: Record<string, unknown>;
}

// ChatActionType: メッセージまたはDecision候補に対して行える操作
export type ChatActionType =
  | 'convert_to_decision' // AI Signalを正式Decision候補に変換
  | 'approve'             // 承認
  | 'reject'              // 却下
  | 'request_revision'    // 修正依頼
  | 'execute'             // 外部API実行指示
  | 'send_to_studio'      // Decision Trace Studioへ送信
  | 'escalate';           // エスカレーション

export interface ChatAction {
  type: ChatActionType;
  label: string;
  icon?: string;
  messageId: number;
  payload?: unknown;
}

// ChatPanelConfig: モードごとの右パネル設定とアクションスロット定義
export interface ChatPanelConfig {
  mode: ChatMode;
  label: string;
  icon: string;
  actionSlots: ChatActionType[];
}

// CHAT_MODE_CONFIGS: 各モードのデフォルト設定
export const CHAT_MODE_CONFIGS: Record<ChatMode, ChatPanelConfig> = {
  signal: {
    mode: 'signal',
    label: 'Signal Chat',
    icon: '🤖',
    actionSlots: ['convert_to_decision', 'send_to_studio'],
  },
  human_gate: {
    mode: 'human_gate',
    label: 'Human Gate',
    icon: '🚦',
    actionSlots: ['approve', 'reject', 'request_revision', 'escalate'],
  },
  execute: {
    mode: 'execute',
    label: 'Execute Chat',
    icon: '⚡',
    actionSlots: ['execute', 'reject'],
  },
  studio: {
    mode: 'studio',
    label: 'Studio Chat',
    icon: '🎨',
    actionSlots: ['send_to_studio', 'convert_to_decision'],
  },
  agent_collaboration: {
    mode: 'agent_collaboration',
    label: 'Agent Collab',
    icon: '🤝',
    actionSlots: ['approve', 'reject', 'request_revision', 'convert_to_decision'],
  },
};

// WebSocket イベント型 (既存 + 新規追加)
export type WsEventType =
  | 'message.created'         // 既存
  | 'analysis.completed'      // 既存
  | 'evidence.created'        // Evidence アップロード完了通知
  | 'decision.created'        // TODO: DecisionModel実装後に有効化
  | 'decision.updated'        // TODO: DecisionModel実装後に有効化
  | 'human_action.created'    // TODO: HumanActionModel実装後に有効化
  | 'execution.requested'     // TODO: ExecutionEvent実装後に有効化
  | 'execution.completed'     // TODO: ExecutionEvent実装後に有効化
  | 'studio.sync.requested';  // TODO: Decision Trace Studio接続後に有効化
