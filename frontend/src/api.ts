import type {
  ChatMessage,
  ExplainResponse,
  HealthResponse,
  IngestResponse,
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
  ) =>
    request<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({
        query,
        repository_id: repositoryIds[0] || null,
        repository_ids: repositoryIds,
        session_id: sessionId || null,
        top_k: 5,
        include_context: true,
      }),
    }),
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
  ingest: (repoUrl: string, branch: string) =>
    request<IngestResponse>("/repositories/github", {
      method: "POST",
      body: JSON.stringify({ repo_url: repoUrl, branch }),
    }),
  uploadProject: async (
    uploadType: "zip" | "folder",
    name: string,
    files: File[],
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
    form.append("upload_type", uploadType);
    form.append("display_name", name);
    form.append(
      "relative_paths",
      JSON.stringify(uploadFiles.map((file) => (
        uploadType === "folder"
          ? ((file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name)
          : file.name
      ))),
    );
    uploadFiles.forEach((file) => form.append("files", file));
    const response = await fetch(`${API_URL}/repositories/upload`, {
      method: "POST",
      headers: authToken.get()
        ? { Authorization: `Bearer ${authToken.get()}` }
        : undefined,
      body: form,
    });
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
