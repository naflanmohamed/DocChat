"use client";

import { useState, KeyboardEvent, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { MAX_QUESTION_LENGTH } from "@/lib/constants";

interface ChatInputProps {
  onSend: (message: string) => void;
  onSendStreaming?: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onSendStreaming,
  isLoading,
  disabled,
  placeholder = "Ask anything about your documents...",
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
    }
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading || disabled) return;

    if (streamingEnabled && onSendStreaming) {
      onSendStreaming(trimmed);
    } else {
      onSend(trimmed);
    }
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isOverLimit = value.length > MAX_QUESTION_LENGTH;
  const canSend =
    value.trim().length > 0 && !isLoading && !disabled && !isOverLimit;

  return (
    <div className="space-y-2">
      {/* Streaming toggle */}
      {onSendStreaming && (
        <div className="flex items-center gap-2 px-1">
          <button
            onClick={() => setStreamingEnabled(!streamingEnabled)}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
              streamingEnabled
                ? "bg-brand-50 text-brand-700"
                : "bg-gray-100 text-gray-500"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                streamingEnabled ? "bg-brand-500 animate-pulse" : "bg-gray-400"
              )}
            />
            {streamingEnabled ? "Streaming on" : "Streaming off"}
          </button>
          <span className="text-xs text-gray-400">
            {streamingEnabled
              ? "Tokens appear as they generate"
              : "Full response at once"}
          </span>
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-3 rounded-2xl border border-gray-300 bg-white p-3 shadow-sm focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500 transition-all">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading || disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none disabled:opacity-50 max-h-40"
        />

        {value.length > MAX_QUESTION_LENGTH * 0.8 && (
          <span
            className={cn(
              "shrink-0 self-end text-xs",
              isOverLimit ? "text-red-500" : "text-gray-400"
            )}
          >
            {value.length}/{MAX_QUESTION_LENGTH}
          </span>
        )}

        <button
          onClick={handleSend}
          disabled={!canSend}
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-colors",
            canSend
              ? "bg-brand-600 text-white hover:bg-brand-700"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          )}
          aria-label="Send message"
        >
          {isLoading ? (
            <svg
              className="h-4 w-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          ) : (
            <svg
              className="h-4 w-4 rotate-90"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          )}
        </button>
      </div>

      <p className="text-center text-xs text-gray-400">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}