"use client";

import { Document } from "@/lib/types";
import { formatFileSize, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/Button";

interface FileListProps {
  documents: Document[];
  onDelete: (documentId: string) => void;
  onStartChat: (documentId: string) => void;
}

export function FileList({ documents, onDelete, onStartChat }: FileListProps) {
  if (documents.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-gray-400">
        No documents yet — upload one above to get started.
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white overflow-hidden">
      {documents.map((doc) => (
        <div key={doc.document_id} className="flex items-center gap-4 px-4 py-3">
          {/* Status dot */}
          <div
            className={`h-2 w-2 shrink-0 rounded-full ${
              doc.status === "ready"
                ? "bg-green-500"
                : doc.status === "error"
                ? "bg-red-500"
                : "bg-amber-400 animate-pulse"
            }`}
          />

          {/* File info */}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-gray-800">
              {doc.filename}
            </p>
            <p className="text-xs text-gray-400">
              {doc.chunk_count != null
                ? `${doc.chunk_count} chunks · `
                : ""}
              {formatFileSize(doc.file_size_bytes)} ·{" "}
              {formatDate(doc.created_at)}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {doc.status === "ready" && (
              <Button
                size="sm"
                variant="primary"
                onClick={() => onStartChat(doc.document_id)}
              >
                Chat
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onDelete(doc.document_id)}
              className="text-red-500 hover:text-red-700 hover:bg-red-50"
            >
              Delete
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}