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
    monkeypatch.delenv("GEMINI_API_KEY_BACKUP", raising=False)
    fake_client = _Client()
    client = GeminiClient(client_factory=lambda _key: fake_client)
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


class _QuotaModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")


class _SuccessfulModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        return _Response()


def test_gemini_switches_to_backup_key_when_primary_quota_is_exhausted(
    monkeypatch,
):
    monkeypatch.setenv("GEMINI_API_KEY", "primary-key")
    monkeypatch.setenv("GEMINI_API_KEY_BACKUP", "backup-key")
    primary = type("PrimaryClient", (), {"models": _QuotaModels()})()
    backup = type("BackupClient", (), {"models": _SuccessfulModels()})()
    clients = {
        "primary-key": primary,
        "backup-key": backup,
    }

    client = GeminiClient(client_factory=lambda key: clients[key])
    client.model_name = "gemini-3.6-flash"
    client.working_model = client.model_name
    client.fallback_models = []

    answer = client.generate("Question")

    assert answer == "Fallback answer"
    assert primary.models.calls == ["gemini-3.6-flash"]
    assert backup.models.calls == ["gemini-3.6-flash"]
    assert client.client is backup
    assert client._key_pool.active_index == 1
