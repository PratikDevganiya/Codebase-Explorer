export type Page = "chat" | "dashboard";

export interface SourceReference {
  file: string;
  path: string;
  type: string;
  name: string;
  lines: string;
  language: string;
  relevance: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceReference[];
  num_sources: number;
  query_info: Record<string, unknown>;
  processing_time: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  index_stats: Record<string, unknown>;
  llm: {
    provider?: string;
    model?: string;
    available?: boolean;
  };
  reindex_required: boolean;
}

export interface StatsResponse {
  indexed_vectors: number;
  dimension: number;
  status: string;
  error?: string;
}

export interface IngestResponse {
  status: string;
  message: string;
  repo_name: string;
  files_processed: number;
  chunks_created: number;
  chunks_indexed: number;
  repository_id: string;
  source_type: "github" | "zip" | "folder";
}

export interface RepositoryRecord {
  repository_id: string;
  name: string;
  source_type: "github" | "zip" | "folder";
  source: string;
  status: "indexing" | "ready" | "failed";
  files_processed: number;
  chunks_created: number;
  chunks_indexed: number;
  created_at: string;
  updated_at: string;
}

export interface RepositoryFile {
  path: string;
  name: string;
  language: string;
  size_bytes: number;
}

export interface RepositoryFileContent extends RepositoryFile {
  content: string;
  line_count: number;
}

export interface ExplainResponse {
  explanation: string;
  code_snippet: string;
  language: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceReference[];
}
