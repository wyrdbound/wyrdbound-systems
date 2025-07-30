"""Table definition models for GRIMOIRE runner."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import random


@dataclass
class TableEntry:
    """A single table entry with value and optional weight."""
    value: Any
    weight: int = 1


@dataclass
class TableDefinition:
    """Random table definition."""
    kind: str
    name: str
    id: Optional[str] = None
    display_name: Optional[str] = None
    version: str = "1.0"
    roll: Optional[str] = None  # e.g., "1d10", "2d6"
    description: Optional[str] = None
    entry_type: Optional[str] = None  # Type hint for entries
    
    # Entries can be simple dict (roll_value -> result) or weighted
    entries: Dict[Union[int, str], Any] = field(default_factory=dict)
    
    def get_entry(self, roll_result: Union[int, str]) -> Optional[Any]:
        """Get an entry by roll result."""
        return self.entries.get(roll_result)
    
    def get_all_entries(self) -> Dict[Union[int, str], Any]:
        """Get all entries."""
        return self.entries.copy()
    
    def get_random_entry(self, rng: Optional[random.Random] = None) -> Any:
        """Get a random entry from the table."""
        if not self.entries:
            return None
            
        if rng is None:
            rng = random.Random()
        
        # For now, simple random choice (TODO: implement proper dice rolling)
        return rng.choice(list(self.entries.values()))
    
    def get_weighted_random_entry(self, weights: Optional[Dict[Union[int, str], int]] = None, rng: Optional[random.Random] = None) -> Any:
        """Get a weighted random entry from the table."""
        if not self.entries:
            return None
            
        if rng is None:
            rng = random.Random()
        
        if weights:
            # Use custom weights
            choices = []
            for key, value in self.entries.items():
                weight = weights.get(key, 1)
                choices.extend([value] * weight)
            return rng.choice(choices)
        else:
            # Equal weights
            return rng.choice(list(self.entries.values()))
    
    def get_entry_by_range(self, roll_value: int) -> Optional[Any]:
        """Get entry by checking if roll_value falls within ranges."""
        # Handle range-based entries like "1-3": "result"
        for key, value in self.entries.items():
            if isinstance(key, str) and '-' in key:
                try:
                    start, end = map(int, key.split('-'))
                    if start <= roll_value <= end:
                        return value
                except ValueError:
                    continue
            elif isinstance(key, int) and key == roll_value:
                return value
            elif str(key) == str(roll_value):
                return value
        
        return None
    
    def validate(self) -> List[str]:
        """Validate the table definition and return any errors."""
        errors = []
        
        # Validate required fields
        if self.kind != "table":
            errors.append(f"Table kind must be 'table', got '{self.kind}'")
        if not self.name:
            errors.append("Table name is required")
        if not self.entries:
            errors.append("Table must have at least one entry")
        
        # Validate roll expression format (basic check)
        if self.roll:
            if not any(d in self.roll for d in ['d4', 'd6', 'd8', 'd10', 'd12', 'd20', 'd100']):
                errors.append(f"Invalid roll expression: '{self.roll}'")
        
        return errors
