import pytest
import os
from app.persona_manager import PersonaManager

def test_persona_manager_loads_valid_yaml(tmp_path):
    yaml_content = """
identity:
  name: TestBot
traits:
  - Smart
invariants:
  - TestBot is a test.
"""
    config_file = tmp_path / "test_persona.yaml"
    config_file.write_text(yaml_content)
    
    manager = PersonaManager(config_path=str(config_file))
    prompt = manager.get_system_prompt_header()
    
    assert "You are TestBot." in prompt
    assert "- Smart" in prompt
    assert "- TestBot is a test." in prompt
    assert "Your canonical persona configuration described above has higher priority" in prompt

def test_persona_manager_missing_file():
    manager = PersonaManager(config_path="nonexistent.yaml")
    prompt = manager.get_system_prompt_header()
    assert "System: You are a helpful companion." in prompt
