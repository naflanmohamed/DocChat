/**
 * Global Chat Store — Zustand
 * ============================
 * Tracks which documents are selected for the current chat session.
 * Persists across page navigations within the same browser session.
 */

import { create } from "zustand";

interface ChatStore {
  // Which documents are selected for filtering
  selectedDocumentIds: string[];
  // Toggle a document in/out of the selection
  toggleDocument: (documentId: string) => void;
  // Select all documents (clear filter)
  selectAll: () => void;
  // Clear selection
  clearSelection: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  selectedDocumentIds: [],

  toggleDocument: (documentId) =>
    set((state) => ({
      selectedDocumentIds: state.selectedDocumentIds.includes(documentId)
        ? state.selectedDocumentIds.filter((id) => id !== documentId)
        : [...state.selectedDocumentIds, documentId],
    })),

  selectAll: () => set({ selectedDocumentIds: [] }),

  clearSelection: () => set({ selectedDocumentIds: [] }),
}));