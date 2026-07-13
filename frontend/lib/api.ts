/**
 * API Client
 * ==========
 * Central place for all backend communication.
 *
 * Why isolate API calls here?
 * - One place to change the base URL
 * - One place to add auth headers later
 * - Components stay clean — no fetch() noise
 * - Easy to mock in tests
 */

import {
  UploadResponse,
  ChatRequest,
  ChatResponse,
  Document,
  DocumentListResponse,
} from "./types";
import { API_ENDPOINTS } from "./constants";

// ── Generic fetch wrapper ─────────────────────────────────────

async function apiFetch<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
    },
  });

  if (!response.ok) {
    // Try to parse error body for a useful message
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // ignore parse error
    }
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}

// ── Upload API ────────────────────────────────────────────────

/**
 * Upload a document to the backend.
 * Uses FormData because we're sending a file (multipart/form-data).
 * Returns immediately — backend processes in background.
 */
export async function uploadDocument(
  file: File,
  userId: string = "default_user"
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);

  const response = await fetch(API_ENDPOINTS.upload, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type — browser sets it with boundary automatically
  });

  if (!response.ok) {
    let errorMessage = `Upload failed: HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {}
    throw new Error(errorMessage);
  }

  return response.json() as Promise<UploadResponse>;
}

// ── Documents API ─────────────────────────────────────────────

/**
 * List all documents for a user.
 * Called on the upload page to show existing documents.
 */
export async function listDocuments(
  userId: string = "default_user"
): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>(
    `${API_ENDPOINTS.documents}?user_id=${encodeURIComponent(userId)}`
  );
}

/**
 * Get the status of one document.
 * Used for polling during processing.
 */
export async function getDocument(documentId: string): Promise<Document> {
  return apiFetch<Document>(`${API_ENDPOINTS.documents}/${documentId}`);
}

/**
 * Delete a document.
 */
export async function deleteDocument(
  documentId: string,
  userId: string = "default_user"
): Promise<void> {
  await apiFetch(
    `${API_ENDPOINTS.documents}/${documentId}?user_id=${encodeURIComponent(userId)}`,
    { method: "DELETE" }
  );
}

// ── Chat API ──────────────────────────────────────────────────

/**
 * Send a question and get an answer with citations.
 */
export async function sendMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>(API_ENDPOINTS.chat, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

// ── Health API ────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(API_ENDPOINTS.health);
}

export async function warmupBackend(): Promise<void> {
  try {
    await fetch(API_ENDPOINTS.health);
  } catch {
    // Silently fail — backend will warm up on actual request
  }
}