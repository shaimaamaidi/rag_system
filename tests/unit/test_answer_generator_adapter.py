import pytest

from src.domain.exceptions.azure_config_exception import AzureOpenAIConfigException
from src.infrastructure.adapters.answer_generation.azure_answer_generator import AzureOpenAIAnswerGenerator


def test_answer_generator_missing_env(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.adapters.answer_generation.azure_answer_generator.load_dotenv",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_NAME", raising=False)

    with pytest.raises(AzureOpenAIConfigException):
        AzureOpenAIAnswerGenerator(prompt_provider=object())


def test_answer_generator_success(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.adapters.answer_generation.azure_answer_generator.load_dotenv",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "http://test")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-01-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "embed")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "chat")

    class DummyCompletions:
        def create(self, *_args, **_kwargs):
            class _Msg:
                content = "ok"
            class _Choice:
                message = _Msg()
            class _Resp:
                choices = [_Choice()]
            return _Resp()

    class DummyChat:
        def __init__(self):
            self.completions = DummyCompletions()

    class DummyClient:
        def __init__(self, **_kwargs):
            self.chat = DummyChat()

    class DummyPrompt:
        def get_system_prompt(self, prompt_type):
            assert prompt_type == "answer_generator"
            return "system"

        def get_user_generator_prompt(self, context, question):
            assert context == "ctx"
            assert question == "q"
            return "user"

    monkeypatch.setattr(
        "src.infrastructure.adapters.answer_generation.azure_answer_generator.AzureOpenAI",
        DummyClient,
    )

    gen = AzureOpenAIAnswerGenerator(prompt_provider=DummyPrompt())
    assert gen.generate_answer("ctx", "q") == "ok"
