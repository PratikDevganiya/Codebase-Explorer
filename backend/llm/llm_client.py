"""LLM Client - Production Ready with Latest Gemini Models"""

import os
from typing import Optional
from backend.utils import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Base LLM Client interface (for backwards compatibility)."""

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
        raise NotImplementedError("Subclass must implement generate()")

    def get_info(self) -> dict:
        return {"provider": "unknown", "model": "unknown", "available": False}


class MockLLMClient(LLMClient):
    """Mock LLM for testing."""

    def generate(self, prompt: str, **kwargs) -> str:
        return (
            "A real language model is not currently available. "
            "The relevant source files are listed below, but an AI answer "
            "cannot be generated until Gemini or OpenAI is connected."
        )

    def get_info(self) -> dict:
        return {"provider": "mock", "model": "none", "available": False}


class GeminiClient(LLMClient):
    """Google Gemini client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None

        from config.settings import settings

        self.model_name = settings.llm_model
        self.fallback_models = [
            model
            for model in ("gemini-3.1-flash-lite", "gemini-2.5-flash")
            if model != self.model_name
        ]
        self.working_model = None

        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("⚠️ No valid Gemini API key")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.working_model = self.model_name
            logger.info(f"✅ Gemini configured with model: {self.working_model}")

        except ImportError:
            logger.error("❌ Run: pip install google-genai")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Gemini init failed: {e}")
            self.client = None

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.client or not self.working_model:
            logger.warning("⚠️ Using mock response (Gemini unavailable)")
            return MockLLMClient().generate(prompt, **kwargs)

        last_error = None
        models = [self.working_model, *self.fallback_models]
        for model in dict.fromkeys(models):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "temperature": kwargs.get("temperature", 0.1),
                        "max_output_tokens": max(kwargs.get("max_tokens", 2048), 256),
                    },
                )
                if not response.text:
                    raise RuntimeError("Gemini returned an empty response")
                if model != self.working_model:
                    logger.warning(f"Using Gemini fallback model: {model}")
                    self.working_model = model
                return response.text
            except Exception as e:
                last_error = e
                error_text = str(e)
                logger.warning(f"Gemini model {model} failed: {error_text[:300]}")
                if not any(
                    marker in error_text
                    for marker in (
                        "RESOURCE_EXHAUSTED",
                        "UNAVAILABLE",
                        "NOT_FOUND",
                        "high demand",
                        "429",
                        "503",
                        "404",
                    )
                ):
                    break

        raise RuntimeError(
            "Gemini could not generate an answer. All configured models were "
            "unavailable or out of quota; check the backend log for details."
        ) from last_error

    def get_info(self) -> dict:
        return {
            "provider": "gemini",
            "model": self.working_model or self.model_name,
            "available": bool(self.client and self.working_model),
        }


class OpenAIClient(LLMClient):
    """OpenAI Client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None

        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info("✅ OpenAI client ready")
        except Exception as e:
            logger.error(f"❌ OpenAI init failed: {e}")
            self.client = None

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.client:
            return MockLLMClient().generate(prompt, **kwargs)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ OpenAI failed: {e}")
            return MockLLMClient().generate(prompt, **kwargs)

    def get_info(self) -> dict:
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "available": bool(self.client),
        }
