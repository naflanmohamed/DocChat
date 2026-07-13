"use client";

import { Message } from "@/lib/types";
import { CitationCard } from "./CitationCard";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3 animate-fade-in",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
          isUser
            ? "bg-brand-600 text-white"
            : "bg-gray-200 text-gray-600"
        )}
      >
        {isUser ? "You" : "AI"}
      </div>

      {/* Message content */}
      <div className={cn("flex max-w-[80%] flex-col gap-2", isUser && "items-end")}>
        {/* Bubble */}
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-sm bg-brand-600 text-white"
              : "rounded-tl-sm bg-white border border-gray-200 text-gray-800"
          )}
        >
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <>
              {message.content ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0"
                >
                  {message.content}
                </ReactMarkdown>
              ) : (
                // Empty content while streaming starts
                <span className="text-gray-400 italic">Thinking...</span>
              )}
              {/* Streaming cursor */}
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 bg-brand-500 ml-0.5 animate-pulse rounded-sm" />
              )}
            </>
          )}
        </div>

        {/* Citations */}
        {!isUser &&
          message.citations &&
          message.citations.length > 0 && (
            <div className="w-full space-y-1.5">
              <p className="text-xs font-medium text-gray-400 px-1">
                Sources used
              </p>
              {message.citations.map((citation, i) => (
                <CitationCard
                  key={citation.source_id}
                  citation={citation}
                  index={i}
                />
              ))}
            </div>
          )}
      </div>
    </div>
  );
}