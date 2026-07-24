"""
FastAPI Application - Production Ready with Real LLM
"""

import hashlib
import json
import shutil
import time
from pathlib import Path
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from typing import Dict

from backend.api.models import (
    QueryRequest, QueryResponse, IngestRequest, IngestResponse,
    ExplainRequest, ExplainResponse, DebugRequest, DebugResponse,
    HealthResponse, RepositoryFile, RepositoryFileContent, RepositoryRecord,
    SourceReference, ChatMessageRecord,
)
from backend.ingestion.github_loader import GitHubLoader
from backend.ingestion.document_loader import DocumentLoader
from backend.ingestion.repository_manager import (
    MAX_FILES,
    create_repository_id,
    extract_zip_safely,
    save_folder_upload,
)
from backend.parsing.chunker import CodeChunker
from backend.parsing.language_detector import detect_code_language, detect_file_language
from backend.retrieval.embeddings import EmbeddingGenerator
from backend.retrieval.vector_store import (
    SupabaseVectorStore,
    VectorStore,
)
from backend.retrieval.indexer import Indexer
from backend.retrieval.search import CodeSearchEngine
from backend.llm.rag_pipeline import RAGPipeline
from backend.llm.llm_client import MockLLMClient, GeminiClient, OpenAIClient
from backend.storage import (
    SupabaseChatRepository,
    SupabaseRepositoryMetadataStore,
    SupabaseSourceStorage,
)
from backend.utils import get_logger
from config.settings import settings

logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="Codebase RAG API",
    description="Intelligent code search and Q&A system using RAG",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
vector_store: VectorStore = None
embedding_generator = None
search_engine: CodeSearchEngine = None
rag_pipeline: RAGPipeline = None
indexer: Indexer = None
llm_client = None
reindex_required = False
repository_registry = SupabaseRepositoryMetadataStore()
source_storage = SupabaseSourceStorage()
chat_repository = SupabaseChatRepository()


def get_llm_client():
    """Get the best available LLM client - FIXED VERSION!"""
    
    # TRY GEMINI FIRST
    if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
        try:
            logger.info("🔄 Attempting Gemini connection...")
            client = GeminiClient()
            # ✅ FIXED: Check if client has working_model instead of model
            if client.client and client.working_model:
                logger.info(f"✅ Using Gemini LLM with model: {client.working_model}!")
                return client
            else:
                logger.warning("⚠️ Gemini client or model initialization failed")
        except Exception as e:
            logger.warning(f"⚠️ Gemini failed: {e}")
    else:
        logger.info("ℹ️ No Gemini API key configured")
    
    # TRY OPENAI SECOND
    if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
        try:
            logger.info("🔄 Attempting OpenAI connection...")
            client = OpenAIClient()
            if client.client:
                logger.info("✅ Using OpenAI LLM!")
                return client
            else:
                logger.warning("⚠️ OpenAI client initialization failed")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI failed: {e}")
    else:
        logger.info("ℹ️ No OpenAI API key configured")
    
    # FALLBACK TO MOCK
    logger.warning("⚠️ No real LLM available, using Mock LLM")
    logger.info("💡 Add GEMINI_API_KEY or OPENAI_API_KEY to .env for real AI responses")
    return MockLLMClient()


def initialize_system():
    """Initialize the RAG system."""
    global vector_store, embedding_generator, search_engine, rag_pipeline, indexer
    global llm_client, reindex_required
    
    logger.info("🚀 Initializing RAG system...")
    reindex_required = False
    
    embedding_generator = EmbeddingGenerator(
        model_name=settings.embedding_model,
        provider=settings.embedding_provider,
    )
    dimension = embedding_generator.get_dimension()
    if dimension <= 0:
        raise RuntimeError(
            f"Could not initialize embedding model: {settings.embedding_model}"
        )
    vector_store = SupabaseVectorStore(dimension=dimension)
    
    search_engine = CodeSearchEngine(vector_store, embedding_generator)
    
    # Get LLM client (will try real APIs first!)
    llm_client = get_llm_client()
    
    rag_pipeline = RAGPipeline(search_engine, llm_client, top_k=5)
    indexer = Indexer(embedding_generator, vector_store)
    
    logger.info("✅ RAG system initialized")


@app.on_event("startup")
async def startup_event():
    """Run on startup."""
    initialize_system()


