import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    def __init__(self):
        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_api_key_backup = os.getenv(
            "GEMINI_API_KEY_BACKUP", ""
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY", "")
        self.supabase_source_bucket = os.getenv(
            "SUPABASE_SOURCE_BUCKET", "project-sources"
        )
        self.github_token = os.getenv("GITHUB_TOKEN", "")

        # Temporary processing paths. Persistent project data lives in
        # Supabase; clones and uploads only exist here during ingestion.
        self.base_dir = Path(__file__).parent.parent
        self.processing_dir = Path(
            os.getenv(
                "PROCESSING_DIR",
                str(Path(tempfile.gettempdir()) / "codebase-explorer"),
            )
        )
        self.repositories_path = self.processing_dir / "repositories"
        self.uploads_path = self.processing_dir / "uploads"

        # Model settings
        self.embedding_provider = os.getenv(
            "EMBEDDING_PROVIDER", "gemini")
        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL", "gemini-embedding-2"
        )
        self.llm_model = os.getenv("LLM_MODEL", "gemini-3.6-flash")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.1"))

        # Retrieval settings
        self.top_k = int(os.getenv("TOP_K", "20"))
        self.top_n = int(os.getenv("TOP_N", "5"))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))

        # Server settings
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.cors_origins = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000").split(",")
        self.query_rate_limit = os.getenv("QUERY_RATE_LIMIT", "30/minute")
        self.ingest_rate_limit = os.getenv("INGEST_RATE_LIMIT", "5/hour")
        self.admin_username = os.getenv("ADMIN_USERNAME", "").strip()
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        self.auth_secret = os.getenv("AUTH_SECRET", "")
        self.auth_token_hours = int(os.getenv("AUTH_TOKEN_HOURS", "12"))

        configured_auth_values = (
            self.admin_username,
            self.admin_password,
            self.auth_secret,
        )
        if any(configured_auth_values) and not all(configured_auth_values):
            raise RuntimeError(
                "ADMIN_USERNAME, ADMIN_PASSWORD, and AUTH_SECRET must all be configured"
            )
        self.auth_enabled = all(configured_auth_values)

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Create directories
        self.repositories_path.mkdir(parents=True, exist_ok=True)
        self.uploads_path.mkdir(parents=True, exist_ok=True)


# Create singleton
settings = Settings()
