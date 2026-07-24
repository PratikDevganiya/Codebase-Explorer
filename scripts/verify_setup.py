#!/usr/bin/env python3
"""Verify that all dependencies are installed correctly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils import get_logger

logger = get_logger(__name__)


def check_imports():
    """Check if all required packages can be imported."""
    packages = {
        "langchain": "langchain",
        "llama-index": "llama_index",
        "tree_sitter": "tree_sitter",
        "git": "git",
        "google.generativeai": "google.generativeai",
        "fastapi": "fastapi",
        "sentence_transformers": "sentence_transformers",
        "openai": "openai",
        "supabase": "supabase",
    }

    failed = []
    for name, import_name in packages.items():
        try:
            __import__(import_name)
            logger.info(f"✅ {name} imported successfully")
        except ImportError as e:
            logger.error(f"❌ Failed to import {name}: {e}")
            failed.append(name)

    return len(failed) == 0


def check_directories():
    """Check if all required directories exist."""
    from config.settings import settings

    dirs = [
        settings.data_dir,
        settings.repositories_path,
        settings.uploads_path,
    ]

    for dir_path in dirs:
        if dir_path.exists():
            logger.info(f"✅ Directory exists: {dir_path}")
        else:
            logger.error(f"❌ Directory missing: {dir_path}")
            return False

    return True


def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if env_file.exists():
        logger.info("✅ .env file exists")
        return True
    else:
        logger.error("❌ .env file not found")
        return False


def main():
    logger.info("🚀 Starting setup verification...")
    logger.info("=" * 50)

    logger.info("\n📦 Checking package imports...")
    imports_ok = check_imports()

    logger.info("\n📁 Checking directories...")
    dirs_ok = check_directories()

    logger.info("\n⚙️  Checking configuration...")
    env_ok = check_env_file()

    logger.info("\n" + "=" * 50)
    if imports_ok and dirs_ok and env_ok:
        logger.info("✅ Setup verification complete! All checks passed.")
        logger.info("\n🎯 Next steps:")
        logger.info("   1. Add your API keys to .env file")
        logger.info("   2. Run: python scripts/validate_production.py")
        logger.info("   3. Run: python scripts/run_api.py")
        return 0
    else:
        logger.error("❌ Setup verification failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
