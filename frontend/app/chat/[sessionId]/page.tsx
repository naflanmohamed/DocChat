"use client";

import { use, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useChat } from "@/hooks/useChat";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { listDocuments } from "@/lib/api";
import { Document } from "@/lib/types";
import { DEFAULT_USER_ID } from "@/lib/constants";

interface ChatPageProps {
  params: Promise<{ sessionId: string }>;
}

export default function ChatPage({ params }: ChatPageProps) {
  const { sessionId } = use(params);
  const searchParams = useSearchParams();
  const focusDocId = searchParams.get("docId");

  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);

  const {
    messages,
    isLoading,
    error,
    ask,
    askStreaming,
    clearChat,
    clearError,
  } = useChat(sessionId, DEFAULT_USER_ID);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await listDocuments(DEFAULT_USER_ID);
        setDocuments(
          result.documents.filter((d: Document) => d.status === "ready")
        );
      } catch (err) {
        console.error("Failed to load documents:", err);
      } finally {
        setIsLoadingDocs(false);
      }
    };
    load();
  }, []);

  const readyDocs = documents.filter((d) => d.status === "ready");

  const handleSend = (question: string) => {
    const docIds = focusDocId ? [focusDocId] : undefined;
    ask(question, docIds);
  };

  const handleSendStreaming = (question: string) => {
    const docIds = focusDocId ? [focusDocId] : undefined;
    askStreaming(question, docIds);
  };

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <nav className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
        <div className="flex items-center gap-3">
          <Link
            href="/upload"
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"
              />
            </svg>
            Documents
          </Link>
          <span className="text-gray-300">·</span>
          <span className="font-semibold text-gray-900">DocChat</span>
        </div>

        {focusDocId && (
          <div className="flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1 text-xs text-brand-700">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
            {documents.find((d) => d.document_id === focusDocId)?.filename ||
              "Selected document"}
          </div>
        )}
      </nav>

      <div className="flex-1 overflow-hidden">
        <div className="mx-auto flex h-full max-w-3xl flex-col">
          <ChatInterface
            messages={messages}
            isLoading={isLoading}
            error={error}
            onSend={handleSend}
            onSendStreaming={handleSendStreaming}
            onClear={clearChat}
            onClearError={clearError}
            documentCount={isLoadingDocs ? 0 : readyDocs.length}
          />
        </div>
      </div>
    </div>
  );
}