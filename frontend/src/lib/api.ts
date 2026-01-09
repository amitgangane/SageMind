/**
 * API Client for SageMind Backend
 */

import type {
  Document,
  ChatSession,
  ChatResponse,
  ChatRequest,
  Chunk,
  SourceChunk,
} from '@/types';

const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ============ Documents API ============

/**
 * Upload a PDF file
 */
export async function uploadPDF(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * List all documents
 */
export async function listDocuments(): Promise<Document[]> {
  return fetchAPI<Document[]>('/documents/');
}

/**
 * Get a document by ID with its chunks
 */
export async function getDocument(documentId: string): Promise<Document & { chunks: Chunk[] }> {
  return fetchAPI(`/documents/${documentId}`);
}

/**
 * Delete a document
 */
export async function deleteDocument(documentId: string): Promise<void> {
  await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
  });
}

/**
 * Trigger processing for a document
 */
export async function processDocument(documentId: string): Promise<Document> {
  return fetchAPI(`/documents/${documentId}/process`, {
    method: 'POST',
  });
}

// ============ Chat API ============

/**
 * Create a new chat session
 */
export async function createSession(
  title?: string,
  documentIds?: string[]
): Promise<ChatSession> {
  return fetchAPI<ChatSession>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({
      title: title || null,
      document_ids: documentIds || [],
    }),
  });
}

/**
 * List all chat sessions
 */
export async function listSessions(): Promise<ChatSession[]> {
  return fetchAPI<ChatSession[]>('/chat/sessions');
}

/**
 * Get a chat session with messages
 */
export async function getSession(sessionId: string): Promise<ChatSession & { messages: any[] }> {
  return fetchAPI(`/chat/sessions/${sessionId}`);
}

/**
 * Delete a chat session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

/**
 * Attach a document to a session
 */
export async function attachDocumentToSession(
  sessionId: string,
  documentId: string
): Promise<ChatSession> {
  return fetchAPI<ChatSession>(`/chat/sessions/${sessionId}/documents/${documentId}`, {
    method: 'POST',
  });
}

/**
 * Send a message and get a RAG-powered response
 */
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  return fetchAPI<ChatResponse>('/chat/message', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get chunk details for citation reference
 */
export async function getChunk(chunkId: string): Promise<{
  chunk_id: string;
  content: string;
  media_type: string;
  page_number: number | null;
  bbox: any;
  document: {
    id: string;
    filename: string;
  } | null;
}> {
  return fetchAPI(`/chat/chunks/${chunkId}`);
}

// ============ Health API ============

/**
 * Check backend health
 */
export async function healthCheck(): Promise<{ status: string; app: string }> {
  const response = await fetch('http://localhost:8000/health');
  return response.json();
}