@app.get("/", response_model=Dict)
async def root():
    """Root endpoint."""
    return {
        "message": "Codebase RAG API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check."""
    stats = indexer.get_stats() if indexer else {}
    llm_info = llm_client.get_info() if llm_client else {
        "provider": "none",
        "model": "none",
        "available": False,
    }
    return HealthResponse(
        status="healthy" if llm_info["available"] else "degraded",
        version="1.0.0",
        index_stats=stats,
        llm=llm_info,
        reindex_required=reindex_required,
    )


@app.post("/query", response_model=QueryResponse)
@limiter.limit(settings.query_rate_limit)
async def query_code(request: Request, payload: QueryRequest):
    """Query the codebase."""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    start_time = time.time()
    
    try:
        response = rag_pipeline.query(
            user_query=payload.query,
            language=payload.language,
            include_context=payload.include_context,
            repository_id=payload.repository_id,
        )
        
        processing_time = time.time() - start_time
        sources = [SourceReference(**source) for source in response['sources']]

        if chat_repository and payload.repository_id and payload.session_id:
            try:
                chat_repository.append(
                    repository_id=payload.repository_id,
                    session_id=payload.session_id,
                    role="user",
                    content=payload.query,
                )
                chat_repository.append(
                    repository_id=payload.repository_id,
                    session_id=payload.session_id,
                    role="assistant",
                    content=response["answer"],
                    sources=response["sources"],
                )
            except Exception as persistence_error:
                logger.warning(
                    f"Could not persist chat history: {persistence_error}"
                )
        
        return QueryResponse(
            answer=response['answer'],
            sources=sources,
            num_sources=response['num_sources'],
            query_info=response['query_info'],
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def index_repository_path(
    repo_path: Path,
    repository_id: str,
    display_name: str,
    source_type: str,
    source: str,
    extensions=None,
) -> IngestResponse:
    """Run the shared file-to-vector ingestion pipeline."""
    global reindex_required

    repository_registry.upsert({
        "repository_id": repository_id,
        "name": display_name,
        "source_type": source_type,
        "source": source,
        "status": "indexing",
        "files_processed": 0,
        "chunks_created": 0,
        "chunks_indexed": 0,
    })

    doc_loader = DocumentLoader()
    selected_extensions = extensions or list(doc_loader.supported_extensions)
    filenames = list(doc_loader.supported_filenames) if extensions is None else None
    files = GitHubLoader().get_file_list(
        repo_path,
        extensions=selected_extensions,
        filenames=filenames,
    )
    documents = doc_loader.load_files(files, show_progress=False)

    chunker = CodeChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        use_ast=True,
    )
    all_chunks = []
    for doc in documents:
        file_path = Path(doc.metadata.get("filepath", ""))
        try:
            indexed_path = file_path.resolve().relative_to(repo_path.resolve()).as_posix()
        except ValueError:
            indexed_path = file_path.name
        chunks = chunker.chunk_code(
            code=doc.content,
            language=doc.metadata.get("language", "unknown"),
            file_path=indexed_path,
        )
        for chunk in chunks:
            chunk.metadata["repository_id"] = repository_id
            chunk.metadata["repository_name"] = display_name
            identity = (
                f"{repository_id}:{indexed_path}:{chunk.chunk_id}"
            ).encode()
            chunk.chunk_id = f"chunk_{hashlib.sha256(identity).hexdigest()[:24]}"
        all_chunks.extend(chunks)

    if not all_chunks:
        raise ValueError("No supported source files were found")

    indexed_count = indexer.index_chunks(all_chunks, batch_size=32)
    if indexed_count == 0:
        raise ValueError("No source chunks could be indexed")

    reindex_required = False
    source_storage.upload_files(repository_id, repo_path, files)
    repository_registry.upsert({
        "repository_id": repository_id,
        "name": display_name,
        "source_type": source_type,
        "source": source,
        "status": "ready",
        "files_processed": len(documents),
        "chunks_created": len(all_chunks),
        "chunks_indexed": indexed_count,
        "storage_prefix": repository_id,
    })
    shutil.rmtree(repo_path, ignore_errors=True)
    return IngestResponse(
        status="success",
        message=f"Repository {display_name} ingested successfully",
        repo_name=display_name,
        files_processed=len(documents),
        chunks_created=len(all_chunks),
        chunks_indexed=indexed_count,
        repository_id=repository_id,
        source_type=source_type,
    )


@app.get("/repositories", response_model=list[RepositoryRecord])
async def list_repositories():
    return repository_registry.list()


@app.delete("/repositories/{repository_id}")
async def delete_repository(repository_id: str):
    """Permanently delete a project and all of its cloud data."""
    record = repository_registry.get(repository_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        deleted_files = source_storage.delete_repository(repository_id)
        deleted = repository_registry.delete(repository_id)
        if deleted is None:
            raise HTTPException(status_code=404, detail="Repository not found")
        shutil.rmtree(settings.uploads_path / repository_id, ignore_errors=True)
        return {
            "status": "deleted",
            "repository_id": repository_id,
            "files_deleted": deleted_files,
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Repository deletion failed for {repository_id}: {error}")
        raise HTTPException(
            status_code=500,
            detail="Could not completely delete the project. Please try again.",
        )


@app.get(
    "/repositories/{repository_id}/messages",
    response_model=list[ChatMessageRecord],
)
async def list_chat_messages(repository_id: str, session_id: str):
    return chat_repository.list(repository_id, session_id)


@app.delete("/repositories/{repository_id}/messages")
async def clear_chat_messages(repository_id: str, session_id: str):
    chat_repository.clear(repository_id, session_id)
    return {"status": "cleared"}


@app.get(
    "/repositories/{repository_id}/files",
    response_model=list[RepositoryFile],
)
async def list_repository_files(repository_id: str):
    record = repository_registry.get(repository_id)
    if not record or not record.get("storage_prefix"):
        raise HTTPException(status_code=404, detail="Repository not found")
    return [
        RepositoryFile(
            path=item.path,
            name=Path(item.path).name,
            language=detect_file_language(Path(item.path)),
            size_bytes=item.size_bytes,
        )
        for item in source_storage.list_files(repository_id)
    ]


@app.get(
    "/repositories/{repository_id}/file",
    response_model=RepositoryFileContent,
)
async def read_repository_file(repository_id: str, path: str):
    normalized_path = path.replace("\\", "/").strip("/")
    record = repository_registry.get(repository_id)
    if not record or not record.get("storage_prefix"):
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        payload = source_storage.read_file(repository_id, normalized_path)
    except Exception as storage_error:
        raise HTTPException(status_code=404, detail=str(storage_error))
    if len(payload) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is too large to preview")
    try:
        content = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="File is not UTF-8 text")
    relative_path = normalized_path
    file_path = Path(relative_path)
    size_bytes = len(payload)

    return RepositoryFileContent(
        path=relative_path,
        name=file_path.name,
        language=detect_file_language(file_path, content),
        size_bytes=size_bytes,
        content=content,
        line_count=content.count("\n") + 1,
    )


@app.post("/repositories/github", response_model=IngestResponse)
@app.post("/ingest", response_model=IngestResponse)
@limiter.limit(settings.ingest_rate_limit)
async def ingest_repository(
    request: Request,
    payload: IngestRequest,
):
    """Ingest a GitHub repository; `/ingest` remains backward compatible."""
    if not indexer:
        raise HTTPException(status_code=503, detail="System not initialized")

    repo_path = None
    try:
        repository_id = create_repository_id()
        display_name = payload.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        loader = GitHubLoader()
        repo_path = loader.clone_repository(
            repo_url=payload.repo_url,
            repo_name=f"{display_name}-{repository_id[5:13]}",
            branch=payload.branch,
        )
        return index_repository_path(
            repo_path=repo_path,
            repository_id=repository_id,
            display_name=display_name,
            source_type="github",
            source=payload.repo_url,
            extensions=payload.extensions,
        )
    except Exception as e:
        if repo_path and repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repositories/upload", response_model=IngestResponse)
@limiter.limit(settings.ingest_rate_limit)
async def ingest_upload(request: Request):
    """Ingest a ZIP or browser-selected local folder."""
    if not indexer:
        raise HTTPException(status_code=503, detail="System not initialized")

    repository_id = create_repository_id()
    destination = settings.uploads_path / repository_id
    try:
        async with request.form(
            max_files=MAX_FILES,
            max_fields=20,
            max_part_size=5 * 1024 * 1024,
        ) as form:
            upload_type = str(form.get("upload_type", ""))
            display_name = str(form.get("display_name", "")).strip()
            relative_paths = str(form.get("relative_paths", "[]"))
            files = [
                item for item in form.getlist("files")
                if hasattr(item, "filename") and hasattr(item, "file")
            ]

            if upload_type not in {"zip", "folder"}:
                raise ValueError("upload_type must be zip or folder")
            if not display_name:
                raise ValueError("A project name is required")
            if not files:
                raise ValueError("No project files were uploaded")

            if upload_type == "zip":
                if len(files) != 1 or not files[0].filename.lower().endswith(".zip"):
                    raise ValueError("Select exactly one ZIP file")
                extract_zip_safely(files[0].file, destination)
            else:
                paths = json.loads(relative_paths)
                if not isinstance(paths, list) or len(paths) != len(files):
                    raise ValueError("Folder paths do not match uploaded files")
                save_folder_upload(
                    destination,
                    ((path, upload.file) for path, upload in zip(paths, files)),
                )

            return index_repository_path(
                repo_path=destination,
                repository_id=repository_id,
                display_name=display_name,
                source_type=upload_type,
                source=files[0].filename if upload_type == "zip" else "Local folder",
            )
    except (ValueError, json.JSONDecodeError) as e:
        if destination.exists():
            shutil.rmtree(destination)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if destination.exists():
            shutil.rmtree(destination)
        logger.error(f"Upload ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain", response_model=ExplainResponse)
async def explain_code(request: ExplainRequest):
    """Explain code."""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        detected_language = request.language or detect_code_language(request.code)
        explanation = rag_pipeline.explain_code(
            code=request.code,
            language=detected_language
        )
        
        return ExplainResponse(
            explanation=explanation,
            code_snippet=request.code,
            language=detected_language
        )
    except Exception as e:
        logger.error(f"Explanation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug", response_model=DebugResponse)
async def debug_help(request: DebugRequest):
    """Debug help."""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        result = rag_pipeline.debug_help(
            error_message=request.error_message,
            language=request.language
        )
        
        sources = [SourceReference(**source) for source in result['related_code']]
        
        return DebugResponse(
            analysis=result['analysis'],
            related_code=sources
        )
    except Exception as e:
        logger.error(f"Debug help failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get stats."""
    if not indexer:
        return {"error": "System not initialized"}
    
    stats = indexer.get_stats()
    return {
        "indexed_vectors": stats.get('total_vectors', 0),
        "dimension": stats.get('dimension', 0),
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
