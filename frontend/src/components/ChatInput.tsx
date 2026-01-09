'use client';

/**
 * ChatInput - Chat input with @ document tagging support
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useResearchStore } from '@/store/useResearchStore';
import { Send, Paperclip, Loader2, FileText, X, AtSign } from 'lucide-react';
import type { Document } from '@/types';

interface ChatInputProps {
  onSend: (message: string, options?: { filterDocumentId?: string }) => void;
  disabled?: boolean;
}

// Document mention dropdown
function DocumentDropdown({
  documents,
  searchTerm,
  onSelect,
  onClose,
  selectedIndex,
}: {
  documents: Document[];
  searchTerm: string;
  onSelect: (doc: Document) => void;
  onClose: () => void;
  selectedIndex: number;
}) {
  const filteredDocs = documents.filter((doc) =>
    doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (filteredDocs.length === 0) {
    return (
      <div className="absolute bottom-full left-0 mb-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 p-3">
        <p className="text-sm text-gray-500">No documents match "{searchTerm}"</p>
      </div>
    );
  }

  return (
    <div className="absolute bottom-full left-0 mb-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden z-50">
      <div className="px-3 py-2 border-b bg-gray-50">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Filter by document
        </p>
      </div>
      <div className="max-h-48 overflow-y-auto">
        {filteredDocs.map((doc, index) => (
          <button
            key={doc.id}
            onClick={() => onSelect(doc)}
            className={`w-full px-3 py-2 flex items-center gap-2 text-left hover:bg-blue-50 transition-colors ${
              index === selectedIndex ? 'bg-blue-50' : ''
            }`}
          >
            <FileText className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">
                {doc.original_filename}
              </p>
              {doc.page_count && (
                <p className="text-xs text-gray-400">{doc.page_count} pages</p>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// Selected document badge
function SelectedDocumentBadge({
  document,
  onRemove,
}: {
  document: Document;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
      <AtSign className="w-3 h-3" />
      <span className="truncate max-w-32">{document.original_filename}</span>
      <button
        onClick={onRemove}
        className="ml-1 hover:bg-blue-200 rounded-full p-0.5"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

// File upload button
function FileUploadButton() {
  const { uploadFile, isUploading, attachDocumentToSession, currentSessionId } = useResearchStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const doc = await uploadFile(file);
      // If we have a current session, auto-attach the new document
      if (doc && currentSessionId) {
        await attachDocumentToSession(doc.id);
      }
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        className="hidden"
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
        title="Upload PDF"
      >
        {isUploading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Paperclip className="w-5 h-5" />
        )}
      </button>
    </>
  );
}

// Session documents indicator
function SessionDocumentsIndicator() {
  const { getCurrentSessionDocuments, currentSessionId } = useResearchStore();
  const docs = getCurrentSessionDocuments();

  if (!currentSessionId || docs.length === 0) return null;

  return (
    <div className="flex items-center gap-1 text-xs text-gray-500">
      <FileText className="w-3 h-3" />
      <span>{docs.length} doc{docs.length !== 1 ? 's' : ''} attached</span>
    </div>
  );
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const { documents, isLoading, hasSessionDocuments } = useResearchStore();
  const [input, setInput] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [dropdownSearch, setDropdownSearch] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [dropdownIndex, setDropdownIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Detect @ trigger
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInput(value);

    // Check for @ trigger
    const lastAtIndex = value.lastIndexOf('@');
    if (lastAtIndex !== -1 && !selectedDoc) {
      const afterAt = value.substring(lastAtIndex + 1);
      // Show dropdown if @ is at the end or followed by a word (no space yet)
      if (!afterAt.includes(' ')) {
        setShowDropdown(true);
        setDropdownSearch(afterAt);
        setDropdownIndex(0);
        return;
      }
    }
    setShowDropdown(false);
  };

  // Handle document selection
  const handleSelectDocument = useCallback((doc: Document) => {
    setSelectedDoc(doc);
    setShowDropdown(false);
    // Remove the @... part from input
    const lastAtIndex = input.lastIndexOf('@');
    if (lastAtIndex !== -1) {
      setInput(input.substring(0, lastAtIndex).trim());
    }
    inputRef.current?.focus();
  }, [input]);

  // Handle keyboard navigation in dropdown
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showDropdown) {
      const filteredDocs = documents.filter((doc) =>
        doc.original_filename.toLowerCase().includes(dropdownSearch.toLowerCase())
      );

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setDropdownIndex((i) => Math.min(i + 1, filteredDocs.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setDropdownIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && filteredDocs.length > 0) {
        e.preventDefault();
        handleSelectDocument(filteredDocs[dropdownIndex]);
      } else if (e.key === 'Escape') {
        setShowDropdown(false);
      }
    }
  };

  // Handle form submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;

    const message = input.trim();
    setInput('');
    setSelectedDoc(null);
    onSend(message, selectedDoc ? { filterDocumentId: selectedDoc.id } : undefined);
  };

  // Check if we should show upload prompt
  const showUploadPrompt = documents.length === 0;

  return (
    <div className="border-t bg-white">
      {/* Upload prompt for first-time users */}
      {showUploadPrompt && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-100">
          <p className="text-sm text-blue-700">
            Upload a PDF to get started. Click the <Paperclip className="w-4 h-4 inline" /> icon.
          </p>
        </div>
      )}

      {/* Selected document filter badge */}
      {selectedDoc && (
        <div className="px-4 py-2 border-b flex items-center gap-2">
          <span className="text-xs text-gray-500">Searching in:</span>
          <SelectedDocumentBadge
            document={selectedDoc}
            onRemove={() => setSelectedDoc(null)}
          />
        </div>
      )}

      {/* Input area */}
      <div className="p-4">
        <form onSubmit={handleSubmit} className="relative">
          {/* Document dropdown */}
          {showDropdown && documents.length > 0 && (
            <DocumentDropdown
              documents={documents}
              searchTerm={dropdownSearch}
              onSelect={handleSelectDocument}
              onClose={() => setShowDropdown(false)}
              selectedIndex={dropdownIndex}
            />
          )}

          <div className="flex items-center gap-2">
            <FileUploadButton />

            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder={
                  showUploadPrompt
                    ? 'Upload a document first...'
                    : 'Ask a question... (type @ to filter by document)'
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50"
                disabled={isLoading || disabled}
              />
            </div>

            <button
              type="submit"
              disabled={!input.trim() || isLoading || disabled}
              className="p-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>

          {/* Session documents indicator */}
          <div className="mt-2 flex justify-end">
            <SessionDocumentsIndicator />
          </div>
        </form>
      </div>
    </div>
  );
}

export default ChatInput;
