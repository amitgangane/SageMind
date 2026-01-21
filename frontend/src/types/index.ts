/**
 * TypeScript types for the Research RAG application
 */

// Media types for chunks
export type MediaType = 'text' | 'table' | 'image';

// Message roles
export type MessageRole = 'user' | 'assistant' | 'system';

// A document uploaded to the system
export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number | null;
  page_count: number | null;
  upload_date: string;
  processed: string | null;
}

// A chunk of content from a document
export interface Chunk {
  id: string;
  document_id: string;
  content: string;
  media_type: MediaType;
  page_number: number | null;
  bbox: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  } | null;
  chunk_index: number | null;
  created_at: string;
}

// A source chunk returned with chat responses
export interface SourceChunk {
  chunk_id: string;
  content: string;
  similarity: number;
  document_id: string;
  document_name: string;
  page_number: number | null;
  media_type: MediaType;
  image_url?: string;  // URL to image file (e.g., /static/images/...)
  caption?: string;  // Image caption if available
}

// A chat message
export interface Message {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
  citations: string[];
}

// Brief document info for session attachments
export interface DocumentBrief {
  id: string;
  original_filename: string;
  file_size: number | null;
  page_count: number | null;
}

// A chat session
export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  document_ids: string[];  // Legacy
  attached_documents: DocumentBrief[];  // Full document relationship
}

// Chat request payload
export interface ChatRequest {
  message: string;
  session_id?: string;
  attach_document_ids?: string[];  // Documents to attach to session
  filter_document_id?: string;  // Filter search to specific document (@ tagging)
}

// Chat response from API
export interface ChatResponse {
  session_id: string;
  message: Message;
  citations: string[];
  sources: SourceChunk[];
}

// Active source for the right panel (click-to-reference)
export interface ActiveSource {
  chunk: SourceChunk;
  highlightedText?: string;
}
