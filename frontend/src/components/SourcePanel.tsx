'use client';

/**
 * SourcePanel - Right panel for displaying source evidence
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useResearchStore, useActiveSource } from '@/store/useResearchStore';
import { FileText, X, Image as ImageIcon, Table2, Type } from 'lucide-react';
import type { SourceChunk } from '@/types';

// Media type icon
function MediaTypeIcon({ type }: { type: string }) {
  switch (type) {
    case 'table':
      return <Table2 className="w-4 h-4" />;
    case 'image':
      return <ImageIcon className="w-4 h-4" />;
    default:
      return <Type className="w-4 h-4" />;
  }
}

// Source content renderer based on media type
function SourceContent({ source }: { source: SourceChunk }) {
  switch (source.media_type) {
    case 'table':
      return (
        <div className="overflow-x-auto">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ children }) => (
                <table className="border-collapse border border-gray-300 w-full text-sm">
                  {children}
                </table>
              ),
              th: ({ children }) => (
                <th className="border border-gray-300 px-3 py-2 bg-gray-100 font-medium text-left">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="border border-gray-300 px-3 py-2">{children}</td>
              ),
            }}
          >
            {source.content}
          </ReactMarkdown>
        </div>
      );

    case 'image':
      // Check if we have image_url from the API
      if (source.image_url) {
        // Build full URL - if relative, prepend backend URL
        const imageSrc = source.image_url.startsWith('http')
          ? source.image_url
          : `http://localhost:8000${source.image_url}`;

        return (
          <div className="space-y-3">
            <img
              src={imageSrc}
              alt={source.caption || `Figure from page ${source.page_number || 'unknown'}`}
              className="max-w-full rounded-lg border shadow-sm bg-white"
              onError={(e) => {
                // Show fallback if image fails to load
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                target.nextElementSibling?.classList.remove('hidden');
              }}
            />
            {/* Fallback shown on error */}
            <div className="hidden bg-gray-100 rounded-lg p-4 text-center">
              <ImageIcon className="w-8 h-8 mx-auto mb-2 text-gray-400" />
              <p className="text-xs text-gray-500">Failed to load image</p>
            </div>
            {/* Caption */}
            {source.caption && (
              <p className="text-sm text-gray-700 italic text-center">
                {source.caption}
              </p>
            )}
            <p className="text-xs text-gray-500 text-center">
              {source.document_name}, Page {source.page_number || 'N/A'}
            </p>
          </div>
        );
      }
      // Fallback for image placeholder when no image_url
      return (
        <div className="bg-gray-100 rounded-lg p-8 text-center border-2 border-dashed border-gray-300">
          <ImageIcon className="w-12 h-12 mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600 font-medium">
            Image from Page {source.page_number || 'unknown'}
          </p>
          {source.caption && (
            <p className="text-xs text-gray-600 mt-2 italic">{source.caption}</p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            Image file not available
          </p>
        </div>
      );

    default:
      // Text content
      return (
        <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
          {source.content}
        </div>
      );
  }
}

// Active source detail view
function ActiveSourceDetail({ source }: { source: SourceChunk }) {
  const { clearActiveSource } = useResearchStore();

  return (
    <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-gray-50 border-b">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-gray-700 truncate">
            {source.document_name}
          </span>
        </div>
        <button
          onClick={clearActiveSource}
          className="p-1 hover:bg-gray-200 rounded transition-colors"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Metadata */}
      <div className="px-4 py-2 bg-gray-50 border-b flex items-center gap-3 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <MediaTypeIcon type={source.media_type} />
          {source.media_type}
        </span>
        {source.page_number && (
          <span>Page {source.page_number}</span>
        )}
        <span>
          {(source.similarity * 100).toFixed(1)}% match
        </span>
      </div>

      {/* Content */}
      <div className="p-4 bg-yellow-50 border-l-4 border-yellow-400">
        <SourceContent source={source} />
      </div>
    </div>
  );
}

// Source list item
function SourceListItem({
  source,
  index,
  onClick,
}: {
  source: SourceChunk;
  index: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-lg border p-3 hover:border-blue-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="w-6 h-6 flex items-center justify-center text-xs bg-blue-100 text-blue-700 rounded-full font-medium">
          {index + 1}
        </span>
        <span className="text-sm font-medium text-gray-700 truncate flex-1">
          {source.document_name}
        </span>
        <MediaTypeIcon type={source.media_type} />
      </div>
      <p className="text-xs text-gray-600 line-clamp-2">
        {source.content.substring(0, 150)}...
      </p>
      <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
        {source.page_number && <span>Page {source.page_number}</span>}
        <span>{(source.similarity * 100).toFixed(0)}% match</span>
      </div>
    </button>
  );
}

// Empty state
function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center text-gray-400 px-4">
        <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
        <p className="text-sm">
          Source references will appear here when you ask questions
        </p>
      </div>
    </div>
  );
}

// Main SourcePanel component
export function SourcePanel() {
  const activeSource = useActiveSource();
  const { sources, setActiveSource } = useResearchStore();

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="p-4 border-b bg-white">
        <h2 className="font-semibold text-gray-800">Evidence Panel</h2>
        {sources.length > 0 && (
          <p className="text-xs text-gray-500 mt-1">
            {sources.length} source{sources.length !== 1 ? 's' : ''} found
          </p>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeSource ? (
          <div className="space-y-4">
            <ActiveSourceDetail source={activeSource.chunk} />

            {/* Other sources */}
            {sources.length > 1 && (
              <div className="mt-6">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Other Sources
                </h3>
                <div className="space-y-2">
                  {sources
                    .filter((s) => s.chunk_id !== activeSource.chunk.chunk_id)
                    .map((source, index) => (
                      <SourceListItem
                        key={source.chunk_id}
                        source={source}
                        index={sources.findIndex((s) => s.chunk_id === source.chunk_id)}
                        onClick={() => setActiveSource({ chunk: source })}
                      />
                    ))}
                </div>
              </div>
            )}
          </div>
        ) : sources.length > 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-gray-500 mb-4">
              Click a citation number in the chat to view the source
            </p>
            {sources.map((source, index) => (
              <SourceListItem
                key={source.chunk_id}
                source={source}
                index={index}
                onClick={() => setActiveSource({ chunk: source })}
              />
            ))}
          </div>
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}

export default SourcePanel;
