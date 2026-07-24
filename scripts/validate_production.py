"""Validate production configuration without printing secrets."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage import get_supabase_client
from config.settings import settings


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> None:
    if not settings.supabase_url or not settings.supabase_secret_key:
        fail("Supabase credentials are not configured")

    client = get_supabase_client()
    for table in ("projects", "code_chunks", "chat_messages"):
        client.table(table).select("id").limit(1).execute()
        print(f"OK: {table}")

    buckets = client.storage.list_buckets()
    if not any(bucket.name == settings.supabase_source_bucket for bucket in buckets):
        fail(f"Storage bucket is missing: {settings.supabase_source_bucket}")
    print(f"OK: private storage bucket {settings.supabase_source_bucket}")
    print("Production storage validation passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: {error}")
        sys.exit(1)
