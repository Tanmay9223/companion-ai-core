import os
import json
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch
import pytest

from app.extractor import MemoryExtractor
from app.schema import ExtractionResult, ExtractedMemory

@pytest.fixture
def clean_env(monkeypatch):
    # Remove relevant environment variables to ensure clean state
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

def test_extractor_no_api_key(clean_env):
    extractor = MemoryExtractor()
    result = extractor.extract_memories("Hello world")

    assert not result.is_memory_worthy
    assert len(result.memories) == 0

def test_extractor_openai_success(clean_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    # We create mock module
    openai_mock = MagicMock()
    sys.modules["openai"] = openai_mock

    try:
        extractor = MemoryExtractor()

        # Setup mock return value
        mock_parsed_result = ExtractionResult(
            is_memory_worthy=True,
            memories=[
                ExtractedMemory(
                    subject="user",
                    predicate="employer",
                    value="Acme Corp",
                    memory_type="employment",
                    importance=0.8,
                    confidence=0.9
                )
            ]
        )

        mock_message = MagicMock()
        mock_message.parsed = mock_parsed_result

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client_instance = MagicMock()
        mock_client_instance.beta.chat.completions.parse.return_value = mock_response

        extractor.client = mock_client_instance

        result = extractor.extract_memories("I work at Acme Corp")

        assert result.is_memory_worthy
        assert len(result.memories) == 1
        assert result.memories[0].value == "Acme Corp"
        mock_client_instance.beta.chat.completions.parse.assert_called_once()
    finally:
        del sys.modules["openai"]

def test_extractor_gemini_success(clean_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    google_mock = MagicMock()
    sys.modules["google"] = google_mock
    sys.modules["google.genai"] = MagicMock()
    sys.modules["google.genai.types"] = MagicMock()

    try:
        extractor = MemoryExtractor()

        # Setup mock return value for gemini text (JSON string)
        json_response = json.dumps({
            "is_memory_worthy": True,
            "memories": [
                {
                    "subject": "user.sister",
                    "predicate": "name",
                    "value": "Neha",
                    "memory_type": "relationship",
                    "importance": 0.7,
                    "confidence": 0.95
                }
            ]
        })

        mock_response = MagicMock()
        mock_response.text = f"```json\n{json_response}\n```"

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response

        extractor.client = mock_client_instance

        result = extractor.extract_memories("My sister Neha is here")

        assert result.is_memory_worthy
        assert len(result.memories) == 1
        assert result.memories[0].value == "Neha"
        assert result.memories[0].subject == "user.sister"
        mock_client_instance.models.generate_content.assert_called_once()
    finally:
        del sys.modules["google"]
        del sys.modules["google.genai"]
        del sys.modules["google.genai.types"]

def test_extractor_openai_error_handling(clean_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    openai_mock = MagicMock()
    sys.modules["openai"] = openai_mock

    try:
        extractor = MemoryExtractor()

        mock_client_instance = MagicMock()
        mock_client_instance.beta.chat.completions.parse.side_effect = Exception("API failure")

        extractor.client = mock_client_instance

        result = extractor.extract_memories("I work at Acme Corp")

        assert not result.is_memory_worthy
        assert len(result.memories) == 0
    finally:
        del sys.modules["openai"]

def test_extractor_gemini_error_handling(clean_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    google_mock = MagicMock()
    sys.modules["google"] = google_mock
    sys.modules["google.genai"] = MagicMock()
    sys.modules["google.genai.types"] = MagicMock()

    try:
        extractor = MemoryExtractor()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = Exception("API failure")

        extractor.client = mock_client_instance

        result = extractor.extract_memories("My sister Neha is here")

        assert not result.is_memory_worthy
        assert len(result.memories) == 0
    finally:
        del sys.modules["google"]
        del sys.modules["google.genai"]
        del sys.modules["google.genai.types"]
