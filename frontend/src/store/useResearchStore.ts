/**
 * Zustand store for SageMind application state management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  ChatSession,
  Message,
  SourceChunk,
  ActiveSource,
  Document,
  DocumentBrief,
} from '@/types';
import * as api from '@/lib/api';

interface ResearchState {
  // Sessions
  sessions: ChatSession[];
  currentSessionId: string | null;

  // Messages for current session
  messages: Message[];

  // Sources from the last response (lookup by chunk_id)
  sources: SourceChunk[];
  sourcesMap: Map<string, SourceChunk>;

  // Currently selected source for the right panel
  activeSource: ActiveSource | null;

  // Documents
  documents: Document[];

  // @ document filter for current message
  filterDocumentId: string | null;

  // Loading states
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;

  // Actions - Sessions
  setSessions: (sessions: ChatSession[]) => void;
  addSession: (session: ChatSession) => void;
  setCurrentSession: (sessionId: string | null) => void;
  deleteSession: (sessionId: string) => void;
  fetchSessions: () => Promise<void>;
  updateSessionDocuments: (sessionId: string, documents: DocumentBrief[]) => void;

  // Actions - Messages
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;

  // Actions - Sources
  setSources: (sources: SourceChunk[]) => void;
  setActiveSource: (source: ActiveSource | null) => void;
  setActiveSourceById: (chunkId: string) => void;
  clearActiveSource: () => void;
  getSourceById: (chunkId: string) => SourceChunk | undefined;

  // Actions - Documents
  setDocuments: (documents: Document[]) => void;
  addDocument: (document: Document) => void;
  removeDocument: (documentId: string) => void;
  fetchDocuments: () => Promise<void>;
  setFilterDocumentId: (documentId: string | null) => void;

  // Actions - Async Operations
  uploadFile: (file: File) => Promise<Document | null>;
  sendUserMessage: (text: string, options?: { attachDocumentIds?: string[]; filterDocumentId?: string }) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  attachDocumentToSession: (documentId: string) => Promise<void>;

  // Actions - Loading & Error
  setIsLoading: (loading: boolean) => void;
  setIsUploading: (uploading: boolean) => void;
  setError: (error: string | null) => void;

  // Actions - Reset
  reset: () => void;

  // Helpers
  getCurrentSessionDocuments: () => DocumentBrief[];
  hasSessionDocuments: () => boolean;
}

const initialState = {
  sessions: [],
  currentSessionId: null,
  messages: [],
  sources: [],
  sourcesMap: new Map<string, SourceChunk>(),
  activeSource: null,
  documents: [],
  filterDocumentId: null,
  isLoading: false,
  isUploading: false,
  error: null,
};

export const useResearchStore = create<ResearchState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Sessions
        setSessions: (sessions) => set({ sessions }, false, 'setSessions'),

        addSession: (session) =>
          set(
            (state) => ({
              sessions: [session, ...state.sessions],
              currentSessionId: session.id,
            }),
            false,
            'addSession'
          ),

        setCurrentSession: (sessionId) =>
          set(
            {
              currentSessionId: sessionId,
              messages: [],
              sources: [],
              sourcesMap: new Map(),
              activeSource: null,
            },
            false,
            'setCurrentSession'
          ),

        deleteSession: (sessionId) =>
          set(
            (state) => ({
              sessions: state.sessions.filter((s) => s.id !== sessionId),
              currentSessionId:
                state.currentSessionId === sessionId
                  ? null
                  : state.currentSessionId,
              messages:
                state.currentSessionId === sessionId ? [] : state.messages,
            }),
            false,
            'deleteSession'
          ),

        fetchSessions: async () => {
          try {
            const sessions = await api.listSessions();
            set({ sessions }, false, 'fetchSessions');
          } catch (error) {
            console.error('Failed to fetch sessions:', error);
          }
        },

        updateSessionDocuments: (sessionId, documents) =>
          set(
            (state) => ({
              sessions: state.sessions.map((s) =>
                s.id === sessionId ? { ...s, attached_documents: documents } : s
              ),
            }),
            false,
            'updateSessionDocuments'
          ),

        // Messages
        setMessages: (messages) => set({ messages }, false, 'setMessages'),

        addMessage: (message) =>
          set(
            (state) => ({
              messages: [...state.messages, message],
            }),
            false,
            'addMessage'
          ),

        clearMessages: () => set({ messages: [] }, false, 'clearMessages'),

        // Sources
        setSources: (sources) => {
          const sourcesMap = new Map<string, SourceChunk>();
          sources.forEach((s) => sourcesMap.set(s.chunk_id, s));
          set({ sources, sourcesMap }, false, 'setSources');
        },

        setActiveSource: (source) =>
          set({ activeSource: source }, false, 'setActiveSource'),

        setActiveSourceById: (chunkId) => {
          const source = get().sourcesMap.get(chunkId);
          if (source) {
            set({ activeSource: { chunk: source } }, false, 'setActiveSourceById');
          }
        },

        clearActiveSource: () =>
          set({ activeSource: null }, false, 'clearActiveSource'),

        getSourceById: (chunkId) => get().sourcesMap.get(chunkId),

        // Documents
        setDocuments: (documents) => set({ documents }, false, 'setDocuments'),

        addDocument: (document) =>
          set(
            (state) => ({
              documents: [...state.documents, document],
            }),
            false,
            'addDocument'
          ),

        removeDocument: (documentId) =>
          set(
            (state) => ({
              documents: state.documents.filter((d) => d.id !== documentId),
            }),
            false,
            'removeDocument'
          ),

        fetchDocuments: async () => {
          try {
            const documents = await api.listDocuments();
            set({ documents }, false, 'fetchDocuments');
          } catch (error) {
            console.error('Failed to fetch documents:', error);
          }
        },

        setFilterDocumentId: (documentId) =>
          set({ filterDocumentId: documentId }, false, 'setFilterDocumentId'),

        // Async: Upload File
        uploadFile: async (file) => {
          set({ isUploading: true, error: null }, false, 'uploadFile:start');

          try {
            const document = await api.uploadPDF(file);
            set(
              (state) => ({
                documents: [...state.documents, document],
                isUploading: false,
              }),
              false,
              'uploadFile:success'
            );
            return document;
          } catch (error) {
            const message = error instanceof Error ? error.message : 'Upload failed';
            set({ isUploading: false, error: message }, false, 'uploadFile:error');
            return null;
          }
        },

        // Async: Send User Message
        sendUserMessage: async (text, options = {}) => {
          const state = get();
          set({ isLoading: true, error: null, filterDocumentId: null }, false, 'sendUserMessage:start');

          const { attachDocumentIds, filterDocumentId } = options;

          // For new sessions without specific documents, auto-attach all documents
          const isNewSession = !state.currentSessionId;
          const docsToAttach = isNewSession && !attachDocumentIds?.length
            ? state.documents.map((d) => d.id)
            : attachDocumentIds;

          // Optimistically add user message
          const tempUserMessage: Message = {
            id: `temp-${Date.now()}`,
            session_id: state.currentSessionId || '',
            role: 'user',
            content: text,
            created_at: new Date().toISOString(),
            citations: [],
          };

          set(
            (s) => ({ messages: [...s.messages, tempUserMessage] }),
            false,
            'sendUserMessage:optimistic'
          );

          try {
            const response = await api.sendMessage({
              message: text,
              session_id: state.currentSessionId || undefined,
              attach_document_ids: docsToAttach,
              filter_document_id: filterDocumentId,
            });

            // Update session if new
            if (isNewSession) {
              const newSession: ChatSession = {
                id: response.session_id,
                title: text.substring(0, 50) + (text.length > 50 ? '...' : ''),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                document_ids: [],
                attached_documents: docsToAttach
                  ? state.documents
                      .filter((d) => docsToAttach.includes(d.id))
                      .map((d) => ({
                        id: d.id,
                        original_filename: d.original_filename,
                        file_size: d.file_size,
                        page_count: d.page_count,
                      }))
                  : [],
              };
              set(
                (s) => ({
                  sessions: [newSession, ...s.sessions],
                  currentSessionId: response.session_id,
                }),
                false,
                'sendUserMessage:newSession'
              );
            }

            // Build sources map
            const sourcesMap = new Map<string, SourceChunk>();
            response.sources.forEach((s) => sourcesMap.set(s.chunk_id, s));

            // Replace temp message with real ones and add AI response
            set(
              (s) => ({
                messages: [
                  ...s.messages.filter((m) => m.id !== tempUserMessage.id),
                  {
                    ...tempUserMessage,
                    id: `user-${Date.now()}`,
                    session_id: response.session_id,
                  },
                  response.message,
                ],
                sources: response.sources,
                sourcesMap,
                isLoading: false,
              }),
              false,
              'sendUserMessage:success'
            );
          } catch (error) {
            const message = error instanceof Error ? error.message : 'Failed to send message';
            // Remove optimistic message on error
            set(
              (s) => ({
                messages: s.messages.filter((m) => m.id !== tempUserMessage.id),
                isLoading: false,
                error: message,
              }),
              false,
              'sendUserMessage:error'
            );
          }
        },

        // Async: Load Session
        loadSession: async (sessionId) => {
          set({ isLoading: true }, false, 'loadSession:start');

          try {
            const session = await api.getSession(sessionId);
            set(
              {
                currentSessionId: sessionId,
                messages: session.messages || [],
                isLoading: false,
              },
              false,
              'loadSession:success'
            );
          } catch (error) {
            console.error('Failed to load session:', error);
            set({ isLoading: false }, false, 'loadSession:error');
          }
        },

        // Async: Attach document to current session
        attachDocumentToSession: async (documentId) => {
          const state = get();
          if (!state.currentSessionId) return;

          try {
            const updatedSession = await api.attachDocumentToSession(
              state.currentSessionId,
              documentId
            );
            // Update the session in the list
            set(
              (s) => ({
                sessions: s.sessions.map((sess) =>
                  sess.id === state.currentSessionId
                    ? { ...sess, attached_documents: updatedSession.attached_documents }
                    : sess
                ),
              }),
              false,
              'attachDocumentToSession'
            );
          } catch (error) {
            console.error('Failed to attach document:', error);
          }
        },

        // Loading & Error
        setIsLoading: (loading) =>
          set({ isLoading: loading }, false, 'setIsLoading'),

        setIsUploading: (uploading) =>
          set({ isUploading: uploading }, false, 'setIsUploading'),

        setError: (error) => set({ error }, false, 'setError'),

        // Reset
        reset: () => set(initialState, false, 'reset'),

        // Helpers
        getCurrentSessionDocuments: () => {
          const state = get();
          const session = state.sessions.find((s) => s.id === state.currentSessionId);
          return session?.attached_documents || [];
        },

        hasSessionDocuments: () => {
          const state = get();
          const session = state.sessions.find((s) => s.id === state.currentSessionId);
          return (session?.attached_documents?.length || 0) > 0;
        },
      }),
      {
        name: 'sagemind-store',
        partialize: (state) => ({
          // Only persist sessions and documents
          sessions: state.sessions,
          currentSessionId: state.currentSessionId,
          documents: state.documents,
        }),
      }
    ),
    { name: 'SageMindStore' }
  )
);

// Selector hooks for common patterns
export const useCurrentSession = () =>
  useResearchStore((state) =>
    state.sessions.find((s) => s.id === state.currentSessionId)
  );

export const useActiveSource = () =>
  useResearchStore((state) => state.activeSource);

export const useMessages = () => useResearchStore((state) => state.messages);

export const useSources = () => useResearchStore((state) => state.sources);

export const useIsLoading = () => useResearchStore((state) => state.isLoading);
