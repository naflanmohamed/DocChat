"use client";

import { UploadProgress as UploadProgressType } from "@/lib/types";
import { cn } from "@/lib/utils";

interface UploadProgressProps {
  upload: UploadProgressType;
  onRemove: (id: string) => void;
}

export function UploadProgressItem({ upload, onRemove }: UploadProgressProps) {
  const { document_id, filename, progress, status, error } = upload;

  const statusConfig = {
    uploading: {
      label: "Uploading...",
      color: "bg-brand-500",
      textColor: "text-brand-700",
    },
    processing: {
      label: "Processing...",
      color: "bg-amber-500",
      textColor: "text-amber-700",
    },
    ready: {
      label: "Ready",
      color: "bg-green-500",
      textColor: "text-green-700",
    },
    error: {
      label: "Failed",
      color: "bg-red-500",
      textColor: "text-red-700",
    },
  };

  const config = statusConfig[status] || statusConfig.uploading;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        {/* File icon + name */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gray-100">
            <svg className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-gray-800">
              {filename}
            </p>
            <p className={cn("text-xs font-medium", config.textColor)}>
              {error || config.label}
            </p>
          </div>
        </div>

        {/* Remove button */}
        {(status === "ready" || status === "error") && (
          <button
            onClick={() => onRemove(document_id)}
            className="shrink-0 text-gray-400 hover:text-gray-600"
            aria-label="Remove"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Progress bar */}
      {status !== "error" && (
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              config.color
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}