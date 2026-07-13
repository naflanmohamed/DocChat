/**
 * useChat Hook — with persistent conversation memory
 * ===================================================
 * Manages message history and supports both regular
 * and streaming responses.
 */

"use client";

import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { sendMessage } from "@/lib/api";
import { Message, Citation, ChatMessage } from "@/lib/types";
import { DEFAULT_USER_ID, MAX_CONVERSATION_HISTORY, API_BASE_URL } from "@/lib/constants";

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  ask: (question: string, documentIds?: string[]) => Promise<void>;
  askStreaming: (question: string, documentIds?: string[]) => Promise<void>;
  clearChat: () => void;
  clearError: () => void;
}

export function useChat(
  sessionId: string,
  userId: string = DEFAULT_USER_ID
): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // ── Build conversation history for API ─────────────────────
  const buildHistory = useCallback(
    (currentMessages: Message[]): ChatMessage[] => {
      return currentMessages
        .slice(-MAX_CONVERSATION_HISTORY)
        .map((m) => ({ role: m.role, content: m.content }));
    },
    []
  );

  // ── Standard (non-streaming) chat ──────────────────────────
  const ask = useCallback(
    async (question: string, documentIds?: string[]) => {
      if (!question.trim() || isLoading) return;
      setError(null);

      const userMessage: Message = {
        id: uuidv4(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => {
        const updated = [...prev, userMessage];
        return updated;
      });
      setIsLoading(true);

      try {
        const history = buildHistory(messages);
        const response = await sendMessage({
          question: question.trim(),
          session_id: sessionId,
          user_id: userId,
          conversation_history: history,
          document_ids: documentIds,
        });

        const assistantMessage: Message = {
          id: uuidv4(),
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to get response";
        setError(errorMessage);
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            role: "assistant",
            content: "I encountered an error. Please try again.",
            timestamp: new Date(),
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, sessionId, userId, isLoading, buildHistory]
  );

  // ── Streaming chat ──────────────────────────────────────────
  const askStreaming = useCallback(
    async (question: string, documentIds?: string[]) => {
      if (!question.trim() || isLoading) return;
      setError(null);

      // Cancel any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      const userMessage: Message = {
        id: uuidv4(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      // Create placeholder for streaming assistant message
      const assistantId = uuidv4();
      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);

      try {
        const history = buildHistory(messages);

        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: question.trim(),
            session_id: sessionId,
            user_id: userId,
            conversation_history: history,
            document_ids: documentIds,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let citations: Citation[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);

              if (data.type === "sources") {
                // Citations arrive before the text
                citations = data.sources.map((s: any) => ({
                  source_id: s.chunk_id,
                  document_name: s.document_name,
                  page_number: s.page_number,
                  chunk_index: 0,
                  relevance_score: s.score,
                  excerpt: s.excerpt,
                }));
                // Update message with citations immediately
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, citations } : m
                  )
                );
              } else if (data.type === "token") {
                // Append token to message content
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: m.content + data.text }
                      : m
                  )
                );
              } else if (data.type === "done") {
                // Mark streaming complete
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, isStreaming: false }
                      : m
                  )
                );
              } else if (data.type === "error") {
                throw new Error(data.message);
              }
            } catch (parseError) {
              // Skip malformed SSE lines
              continue;
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        const errorMessage =
          err instanceof Error ? err.message : "Streaming failed";
        setError(errorMessage);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: "I encountered an error. Please try again.",
                  isStreaming: false,
                }
              : m
          )
        );
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [messages, sessionId, userId, isLoading, buildHistory]
  );

  const clearChat = useCallback(() => {
    // Abort any active stream before clearing
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    ask,
    askStreaming,
    clearChat,
    clearError: () => setError(null),
  };
}