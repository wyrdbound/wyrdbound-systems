"""
Tests for the GRIMOIRE SystemLoader.
"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.models.flow import StepType
from grimoire_runner.models.system import System


class TestSystemLoader:
    """Test the SystemLoader class."""

    def setup_method(self):
        """Set up each test."""
        self.loader = SystemLoader()

    def create_minimal_system(self, temp_dir, system_id="test_system"):
        """Create a minimal valid system for testing."""
        system_path = Path(temp_dir) / system_id
        system_path.mkdir()

        # Create system.yaml
        system_data = {
            "id": system_id,
            "name": "Test System",
            "version": "1.0.0",
            "description": "A test system",
            "currency": {
                "base_unit": "gold",
                "denominations": {
                    "copper": {"name": "Copper", "symbol": "cp", "value": 1},
                    "silver": {"name": "Silver", "symbol": "sp", "value": 10},
                    "gold": {"name": "Gold", "symbol": "gp", "value": 100},
                },
            },
        }

        with open(system_path / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create required directories
        for subdir in ["flows", "models", "compendium", "tables", "sources"]:
            (system_path / subdir).mkdir()

        return system_path

    def create_system_with_flows(self, temp_dir, system_id="flow_system"):
        """Create a system with flows for testing."""
        system_path = Path(temp_dir) / system_id
        system_path.mkdir()

        # Create system.yaml
        system_data = {
            "id": system_id,
            "name": "Flow Test System",
            "version": "1.0.0",
            "description": "A system with flows",
            "currency": {
                "base_unit": "gold",
                "denominations": {
                    "gold": {"name": "Gold", "symbol": "gp", "value": 100}
                },
            },
        }

        with open(system_path / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create flows directory
        flows_dir = system_path / "flows"
        flows_dir.mkdir()

        # Create a simple test flow
        simple_flow_data = {
            "id": "simple_flow",
            "name": "Simple Test Flow",
            "description": "A simple test flow",
            "variables": {"test_var": "test_value"},
            "steps": [
                {
                    "id": "step1",
                    "type": "dice_roll",
                    "name": "Roll dice",
                    "roll": "1d6",
                    "output": "result",
                }
            ],
        }

        with open(flows_dir / "simple_flow.yaml", "w") as f:
            yaml.dump(simple_flow_data, f)

        # Create a complex test flow
        complex_flow_data = {
            "id": "complex_flow",
            "name": "Complex Test Flow",
            "description": "A complex test flow",
            "steps": [
                {
                    "id": "step1",
                    "type": "dice_roll",
                    "name": "Roll dice",
                    "roll": "1d6",
                    "output": "result",
                },
                {
                    "id": "step2",
                    "type": "player_choice",
                    "name": "Make choice",
                    "choices": [
                        {"id": "choice_a", "label": "Option A"},
                        {"id": "choice_b", "label": "Option B"},
                    ],
                },
            ],
        }

        with open(flows_dir / "complex_flow.yaml", "w") as f:
            yaml.dump(complex_flow_data, f)

        return system_path

    def create_system_with_tables(self, temp_dir, system_id="table_system"):
        """Create a system with tables for testing."""
        system_path = Path(temp_dir) / system_id
        system_path.mkdir()

        # Create system.yaml
        system_data = {
            "id": system_id,
            "name": "Table Test System",
            "version": "1.0.0",
            "description": "A system with tables",
            "currency": {
                "base_unit": "gold",
                "denominations": {
                    "gold": {"name": "Gold", "symbol": "gp", "value": 100}
                },
            },
        }

        with open(system_path / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create tables directory
        tables_dir = system_path / "tables"
        tables_dir.mkdir()

        # Create a test table
        table_data = {
            "id": "test_table",
            "name": "Test Table",
            "kind": "table",
            "description": "A test table",
            "roll": "1d6",
            "entries": {
                1: "First result",
                2: "First result",
                3: "Second result",
                4: "Second result",
                5: "Third result",
                6: "Third result",
            },
        }

        with open(tables_dir / "test_table.yaml", "w") as f:
            yaml.dump(table_data, f)

        return system_path

    def create_system_with_models(self, temp_dir, system_id="model_system"):
        """Create a system with models for testing."""
        system_path = Path(temp_dir) / system_id
        system_path.mkdir()

        # Create system.yaml
        system_data = {
            "id": system_id,
            "name": "Model Test System",
            "version": "1.0.0",
            "description": "A system with models",
            "currency": {
                "base_unit": "gold",
                "denominations": {
                    "gold": {"name": "Gold", "symbol": "gp", "value": 100}
                },
            },
        }

        with open(system_path / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create models directory
        models_dir = system_path / "models"
        models_dir.mkdir()

        # Create a model with attributes structure
        model_file = models_dir / "character.yaml"
        model_file.write_text(
            yaml.dump(
                {
                    "id": "character",
                    "name": "Character",
                    "kind": "model",
                    "description": "A character model",
                    "attributes": {
                        "name": {"type": "str", "required": True},
                        "level": {"type": "int", "default": 1},
                    },
                }
            )
        )

        return system_path

    def create_corrupted_system(self, temp_dir: str) -> Path:
        """Create a corrupted system for error testing."""
        system_dir = Path(temp_dir) / "corrupted_system"
        system_dir.mkdir()

        # Create invalid system.yaml
        with open(system_dir / "system.yaml", "w") as f:
            f.write("invalid: yaml: content: {{{")

        return system_dir

    def test_loader_initialization(self):
        """Test that SystemLoader initializes correctly."""
        assert isinstance(self.loader._loaded_systems, dict)
        assert len(self.loader._loaded_systems) == 0

    def test_load_minimal_system(self):
        """Test loading a minimal valid system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_minimal_system(temp_dir)

            system = self.loader.load_system(system_path)

            assert isinstance(system, System)
            assert system.id == "test_system"
            assert system.name == "Test System"
            assert system.version == "1.0.0"
            assert system.description == "A test system"
            assert hasattr(system, "currency")
            assert system.currency.base_unit == "gold"
            assert len(system.currency.denominations) == 3

    def test_load_system_with_flows(self):
        """Test loading a system with flows."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_system_with_flows(temp_dir)

            system = self.loader.load_system(system_path)

            assert len(system.flows) == 2

            # Test simple flow
            simple_flow = system.get_flow("simple_flow")
            assert simple_flow is not None
            assert simple_flow.name == "Simple Test Flow"
            assert simple_flow.variables["test_var"] == "test_value"
            assert len(simple_flow.steps) == 1
            assert simple_flow.steps[0].type == StepType.DICE_ROLL

            # Test complex flow
            complex_flow = system.get_flow("complex_flow")
            assert complex_flow is not None
            assert len(complex_flow.steps) == 2
            assert complex_flow.steps[0].type == StepType.DICE_ROLL
            assert complex_flow.steps[1].type == StepType.PLAYER_CHOICE

    def test_load_system_with_tables(self):
        """Test loading a system with tables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_system_with_tables(temp_dir)

            system = self.loader.load_system(system_path)

            assert len(system.tables) == 1

            table = system.get_table("test_table")
            assert table is not None
            assert table.name == "Test Table"
            assert table.roll == "1d6"
            assert len(table.entries) == 6

    def test_load_system_with_models(self):
        """Test loading a system with models."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_system_with_models(temp_dir)

            system = self.loader.load_system(system_path)

            assert len(system.models) == 1

            model = system.get_model("character")
            assert model is not None
            assert model.name == "Character"
            assert len(model.attributes) == 2
            assert "name" in model.attributes
            assert "level" in model.attributes
            assert model.attributes["name"].type == "str"
            assert model.attributes["level"].type == "int"

    def test_load_nonexistent_system(self):
        """Test loading a system that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            self.loader.load_system("/nonexistent/path")

    def test_load_system_file_instead_of_directory(self):
        """Test loading a file instead of a directory."""
        with tempfile.NamedTemporaryFile(suffix=".yaml") as temp_file:
            with pytest.raises(ValueError, match="System path must be a directory"):
                self.loader.load_system(temp_file.name)

    def test_load_system_without_system_yaml(self):
        """Test loading a directory without system.yaml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "no_system_yaml"
            system_dir.mkdir()

            with pytest.raises(FileNotFoundError, match="system.yaml not found"):
                self.loader.load_system(system_dir)

    def test_load_corrupted_system_yaml(self):
        """Test loading a system with corrupted YAML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_corrupted_system(temp_dir)

            with pytest.raises(yaml.YAMLError):
                self.loader.load_system(system_path)

    def test_system_caching(self):
        """Test that systems are cached and not reloaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_minimal_system(temp_dir)

            # Load system first time
            system1 = self.loader.load_system(system_path)

            # Load system second time (should be cached)
            system2 = self.loader.load_system(system_path)

            assert system1 is system2  # Same object reference
            assert len(self.loader._loaded_systems) == 1

    def test_list_loaded_systems(self):
        """Test listing loaded systems."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path1 = self.create_minimal_system(temp_dir, "system1")
            system_path2 = self.create_minimal_system(temp_dir, "system2")

            # Initially no systems loaded
            assert len(self.loader.list_loaded_systems()) == 0

            # Load first system
            self.loader.load_system(system_path1)
            loaded = self.loader.list_loaded_systems()
            assert len(loaded) == 1
            assert "system1" in loaded

            # Load second system
            self.loader.load_system(system_path2)
            loaded = self.loader.list_loaded_systems()
            assert len(loaded) == 2
            assert "system1" in loaded
            assert "system2" in loaded

    def test_system_access_after_loading(self):
        """Test accessing a loaded system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_minimal_system(temp_dir)

            # Load system
            system = self.loader.load_system(system_path)

            # Check that it's in the loaded systems list
            loaded_systems = self.loader.list_loaded_systems()
            assert "test_system" in loaded_systems
            assert len(loaded_systems) == 1

    def test_load_system_missing_required_field(self):
        """Test loading a system with missing required fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "incomplete_system"
            system_dir.mkdir()

            # Create system.yaml without required field
            system_data = {
                "name": "Incomplete System",
                # Missing 'id' and 'version'
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            with pytest.raises((KeyError, ValueError)):
                self.loader.load_system(system_dir)

    @pytest.mark.parametrize(
        "invalid_content",
        [
            "",  # Empty file
            "just text",  # Not YAML
            "key: value\ninvalid_yaml: {",  # Partial YAML
            "list:\n  - item1\n  invalid: {",  # Mixed valid/invalid
        ],
    )
    def test_load_system_invalid_yaml_formats(self, invalid_content):
        """Test loading systems with various invalid YAML formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "invalid_system"
            system_dir.mkdir()

            with open(system_dir / "system.yaml", "w") as f:
                f.write(invalid_content)

            with pytest.raises((yaml.YAMLError, ValueError, KeyError, TypeError)):
                self.loader.load_system(system_dir)

    def test_load_system_with_subdirectory_flows(self):
        """Test loading flows from subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_minimal_system(temp_dir)

            # Create subdirectory in flows
            flows_subdir = system_dir / "flows" / "character"
            flows_subdir.mkdir(parents=True)

            # Create flow in subdirectory
            flow_data = {
                "id": "character_creation",
                "name": "Character Creation",
                "description": "Create a character",
                "steps": [
                    {
                        "id": "name_step",
                        "name": "Choose Name",
                        "type": "player_choice",
                        "prompt": "Enter character name:",
                        "choices": [{"id": "custom", "label": "Enter custom name"}],
                    }
                ],
            }

            with open(flows_subdir / "character_creation.yaml", "w") as f:
                yaml.dump(flow_data, f)

            system = self.loader.load_system(system_dir)

            # Should find flow in subdirectory
            flow = system.get_flow("character_creation")
            assert flow is not None
            assert flow.name == "Character Creation"

    def test_template_resolution_in_system(self):
        """Test that templates are resolved in system loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_minimal_system(temp_dir)

            # Create flow with template
            flows_dir = system_dir / "flows"
            flow_data = {
                "id": "template_flow",
                "name": "Flow for {{ system.name }}",
                "description": "This flow is for the {{ system.name }} system",
                "steps": [
                    {
                        "id": "template_step",
                        "name": "Step in {{ system.name }}",
                        "type": "dice_roll",
                        "roll": "1d6",
                    }
                ],
            }

            with open(flows_dir / "template_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            system = self.loader.load_system(system_dir)
            flow = system.get_flow("template_flow")

            # Templates should be resolved
            assert flow.name == "Flow for Test System"
            assert flow.description == "This flow is for the Test System system"
            assert flow.steps[0].name == "Step in Test System"


class TestSystemLoaderEdgeCases:
    """Test edge cases and error conditions for SystemLoader."""

    def setup_method(self):
        """Set up each test."""
        self.loader = SystemLoader()

    def test_load_system_with_circular_references(self):
        """Test handling of circular references in flows."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "circular_system"
            system_dir.mkdir()

            # Create system.yaml
            system_data = {
                "id": "circular_system",
                "name": "Circular System",
                "version": "1.0.0",
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create required directories
            flows_dir = system_dir / "flows"
            flows_dir.mkdir()

            # Create flows with circular references
            flow_a = {
                "id": "flow_a",
                "name": "Flow A",
                "steps": [
                    {
                        "id": "call_b",
                        "name": "Call Flow B",
                        "type": "flow_call",
                        "flow": "flow_b",
                    }
                ],
            }

            flow_b = {
                "id": "flow_b",
                "name": "Flow B",
                "steps": [
                    {
                        "id": "call_a",
                        "name": "Call Flow A",
                        "type": "flow_call",
                        "flow": "flow_a",
                    }
                ],
            }

            with open(flows_dir / "flow_a.yaml", "w") as f:
                yaml.dump(flow_a, f)

            with open(flows_dir / "flow_b.yaml", "w") as f:
                yaml.dump(flow_b, f)

            # Should load without error (circular detection happens at execution)
            system = self.loader.load_system(system_dir)
            assert len(system.flows) == 2

    def test_load_system_with_unicode_content(self):
        """Test loading system with Unicode content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "unicode_system"
            system_dir.mkdir()

            # Create system with Unicode content
            system_data = {
                "id": "unicode_system",
                "name": "系统 with émojis 🎮",
                "version": "1.0.0",
                "description": "ñáéíóú русский العربية 中文",
            }

            with open(system_dir / "system.yaml", "w", encoding="utf-8") as f:
                yaml.dump(system_data, f, allow_unicode=True)

            # Create directories
            for subdir in ["flows", "models", "compendium", "tables", "sources"]:
                (system_dir / subdir).mkdir()

            system = self.loader.load_system(system_dir)

            assert system.name == "系统 with émojis 🎮"
            assert "ñáéíóú" in system.description
            assert "русский" in system.description
            assert "العربية" in system.description
            assert "中文" in system.description

    def test_load_system_with_very_large_files(self):
        """Test loading system with large files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "large_system"
            system_dir.mkdir()

            # Create minimal system
            system_data = {
                "id": "large_system",
                "name": "Large System",
                "version": "1.0.0",
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create directories
            flows_dir = system_dir / "flows"
            flows_dir.mkdir()

            # Create flow with many steps
            large_flow = {
                "id": "large_flow",
                "name": "Large Flow",
                "description": "A flow with many steps",
                "steps": [],
            }

            # Add 1000 steps
            for i in range(1000):
                large_flow["steps"].append(
                    {
                        "id": f"step_{i}",
                        "name": f"Step {i}",
                        "type": "dice_roll",
                        "roll": "1d6",
                        "output": f"result_{i}",
                    }
                )

            with open(flows_dir / "large_flow.yaml", "w") as f:
                yaml.dump(large_flow, f)

            # Should load successfully
            system = self.loader.load_system(system_dir)
            flow = system.get_flow("large_flow")
            assert len(flow.steps) == 1000

    def test_load_system_with_permission_errors(self):
        """Test handling of permission errors."""
        # Skip on Windows where permission handling is different
        import platform

        if platform.system() == "Windows":
            pytest.skip("Permission tests not applicable on Windows")

        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "permission_system"
            system_dir.mkdir()

            # Create system.yaml with no read permission
            system_file = system_dir / "system.yaml"
            system_file.write_text("id: test\nname: Test\nversion: 1.0.0")
            system_file.chmod(0o000)  # No permissions

            try:
                with pytest.raises(PermissionError):
                    self.loader.load_system(system_dir)
            finally:
                # Restore permissions for cleanup
                system_file.chmod(0o644)


class TestSystemLoaderPerformance:
    """Test SystemLoader performance characteristics."""

    def setup_method(self):
        """Set up each test."""
        self.loader = SystemLoader()

    def test_load_multiple_systems_performance(self):
        """Test loading multiple systems performance."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            system_paths = []

            # Create 10 systems
            for i in range(10):
                system_dir = Path(temp_dir) / f"system_{i}"
                system_dir.mkdir()

                system_data = {
                    "id": f"system_{i}",
                    "name": f"System {i}",
                    "version": "1.0.0",
                }

                with open(system_dir / "system.yaml", "w") as f:
                    yaml.dump(system_data, f)

                # Create directories
                for subdir in ["flows", "models", "compendium", "tables", "sources"]:
                    (system_dir / subdir).mkdir()

                system_paths.append(system_dir)

            # Time loading all systems
            start_time = time.time()

            for system_path in system_paths:
                self.loader.load_system(system_path)

            load_time = time.time() - start_time

            assert len(self.loader._loaded_systems) == 10
            assert load_time < 5.0  # Should load 10 systems in under 5 seconds

    def test_cache_performance(self):
        """Test that caching improves performance."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "cache_test_system"
            system_dir.mkdir()

            system_data = {
                "id": "cache_test_system",
                "name": "Cache Test System",
                "version": "1.0.0",
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create directories
            for subdir in ["flows", "models", "compendium", "tables", "sources"]:
                (system_dir / subdir).mkdir()

            # Time first load
            start_time = time.time()
            system1 = self.loader.load_system(system_dir)
            first_load_time = time.time() - start_time

            # Time second load (cached)
            start_time = time.time()
            system2 = self.loader.load_system(system_dir)
            second_load_time = time.time() - start_time

            assert system1 is system2  # Same object
            assert second_load_time < first_load_time  # Cached should be faster


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
