/**
 * DropZone Component
 * ==================
 * Drag-and-drop file upload area.
 * Uses react-dropzone for cross-browser drag events.
 */

"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { cn } from "@/lib/utils";
import { ALLOWED_FILE_TYPES, MAX_FILE_SIZE_BYTES } from "@/lib/constants";

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  isUploading?: boolean;
  className?: string;
}

export function DropZone({ onFiles, isUploading, className }: DropZoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFiles(acceptedFiles);
      }
    },
    [onFiles]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: ALLOWED_FILE_TYPES,
      maxSize: MAX_FILE_SIZE_BYTES,
      disabled: isUploading,
      multiple: true,
    });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 text-center transition-colors cursor-pointer",
        isDragActive && !isDragReject
          ? "border-brand-500 bg-brand-50"
          : isDragReject
          ? "border-red-400 bg-red-50"
          : "border-gray-300 bg-white hover:border-brand-400 hover:bg-gray-50",
        isUploading && "opacity-60 cursor-not-allowed",
        className
      )}
    >
      <input {...getInputProps()} />

      {/* Upload icon */}
      <div
        className={cn(
          "mb-4 flex h-16 w-16 items-center justify-center rounded-full",
          isDragActive && !isDragReject
            ? "bg-brand-100"
            : "bg-gray-100"
        )}
      >
        <svg
          className={cn(
            "h-8 w-8",
            isDragActive && !isDragReject
              ? "text-brand-600"
              : "text-gray-400"
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
      </div>

      {/* Text */}
      {isDragReject ? (
        <p className="text-sm font-medium text-red-600">
          File type not supported
        </p>
      ) : isDragActive ? (
        <p className="text-sm font-medium text-brand-600">Drop to upload</p>
      ) : (
        <>
          <p className="text-sm font-medium text-gray-700">
            Drop files here, or{" "}
            <span className="text-brand-600 underline underline-offset-2">
              browse
            </span>
          </p>
          <p className="mt-1 text-xs text-gray-400">
            PDF, DOCX, TXT up to 50MB each
          </p>
        </>
      )}
    </div>
  );
}