# Architecture Document

## Overall System Architecture

Codebase Explorer is a Retrieval-Augmented Generation (RAG) application that
helps developers understand unfamiliar software projects. Users upload a GitHub
repository, ZIP archive, local folder, or pasted code through the React
frontend. The FastAPI backend processes the code, stores searchable project
data, and answers questions using retrieved code context.

```text
┌─────────────────────────────────────┐
│          React Frontend              │
│ Upload projects · Chat · Code viewer │
└──────────────────┬──────────────────┘
                   │ HTTPS / JSON
                   ▼
┌─────────────────────────────────────┐
│          FastAPI Backend             │
│ Validation · Ingestion · Retrieval   │
│ RAG orchestration · Authentication   │
└───────────┬────────────────┬────────┘
            │                │
            ▼                ▼
┌───────────────────┐  ┌──────────────────┐
│ Supabase          │  │ Gemini APIs      │
│ PostgreSQL        │  │ Embeddings       │
│ pgvector          │  │ Answer generation│
│ Private storage   │  └──────────────────┘
└───────────────────┘
```

During ingestion, the backend detects supported files, identifies their
languages, parses them, creates semantic chunks, and produces vector embeddings.
The chunks, source files, metadata, and embeddings are stored in Supabase. When
a user asks a question, the backend embeds the question, retrieves relevant code
chunks from the selected projects, and passes that context to Gemini to generate
a grounded answer with source references.

## Major Components

- **React frontend:** Provides project upload, project selection, chat,
  conversation history, dashboard, and source-code browsing.
- **FastAPI backend:** Exposes API endpoints and coordinates validation,
  authentication, ingestion, retrieval, and answer generation.
- **Ingestion pipeline:** Imports projects from GitHub, ZIP archives, folders,
  or pasted code and excludes generated, unsafe, binary, and oversized files.
- **Parsing and chunking:** Uses language detection and Tree-sitter parsing to
  split source code into meaningful chunks with file-path and line metadata.
- **Embedding and retrieval:** Creates vector embeddings for code and queries,
  then uses Supabase pgvector to find semantically similar chunks.
- **RAG pipeline:** Sends the user question and retrieved code context to Gemini
  Flash and returns an answer based on that evidence.
- **Supabase:** Persists project metadata, source files, embeddings, chat
  conversations, and messages.

## Design Decisions

- **Retrieval-Augmented Generation:** The system retrieves relevant code before
  prompting the model instead of sending an entire repository to the model.
- **Project-scoped retrieval:** Each code chunk is linked to a project ID so
  answers use only the currently selected project or projects.
- **Tree-sitter parsing:** Code-aware parsing preserves structures such as
  functions and classes better than splitting files by a fixed character count.
- **Managed storage and vectors:** Supabase combines relational data, private
  source storage, chat history, and pgvector similarity search.
- **Hosted AI services:** Gemini handles embeddings and answer generation,
  avoiding the infrastructure cost of self-hosted models.
- **Separated frontend and backend:** The frontend never receives Gemini or
  Supabase service credentials; sensitive operations remain on the backend.

## Trade-offs Considered

| Decision | Benefit | Trade-off |
| --- | --- | --- |
| RAG retrieval | More relevant, evidence-based answers | Quality depends on chunking and embedding quality |
| Gemini APIs | Fast AI capabilities without local model hosting | Depends on network access, quotas, and provider availability |
| Supabase with pgvector | One managed platform for application and vector data | Introduces an external service dependency |
| Tree-sitter parsing | Produces more meaningful code chunks | Requires grammar support and dependency maintenance |
| Separate frontend and backend | Protects credentials and improves maintainability | Requires two deployment services |
| Project-scoped search | Prevents unrelated projects affecting answers | Cross-project analysis requires selecting multiple projects |

## Challenges Encountered

- Supporting several ingestion methods while keeping validation and processing
  behaviour consistent.
- Safely extracting ZIP uploads and preventing unsafe paths or unsupported
  content from being processed.
- Handling mixed-language repositories and preserving useful code boundaries.
- Avoiding dependency folders, generated files, binaries, and very large files
  that would increase indexing time and cost.
- Managing embedding failures and Gemini quota limits during repository indexing.
- Ensuring retrieved chunks remain isolated to the selected project scope.
- Communicating indexing progress and failures clearly to the user.

## What Would Be Improved With Additional Time

- Move ingestion and embedding work to a background job queue for larger
  repositories and more reliable progress reporting.
- Add multi-user accounts, organisation workspaces, and role-based access
  control.
- Implement incremental Git indexing so only changed files are reprocessed.
- Add retrieval evaluation datasets and automated answer-quality testing.
- Add real-time progress updates and streaming chat responses.
- Extend language support and introduce dependency, call-graph, and architecture
  visualisations.
- Improve observability for latency, indexing failures, retrieval relevance,
  token usage, and provider cost.
