"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { v4 as uuidv4 } from "uuid";
import { useUpload } from "@/hooks/useUpload";
import { DropZone } from "@/components/upload/DropZone";
import { UploadProgressItem } from "@/components/upload/UploadProgress";
import { FileList } from "@/components/upload/FileList";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Button } from "@/components/ui/Button";
import { DEFAULT_USER_ID } from "@/lib/constants";

export default function UploadPage() {
  const router = useRouter();
  const {
    uploads,
    documents,
    isLoadingDocuments,
    error,
    handleFiles,
    removeUpload,
    deleteDocument,
    refreshDocuments,
    clearError,
  } = useUpload(DEFAULT_USER_ID);

  // Load existing documents on mount
  useEffect(() => {
    refreshDocuments();
  }, []);

  const isUploading = uploads.some(
    (u) => u.status === "uploading" || u.status === "processing"
  );

  const handleStartChat = (documentId: string) => {
    const sessionId = uuidv4();
    router.push(`/chat/${sessionId}?docId=${documentId}`);
  };

  const handleStartFreshChat = () => {
    const sessionId = uuidv4();
    router.push(`/chat/${sessionId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <span className="font-semibold text-gray-900">DocChat</span>
          </div>

          {documents.some((d) => d.status === "ready") && (
            <Button onClick={handleStartFreshChat} size="sm">
              Open chat
            </Button>
          )}
        </div>
      </nav>

      {/* Main */}
      <main className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">
            Chat with your documents
          </h1>
          <p className="mt-2 text-gray-500">
            Upload PDF, DOCX, or TXT files. Every answer includes citations.
          </p>
        </div>

        {/* Error banner */}
        {error && (
          <ErrorBanner
            message={error}
            onDismiss={clearError}
            className="mb-4"
          />
        )}

        {/* Drop zone */}
        <DropZone
          onFiles={handleFiles}
          isUploading={isUploading}
          className="mb-6"
        />

        {/* Active uploads */}
        {uploads.length > 0 && (
          <div className="mb-6 space-y-2">
            <h2 className="text-sm font-medium text-gray-700">
              Uploads
            </h2>
            {uploads.map((upload) => (
              <UploadProgressItem
                key={upload.document_id}
                upload={upload}
                onRemove={removeUpload}
              />
            ))}
          </div>
        )}

        {/* Existing documents */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-700">
              Your documents
              {documents.length > 0 && (
                <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                  {documents.length}
                </span>
              )}
            </h2>
            <button
              onClick={refreshDocuments}
              className="text-xs text-brand-600 hover:underline"
            >
              Refresh
            </button>
          </div>

          {isLoadingDocuments ? (
            <div className="flex items-center justify-center py-10">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
            </div>
          ) : (
            <FileList
              documents={documents}
              onDelete={deleteDocument}
              onStartChat={handleStartChat}
            />
          )}
        </div>
      </main>
    </div>
  );
}