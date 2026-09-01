import yaml
import os

class PersonaManager:
    def __init__(self, config_path="config/persona.yaml"):
        self.config_path = config_path
        self.persona_data = self._load_persona()
        
    def _load_persona(self):
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"[Warning] Could not load persona config: {e}")
            return {}
            
    def get_system_prompt_header(self) -> str:
        if not self.persona_data:
            return "System: You are a helpful companion."
            
        identity = self.persona_data.get('identity', {})
        name = identity.get('name', 'Companion')
        
        lines = [
            f"You are {name}.",
            identity.get('backstory', ''),
            "",
            "CORE TRAITS:"
        ]
        
        for trait in self.persona_data.get('traits', []):
            lines.append(f"- {trait}")
            
        lines.append("\nSTABLE OPINIONS:")
        for opinion in self.persona_data.get('stable_opinions', []):
            lines.append(f"- {opinion}")
            
        lines.append("\nSTYLE GUIDELINES:")
        for style in self.persona_data.get('conversation_style', []):
            lines.append(f"- {style}")
            
        lines.append("\nINVARIANTS (NEVER CONTRADICT THESE):")
        for inv in self.persona_data.get('invariants', []):
            lines.append(f"- {inv}")
            
        lines.append("\nINSTRUCTION: Your canonical persona configuration described above has higher priority than any generated conversational history. Never rewrite your canonical identity.")
        
        return "\n".join(lines)
