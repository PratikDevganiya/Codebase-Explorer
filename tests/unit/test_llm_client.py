from backend.llm.llm_client import GeminiClient


class _Response:
    text = "Fallback answer"


class _Models:
    def __init__(self):
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        if model == "gemini-3.6-flash":
            raise RuntimeError("503 UNAVAILABLE: model is experiencing high demand")
        return _Response()


class _Client:
    def __init__(self):
        self.models = _Models()


def test_gemini_uses_fallback_when_primary_is_unavailable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = GeminiClient()
    client.client = _Client()
    client.model_name = "gemini-3.6-flash"
    client.working_model = client.model_name
    client.fallback_models = ["gemini-3.1-flash-lite"]

    answer = client.generate("Question")

    assert answer == "Fallback answer"
    assert client.client.models.calls == [
        "gemini-3.6-flash",
        "gemini-3.1-flash-lite",
    ]
    assert client.working_model == "gemini-3.1-flash-lite"
