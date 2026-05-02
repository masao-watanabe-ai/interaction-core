export interface EvidenceItem {
  id: number;
  channel_id: number;
  uploaded_by: number;
  file_name: string;
  file_path: string;
  mime_type: string;
  extracted_text: string | null;
  created_at: string;
  // optional fields — not in current backend model, reserved for future
  message_id?: number | null;
  file_size?: number | null;
}
