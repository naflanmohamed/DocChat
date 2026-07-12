"use client";

import { useState } from "react";
import { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const scorePercent = Math.round(citation.relevance_score * 100);
  const scoreColor =
    scorePercent >= 80
      ? "text-green-700 bg-green-50 border-green-200"
      : scorePercent >= 60
      ? "text-amber-700 bg-amber-50 border-amber-200"
      : "text-gray-600 bg-gray-50 border-gray-200";

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden text-sm">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors"
      >
        {/* Source number badge */}
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
          {index + 1}
        </span>

        {/* File info */}
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-gray-800">
            {citation.document_name}
          </p>
          {citation.page_number != null && (
            <p className="text-xs text-gray-400">
              Page {citation.page_number}
            </p>
          )}
        </div>

        {/* Relevance score */}
        <span
          className={cn(
            "shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium",
            scoreColor
          )}
        >
          {scorePercent}% match
        </span>

        {/* Expand chevron */}
        <svg
          className={cn(
            "h-4 w-4 shrink-0 text-gray-400 transition-transform",
            isExpanded && "rotate-180"
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Excerpt — shown when expanded */}
      {isExpanded && (
        <div className="border-t border-gray-100 bg-gray-50 px-3 py-2.5">
          <p className="text-xs leading-relaxed text-gray-600 whitespace-pre-wrap">
            {citation.excerpt}
          </p>
        </div>
      )}
    </div>
  );
}