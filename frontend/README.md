# React frontend

This is the production frontend for Codebase Explorer. It uses the FastAPI
endpoints and does not import or duplicate backend business logic.

## Run locally

Start the existing API:

```bash
codebase-rag-env/bin/python scripts/run_api.py
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The port is intentionally `3000` because it is
already included in the backend CORS configuration.

To use another API URL, copy `.env.example` to `.env` and edit
`VITE_API_URL`.

## Feature parity

- Chat scoped to one attached repository
- Attach a GitHub link, ZIP file, or browser-selected local folder
- Uploading, cloning, indexing, and ready states in Chat
- Automatic per-file language detection
- Persistent repository history and per-project statistics
- Code explanation inside Chat with automatic snippet-language detection
- Optional read-only Explorer with a file tree and line-numbered code preview
- Clickable related-file references with automatic line highlighting
- Dashboard health, index statistics, activity, and project details

ZIP and folder uploads are validated by the backend. Paths cannot escape the
upload workspace, symlinks are rejected, and file-count and extraction-size
limits are enforced. Explorer file reads are repository-scoped, restricted to
supported text files, and exclude common secret-file formats.
