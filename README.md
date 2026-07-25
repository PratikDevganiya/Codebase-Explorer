# Codebase Explorer

An AI-powered codebase assistant that lets developers upload a software project
and ask natural-language questions about it.

[Live application](https://codebase-explorer-ypha.onrender.com) ·
[API health](https://codebase-explorer-api.onrender.com/health) ·
[API documentation](https://codebase-explorer-api.onrender.com/docs)

## Overview

Codebase Explorer helps developers understand unfamiliar projects without
reading every file manually. It accepts a GitHub repository, ZIP archive, or
local folder, detects the language of each source file, creates semantic code
embeddings, and retrieves the most relevant code before asking Gemini to
generate an answer.

The application supports multiple projects. Source files, vector embeddings,
project metadata, named conversation history, and chat messages are persisted
in Supabase and scoped to the selected projects.

## Features

- Import one or multiple public GitHub repositories, ZIP archives, and
  browser-selected folders in one attachment batch
- Automatically detect the programming language of each file
- Ignore common generated content such as `.git`, virtual environments,
  `node_modules`, build output, and caches
- Parse and split source code into searchable chunks
- Ask natural-language questions about one project or a selected project group
- Retrieve code semantically instead of relying only on keyword matching
- Display related files and line ranges with each answer
- Browse an expandable VS Code-style project tree and inspect source files
- Create named chats, search recent conversations, and reopen their complete
  project scope and message history from a collapsible workspace sidebar
- View project, indexing, query, and system-health information on a dashboard
- Delete one or multiple projects, including their database records, vectors,
  chat history, and stored source files
- Apply upload validation, safe ZIP extraction, path validation, rate limits,
  and project-level retrieval isolation

## How the AI pipeline works

1. The user imports a GitHub repository, ZIP file, or local folder.
2. The backend temporarily clones or reconstructs it in a processing directory.
3. Supported files are detected and loaded; each file is assigned its own
   language.
4. Tree-sitter and the chunking pipeline divide code into meaningful sections.
5. Gemini Embedding 2 converts every chunk into a 384-dimensional vector.
6. Source files are uploaded to private Supabase Storage. Project metadata,
   chunks, and vectors are saved in Supabase Postgres with pgvector.
7. When the user asks a question, the question is embedded with the same model.
8. pgvector retrieves the most semantically relevant chunks from only the
   selected project.
9. The RAG pipeline sends the question and retrieved code to Gemini 3.6 Flash.
10. The UI displays the generated answer and related source locations.

## Technology stack

| Layer | Technology | Why it was selected |
|---|---|---|
| Frontend | React, TypeScript, Vite | Fast, typed, responsive single-page interface |
| API | FastAPI, Pydantic | Typed request validation and automatic API documentation |
| Code parsing | Tree-sitter | Code-aware structure across multiple languages |
| Embeddings | Gemini Embedding 2 | Configurable 384-dimensional remote embeddings without a memory-heavy local model |
| Answer generation | Gemini 3.6 Flash | Fast, cost-conscious code reasoning |
| Retrieval | PostgreSQL + pgvector | Semantic search beside the application's relational data |
| Persistence | Supabase Postgres and Storage | Managed database, private object storage, and vector support in one service |
| Deployment | Render Blueprint and Docker | Reproducible frontend and backend deployment from one repository |
| Testing | Pytest, pytest-cov | Unit and integration coverage for backend behavior |

## Architecture

```text
┌──────────────────────────── React + TypeScript ────────────────────────────┐
│ Project upload · Chat · Dashboard · Code explorer                         │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ HTTPS/JSON
                                   ▼
┌────────────────────────────── FastAPI API ─────────────────────────────────┐
│ Ingestion routes · Query routes · File routes · Project/chat management   │
└──────────────┬───────────────────┬──────────────────────┬──────────────────┘
               │                   │                      │
               ▼                   ▼                      ▼
      Git/ZIP/folder loader   Tree-sitter parser    RAG query pipeline
               │                   │                      │
               └──────────────► Code chunks ◄─────────────┘
                                   │                      │
                                   ▼                      ▼
                         Gemini Embedding 2       Gemini 3.6 Flash
                                   │                      ▲
                                   ▼                      │
┌──────────────────────────────── Supabase ──────────────────────────────────┐
│ Projects and chat │ Source files in private Storage │ pgvector code chunks│
└────────────────────────────────────────────────────────────────────────────┘
```

### Major components

- `backend/ingestion`: clones GitHub repositories and safely loads uploads.
- `backend/parsing`: detects languages, parses supported code, and creates
  semantic chunks.
- `backend/retrieval`: generates embeddings, indexes chunks, and performs
  project-filtered similarity search.
- `backend/llm`: builds retrieval queries and produces grounded answers.
- `backend/storage`: isolates all Supabase database, vector, chat, and object
  storage operations.
- `backend/api`: exposes the application through FastAPI.
- `frontend`: provides the Chat, Dashboard, attachment flow, and code explorer.

### Key design decisions and trade-offs

- **Per-file language detection:** mixed-language repositories work without
  requiring the user to choose one language for the entire project.
- **RAG instead of full-repository prompting:** only relevant chunks are sent to
  the LLM, reducing prompt size and improving grounding.
- **One managed data platform:** Supabase reduces operational complexity, but
  introduces an external dependency and free-tier quotas.
- **Remote Gemini embeddings:** this keeps the Render backend within its memory
  limit. It trades local/offline operation for API availability and quota
  dependence.
- **Project-scoped retrieval:** prevents results from one uploaded project from
  contaminating another project's answers.
- **Temporary server workspace:** uploaded content is processed locally only
  during ingestion; Supabase is the persistent source of truth.

## Project structure

```text
Codebase-Explorer/
├── backend/
│   ├── api/                 # FastAPI routes and request/response models
│   ├── ingestion/           # GitHub, ZIP, and folder ingestion
│   ├── llm/                 # Gemini client and RAG pipeline
│   ├── parsing/             # Language detection, parsing, and chunking
│   ├── retrieval/           # Embeddings, pgvector search, and indexing
│   └── storage/             # Supabase repositories and source storage
├── config/                  # Environment-based application settings
├── frontend/                # React + TypeScript application
├── scripts/                 # Run and production-validation scripts
├── supabase/migrations/     # Database, pgvector, storage, and chat migrations
├── tests/                   # Unit and integration tests
├── Dockerfile               # Production backend image
├── render.yaml              # Render Blueprint
├── requirements-prod.txt    # Minimal production dependencies
├── requirements.txt         # Local development and test dependencies
└── README.md
```

## Local setup

### Prerequisites

- Python 3.12
- Node.js 18 or newer and npm
- Git
- A Google AI Studio API key
- A Supabase project with the `vector` and `pgcrypto` extensions

### 1. Clone the repository

```bash
git clone https://github.com/PratikDevganiya/Codebase-Explorer.git
cd Codebase-Explorer
```

### 2. Create the Python environment

```bash
python3.12 -m venv codebase-explorer-env
source codebase-explorer-env/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Supabase

In the Supabase SQL editor, create the base `projects` table:

```sql
create extension if not exists pgcrypto;

create table if not exists public.projects (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    source_type text not null
        check (source_type in ('github', 'folder', 'zip')),
    source_url text,
    branch text,
    status text not null default 'pending'
        check (status in ('pending', 'uploading', 'indexing', 'ready', 'failed')),
    file_count integer not null default 0 check (file_count >= 0),
    chunk_count integer not null default 0 check (chunk_count >= 0),
    indexed_count integer not null default 0 check (indexed_count >= 0),
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create or replace function public.update_updated_at_column()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists update_projects_updated_at on public.projects;
create trigger update_projects_updated_at
before update on public.projects
for each row execute function public.update_updated_at_column();

alter table public.projects enable row level security;
```

Then execute the files in `supabase/migrations/` in numeric order. They add the
stable repository identifier, pgvector table and similarity function, private
source bucket, chat persistence, and final cloud-only schema.

The backend uses a Supabase secret/service-role key. Never expose that key in
React, commit it to Git, or place it in a `VITE_*` variable.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Set at least:

```dotenv
GEMINI_API_KEY=your_google_ai_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your_backend_only_secret_key
CORS_ORIGINS=http://localhost:3000
```

To enable the optional single-user login, also set:

```dotenv
ADMIN_USERNAME=your_private_id
ADMIN_PASSWORD=use_a_long_unique_password
AUTH_SECRET=generate_with_openssl_rand_hex_32
AUTH_TOKEN_HOURS=12
```

Generate the signing secret with `openssl rand -hex 32`. Authentication is
enabled only when `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `AUTH_SECRET` are all
present. Credentials stay in the backend environment; React receives only a
short-lived signed access token.

The defaults use:

```dotenv
LLM_MODEL=gemini-3.6-flash
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-2
SUPABASE_SOURCE_BUCKET=project-sources
```

Optionally validate cloud storage after applying the migrations:

```bash
python scripts/validate_production.py
```

### 5. Start the backend

```bash
python scripts/run_api.py
```

The API runs at `http://localhost:8000`; Swagger documentation is available at
`http://localhost:8000/docs`.

### 6. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Example usage

### Through the UI

1. Open the Chat page.
2. Select the plus button.
3. Attach a GitHub repository, ZIP archive, or local folder.
4. Wait until the project status becomes **Ready**.
5. Ask questions such as:
   - “Explain the architecture of this project.”
   - “How does authentication work?”
   - “Which API creates a user?”
   - “Where is data stored and retrieved?”
   - “Which files should I change to add this feature?”
6. Select a related file or choose **View code** to inspect the implementation.

### Through the API

Index a public GitHub repository:

```bash
curl -X POST http://localhost:8000/repositories/github \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_url": "https://github.com/owner/repository.git",
    "branch": "main"
  }'
```

Ask a project-scoped question using the returned `repository_id`:

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Explain the main request flow.",
    "repository_id": "repo_your_repository_id",
    "top_k": 5,
    "include_context": true
  }'
```

## Testing

Run the full backend suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=backend --cov-report=term-missing --cov-report=html
```

Validate the frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

At the time of this README update, the backend suite contains **61 passing
tests** with approximately **67% statement coverage**. GitHub Actions runs the
suite with Python 3.12. Test counts and coverage can change as the project
evolves; the workflow result is the authoritative status.

## Deployment

The repository includes `render.yaml`, which creates:

- A Docker-based FastAPI web service
- A Vite static frontend

### Render environment variables

Backend:

```text
GEMINI_API_KEY
SUPABASE_URL
SUPABASE_SECRET_KEY
CORS_ORIGINS=https://your-frontend.onrender.com
ADMIN_USERNAME=your_private_id
ADMIN_PASSWORD=use_a_long_unique_password
AUTH_SECRET=generated_secret_value
```

Frontend:

```text
VITE_API_URL=https://your-backend.onrender.com
```

Create a Render Blueprint from this repository, enter the secret values, and
deploy. Because Vite embeds environment variables at build time, rebuild the
static site after changing `VITE_API_URL`. Set backend `CORS_ORIGINS` to the
exact frontend origin without a trailing slash.

The deployed architecture is:

```text
Render static site → Render Docker API → Gemini APIs
                                      └→ Supabase Postgres/pgvector/Storage
```

The hosted application uses the optional single-administrator login. Supply
demo credentials privately when sharing the deployment; never commit them to
the repository.

## Error and edge-case handling

- Unsupported and generated files are excluded from indexing.
- Empty uploads, invalid types, oversized parts, unsafe paths, and unsafe ZIP
  members are rejected.
- Conversation IDs persist named chat history, while repository IDs scope
  vector retrieval and source files.
- Failed ingestion is reported through project status and error messages.
- API ingestion and query endpoints are rate-limited.
- Project deletion cascades through related database records and explicitly
  removes stored source objects.
- API health is visible in the Dashboard and through `/health`.

## Assumptions

- GitHub ingestion currently targets repositories the server can clone; a
  `GITHUB_TOKEN` may be configured for supported private access.
- Source files are text-based and use a supported filename or extension.
- The current deployment is designed for one authenticated administrator.
- Supabase and Gemini are available and their quotas have not been exhausted.
- The embedding schema and query model both use 384 dimensions.

## Known limitations

- The optional login supports one administrator account; multi-user accounts
  and tenant-level authorization are not implemented.
- Render Free services can sleep and may have a cold-start delay.
- Gemini and Supabase free tiers impose request, storage, and compute limits.
- Ingestion currently runs in the API request rather than a background job
  queue, so very large repositories are not ideal.
- Browser folder upload is limited by browser and server request constraints.
- Private repository authentication is not exposed as a complete UI workflow.
- Answers are grounded by retrieved code but can still contain LLM mistakes.
  Related source files should be used to verify important claims.
- Changing the embedding model requires existing projects to be reindexed.
- Privacy extensions such as Brave Shields may block the separately hosted API
  and must allow requests to the backend domain.

## Future improvements

- Add multi-user authentication, per-user ownership, and Supabase RLS policies
- Move ingestion to background workers with progress events and retries
- Add hybrid keyword/vector retrieval and a reranking stage
- Add evaluation datasets for retrieval quality and answer faithfulness
- Support incremental reindexing after Git commits instead of full ingestion
- Add encrypted private-repository credentials and organization integrations
- Add observability for latency, token usage, failures, and model costs
- Add pagination and lifecycle policies for large project collections
- Add automated end-to-end browser and deployed smoke tests

## Security notes

- `.env` is ignored by Git; `.env.example` contains names only.
- Supabase secret keys and Gemini API keys belong only in the backend
  environment.
- Only `VITE_API_URL` is safe to expose to the browser.
- The Supabase source bucket is private.
- The single-user login protects every application API except the public
  health and login endpoints when its three required environment variables are
  configured.
- For a multi-user production release, add per-user ownership checks and
  restrictive Row Level Security policies before accepting sensitive code.

## License

No open-source license has been added yet. All rights remain with the repository
owner unless a license is added.
