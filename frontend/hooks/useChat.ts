/**
 * useChat Hook
 * ============
 * Manages the complete chat flow:
 * - Message history
 * - Sending questions to the backend
 * - Loading states
 * - Citation tracking
 */

import { useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { sendMessage } from "@/lib/api";
import { Message, Citation, ChatMessage } from "@/lib/types";
import { DEFAULT_USER_ID, MAX_CONVERSATION_HISTORY } from "@/lib/constants";

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  ask: (question: string, documentIds?: string[]) => Promise<void>;
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

  const ask = useCallback(
    async (question: string, documentIds?: string[]) => {
      if (!question.trim() || isLoading) return;

      setError(null);

      // Add user message immediately (optimistic update)
      const userMessage: Message = {
        id: uuidv4(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        // Build conversation history for the API
        // Only send the last MAX_CONVERSATION_HISTORY messages
        const history: ChatMessage[] = messages
          .slice(-MAX_CONVERSATION_HISTORY)
          .map((m) => ({ role: m.role, content: m.content }));

        const response = await sendMessage({
          question: question.trim(),
          session_id: sessionId,
          user_id: userId,
          conversation_history: history,
          document_ids: documentIds,
        });

        // Add assistant response
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

        // Add error message to chat so the user sees it inline
        const errorMsg: Message = {
          id: uuidv4(),
          role: "assistant",
          content:
            "I encountered an error while processing your question. Please try again.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, sessionId, userId, isLoading]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    ask,
    clearChat,
    clearError: () => setError(null),
  };
}