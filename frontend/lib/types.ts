// ═══════════════════════════════════════════════════════════
// SHARED TYPESCRIPT TYPE DEFINITIONS
// ═══════════════════════════════════════════════════════════

// ── Document Types ───────────────────────────────────────────

export type DocumentStatus = "uploading" | "processing" | "ready" | "error";

export interface Document {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  chunk_count?: number;
  error_message?: string;
  created_at: string;       // ISO 8601 datetime string
  file_size_bytes: number;
}

export interface DocumentListResponse {
  documents: Document[];
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

// ── Chat Types ────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  role: MessageRole;
  content: string;
}

export interface Citation {
  source_id: string;
  document_name: string;
  page_number?: number;
  chunk_index: number;
  relevance_score: number;
  excerpt: string;
}

export interface Message {
  id: string;               // Frontend-generated UUID
  role: MessageRole;
  content: string;
  citations?: Citation[];   // Only present on assistant messages
  timestamp: Date;
  isStreaming?: boolean;    // True while tokens are arriving
}

export interface ChatRequest {
  question: string;
  session_id: string;
  user_id: string;
  conversation_history: Array<{
    role: MessageRole;
    content: string;
  }>;
  document_ids?: string[];
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  session_id: string;
  model_used: string;
  retrieval_count: number;
  has_relevant_sources: boolean;
}

export interface ChatMessage {
  role: MessageRole;
  content: string;
}

// ── API State Types ───────────────────────────────────────────

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export interface UploadProgress {
  document_id: string;
  filename: string;
  progress: number;         // 0-100
  status: DocumentStatus;
  error?: string;
}

// ── UI Types ──────────────────────────────────────────────────

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";