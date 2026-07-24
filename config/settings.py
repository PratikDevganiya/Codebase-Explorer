import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    def __init__(self):
        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY", "")
        self.supabase_source_bucket = os.getenv(
            "SUPABASE_SOURCE_BUCKET", "project-sources"
        )
        self.github_token = os.getenv("GITHUB_TOKEN", "")

        # Paths
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.repositories_path = self.data_dir / "repositories"
        self.uploads_path = self.data_dir / "uploads"

        # Model settings
        self.embedding_provider = os.getenv(
            "EMBEDDING_PROVIDER", "huggingface")
        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
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

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.repositories_path.mkdir(exist_ok=True)
        self.uploads_path.mkdir(exist_ok=True)


# Create singleton
settings = Settings()
