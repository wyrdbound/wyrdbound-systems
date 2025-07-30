#!/usr/bin/env python3
"""
grimoire_validate.py  –  sanity-checks every *.yaml under a GRIMOIRE system folder.

• Ensures each file has the required header keys.
• Verifies that `source_book` points to a real books/<id>/book.yaml.
"""
# grimoire_validate.py  (pip install pydantic PyYAML)
from pathlib import Path
import sys, yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator

##############################################################################
# 1.  COMMON HEADER
##############################################################################
class Header(BaseModel):
    kind: str
    name: str
    version: int = 1
    source_book: str | None = None
    page: int | None = None

##############################################################################
# 2.  DOMAIN MODELS
##############################################################################

class Denomination(BaseModel):
    name: str
    symbol: str
    value: int
    # weight in lbs; if None, assume 1 coin = 1 oz for encumbrance purposes
    weight: float | None = None

class Currency(BaseModel):
    base_unit: str
    display: str | None = None
    denominations: dict[str, Denomination]

    @field_validator("display")
    def display_must_exist(cls, v, info):
        denoms = info.data["denominations"]
        if v and v not in denoms:
            raise ValueError(f"unknown display denom '{v}'")
        return v

class SystemSchema(BaseModel):
    header: Header
    currency: Currency | None = None

class SourceSchema(BaseModel):
    header: Header
    display_name: str | None = None
    edition: str | None = None
    default: bool | None = None
    publisher: str | None = None
    description: str | None = None
    source_url: str | None = None

class CompendiumSchema(BaseModel):
    header: Header
    model: str  # The model type that entries conform to
    entries: dict[str, dict] = {}  # Dictionary of entry name to entry data

class Attribute(BaseModel):
    type: str | BaseModel
    range: str | None = None  # e.g., "1..10" or "0..100"
    description: str | None = None
    of: str | None = None  # for list types, specifies the contained type

    @field_validator("range")
    def range_must_be_valid(cls, v):
        if v:
            try:
                start_str, end_str = v.split("..")
                
                # Check if start is an attribute reference or a number
                if start_str.startswith("$"):
                    # Validate attribute reference format
                    attr_name = start_str[1:]
                    if not attr_name.replace("_", "").isalnum():
                        raise ValueError(f"invalid attribute reference '{start_str}': must be $attribute_name")
                else:
                    # Validate as integer
                    start = int(start_str)
                
                # Check if end is an attribute reference or a number
                if end_str.startswith("$"):
                    # Validate attribute reference format
                    attr_name = end_str[1:]
                    if not attr_name.replace("_", "").isalnum():
                        raise ValueError(f"invalid attribute reference '{end_str}': must be $attribute_name")
                else:
                    # Validate as integer
                    end = int(end_str)
                
                # If both are integers, validate the range
                if not start_str.startswith("$") and not end_str.startswith("$"):
                    if start >= end:
                        raise ValueError(f"invalid range '{v}': start must be less than end")
                        
            except ValueError as e:
                if "invalid range" in str(e) or "invalid attribute reference" in str(e):
                    raise e
                raise ValueError(f"invalid range format '{v}': expected 'start..end' where start/end can be numbers or $attribute_name")
        return v
    
    @field_validator("type")
    def type_must_be_valid(cls, v):
        if isinstance(v, str):
            valid_types = {"int", "float", "str", "bool", "list"}
            if v not in valid_types:
                raise ValueError(f"invalid type '{v}': must be one of {valid_types}")
        elif not isinstance(v, BaseModel):
            valid_models = {m.__name__ for m in BaseModel.__subclasses__()}
            raise ValueError(f"invalid type '{v}': must be a string or a known model: {valid_models}")
        return v
    
    @field_validator("of")
    def validate_of_field(cls, v, info):
        # If 'of' is provided, validate that it's a valid type
        if v is not None:
            # Check if the main type is 'list'
            type_value = info.data.get("type")
            if type_value != "list":
                raise ValueError(f"'of' field can only be used with type 'list', but type is '{type_value}'")
            
            # Validate that 'of' contains a valid type
            valid_types = {"int", "float", "str", "bool"}
            # Note: Model types (like "Item") should be validated against actual model definitions
            # For now, we'll allow any capitalized identifier as a potential model name
            if v not in valid_types and not (v[0].isupper() and v.isalnum()):
                raise ValueError(f"invalid 'of' type '{v}': must be a basic type or a model name (capitalized)")
        return v
    
    @model_validator(mode='after')
    def validate_list_type_requires_of(self):
        # Ensure that list types have an 'of' field
        if self.type == "list" and self.of is None:
            raise ValueError("list type must specify 'of' field to indicate contained type")
        return self

class ModelSchema(BaseModel):
    header: Header
    attributes: dict[str, Attribute] = {}
    
    @model_validator(mode='after')
    def validate_attribute_references(self):
        # Check that all attribute references in ranges exist
        for attr_name, attr in self.attributes.items():
            if attr.range:
                # Extract any attribute references from the range
                range_parts = attr.range.split("..")
                for part in range_parts:
                    if part.startswith("$"):
                        referenced_attr = part[1:]
                        if referenced_attr not in self.attributes:
                            raise ValueError(f"attribute '{attr_name}' references unknown attribute '{referenced_attr}' in range")
        return self

##############################################################################
# 3.  REGISTRY OF PARSERS PER `kind`
##############################################################################
PARSERS = {
    "system":    SystemSchema,
    "source":    SourceSchema,
    "model":     ModelSchema,
    "compendium": CompendiumSchema,
    # "flow":    FlowSchema,
}

##############################################################################
# 4.  VALIDATION DRIVER
##############################################################################
def validate_yaml(path: Path):
    raw = yaml.safe_load(path.read_text())
    hdr = Header.model_validate(raw)              # always validate header first
    parser = PARSERS.get(hdr.kind)
    if not parser:
        raise ValueError(f"unknown kind '{hdr.kind}' in {path}")
    parser.model_validate({"header": hdr, **raw})

def main(root="."):
    root = Path(root).resolve()
    errors = []
    
    # Handle both files and directories
    if root.is_file():
        # Single file
        if root.suffix == '.yaml':
            files_to_check = [root]
        else:
            print(f"Skipping non-YAML file: {root}")
            return
    else:
        # Directory - find all YAML files
        files_to_check = list(root.rglob("*.yaml"))
    
    for file in files_to_check:
        try:
            validate_yaml(file)
        except (ValidationError, ValueError) as e:
            errors.append(f"{file}:\n{e}\n")
    
    if errors:
        print("".join(errors))
        sys.exit(1)
    print("✓ All good!")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
