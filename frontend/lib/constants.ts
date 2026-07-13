// ── API Configuration ─────────────────────────────────────────
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const API_ENDPOINTS = {
  health:    `${API_BASE_URL}/api/health`,
  upload:    `${API_BASE_URL}/api/upload`,
  chat:      `${API_BASE_URL}/api/chat`,
  documents: `${API_BASE_URL}/api/documents`,
} as const;

// ── Upload Configuration ──────────────────────────────────────
export const MAX_FILE_SIZE_MB =
  Number(process.env.NEXT_PUBLIC_MAX_FILE_SIZE_MB) || 50;

export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export const ALLOWED_FILE_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
} as const;

export const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"] as const;

// ── Chat Configuration ────────────────────────────────────────
export const DEFAULT_USER_ID = "default_user";

export const MAX_QUESTION_LENGTH = 2000;
export const MAX_CONVERSATION_HISTORY = 20;

// ── UI Configuration ──────────────────────────────────────────
export const POLLING_INTERVAL_MS = 2000;   // How often to check doc status
export const MAX_POLLING_ATTEMPTS = 30;    // Give up after 60 seconds

export const TOAST_DURATION_MS = 4000;