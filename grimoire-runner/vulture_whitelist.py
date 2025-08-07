# Vulture whitelist for GRIMOIRE engine
# These are intentionally "unused" items that shouldn't be flagged

# Model dataclass fields (used in data structures)
of = None
optional = None
message = None
symbol = None
base_unit = None
author = None
license = None
publisher = None
source_url = None
edition = None
timestamp = None
max_tokens = None
temperature = None
completed_at_step = None
reset_outputs = None

# Step type constants (used for validation)
DICE_ROLL = None
DICE_SEQUENCE = None
PLAYER_CHOICE = None
TABLE_ROLL = None
LLM_GENERATION = None
COMPLETION = None
FLOW_CALL = None

# Observable attributes (used by reactive system)
derived_fields = None

# CLI entry points (may be called externally)
def browse(): pass
def interactive(): pass

# Template methods (used in template rendering)
def get_source(): pass
