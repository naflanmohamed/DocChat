/**
 * useUpload Hook
 * ==============
 * Manages the complete upload flow:
 * 1. Accept dropped/selected files
 * 2. Validate type and size
 * 3. Upload to backend
 * 4. Poll for processing completion
 * 5. Expose state to the upload page
 */

import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { uploadDocument, listDocuments, getDocument } from "@/lib/api";
import { Document, UploadProgress } from "@/lib/types";
import {
  MAX_FILE_SIZE_BYTES,
  ALLOWED_EXTENSIONS,
  DEFAULT_USER_ID,
  POLLING_INTERVAL_MS,
  MAX_POLLING_ATTEMPTS,
} from "@/lib/constants";

interface UseUploadReturn {
  // State
  uploads: UploadProgress[];
  documents: Document[];
  isLoadingDocuments: boolean;
  error: string | null;

  // Actions
  handleFiles: (files: File[]) => Promise<void>;
  removeUpload: (documentId: string) => void;
  deleteDocument: (documentId: string) => Promise<void>;
  refreshDocuments: () => Promise<void>;
  clearError: () => void;
}

export function useUpload(userId: string = DEFAULT_USER_ID): UseUploadReturn {
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track polling intervals so we can clear them on unmount
  const pollingRefs = useRef<Record<string, NodeJS.Timeout>>({});

  // ── Validate a file before uploading ──────────────────────

  const validateFile = (file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext as any)) {
      return `${file.name}: file type not supported. Use PDF, DOCX, or TXT.`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      return `${file.name}: file is ${sizeMB}MB, maximum is 50MB.`;
    }
    if (file.size === 0) {
      return `${file.name}: file is empty.`;
    }
    return null;
  };

  // ── Poll document status until ready ──────────────────────

  const startPolling = useCallback(
    (documentId: string) => {
      let attempts = 0;

      const poll = async () => {
        attempts++;

        try {
          const doc = await getDocument(documentId);

          // Update upload progress state
          setUploads((prev) =>
            prev.map((u) =>
              u.document_id === documentId
                ? {
                    ...u,
                    status: doc.status,
                    progress: doc.status === "ready" ? 100 : Math.min(90, attempts * 10),
                    error: doc.error_message || undefined,
                  }
                : u
            )
          );

          if (doc.status === "ready") {
            // Processing complete — add to documents list
            clearInterval(pollingRefs.current[documentId]);
            delete pollingRefs.current[documentId];
            setDocuments((prev) => {
              const exists = prev.find((d) => d.document_id === documentId);
              if (exists) return prev;
              return [doc, ...prev];
            });
          } else if (doc.status === "error") {
            clearInterval(pollingRefs.current[documentId]);
            delete pollingRefs.current[documentId];
          } else if (attempts >= MAX_POLLING_ATTEMPTS) {
            // Timed out
            clearInterval(pollingRefs.current[documentId]);
            delete pollingRefs.current[documentId];
            setUploads((prev) =>
              prev.map((u) =>
                u.document_id === documentId
                  ? { ...u, status: "error", error: "Processing timed out. Please try again." }
                  : u
              )
            );
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      };

      pollingRefs.current[documentId] = setInterval(poll, POLLING_INTERVAL_MS);
    },
    []
  );

  // ── Handle file drop or selection ─────────────────────────

  const handleFiles = useCallback(
    async (files: File[]) => {
      setError(null);

      for (const file of files) {
        // Validate
        const validationError = validateFile(file);
        if (validationError) {
          setError(validationError);
          continue;
        }

        // Create optimistic upload entry
        const tempId = uuidv4();
        const newUpload: UploadProgress = {
          document_id: tempId,
          filename: file.name,
          progress: 10,
          status: "uploading",
        };

        setUploads((prev) => [newUpload, ...prev]);

        try {
          // Upload file
          const response = await uploadDocument(file, userId);

          // Replace temp entry with real document_id
          setUploads((prev) =>
            prev.map((u) =>
              u.document_id === tempId
                ? {
                    document_id: response.document_id,
                    filename: response.filename,
                    progress: 30,
                    status: "processing",
                  }
                : u
            )
          );

          // Start polling for completion
          startPolling(response.document_id);
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Upload failed";

          setUploads((prev) =>
            prev.map((u) =>
              u.document_id === tempId
                ? { ...u, status: "error", error: message, progress: 0 }
                : u
            )
          );
          setError(message);
        }
      }
    },
    [userId, startPolling]
  );

  // ── Load existing documents ────────────────────────────────

  const refreshDocuments = useCallback(async () => {
    setIsLoadingDocuments(true);
    try {
      const result = await listDocuments(userId);
      setDocuments(result.documents);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setIsLoadingDocuments(false);
    }
  }, [userId]);

  // ── Delete a document ──────────────────────────────────────

  const handleDeleteDocument = useCallback(
    async (documentId: string) => {
      try {
        const { deleteDocument: apiDelete } = await import("@/lib/api");
        await apiDelete(documentId, userId);
        setDocuments((prev) =>
          prev.filter((d) => d.document_id !== documentId)
        );
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to delete document"
        );
      }
    },
    [userId]
  );

  const removeUpload = useCallback((documentId: string) => {
    setUploads((prev) => prev.filter((u) => u.document_id !== documentId));
    // Clear polling if active
    if (pollingRefs.current[documentId]) {
      clearInterval(pollingRefs.current[documentId]);
      delete pollingRefs.current[documentId];
    }
  }, []);

  return {
    uploads,
    documents,
    isLoadingDocuments,
    error,
    handleFiles,
    removeUpload,
    deleteDocument: handleDeleteDocument,
    refreshDocuments,
    clearError: () => setError(null),
  };
}