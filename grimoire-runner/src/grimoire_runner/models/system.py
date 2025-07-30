"""System definition models for GRIMOIRE runner."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

from .flow import FlowDefinition
from .compendium import CompendiumDefinition
from .table import TableDefinition
from .source import SourceDefinition
from .model import ModelDefinition


@dataclass
class CurrencyDenomination:
    """A currency denomination definition."""
    name: str
    symbol: str
    value: int
    weight: Optional[float] = None


@dataclass
class Currency:
    """Currency system definition."""
    base_unit: str
    denominations: Dict[str, CurrencyDenomination] = field(default_factory=dict)


@dataclass
class Credits:
    """Attribution and licensing information."""
    author: Optional[str] = None
    license: Optional[str] = None
    publisher: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class System:
    """Complete GRIMOIRE system definition."""
    
    # Required fields
    id: str
    name: str
    kind: str = "system"
    
    # Optional metadata
    description: Optional[str] = None
    version: Optional[str] = None
    default_source: Optional[str] = None
    
    # System configuration
    currency: Optional[Currency] = None
    credits: Optional[Credits] = None
    
    # Content collections
    models: Dict[str, ModelDefinition] = field(default_factory=dict)
    flows: Dict[str, FlowDefinition] = field(default_factory=dict)
    compendiums: Dict[str, CompendiumDefinition] = field(default_factory=dict)
    tables: Dict[str, TableDefinition] = field(default_factory=dict)
    sources: Dict[str, SourceDefinition] = field(default_factory=dict)
    
    # Internal fields
    _system_path: Optional[Path] = field(default=None, repr=False)
    
    def get_model(self, model_id: str) -> Optional[ModelDefinition]:
        """Get a model definition by ID."""
        return self.models.get(model_id)
    
    def get_flow(self, flow_id: str) -> Optional[FlowDefinition]:
        """Get a flow definition by ID."""
        return self.flows.get(flow_id)
    
    def get_compendium(self, compendium_id: str) -> Optional[CompendiumDefinition]:
        """Get a compendium definition by ID."""
        return self.compendiums.get(compendium_id)
    
    def get_table(self, table_id: str) -> Optional[TableDefinition]:
        """Get a table definition by ID."""
        return self.tables.get(table_id)
    
    def get_source(self, source_id: str) -> Optional[SourceDefinition]:
        """Get a source definition by ID."""
        return self.sources.get(source_id)
    
    def list_flows(self) -> List[str]:
        """Get a list of all available flow IDs."""
        return list(self.flows.keys())
    
    def list_models(self) -> List[str]:
        """Get a list of all available model IDs.""" 
        return list(self.models.keys())
    
    def list_compendiums(self) -> List[str]:
        """Get a list of all available compendium IDs."""
        return list(self.compendiums.keys())
    
    def list_tables(self) -> List[str]:
        """Get a list of all available table IDs."""
        return list(self.tables.keys())
    
    def validate(self) -> List[str]:
        """Validate the system definition and return any errors."""
        errors = []
        
        # Validate required fields
        if not self.id:
            errors.append("System ID is required")
        if not self.name:
            errors.append("System name is required")
        if self.kind != "system":
            errors.append(f"System kind must be 'system', got '{self.kind}'")
            
        # Validate references
        if self.default_source and self.default_source not in self.sources:
            errors.append(f"Default source '{self.default_source}' not found")
            
        # Validate currency denominations
        if self.currency:
            for denom_id, denom in self.currency.denominations.items():
                if denom.value <= 0:
                    errors.append(f"Currency denomination '{denom_id}' must have positive value")
        
        return errors
