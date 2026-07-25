import type {
  ChatMessage,
  ConversationRecord,
  ExplainResponse,
  HealthResponse,
  IngestResponse,
  IngestionProgress,
  QueryResponse,
  RepositoryFile,
  RepositoryFileContent,
  RepositoryRecord,
  StatsResponse,
} from "./types";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const AUTH_TOKEN_KEY = "codebase-explorer-auth-token";

export const authToken = {
  get: () => window.localStorage.getItem(AUTH_TOKEN_KEY) || "",
  set: (token: string) => window.localStorage.setItem(AUTH_TOKEN_KEY, token),
  clear: () => window.localStorage.removeItem(AUTH_TOKEN_KEY),
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = authToken.get();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") {
      authToken.clear();
      window.dispatchEvent(new Event("codebase-auth-required"));
    }
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || body.error || message;
    } catch {
      // The status text above is enough for non-JSON failures.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  authStatus: (signal?: AbortSignal) =>
    request<{ enabled: boolean }>("/auth/status", { signal }),
  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: string; expires_in: number }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
      },
    ),
  currentUser: (signal?: AbortSignal) =>
    request<{ username: string }>("/auth/me", { signal }),
  health: (signal?: AbortSignal) => request<HealthResponse>("/health", { signal }),
  stats: (signal?: AbortSignal) => request<StatsResponse>("/stats", { signal }),
  repositories: (signal?: AbortSignal) =>
    request<RepositoryRecord[]>("/repositories", { signal }),
  deleteRepository: (repositoryId: string) =>
    request<{ status: string; repository_id: string; files_deleted: number }>(
      `/repositories/${encodeURIComponent(repositoryId)}`,
      { method: "DELETE" },
    ),
  repositoryFiles: (repositoryId: string, signal?: AbortSignal) =>
    request<RepositoryFile[]>(`/repositories/${encodeURIComponent(repositoryId)}/files`, { signal }),
  repositoryFile: (
    repositoryId: string,
    path: string,
    signal?: AbortSignal,
  ) => request<RepositoryFileContent>(
    `/repositories/${encodeURIComponent(repositoryId)}/file?path=${encodeURIComponent(path)}`,
    { signal },
  ),
  query: (
    query: string,
    repositoryIds: string[] = [],
    sessionId?: string,
    conversationId?: string,
  ) =>
    request<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({
        query,
        repository_id: repositoryIds[0] || null,
        repository_ids: repositoryIds,
        session_id: sessionId || null,
        conversation_id: conversationId || null,
        top_k: 5,
        include_context: true,
      }),
    }),
  conversations: (signal?: AbortSignal) =>
    request<ConversationRecord[]>("/conversations", { signal }),
  createConversation: (repositoryIds: string[], title = "New chat") =>
    request<ConversationRecord>("/conversations", {
      method: "POST",
      body: JSON.stringify({
        repository_ids: repositoryIds,
        title,
      }),
    }),
  updateConversation: (
    conversationId: string,
    updates: { title?: string; repository_ids?: string[] },
  ) => request<ConversationRecord>(
    `/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(updates),
    },
  ),
  deleteConversation: (conversationId: string) =>
    request<{ status: string; conversation_id: string }>(
      `/conversations/${encodeURIComponent(conversationId)}`,
      { method: "DELETE" },
    ),
  conversationMessages: (
    conversationId: string,
    signal?: AbortSignal,
  ) => request<ChatMessage[]>(
    `/conversations/${encodeURIComponent(conversationId)}/messages`,
    { signal },
  ),
  clearConversationMessages: (conversationId: string) =>
    request<{ status: string }>(
      `/conversations/${encodeURIComponent(conversationId)}/messages`,
      { method: "DELETE" },
    ),
  chatMessages: (
    repositoryId: string,
    sessionId: string,
    signal?: AbortSignal,
  ) => request<ChatMessage[]>(
    `/repositories/${encodeURIComponent(repositoryId)}/messages?session_id=${encodeURIComponent(sessionId)}`,
    { signal },
  ),
  clearChatMessages: (repositoryId: string, sessionId: string) =>
    request<{ status: string }>(
      `/repositories/${encodeURIComponent(repositoryId)}/messages?session_id=${encodeURIComponent(sessionId)}`,
      { method: "DELETE" },
    ),
  ingest: async (
    repoUrl: string,
    branch: string,
    onProgress?: (progress: IngestionProgress) => void,
  ) => {
    const operationId = crypto.randomUUID();
    let polling = true;
    const pollProgress = async () => {
      while (polling) {
        try {
          const progress = await request<IngestionProgress>(
            `/ingestion-progress/${encodeURIComponent(operationId)}`,
          );
          onProgress?.(progress);
          if (progress.stage === "ready" || progress.stage === "failed") break;
        } catch {
          // The ingestion request below reports terminal errors.
        }
        await new Promise((resolve) => window.setTimeout(resolve, 450));
      }
    };
    const progressTask = pollProgress();
    try {
      return await request<IngestResponse>("/repositories/github", {
        method: "POST",
        body: JSON.stringify({
          repo_url: repoUrl,
          branch,
          operation_id: operationId,
        }),
      });
    } finally {
      polling = false;
      await progressTask;
    }
  },
  uploadProject: async (
    uploadType: "zip" | "folder",
    name: string,
    files: File[],
    onProgress?: (progress: IngestionProgress) => void,
  ) => {
    const ignoredDirectories = new Set([
      ".git", ".idea", ".next", ".pytest_cache", ".venv", ".vscode",
      "__pycache__", "build", "coverage", "dist", "env", "node_modules",
      "target", "venv",
    ]);
    const ignoredFiles = new Set([
      ".DS_Store", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    ]);
    const uploadFiles = uploadType === "folder"
      ? files.filter((file) => {
          const path = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
          const parts = path.replaceAll("\\", "/").split("/");
          return !parts.some((part) => ignoredDirectories.has(part))
            && !ignoredFiles.has(file.name);
        })
      : files;
    if (!uploadFiles.length) {
      throw new Error("No supported project files remain after excluding generated folders.");
    }
    if (uploadFiles.length > 2000) {
      throw new Error("This project still contains more than 2,000 files after excluding generated folders.");
    }
    const form = new FormData();
    const operationId = crypto.randomUUID();
    form.append("upload_type", uploadType);
    form.append("display_name", name);
    form.append("operation_id", operationId);
    form.append(
      "relative_paths",
      JSON.stringify(uploadFiles.map((file) => (
        uploadType === "folder"
          ? ((file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name)
          : file.name
      ))),
    );
    uploadFiles.forEach((file) => form.append("files", file));
    let polling = true;
    const pollProgress = async () => {
      while (polling) {
        try {
          const progress = await request<IngestionProgress>(
            `/ingestion-progress/${encodeURIComponent(operationId)}`,
          );
          onProgress?.(progress);
          if (progress.stage === "ready" || progress.stage === "failed") break;
        } catch {
          // The upload request below reports terminal errors.
        }
        await new Promise((resolve) => window.setTimeout(resolve, 450));
      }
    };
    const progressTask = pollProgress();
    let response: Response;
    try {
      response = await fetch(`${API_URL}/repositories/upload`, {
        method: "POST",
        headers: authToken.get()
          ? { Authorization: `Bearer ${authToken.get()}` }
          : undefined,
        body: form,
      });
    } finally {
      polling = false;
      await progressTask;
    }
    if (!response.ok) {
      if (response.status === 401) {
        authToken.clear();
        window.dispatchEvent(new Event("codebase-auth-required"));
      }
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Upload failed (${response.status})`);
    }
    return response.json() as Promise<IngestResponse>;
  },
  explain: (code: string) =>
    request<ExplainResponse>("/explain", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
};
