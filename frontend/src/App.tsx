import { FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type {
  ChatMessage,
  HealthResponse,
  IngestResponse,
  Page,
  RepositoryFile,
  RepositoryFileContent,
  RepositoryRecord,
  SourceReference,
  StatsResponse,
} from "./types";

const nav: { id: Page; label: string; icon: Page }[] = [
  { id: "chat", label: "Chat", icon: "chat" },
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
];

function NavigationIcon({ name }: { name: Page }) {
  if (name === "chat") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 5.75h14v9.5H9.2L5 18.5V5.75Z" />
        <path d="M8.5 9.25h7M8.5 12h4.5" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4.5" y="4.5" width="6" height="6" rx="1" />
      <rect x="13.5" y="4.5" width="6" height="6" rx="1" />
      <rect x="4.5" y="13.5" width="6" height="6" rx="1" />
      <rect x="13.5" y="13.5" width="6" height="6" rx="1" />
    </svg>
  );
}

function useStoredState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored ? (JSON.parse(stored) as T) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => localStorage.setItem(key, JSON.stringify(value)), [key, value]);
  return [value, setValue] as const;
}

function ErrorNotice({ message }: { message: string }) {
  return <div className="notice error" role="alert">{message}</div>;
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <span>⌁</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.filter(Boolean).map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("***") && part.endsWith("***")) {
      return <strong key={key}><em>{part.slice(3, -3)}</em></strong>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

function MarkdownContent({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  const isBlockStart = (line: string) => (
    /^```/.test(line)
    || /^#{1,6}\s+/.test(line)
    || /^(?:\*{3,}|-{3,}|_{3,})\s*$/.test(line)
    || /^\s*[-*]\s+/.test(line)
    || /^\s*\d+\.\s+/.test(line)
    || /^>\s?/.test(line)
  );

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.startsWith("```")) {
      const language = line.slice(3).trim();
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        code.push(lines[index]);
        index += 1;
      }
      index += index < lines.length ? 1 : 0;
      blocks.push(
        <pre className="answer-code" key={`code-${index}`}>
          {language && <span>{language}</span>}
          <code>{code.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length, 4);
      const children = renderInlineMarkdown(heading[2], `heading-${index}`);
      if (level === 1) blocks.push(<h2 key={`heading-${index}`}>{children}</h2>);
      else if (level === 2) blocks.push(<h3 key={`heading-${index}`}>{children}</h3>);
      else blocks.push(<h4 key={`heading-${index}`}>{children}</h4>);
      index += 1;
      continue;
    }

    if (/^(?:\*{3,}|-{3,}|_{3,})\s*$/.test(line)) {
      blocks.push(<hr key={`rule-${index}`} />);
      index += 1;
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (unordered || ordered) {
      const orderedList = !!ordered;
      const items: ReactNode[] = [];
      const pattern = orderedList ? /^\s*\d+\.\s+(.+)$/ : /^\s*[-*]\s+(.+)$/;
      while (index < lines.length) {
        const item = lines[index].match(pattern);
        if (!item) break;
        items.push(<li key={`item-${index}`}>{renderInlineMarkdown(item[1], `item-${index}`)}</li>);
        index += 1;
      }
      blocks.push(orderedList
        ? <ol key={`list-${index}`}>{items}</ol>
        : <ul key={`list-${index}`}>{items}</ul>);
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quote: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quote.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(
        <blockquote key={`quote-${index}`}>
          {renderInlineMarkdown(quote.join(" "), `quote-${index}`)}
        </blockquote>,
      );
      continue;
    }

    const paragraph: string[] = [line.trim()];
    index += 1;
    while (
      index < lines.length
      && lines[index].trim()
      && !isBlockStart(lines[index])
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(
      <p key={`paragraph-${index}`}>
        {renderInlineMarkdown(paragraph.join(" "), `paragraph-${index}`)}
      </p>,
    );
  }

  return <div className="markdown-content">{blocks}</div>;
}

function sourceLineRange(lines: string) {
  const [start, end] = lines.split("-").map(Number);
  return {
    start: Number.isFinite(start) ? start : 0,
    end: Number.isFinite(end) ? end : start || 0,
  };
}

function resolveSourcePath(files: RepositoryFile[], source: SourceReference) {
  const normalized = source.path.replaceAll("\\", "/");
  return files.find((file) => (
    normalized === file.path
    || normalized.endsWith(`/${file.path}`)
  ))?.path || files.find((file) => file.name === source.file)?.path;
}

type FileTreeNode = {
  name: string;
  path: string;
  type: "folder" | "file";
  file?: RepositoryFile;
  children: FileTreeNode[];
};

function buildFileTree(files: RepositoryFile[]) {
  const root: FileTreeNode = {
    name: "root",
    path: "",
    type: "folder",
    children: [],
  };

  files.forEach((file) => {
    const parts = file.path.split("/");
    let parent = root;
    parts.forEach((part, index) => {
      const path = parts.slice(0, index + 1).join("/");
      const isFile = index === parts.length - 1;
      let node = parent.children.find((child) => (
        child.name === part && child.type === (isFile ? "file" : "folder")
      ));
      if (!node) {
        node = {
          name: part,
          path,
          type: isFile ? "file" : "folder",
          file: isFile ? file : undefined,
          children: [],
        };
        parent.children.push(node);
      }
      parent = node;
    });
  });

  const sortNodes = (nodes: FileTreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((node) => sortNodes(node.children));
  };
  sortNodes(root.children);
  return root.children;
}

function FolderTreeIcon({ open }: { open: boolean }) {
  return (
    <svg className="folder-tree-icon" viewBox="0 0 20 20" aria-hidden="true">
      {open ? (
        <path d="M2.5 6.5h5l1.5 1.7h8.5l-1.7 7H4.1l-1.6-8.7Z" />
      ) : (
        <path d="M2.5 5.5h5l1.5 1.7h8.5v7.3h-15v-9Z" />
      )}
    </svg>
  );
}

function FileTreeIcon() {
  return (
    <svg className="file-tree-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M5 2.8h6.2L15 6.6v10.6H5V2.8Z" />
      <path d="M11 2.8v4h4M7.5 10h5M7.5 13h5" />
    </svg>
  );
}

function CodeExplorer({
  files,
  selectedPath,
  fileContent,
  highlight,
  loading,
  error,
  onSelect,
  onClose,
}: {
  files: RepositoryFile[];
  selectedPath: string;
  fileContent: RepositoryFileContent | null;
  highlight: { start: number; end: number } | null;
  loading: boolean;
  error: string;
  onSelect: (path: string) => void;
  onClose: () => void;
}) {
  const highlightedLine = useRef<HTMLSpanElement>(null);
  const tree = buildFileTree(files);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  useEffect(() => {
    highlightedLine.current?.scrollIntoView({ block: "center" });
  }, [fileContent?.path, highlight?.start, highlight?.end]);

  useEffect(() => {
    setExpandedFolders((current) => {
      const next = new Set(current);
      tree.filter((node) => node.type === "folder").forEach((node) => next.add(node.path));
      return next;
    });
  }, [files]);

  useEffect(() => {
    if (!selectedPath) return;
    const parts = selectedPath.split("/");
    setExpandedFolders((current) => {
      const next = new Set(current);
      parts.slice(0, -1).forEach((_, index) => {
        next.add(parts.slice(0, index + 1).join("/"));
      });
      return next;
    });
  }, [selectedPath]);

  const toggleFolder = (path: string) => {
    setExpandedFolders((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const renderTree = (nodes: FileTreeNode[], depth = 0): ReactNode => nodes.map((node) => {
    if (node.type === "folder") {
      const expanded = expandedFolders.has(node.path);
      return (
        <div className="tree-node" key={`folder-${node.path}`}>
          <button
            className="folder-row"
            onClick={() => toggleFolder(node.path)}
            style={{ paddingLeft: `${10 + depth * 14}px` }}
            title={node.path}
          >
            <span className={expanded ? "tree-arrow expanded" : "tree-arrow"}>›</span>
            <FolderTreeIcon open={expanded} />
            <strong>{node.name}</strong>
          </button>
          {expanded && renderTree(node.children, depth + 1)}
        </div>
      );
    }
    return (
      <button
        className={selectedPath === node.path ? "file-row active" : "file-row"}
        key={`file-${node.path}`}
        onClick={() => onSelect(node.path)}
        style={{ paddingLeft: `${12 + depth * 14}px` }}
        title={node.path}
      >
        <FileTreeIcon />
        <span className="file-label"><strong>{node.name}</strong></span>
      </button>
    );
  });

  return (
    <section className="code-explorer panel" aria-label="Repository code explorer">
      <div className="explorer-toolbar">
        <div><strong>Explorer</strong><span>{files.length} source files</span></div>
        <button className="text-button" onClick={onClose}>Close</button>
      </div>
      <div className="explorer-body">
        <aside className="file-tree">
          {renderTree(tree)}
        </aside>
        <div className="code-viewer">
          <div className="file-tab">
            <span>{fileContent?.path || "Select a file"}</span>
            {fileContent && <small>{fileContent.language} · {fileContent.line_count} lines</small>}
          </div>
          {error ? (
            <div className="viewer-message error">{error}</div>
          ) : loading ? (
            <div className="viewer-message">Loading source…</div>
          ) : fileContent ? (
            <pre>
              {fileContent.content.split("\n").map((line, index) => {
                const lineNumber = index + 1;
                const highlighted = !!highlight
                  && lineNumber >= highlight.start
                  && lineNumber <= highlight.end;
                return (
                  <span
                    className={highlighted ? "code-line highlighted" : "code-line"}
                    key={lineNumber}
                    ref={highlighted && lineNumber === highlight?.start ? highlightedLine : undefined}
                  >
                    <i>{lineNumber}</i><code>{line || " "}</code>
                  </span>
                );
              })}
            </pre>
          ) : (
            <div className="viewer-message">Choose a source file from the explorer.</div>
          )}
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("chat");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [apiError, setApiError] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [repositories, setRepositories] = useState<RepositoryRecord[]>([]);

  const refreshStatus = async (signal?: AbortSignal) => {
    try {
      const [nextHealth, nextStats, nextRepositories] = await Promise.all([
        api.health(signal),
        api.stats(signal),
        api.repositories(signal),
      ]);
      setHealth(nextHealth);
      setStats(nextStats);
      setRepositories(nextRepositories);
      setApiError("");
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        setApiError("FastAPI is offline. Start it with python scripts/run_api.py.");
        setHealth(null);
      }
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    refreshStatus(controller.signal);
    const timer = window.setInterval(() => refreshStatus(), 30_000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">
          <strong className="brand-wordmark">
            <span>Codebase</span><span>Explorer</span>
          </strong>
        </div>
        <nav aria-label="Main navigation">
          {nav.map((item) => (
            <button
              className={page === item.id ? "nav-item active" : "nav-item"}
              key={item.id}
              onClick={() => setPage(item.id)}
            >
              <span><NavigationIcon name={item.icon} /></span>{item.label}
            </button>
          ))}
        </nav>
      </div>

      <main>
        <header>
          <div>
            <p className="eyebrow">AI-POWERED CODE INTELLIGENCE</p>
            <h1>{nav.find((item) => item.id === page)?.label}</h1>
          </div>
        </header>
        {apiError && <ErrorNotice message={apiError} />}
        {health?.reindex_required && (
          <ErrorNotice message="The saved index uses the old hash embeddings. Re-index a repository before asking questions." />
        )}
        {page === "chat" && (
          <ChatPage
            messages={messages}
            setMessages={setMessages}
            onIndexComplete={() => refreshStatus()}
          />
        )}
        {page === "dashboard" && (
          <Dashboard
            health={health}
            stats={stats}
            messages={messages}
            repositories={repositories}
            onProjectsChanged={() => refreshStatus()}
          />
        )}
      </main>
    </div>
  );
}

function ChatPage({
  messages,
  setMessages,
  onIndexComplete,
}: {
  messages: ChatMessage[];
  setMessages: (messages: ChatMessage[]) => void;
  onIndexComplete: () => void;
}) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [repositories, setRepositories] = useState<RepositoryRecord[]>([]);
  const [selectedId, setSelectedId] = useStoredState("rag-active-repository", "");
  const [sessionId] = useStoredState("rag-session-id", crypto.randomUUID());
  const [attachOpen, setAttachOpen] = useState(false);
  const [attachType, setAttachType] = useState<"github" | "zip" | "folder" | "code">("github");
  const [projectName, setProjectName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [codeSnippet, setCodeSnippet] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [phase, setPhase] = useState<"" | "uploading" | "cloning" | "indexing" | "analyzing" | "ready">("");
  const [explorerOpen, setExplorerOpen] = useState(false);
  const [repositoryFiles, setRepositoryFiles] = useState<RepositoryFile[]>([]);
  const [selectedPath, setSelectedPath] = useState("");
  const [fileContent, setFileContent] = useState<RepositoryFileContent | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [explorerError, setExplorerError] = useState("");
  const [highlight, setHighlight] = useState<{ start: number; end: number } | null>(null);
  const folderInput = useRef<HTMLInputElement>(null);

  const loadRepositories = async () => {
    try {
      const records = await api.repositories();
      setRepositories(records);
      if (!records.some((record) => record.repository_id === selectedId)) {
        setSelectedId(records[0]?.repository_id || "");
      }
    } catch {
      // The main API status notice already reports connectivity failures.
    }
  };

  useEffect(() => {
    loadRepositories();
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    setMessages([]);
    api.chatMessages(selectedId, sessionId, controller.signal)
      .then((storedMessages) => {
        setMessages(storedMessages);
      })
      .catch((requestError) => {
        if ((requestError as Error).name !== "AbortError") {
          setError((requestError as Error).message);
        }
      });
    return () => controller.abort();
  }, [selectedId, sessionId]);

  useEffect(() => {
    folderInput.current?.setAttribute("webkitdirectory", "");
    folderInput.current?.setAttribute("directory", "");
  }, [attachType]);

  useEffect(() => {
    if (!explorerOpen || !selectedId) return;
    const controller = new AbortController();
    setFileLoading(true);
    setExplorerError("");
    api.repositoryFiles(selectedId, controller.signal)
      .then(async (files) => {
        setRepositoryFiles(files);
        if (!files.length) {
          setSelectedPath("");
          setFileContent(null);
          return;
        }
        const nextPath = files.some((file) => file.path === selectedPath)
          ? selectedPath
          : files[0].path;
        setSelectedPath(nextPath);
        setFileContent(await api.repositoryFile(selectedId, nextPath, controller.signal));
      })
      .catch((requestError) => {
        if ((requestError as Error).name !== "AbortError") {
          setExplorerError((requestError as Error).message);
        }
      })
      .finally(() => setFileLoading(false));
    return () => controller.abort();
  }, [explorerOpen, selectedId]);

  const activeRepository = repositories.find((item) => item.repository_id === selectedId);

  const setCurrentMessages = (nextMessages: ChatMessage[]) => {
    setMessages(nextMessages);
  };

  const selectRepository = (repositoryId: string) => {
    setSelectedId(repositoryId);
    setMessages([]);
    setExplorerOpen(false);
    setFileContent(null);
    setSelectedPath("");
    setHighlight(null);
  };

  const clearCurrentMessages = () => {
    setCurrentMessages([]);
    if (selectedId) {
      api.clearChatMessages(selectedId, sessionId).catch(() => {
        // The visible chat is already cleared; report failures on next load.
      });
    }
  };

  const deleteCurrentRepository = async () => {
    if (!activeRepository || deleting) return;
    const confirmed = window.confirm(
      `Delete "${activeRepository.name}" permanently?\n\nThis removes its files, vectors, and chat history from Supabase. This cannot be undone.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    setError("");
    try {
      await api.deleteRepository(activeRepository.repository_id);
      const remaining = repositories.filter(
        (repository) => repository.repository_id !== activeRepository.repository_id,
      );
      setRepositories(remaining);
      selectRepository(remaining[0]?.repository_id || "");
      setMessages([]);
      onIndexComplete();
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  const openFile = async (
    path: string,
    lineRange: { start: number; end: number } | null = null,
  ) => {
    if (!selectedId) return;
    setExplorerOpen(true);
    setSelectedPath(path);
    setHighlight(lineRange);
    setFileLoading(true);
    setExplorerError("");
    try {
      setFileContent(await api.repositoryFile(selectedId, path));
    } catch (requestError) {
      setExplorerError((requestError as Error).message);
    } finally {
      setFileLoading(false);
    }
  };

  const openSource = (source: SourceReference) => {
    const path = resolveSourcePath(repositoryFiles, source);
    if (path) {
      openFile(path, sourceLineRange(source.lines));
      return;
    }
    setExplorerOpen(true);
    setExplorerError(`The source file ${source.file} is unavailable in this project preview.`);
  };

  const attachProject = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      if (attachType === "code") {
        const code = codeSnippet.trim();
        if (!code) return;
        setPhase("analyzing");
        const result = await api.explain(code);
        setCurrentMessages([
          ...messages,
          {
            id: crypto.randomUUID(),
            role: "user",
            content: `Explain this code:\n\n${code}`,
          },
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `Detected language: ${result.language}\n\n${result.explanation}`,
          },
        ]);
        setCodeSnippet("");
        setPhase("ready");
        window.setTimeout(() => {
          setAttachOpen(false);
          setPhase("");
        }, 700);
        return;
      }

      let result: IngestResponse;
      if (attachType === "github") {
        if (!repoUrl.trim()) return;
        setPhase("cloning");
        const request = api.ingest(repoUrl.trim(), branch.trim() || "main");
        window.setTimeout(() => setPhase((current) => current === "cloning" ? "indexing" : current), 900);
        result = await request;
      } else {
        if (!selectedFiles.length || !projectName.trim()) return;
        setPhase("uploading");
        const request = api.uploadProject(attachType, projectName.trim(), selectedFiles);
        window.setTimeout(() => setPhase((current) => current === "uploading" ? "indexing" : current), 900);
        result = await request;
      }
      setPhase("ready");
      selectRepository(result.repository_id);
      await loadRepositories();
      onIndexComplete();
      window.setTimeout(() => {
        setAttachOpen(false);
        setPhase("");
      }, 700);
    } catch (requestError) {
      setPhase("");
      setError((requestError as Error).message);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const text = query.trim();
    if (!text || loading || !selectedId) return;
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: text };
    const pending = [...messages, userMessage];
    setCurrentMessages(pending);
    setQuery("");
    setLoading(true);
    setError("");
    try {
      const result = await api.query(text, selectedId, sessionId);
      setCurrentMessages([...pending, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.answer,
        sources: result.sources,
      }]);
      if (explorerOpen && result.sources.length) {
        const path = resolveSourcePath(repositoryFiles, result.sources[0]);
        if (path) await openFile(path, sourceLineRange(result.sources[0].lines));
      }
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className={explorerOpen ? "chat-page explorer-open" : "chat-page"}>
      {explorerOpen && (
        <CodeExplorer
          files={repositoryFiles}
          selectedPath={selectedPath}
          fileContent={fileContent}
          highlight={highlight}
          loading={fileLoading}
          error={explorerError}
          onSelect={(path) => openFile(path)}
          onClose={() => setExplorerOpen(false)}
        />
      )}
      <div className="panel conversation">
        <div className="panel-heading">
          <div>
            <h2>Ask your codebase</h2>
            <p>{activeRepository ? `Answers are scoped to ${activeRepository.name}.` : "Attach a project to begin."}</p>
          </div>
          {messages.length > 0 && <button className="text-button" onClick={clearCurrentMessages}>Clear chat</button>}
        </div>
        {activeRepository && (
          <div className="workspace-strip">
            <div className="repository-chip">
              <span>⌘</span>
              <div><strong>{activeRepository.name}</strong><small>{activeRepository.source_type} · ready</small></div>
              <button onClick={() => setAttachOpen(!attachOpen)} aria-label="Change project">Change</button>
              <button
                className="chip-delete"
                onClick={deleteCurrentRepository}
                disabled={deleting}
                aria-label={`Delete ${activeRepository.name}`}
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
            {repositories.length > 1 && (
              <select value={selectedId} onChange={(event) => {
                selectRepository(event.target.value);
              }} aria-label="Active repository">
                {repositories.map((repository) => (
                  <option value={repository.repository_id} key={repository.repository_id}>{repository.name}</option>
                ))}
              </select>
            )}
            <button
              className="explorer-toggle"
              onClick={() => setExplorerOpen((open) => !open)}
            >
              {explorerOpen ? "Hide code" : "View code"}
            </button>
          </div>
        )}
        {attachOpen && (
          <form className="attachment-panel" onSubmit={attachProject}>
            <div className="attachment-tabs">
              {(["github", "zip", "folder", "code"] as const).map((type) => (
                <button type="button" className={attachType === type ? "active" : ""} onClick={() => {
                  setAttachType(type);
                  setSelectedFiles([]);
                }} key={type}>
                  {type === "github" ? "GitHub link" : type === "zip" ? "ZIP file" : type === "folder" ? "Local folder" : "Paste code"}
                </button>
              ))}
            </div>
            {attachType === "github" ? (
              <div className="attachment-fields">
                <input type="url" value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="https://github.com/owner/repository" required />
                <input value={branch} onChange={(event) => setBranch(event.target.value)} placeholder="main" aria-label="Git branch" />
              </div>
            ) : attachType === "code" ? (
              <textarea
                className="code-snippet-input"
                value={codeSnippet}
                onChange={(event) => setCodeSnippet(event.target.value)}
                placeholder="Paste a function or code snippet here…"
                spellCheck={false}
                required
              />
            ) : (
              <div className="attachment-fields upload-fields">
                <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Project name" required />
                <label className="file-picker">
                  <input
                    ref={attachType === "folder" ? folderInput : undefined}
                    type="file"
                    accept={attachType === "zip" ? ".zip,application/zip" : undefined}
                    multiple={attachType === "folder"}
                    onChange={(event) => {
                      const files = Array.from(event.target.files || []);
                      setSelectedFiles(files);
                      if (!projectName && files.length) {
                        const relative = (files[0] as File & { webkitRelativePath?: string }).webkitRelativePath;
                        setProjectName(relative?.split("/")[0] || files[0].name.replace(/\.zip$/i, ""));
                      }
                    }}
                  />
                  {selectedFiles.length ? `${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"} selected` : `Choose ${attachType}`}
                </label>
              </div>
            )}
            <div className="attachment-actions">
              <div className={`index-phase ${phase ? "visible" : ""}`}>
                <i className={phase === "ready" ? "done" : ""}>{phase === "ready" ? "✓" : "↻"}</i>
                <span>{phase || (attachType === "code" ? "Language is detected automatically" : "Files stay scoped to this project")}</span>
              </div>
              <button disabled={!!phase}>
                {phase ? "Working…" : attachType === "code" ? "Explain in chat →" : "Attach and index →"}
              </button>
            </div>
          </form>
        )}
        <div className="messages" aria-live="polite">
          {messages.length === 0 && (
            <EmptyState
              title={activeRepository ? `Chat with ${activeRepository.name}` : "Attach a project or paste code"}
              text={activeRepository ? "Ask about the project, or use the plus button to paste a code snippet." : "Use the plus button to add a project or explain a pasted code snippet."}
            />
          )}
          {messages.map((message) => (
            <article className={`message ${message.role}`} key={message.id}>
              <div className="avatar">{message.role === "user" ? "You" : "AI"}</div>
              <div className="bubble">
                {message.role === "assistant"
                  ? <MarkdownContent content={message.content} />
                  : <p>{message.content}</p>}
                {!!message.sources?.length && (
                  <div className="source-links" aria-label="Related files">
                    {message.sources.slice(0, 3).map((source, index) => (
                      <button
                        key={`${source.path}-${source.lines}-${index}`}
                        onClick={() => openSource(source)}
                        title={`Open ${source.path}, lines ${source.lines}`}
                      >
                        <span>‹›</span>
                        {source.file}
                        <small>:{source.lines}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))}
          {loading && <div className="typing"><i /><i /><i /> Searching your codebase</div>}
        </div>
        {error && <ErrorNotice message={error} />}
        <form className="query-form" onSubmit={submit}>
          <button type="button" className="plus-button" onClick={() => setAttachOpen(!attachOpen)} aria-label="Add project or code">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
          <input disabled={!activeRepository} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={activeRepository ? `Ask about ${activeRepository.name}…` : "Attach a project to start chatting"} aria-label="Codebase question" />
          <button disabled={!query.trim() || loading || !activeRepository}>{loading ? "Working…" : "Ask →"}</button>
        </form>
      </div>
    </section>
  );
}

function Dashboard({
  health,
  stats,
  messages,
  repositories,
  onProjectsChanged,
}: {
  health: HealthResponse | null;
  stats: StatsResponse | null;
  messages: ChatMessage[];
  repositories: RepositoryRecord[];
  onProjectsChanged: () => void;
}) {
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const questions = messages.filter((item) => item.role === "user").length;
  const answers = messages.filter((item) => item.role === "assistant").length;
  const maxActivity = Math.max(questions, answers, 1);
  const selectedCount = selectedProjects.size;
  const allSelected = repositories.length > 0
    && repositories.every((repository) => selectedProjects.has(repository.repository_id));

  useEffect(() => {
    setSelectedProjects((current) => new Set(
      [...current].filter((repositoryId) => (
        repositories.some((repository) => repository.repository_id === repositoryId)
      )),
    ));
  }, [repositories]);

  const toggleProject = (repositoryId: string) => {
    setSelectedProjects((current) => {
      const next = new Set(current);
      if (next.has(repositoryId)) next.delete(repositoryId);
      else next.add(repositoryId);
      return next;
    });
  };

  const deleteSelectedProjects = async () => {
    if (!selectedCount || deleting) return;
    const names = repositories
      .filter((repository) => selectedProjects.has(repository.repository_id))
      .map((repository) => repository.name);
    const confirmed = window.confirm(
      `Delete ${selectedCount} project${selectedCount === 1 ? "" : "s"} permanently?\n\n${names.join(", ")}\n\nAll related files, vectors, and chats will be removed from Supabase. This cannot be undone.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    setDeleteError("");
    const failed: string[] = [];
    for (const repository of repositories) {
      if (!selectedProjects.has(repository.repository_id)) continue;
      try {
        await api.deleteRepository(repository.repository_id);
      } catch {
        failed.push(repository.name);
      }
    }
    setDeleting(false);
    if (failed.length) {
      setDeleteError(`Could not delete: ${failed.join(", ")}. Please try again.`);
      setSelectedProjects(new Set(
        repositories
          .filter((repository) => failed.includes(repository.name))
          .map((repository) => repository.repository_id),
      ));
    } else {
      setSelectedProjects(new Set());
    }
    onProjectsChanged();
  };

  return (
    <section className="stack">
      <div className="stat-grid">
        <div className="stat"><span>Indexed vectors</span><strong>{(stats?.indexed_vectors || 0).toLocaleString()}</strong><small>Supabase pgvector</small></div>
        <div className="stat"><span>Total queries</span><strong>{questions}</strong><small>This browser</small></div>
        <div className="stat"><span>Vector dimension</span><strong>{stats?.dimension || 0}</strong><small>Embedding size</small></div>
        <div className="stat"><span>Projects</span><strong>{repositories.length}</strong><small>Indexed by the API</small></div>
      </div>
      <div className="dashboard-grid">
        <div className="panel activity">
          <div className="panel-heading"><div><h2>Chat activity</h2><p>Questions and successful responses.</p></div></div>
          <div className="bars">
            <div><span>Questions</span><i style={{ width: `${(questions / maxActivity) * 100}%` }} /><strong>{questions}</strong></div>
            <div><span>Responses</span><i style={{ width: `${(answers / maxActivity) * 100}%` }} /><strong>{answers}</strong></div>
          </div>
        </div>
        <div className="panel health-card">
          <div className="panel-heading"><div><h2>System health</h2><p>FastAPI service availability.</p></div></div>
          <div className="health-row"><i className={health ? "online" : "offline"} /><div><strong>{health?.status || "offline"}</strong><span>API status</span></div></div>
          <div className="health-row"><div className="version">v</div><div><strong>{health?.version || "—"}</strong><span>Backend version</span></div></div>
          <div className="health-row"><div className="version">AI</div><div><strong>{health?.llm?.model || "unavailable"}</strong><span>{health?.llm?.provider || "No"} language model</span></div></div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Indexed projects</h2>
            <p>Repository details and per-project indexing results.</p>
          </div>
          <div className="project-actions">
            {repositories.length > 0 && (
              <>
                <label className="select-all">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={() => setSelectedProjects(
                      allSelected
                        ? new Set()
                        : new Set(repositories.map((repository) => repository.repository_id)),
                    )}
                  />
                  Select all
                </label>
                <button
                  className="danger-button"
                  disabled={!selectedCount || deleting}
                  onClick={deleteSelectedProjects}
                >
                  {deleting ? "Deleting…" : `Delete selected${selectedCount ? ` (${selectedCount})` : ""}`}
                </button>
              </>
            )}
            <span className="count">{repositories.length}</span>
          </div>
        </div>
        {deleteError && <ErrorNotice message={deleteError} />}
        {repositories.length === 0 ? (
          <EmptyState
            title="No indexed projects"
            text="Attach a GitHub repository, ZIP, or local folder from Chat."
          />
        ) : (
          <div className="repo-list">
            {repositories.map((repository) => (
              <article
                className={selectedProjects.has(repository.repository_id) ? "selected" : ""}
                key={repository.repository_id}
              >
                <input
                  className="repo-checkbox"
                  type="checkbox"
                  checked={selectedProjects.has(repository.repository_id)}
                  onChange={() => toggleProject(repository.repository_id)}
                  aria-label={`Select ${repository.name}`}
                />
                <div className="repo-icon">
                  {repository.source_type === "github" ? "⌘" : repository.source_type === "zip" ? "ZIP" : "⌁"}
                </div>
                <div className="repo-details">
                  <div className="repo-title">
                    <h3>{repository.name}</h3>
                    <span className={`repo-status ${repository.status}`}>{repository.status}</span>
                  </div>
                  {repository.source_type === "github" ? (
                    <a href={repository.source} target="_blank" rel="noreferrer">{repository.source}</a>
                  ) : (
                    <span className="repo-source">{repository.source_type === "folder" ? "Local folder" : repository.source}</span>
                  )}
                  <small>
                    {repository.source_type} · Indexed {new Date(repository.updated_at).toLocaleString()}
                  </small>
                </div>
                <div className="repo-metrics">
                  <span><strong>{repository.files_processed}</strong> files</span>
                  <span><strong>{repository.chunks_created || repository.chunks_indexed}</strong> chunks</span>
                  <span><strong>{repository.chunks_indexed}</strong> indexed</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
