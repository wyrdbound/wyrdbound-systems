"""Source definition models for GRIMOIRE runner."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceDefinition:
    """Source material definition for attribution and licensing."""
    kind: str
    name: str
    id: Optional[str] = None
    display_name: Optional[str] = None
    edition: Optional[str] = None
    default: Optional[bool] = None
    publisher: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    version: str = "1.0"
    
    def validate(self) -> list[str]:
        """Validate the source definition and return any errors."""
        errors = []
        
        # Validate required fields
        if self.kind != "source":
            errors.append(f"Source kind must be 'source', got '{self.kind}'")
        if not self.name:
            errors.append("Source name is required")
        
        return errors
