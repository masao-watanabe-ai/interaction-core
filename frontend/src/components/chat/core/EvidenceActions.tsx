'use client';

export type EvidenceActionType = 'analyze' | 'convert_to_decision' | 'send_to_studio';

const ACTION_CONFIG: Record<EvidenceActionType, { label: string; icon: string; color: string }> = {
  analyze:             { label: 'Analyze',          icon: '🔍', color: '#faa61a' },
  convert_to_decision: { label: 'Convert to Decision', icon: '📋', color: '#5865f2' },
  send_to_studio:      { label: 'Send to Studio',   icon: '🎨', color: '#3ba55d' },
};

interface Props {
  evidenceId: number;
}

export function EvidenceActions({ evidenceId }: Props) {
  function handleClick(action: EvidenceActionType) {
    console.log('[EvidenceAction]', { evidence_id: evidenceId, action });
    // TODO: analyze → POST /evidence/{id}/analyze (extracted_text 生成)
    // TODO: convert_to_decision → POST /decisions (evidence_id を source として渡す)
    // TODO: send_to_studio → WS event: studio.sync.requested { evidence_id }
  }

  return (
    <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
      {(Object.keys(ACTION_CONFIG) as EvidenceActionType[]).map((actionType) => {
        const cfg = ACTION_CONFIG[actionType];
        return (
          <button
            key={actionType}
            onClick={() => handleClick(actionType)}
            style={{
              padding: '2px 8px',
              borderRadius: 10,
              border: `1px solid ${cfg.color}44`,
              background: `${cfg.color}11`,
              color: cfg.color,
              cursor: 'pointer',
              fontSize: 10,
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 3,
              transition: 'all 0.15s',
            }}
            title={cfg.label}
          >
            <span>{cfg.icon}</span>
            <span>{cfg.label}</span>
          </button>
        );
      })}
    </div>
  );
}
