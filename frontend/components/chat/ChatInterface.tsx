"use client";

import { useEffect, useRef } from "react";
import { Message } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { ChatInput } from "./ChatInput";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Button } from "@/components/ui/Button";

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  onSend: (message: string) => void;
  onClear: () => void;
  onClearError: () => void;
  documentCount: number;
}

export function ChatInterface({
  messages,
  isLoading,
  error,
  onSend,
  onClear,
  onClearError,
  documentCount,
}: ChatInterfaceProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
        <div>
          <h2 className="font-semibold text-gray-900">Chat</h2>
          <p className="text-xs text-gray-400">
            {documentCount} document{documentCount !== 1 ? "s" : ""} loaded
          </p>
        </div>
        {hasMessages && (
          <Button variant="ghost" size="sm" onClick={onClear}>
            Clear chat
          </Button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {!hasMessages && (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand-50">
              <svg className="h-8 w-8 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>
            </div>
            <h3 className="font-medium text-gray-700 mb-1">
              Ask anything about your documents
            </h3>
            <p className="text-sm text-gray-400 max-w-xs">
              Every answer includes citations showing exactly which part of the document was used.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && <TypingIndicator />}

        {error && (
          <ErrorBanner
            message={error}
            onDismiss={onClearError}
          />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 px-6 py-4">
        <ChatInput
          onSend={onSend}
          isLoading={isLoading}
          disabled={documentCount === 0}
          placeholder={
            documentCount === 0
              ? "Upload a document first..."
              : "Ask anything about your documents..."
          }
        />
        <p className="mt-2 text-center text-xs text-gray-400">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}