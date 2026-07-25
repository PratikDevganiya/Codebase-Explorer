"""
API Models
Pydantic models for request/response validation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=500)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class QueryRequest(BaseModel):
    """Request model for code search query."""

    query: str = Field(..., description="User's natural language question")
    language: Optional[str] = Field(None, description="Filter by programming language")
    code_type: Optional[str] = Field(
        None, description="Filter by code type (function, class, etc.)"
    )
    top_k: Optional[int] = Field(5, description="Number of results to return")
    include_context: Optional[bool] = Field(
        True, description="Include full context in response"
    )
    repository_id: Optional[str] = Field(
        None, description="Restrict retrieval to one indexed repository"
    )
    repository_ids: Optional[List[str]] = Field(
        None,
        max_length=10,
        description="Restrict retrieval to up to ten indexed repositories",
    )
    session_id: Optional[str] = Field(
        None, description="Anonymous browser session used for chat persistence"
    )
    conversation_id: Optional[str] = Field(
        None, description="Named conversation used for persistent chat history"
    )


class SourceReference(BaseModel):
    """Source code reference."""

    file: str
    path: str
    type: str
    name: str
    lines: str
    language: str
    relevance: float
    repository_id: Optional[str] = None
    repository_name: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for code search query."""

    answer: str
    sources: List[SourceReference]
    num_sources: int
    query_info: Dict[str, Any]
    processing_time: float


class IngestRequest(BaseModel):
    """Request model for repository ingestion."""

    repo_url: str = Field(..., description="GitHub repository URL")
    branch: Optional[str] = Field("main", description="Branch to clone")
    operation_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Client-generated identifier used to report ingestion progress",
    )
    extensions: Optional[List[str]] = Field(
        None, description="File extensions to index"
    )


class IngestResponse(BaseModel):
    """Response model for repository ingestion."""

    status: str
    message: str
    repo_name: str
    files_processed: int
    chunks_created: int
    chunks_indexed: int
    repository_id: Optional[str] = None
    source_type: str = "github"


class RepositoryRecord(BaseModel):
    repository_id: str
    name: str
    source_type: str
    source: str
    status: str
    files_processed: int = 0
    chunks_created: int = 0
    chunks_indexed: int = 0
    created_at: str
    updated_at: str


class RepositoryFile(BaseModel):
    path: str
    name: str
    language: str
    size_bytes: int


class RepositoryFileContent(RepositoryFile):
    content: str
    line_count: int


class ChatMessageRecord(BaseModel):
    id: str
    repository_id: str
    session_id: str
    role: str
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str
    conversation_id: Optional[str] = None


class ConversationCreate(BaseModel):
    repository_ids: List[str] = Field(..., min_length=1, max_length=10)
    title: str = Field("New chat", min_length=1, max_length=120)


class ConversationUpdate(BaseModel):
    repository_ids: Optional[List[str]] = Field(
        None,
        min_length=1,
        max_length=10,
    )
    title: Optional[str] = Field(None, min_length=1, max_length=120)


class ConversationRecord(BaseModel):
    id: str
    title: str
    repository_ids: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ExplainRequest(BaseModel):
    """Request model for code explanation."""

    code: str = Field(..., description="Code snippet to explain")
    language: Optional[str] = Field(
        None,
        description="Optional language override; detected automatically when omitted",
    )


class ExplainResponse(BaseModel):
    """Response model for code explanation."""

    explanation: str
    code_snippet: str
    language: str


class DebugRequest(BaseModel):
    """Request model for debug help."""

    error_message: str = Field(..., description="Error message or description")
    language: Optional[str] = Field(None, description="Programming language")


class DebugResponse(BaseModel):
    """Response model for debug help."""

    analysis: str
    related_code: List[SourceReference]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    index_stats: Dict[str, Any]
    llm: Dict[str, Any] = Field(default_factory=dict)
    reindex_required: bool = False
