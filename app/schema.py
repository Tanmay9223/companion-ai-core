from pydantic import BaseModel, Field
from typing import List

class ExtractedMemory(BaseModel):
    subject: str = Field(description="The canonical entity (e.g., 'user', 'user.sister.Neha', 'companion')")
    predicate: str = Field(description="The relationship or property (e.g., 'employer', 'preference_weather')")
    value: str = Field(description="The specific value of the fact")
    memory_type: str = Field(description="Category: identity, relationship, employment, preference, plan, goal, event")
    importance: float = Field(description="Scale 0.0 to 1.0 on how important this fact is long-term", ge=0.0, le=1.0)
    confidence: float = Field(description="Scale 0.0 to 1.0 on how confident you are this is a factual statement", ge=0.0, le=1.0)
    
class ExtractionResult(BaseModel):
    is_memory_worthy: bool = Field(description="True if the message contains durable facts worth remembering, False if it is just casual conversation")
    memories: List[ExtractedMemory] = Field(description="List of extracted memories, empty if none")
