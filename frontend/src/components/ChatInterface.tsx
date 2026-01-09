'use client';

/**
 * ChatInterface - Main chat component with message rendering and citation support
 */

import React, { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useResearchStore } from '@/store/useResearchStore';
import { MessageSquare, Loader2, AlertCircle } from 'lucide-react';
import { ChatInput } from './ChatInput';
import type { Message } from '@/types';

// Citation button component
interface CitationButtonProps {
  chunkId: string;
  index: number;
}

function CitationButton({ chunkId }: CitationButtonProps) {
  const { setActiveSourceById, sources } = useResearchStore();
  const source = sources.find((s) => s.chunk_id === chunkId);

  if (!source) {
    return (
      <span className="inline-flex items-center justify-center w-5 h-5 text-xs bg-gray-200 text-gray-500 rounded-full mx-0.5">
        ?
      </span>
    );
  }

  const sourceIndex = sources.findIndex((s) => s.chunk_id === chunkId) + 1;

  return (
    <button
      onClick={() => setActiveSourceById(chunkId)}
      className="inline-flex items-center justify-center min-w-[20px] h-5 px-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors mx-0.5 font-medium"
      title={`Source: ${source.document_name}${source.page_number ? `, Page ${source.page_number}` : ''}`}
    >
      {sourceIndex}
    </button>
  );
}

// Custom markdown components with citation support
function MarkdownWithCitations({ content }: { content: string }) {
  // First, split by citations and process
  const citationPattern = /(\[\[[a-f0-9-]+\]\])/gi;
  const segments = content.split(citationPattern);

  return (
    <div className="prose prose-sm max-w-none">
      {segments.map((segment, index) => {
        // Check if this segment is a citation
        const citationMatch = segment.match(/^\[\[([a-f0-9-]+)\]\]$/i);
        if (citationMatch) {
          return <CitationButton key={index} chunkId={citationMatch[1]} index={index} />;
        }

        // Otherwise render as markdown
        if (segment.trim()) {
          return (
            <ReactMarkdown
              key={index}
              remarkPlugins={[remarkGfm]}
              components={{
                // Style tables
                table: ({ children }) => (
                  <table className="border-collapse border border-gray-300 my-2 text-sm">
                    {children}
                  </table>
                ),
                th: ({ children }) => (
                  <th className="border border-gray-300 px-2 py-1 bg-gray-100 font-medium">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="border border-gray-300 px-2 py-1">{children}</td>
                ),
                // Style code blocks
                code: ({ className, children }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{children}</code>
                  ) : (
                    <code className={`${className} block bg-gray-100 p-2 rounded text-sm overflow-x-auto`}>
                      {children}
                    </code>
                  );
                },
                // Style paragraphs
                p: ({ children }) => <span>{children}</span>,
              }}
            >
              {segment}
            </ReactMarkdown>
          );
        }
        return null;
      })}
    </div>
  );
}

// Message bubble component
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-gray-100 text-gray-800 rounded-bl-md'
        }`}
      >
        {isUser ? (
          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
        ) : (
          <MarkdownWithCitations content={message.content} />
        )}
      </div>
    </div>
  );
}

// Loading indicator
function LoadingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Thinking...</span>
        </div>
      </div>
    </div>
  );
}

// Error message
function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="flex justify-center">
      <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 flex items-center gap-2 text-red-700">
        <AlertCircle className="w-4 h-4" />
        <span className="text-sm">{message}</span>
      </div>
    </div>
  );
}

// Empty state
function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center text-gray-500 max-w-md">
        <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h2 className="text-xl font-medium mb-2">Start a conversation</h2>
        <p className="text-sm text-gray-400">
          Ask questions about your uploaded documents. I&apos;ll search through them
          and provide answers with citations you can click to see the source.
        </p>
        <p className="text-xs text-gray-300 mt-2">
          Tip: Type @ to filter by a specific document
        </p>
      </div>
    </div>
  );
}

// Main chat interface
export function ChatInterface() {
  const { messages, isLoading, error, sendUserMessage } = useResearchStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (message: string, options?: { filterDocumentId?: string }) => {
    await sendUserMessage(message, options);
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <LoadingIndicator />}
            {error && <ErrorMessage message={error} />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Chat Input with @ document tagging */}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}

export default ChatInterface;
