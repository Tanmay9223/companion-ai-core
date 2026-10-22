import os
import pytest
from unittest.mock import patch, MagicMock
from app.llm_adapter import LLMAdapter

@pytest.fixture
def mock_env(monkeypatch):
    """Clear relevant environment variables for clean testing."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

def test_init_openai_with_key(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")

    with patch("openai.OpenAI") as mock_openai:
        adapter = LLMAdapter()
        assert adapter.provider == "openai"
        assert adapter.model == "gpt-4.1-mini"
        mock_openai.assert_called_once_with(api_key="test_openai_key")
        assert adapter.client == mock_openai.return_value

def test_init_openai_without_key(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    adapter = LLMAdapter()
    assert adapter.provider == "openai"
    assert adapter.client is None

def test_init_gemini_with_key(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key")

    with patch("google.genai.Client") as mock_genai_client:
        adapter = LLMAdapter()
        assert adapter.provider == "gemini"
        assert adapter.model == "gemini-3.5-flash"
        mock_genai_client.assert_called_once_with(api_key="test_google_key")
        assert adapter.client == mock_genai_client.return_value

def test_init_gemini_without_key(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    adapter = LLMAdapter()
    assert adapter.provider == "gemini"
    assert adapter.client is None

def test_generate_response_mocked(mock_env):
    adapter = LLMAdapter()
    adapter.client = None
    response = adapter.generate_response("system", "hello")
    assert response == "[Mock] hello"

def test_generate_response_dispatch_openai(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    adapter = LLMAdapter()
    adapter.client = MagicMock()

    with patch.object(adapter, "_openai_response", return_value="openai_res") as mock_openai:
        result = adapter.generate_response("sys", "user", [{"role": "user", "content": "hi"}])
        assert result == "openai_res"
        mock_openai.assert_called_once_with("sys", "user", [{"role": "user", "content": "hi"}])

def test_generate_response_dispatch_gemini(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    adapter = LLMAdapter()
    adapter.client = MagicMock()

    with patch.object(adapter, "_gemini_response", return_value="gemini_res") as mock_gemini:
        result = adapter.generate_response("sys", "user", [{"role": "user", "content": "hi"}])
        assert result == "gemini_res"
        mock_gemini.assert_called_once_with("sys", "user", [{"role": "user", "content": "hi"}])

def test_openai_response_success(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    adapter = LLMAdapter()
    adapter.client = MagicMock()

    mock_choice = MagicMock()
    mock_choice.message.content = "  success response  "
    adapter.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    history = [{"role": "user", "content": "hi"}]
    result = adapter._openai_response("system prompt", "user prompt", history)

    assert result == "success response"
    adapter.client.chat.completions.create.assert_called_once_with(
        model=adapter.model,
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hi"},
            {"role": "user", "content": "user prompt"}
        ],
        temperature=0.8,
    )

def test_openai_response_exception(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    adapter = LLMAdapter()
    adapter.client = MagicMock()
    adapter.client.chat.completions.create.side_effect = Exception("API error")

    result = adapter._openai_response("system", "user", [])
    assert result == "I'm having trouble thinking right now. Could you try again?"

def test_gemini_response_success(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    adapter = LLMAdapter()
    adapter.client = MagicMock()

    adapter.client.models.generate_content.return_value = MagicMock(text="  gemini success  ")

    history = [{"role": "user", "content": "hi user"}, {"role": "model", "content": "hi model"}]

    result = adapter._gemini_response("system prompt", "user prompt", history)

    assert result == "gemini success"

    adapter.client.models.generate_content.assert_called_once()
    call_kwargs = adapter.client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == adapter.model
    assert len(call_kwargs["contents"]) == 3
    assert call_kwargs["contents"][0].role == "user"
    assert call_kwargs["contents"][0].parts[0].text == "hi user"
    assert call_kwargs["contents"][1].role == "model"
    assert call_kwargs["contents"][1].parts[0].text == "hi model"
    assert call_kwargs["contents"][2].role == "user"
    assert call_kwargs["contents"][2].parts[0].text == "user prompt"
    assert call_kwargs["config"].system_instruction == "system prompt"
    assert call_kwargs["config"].temperature == 0.8

def test_gemini_response_exception(mock_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    adapter = LLMAdapter()
    adapter.client = MagicMock()
    adapter.client.models.generate_content.side_effect = Exception("Gemini error")

    result = adapter._gemini_response("system", "user", [])
    assert result == "I'm having trouble thinking right now. Could you try again?"
