'use client';

/**
 * ResearchLayout - The Holy Grail 3-pane layout for SageMind
 *
 * Layout:
 * - Left (280px): Sidebar with chat history and document list
 * - Middle (flex): Main chat area
 * - Right (400px): Evidence/Source panel for click-to-reference
 */

import React, { useState, useEffect, useRef } from 'react';
import { useResearchStore } from '@/store/useResearchStore';
import {
  FileText,
  MessageSquare,
  Search,
  Upload,
  Trash2,
  Loader2,
  Plus,
} from 'lucide-react';
import { ChatInterface } from './ChatInterface';
import { SourcePanel } from './SourcePanel';

// Sidebar Panel (Left)
function SidebarPanel() {
  const {
    sessions,
    currentSessionId,
    setCurrentSession,
    loadSession,
    documents,
    uploadFile,
    isUploading,
    fetchSessions,
    fetchDocuments,
  } = useResearchStore();

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch sessions and documents on mount
  useEffect(() => {
    fetchSessions();
    fetchDocuments();
  }, [fetchSessions, fetchDocuments]);

  const handleNewChat = () => {
    setCurrentSession(null);
  };

  const handleSessionClick = async (sessionId: string) => {
    await loadSession(sessionId);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await uploadFile(file);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <Search className="w-5 h-5 text-blue-400" />
          SageMind
        </h1>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-3 py-2">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-2">
            Chat History
          </h2>
          {sessions.length === 0 ? (
            <p className="text-sm text-gray-500 px-2">No conversations yet</p>
          ) : (
            <ul className="space-y-1">
              {sessions.map((session) => (
                <li key={session.id}>
                  <button
                    onClick={() => handleSessionClick(session.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors flex items-center gap-2 ${
                      currentSessionId === session.id
                        ? 'bg-gray-700 text-white'
                        : 'text-gray-300 hover:bg-gray-800'
                    }`}
                  >
                    <MessageSquare className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">
                      {session.title || 'Untitled Chat'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Documents Section */}
        <div className="px-3 py-2 mt-4">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-2">
            Documents
          </h2>
          {documents.length === 0 ? (
            <p className="text-sm text-gray-500 px-2">No documents uploaded</p>
          ) : (
            <ul className="space-y-1">
              {documents.map((doc) => (
                <li
                  key={doc.id}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg cursor-default"
                  title={doc.original_filename}
                >
                  <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  <span className="truncate">{doc.original_filename}</span>
                  {doc.processed && (
                    <span className="w-2 h-2 bg-green-500 rounded-full flex-shrink-0" title="Processed" />
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Upload Button */}
      <div className="p-3 border-t border-gray-700">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="w-full py-2.5 px-4 border border-gray-600 hover:bg-gray-800 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {isUploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload PDF
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// Main Layout Component
export function ResearchLayout() {
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [sourceWidth, setSourceWidth] = useState(400);

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-gray-100">
      {/* Left Sidebar */}
      <div className="h-full flex-shrink-0" style={{ width: sidebarWidth }}>
        <SidebarPanel />
      </div>

      {/* Resize Handle */}
      <div
        className="w-1 bg-gray-300 hover:bg-blue-500 cursor-col-resize flex-shrink-0 transition-colors"
        onMouseDown={(e) => {
          e.preventDefault();
          const startX = e.clientX;
          const startWidth = sidebarWidth;

          const onMouseMove = (e: MouseEvent) => {
            const newWidth = startWidth + (e.clientX - startX);
            setSidebarWidth(Math.max(200, Math.min(400, newWidth)));
          };

          const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
          };

          document.addEventListener('mousemove', onMouseMove);
          document.addEventListener('mouseup', onMouseUp);
        }}
      />

      {/* Middle Chat Area */}
      <div className="h-full flex-1 min-w-0">
        <ChatInterface />
      </div>

      {/* Resize Handle */}
      <div
        className="w-1 bg-gray-300 hover:bg-blue-500 cursor-col-resize flex-shrink-0 transition-colors"
        onMouseDown={(e) => {
          e.preventDefault();
          const startX = e.clientX;
          const startWidth = sourceWidth;

          const onMouseMove = (e: MouseEvent) => {
            const newWidth = startWidth - (e.clientX - startX);
            setSourceWidth(Math.max(250, Math.min(600, newWidth)));
          };

          const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
          };

          document.addEventListener('mousemove', onMouseMove);
          document.addEventListener('mouseup', onMouseUp);
        }}
      />

      {/* Right Source Panel */}
      <div className="h-full flex-shrink-0" style={{ width: sourceWidth }}>
        <SourcePanel />
      </div>
    </div>
  );
}

export default ResearchLayout;
